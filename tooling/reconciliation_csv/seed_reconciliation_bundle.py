"""Local reconciliation phase 1: private evidence, source mapping and strategy.

This is not the financial posting phase. No bookings, flows, balances, prices or
rights are inferred from possession of CSV files. Explicit --bonds approval
creates only consistent zero-coupon instrument definitions via normal services.
Run without --apply for a read-only preflight. Source files remain outside Git.
"""
import argparse
from datetime import date,datetime,timezone
from hashlib import sha256
import json
from pathlib import Path
import sys
from uuid import UUID

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from tooling.reconciliation_csv.reconciliation import load_bundle,retain_files


def strategy_code(bundle):
    return f'RECON_{bundle.name}'


def apply_foundation(c,bundle,tenant,actor,evidence_dir):
    """Caller owns transaction. Recheck authority on every call, including replay."""
    from sqlalchemy import select,func
    from security_master_schema import models as m
    from security_master_schema.reference_authority import require_reference_action
    from security_master_schema.tenant_workspace import require_tenant_action,resolve_tenant_workspace
    from security_master_schema.strategy_access import require_strategy_action
    from security_master_schema.governance_clock import governance_date
    from security_master_schema.access_management import audit
    from apps.reference_api.repository import create_strategy
    from apps.reference_api.contracts import StrategyCreateRequest
    require_reference_action(c,tenant,actor)
    workspace=resolve_tenant_workspace(c,tenant,actor,governance_date())
    require_tenant_action(workspace,'TRADE_WRITE')
    code=strategy_code(bundle)
    source_code='RECON_'+tenant.hex+'_'+sha256(bundle.name.encode()).hexdigest()[:24]
    # Serialize the entire source scope, not just this delivery, so changed
    # bundle hashes cannot race to provision the same strategy or namespace.
    lock=int.from_bytes(sha256(source_code.encode()).digest()[:8],'big',signed=True)
    c.execute(select(func.pg_advisory_xact_lock(lock)))
    existing=c.execute(select(m.strategy).where(m.strategy.c.tenant_id==tenant,m.strategy.c.strategy_code==code)).mappings().one_or_none()
    source=c.execute(select(m.integration_source_system).where(m.integration_source_system.c.system_code==source_code)).mappings().one_or_none()
    if existing and not source:raise ValueError('Unowned strategy code; refusing adoption')
    if source and (source['tenant_id']!=tenant or source['status']!='ACTIVE' or source['source_kind']!='CLIENT_PMS'):
        raise ValueError('Source ownership or lifecycle differs')
    if existing:
        prior=c.execute(select(m.external_object_mapping).join(m.external_id_namespace).where(
            m.external_id_namespace.c.integration_source_system_id==source['integration_source_system_id'],
            m.external_id_namespace.c.namespace_code==source_code+'_STRATEGY',
            m.external_object_mapping.c.external_id_value==bundle.manifest['sourceStrategyId'])).mappings().all()
        if len(prior)!=1 or prior[0]['tenant_id']!=tenant or prior[0]['target_object_id']!=existing['strategy_id'] or prior[0]['target_object_type']!='STRATEGY' or prior[0]['status']!='VERIFIED':
            raise ValueError('Unowned strategy source identity; refusing adoption')
        require_strategy_action(c,tenant,actor,'STRATEGY_WRITE',existing['strategy_id'])
        require_strategy_action(c,tenant,actor,'TRADE_WRITE',existing['strategy_id'])
    else:require_tenant_action(workspace,'STRATEGY_CREATE')
    currency_ids={}
    for code_currency in bundle.manifest['requiredCurrencies']:
        row=c.execute(select(m.currency).where(m.currency.c.currency_code==code_currency)).mappings().one_or_none()
        if row is None and code_currency=='SGD':
            currency_ids[code_currency]=c.scalar(m.currency.insert().values(currency_code='SGD',display_name='Singapore dollar',
                numeric_code='702',minor_unit=2,currency_kind='FIAT',status='ACTIVE').returning(m.currency.c.currency_id))
            audit(c,actor,tenant,'RECONCILIATION_CURRENCY_CREATED',dict(currency='SGD',reason='Owner authorized legacy cash-balance currency reference'))
        elif row is None or row['status']!='ACTIVE' or row['currency_kind']!='FIAT':
            raise ValueError('Required active fiat currency unavailable: '+code_currency)
        else:currency_ids[code_currency]=row['currency_id']
    start=date.fromisoformat(bundle.manifest['earliestTradeDate'])
    if not source:
        source_id=c.scalar(m.integration_source_system.insert().values(tenant_id=tenant,system_code=source_code,
            display_name='Private reconciliation export — '+bundle.name,source_kind='CLIENT_PMS',environment='SANDBOX',status='ACTIVE')
            .returning(m.integration_source_system.c.integration_source_system_id))
    else:source_id=source['integration_source_system_id']
    namespace=c.execute(select(m.external_id_namespace).where(m.external_id_namespace.c.namespace_code==source_code+'_STRATEGY')).mappings().one_or_none()
    if namespace:
        if namespace['integration_source_system_id']!=source_id or namespace['status']!='ACTIVE' or namespace['external_object_type']!='STRATEGY':
            raise ValueError('Unexpected strategy namespace')
        namespace_id=namespace['external_id_namespace_id']
    else:
        namespace_id=c.scalar(m.external_id_namespace.insert().values(integration_source_system_id=source_id,
            namespace_code=source_code+'_STRATEGY',external_object_type='STRATEGY',valid_from=start,
            description='Tenant-local source strategy IDs; not instrument or counterparty identity').returning(m.external_id_namespace.c.external_id_namespace_id))
    if existing:
        sid=existing['strategy_id']
        if existing['strategy_type']!='FUND' or existing['base_currency_id']!=currency_ids[bundle.manifest['baseCurrency']] or existing['status']!='ACTIVE' or existing['effective_from']>start:
            raise ValueError('Existing reconciliation strategy differs')
    else:
        view=create_strategy(c,tenant,actor,StrategyCreateRequest(strategyCode=code,
            displayName=bundle.name+' — imported reconciliation',strategyType='FUND',baseCurrencyCode=bundle.manifest['baseCurrency']))
        sid=view.strategy_id
        # Only this newly created, empty strategy receives the observed historical
        # start. Existing strategies, reference histories and receipts are untouched.
        c.execute(m.strategy.update().where(m.strategy.c.strategy_id==sid,m.strategy.c.tenant_id==tenant).values(effective_from=start))
    require_strategy_action(c,tenant,actor,'STRATEGY_WRITE',sid)
    require_strategy_action(c,tenant,actor,'TRADE_WRITE',sid)
    retained=retain_files(bundle,evidence_dir)
    payload_ids={}
    for kind,path in retained.items():
        content=path.read_bytes();digest=sha256(content).hexdigest();reference=bundle.digest+':'+kind
        previous=c.execute(select(m.source_payload).where(m.source_payload.c.integration_source_system_id==source_id,
            m.source_payload.c.tenant_id==tenant,m.source_payload.c.external_message_reference==reference)).mappings().one_or_none()
        if previous:
            if previous['payload_sha256']!=digest or previous['payload_locator']!=path.as_uri():raise ValueError('Retained receipt differs')
            payload_ids[kind]=previous['source_payload_id']
        else:
            payload_ids[kind]=c.scalar(m.source_payload.insert().values(integration_source_system_id=source_id,tenant_id=tenant,
                payload_format='JSON' if kind=='manifest' else 'CSV',external_message_reference=reference,
                payload_locator=path.as_uri(),payload_sha256=digest,processing_status='RECEIVED').returning(m.source_payload.c.source_payload_id))
    mapping=c.execute(select(m.external_object_mapping).where(m.external_object_mapping.c.external_id_namespace_id==namespace_id,
        m.external_object_mapping.c.external_id_value==bundle.manifest['sourceStrategyId'])).mappings().all()
    if mapping:
        if len(mapping)!=1 or mapping[0]['tenant_id']!=tenant or mapping[0]['target_object_id']!=sid or mapping[0]['target_object_type']!='STRATEGY' or mapping[0]['status']!='VERIFIED':
            raise ValueError('Strategy source identity already maps elsewhere')
    else:
        c.execute(m.external_object_mapping.insert().values(external_id_namespace_id=namespace_id,external_object_type='STRATEGY',
            external_id_value=bundle.manifest['sourceStrategyId'],tenant_id=tenant,target_object_type='STRATEGY',target_object_id=sid,
            mapping_role='SOURCE_REFERENCE',mapping_method='CLIENT_CONFIRMED',status='VERIFIED',verified_by_user_account_id=actor,
            verified_at_utc=datetime.now(timezone.utc),valid_from=start,source_payload_id=payload_ids['strategy_info']))
    event='RECONCILIATION_BUNDLE_RETAINED'
    if not c.scalar(select(m.access_audit_event.c.event_id).where(m.access_audit_event.c.tenant_id==tenant,
        m.access_audit_event.c.action==event,m.access_audit_event.c.details['bundleHash'].as_string()==bundle.digest)):
        audit(c,actor,tenant,event,dict(bundleHash=bundle.digest,strategyId=str(sid),sourceId=str(source_id),
            sourcePayloadIds={k:str(v) for k,v in payload_ids.items()},phase='SOURCE_AND_STRATEGY_ONLY',
            effectiveFrom=str(start),financialPostingStatus='NOT_POSTED'))
    return dict(strategyId=sid,sourceId=source_id,namespaceId=namespace_id,bundleHash=bundle.digest,
        receipts=len(payload_ids),financialPostingStatus='NOT_POSTED')


def apply_confirmed_company(c,bundle,tenant,actor,foundation,company_id,label,*,confirmed=True):
    """Operational source alias only: a user label is not a verified legal entity."""
    from sqlalchemy import select,func
    from security_master_schema import models as m
    from security_master_schema.reference_authority import require_reference_action
    from security_master_schema.strategy_access import require_strategy_action
    from security_master_schema.access_management import audit
    from tooling.reconciliation_csv.reconciliation import source_id
    from apps.reference_api.tenant_organisations import save_organisation,policies
    from uuid import uuid4
    require_reference_action(c,tenant,actor)
    require_strategy_action(c,tenant,actor,'STRATEGY_WRITE',foundation['strategyId'])
    company_id=source_id(company_id);label=label.strip()
    if company_id not in bundle.manifest['unmappedOrganisationIds']:raise ValueError('Company ID not present in the bundle')
    if not label or len(label)>250:raise ValueError('Use a nonempty company label of at most 250 characters')
    source=c.execute(select(m.integration_source_system).where(m.integration_source_system.c.integration_source_system_id==foundation['sourceId'],
        m.integration_source_system.c.tenant_id==tenant,m.integration_source_system.c.status=='ACTIVE')).mappings().one()
    if foundation['bundleHash']!=bundle.digest or not c.scalar(select(m.source_payload.c.source_payload_id).where(
        m.source_payload.c.integration_source_system_id==foundation['sourceId'],m.source_payload.c.tenant_id==tenant,
        m.source_payload.c.external_message_reference==bundle.digest+':manifest')):raise ValueError('Confirmed company needs the retained source bundle')
    code=source['system_code']+'_COMPANY';start=date.fromisoformat(bundle.manifest['earliestTradeDate'])
    c.execute(select(func.pg_advisory_xact_lock(int.from_bytes(sha256(code.encode()).digest()[:8],'big',signed=True))))
    ns=c.execute(select(m.external_id_namespace).where(m.external_id_namespace.c.namespace_code==code)).mappings().one_or_none()
    if ns:
        if ns['integration_source_system_id']!=foundation['sourceId'] or ns['status']!='ACTIVE':raise ValueError('Company namespace differs')
        namespace=ns['external_id_namespace_id']
    else:
        namespace=c.scalar(m.external_id_namespace.insert().values(integration_source_system_id=foundation['sourceId'],namespace_code=code,
            external_object_type='ORGANISATION',valid_from=start,description='Owner-confirmed operational company names; not legal-entity or LEI verification')
            .returning(m.external_id_namespace.c.external_id_namespace_id))
    old=c.execute(select(m.external_object_mapping).where(m.external_object_mapping.c.external_id_namespace_id==namespace,
        m.external_object_mapping.c.external_id_value==company_id)).mappings().all()
    if old:
        if len(old)!=1 or old[0]['tenant_id']!=tenant or old[0]['target_object_type']!='ORGANISATION' or old[0]['status']!='VERIFIED':raise ValueError('Company mapping differs')
        org=c.execute(select(m.organisation).where(m.organisation.c.organisation_id==old[0]['target_object_id'])).mappings().one()
        if org['display_name']!=label or org['status']!='ACTIVE':raise ValueError('Company label changed; explicit revision required')
        return org['organisation_id']
    identity='SRC_'+foundation['sourceId'].hex+'_COMPANY_'+company_id
    entity=c.scalar(m.entity.insert().values(entity_code=identity,display_name=label,status='ACTIVE').returning(m.entity.c.entity_id))
    organisation=c.scalar(m.organisation.insert().values(entity_id=entity,organisation_type='OPERATIONAL_REFERENCE',
        display_name=label,status='ACTIVE').returning(m.organisation.c.organisation_id))
    notes=('Owner-confirmed source company ' if confirmed else 'UNVERIFIED source company placeholder ')+company_id+'. Imported operational reference only; legal entity and LEI are not verified. '
    notes+='Reporting company does not identify each underlying third-party trading venue.'
    save_organisation(c,tenant,actor,organisation,dict(expectedVersion=0,expectedRoleVersions={r:v['versionNo'] for r,v in policies(c,tenant).items()},
            roles={},label=label,internalCode=identity,notes=notes,reason='Owner-authorized local reconciliation company mapping; no legal identity inference or eligibility-list change.',
        idempotencyKey=str(uuid4())))
    c.execute(m.external_object_mapping.insert().values(external_id_namespace_id=namespace,external_object_type='ORGANISATION',external_id_value=company_id,
        tenant_id=tenant,target_object_type='ORGANISATION',target_object_id=organisation,mapping_role='SOURCE_REFERENCE',mapping_method='CLIENT_CONFIRMED',
        status='VERIFIED',verified_by_user_account_id=actor,verified_at_utc=datetime.now(timezone.utc),valid_from=start))
    audit(c,actor,tenant,'RECONCILIATION_COMPANY_CONFIRMED',dict(sourceCompanyId=company_id,sourceId=str(foundation['sourceId']),
        organisationId=str(organisation),label=label,ownerConfirmedLabel=confirmed,legalEntityVerified=False,leiInferred=False,eligibilityChanged=False))
    return organisation


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-dir',type=Path,required=True)
    parser.add_argument('--fund',default='FCAGF');parser.add_argument('--as-of',type=date.fromisoformat,required=True)
    parser.add_argument('--tenant',type=UUID,default=UUID('00000000-0000-7000-8000-000000000011'))
    parser.add_argument('--actor',type=UUID,default=UUID('00000000-0000-7000-8000-000000000083'))
    parser.add_argument('--apply',action='store_true')
    parser.add_argument('--bonds',choices=('stage','approve-ready'),help='Prepare bond proposals; approve-ready also materializes unambiguous zero-coupon definitions, never trades')
    parser.add_argument('--review-dmo-gilts',action='store_true',help='Append/approve ISIN-bound researched DMO gilt terms, retaining superseded requests')
    parser.add_argument('--products',action='store_true',help='Create private indices/rate references and complete swaps with owner-authorized mockup terms; no bookings')
    parser.add_argument('--additional',action='store_true',help='Create native AMC and source-normalized SPX option; retain the mistaken ETI rejection and source evidence; no bookings')
    parser.add_argument('--book-positions',action='store_true',help='Post supported source investment trades via native writers; retain per-row failures, exact originals and authorized 12-decimal truncation')
    parser.add_argument('--book-bonds',action='store_true',help='Complete source-bound UK penny-nominal bond metadata and book CLEAN bond executions through the native writer')
    parser.add_argument('--book-spx-option',action='store_true',help='Book owner-confirmed source option 20265 as standard contracts: source quantity /100 and multiplier 100')
    parser.add_argument('--cash-balances',action='store_true',help='Upload exact-date cash snapshots through native revision writer, preserving agent/wash account separation')
    parser.add_argument('--forwards',action='store_true',help='Post the two owner-confirmed FCAGF USD-quantity/GBP-quote forwards through native approval/booking')
    parser.add_argument('--daily-interest',action='store_true',help='Aggregate supplied trade-level daily earnings once per bond/date/currency through the native accrual writer; no balance fabrication')
    parser.add_argument('--reset-flows',action='store_true',help='Post only RESET rows with explicit mapped private swap references as dated income, not cumulative positions or payment confirmations')
    parser.add_argument('--fx-rates',action='store_true',help='Import the selected 15 fiat currencies and direct source cross-rates into a private inspection dataset; no fixing or valuation-rights inference')
    parser.add_argument('--fx-operator',type=UUID,help='Explicit personal operator organisation for the owner-supplied local FX file; not inferred from tenant ownership')
    parser.add_argument('--market-prices',action='store_true',help='Import source market quotes into a separate private dataset using audited native mappings and explicit quote dimensions')
    parser.add_argument('--prices-operator',type=UUID,help='Explicit personal operator organisation for the supplied private price file; not an inferred upstream provider')
    parser.add_argument('--property',action='append',default=[],metavar='CODE=VALUE',help='Explicit tenant custom-field mapping for reconciliation trades, retained as an operator assumption')
    parser.add_argument('--confirmed-company',action='append',default=[],metavar='ID=NAME',help='Explicit owner-supplied operational company label; no guessed legal identifiers')
    args=parser.parse_args()
    if args.fx_rates and args.fx_operator is None:parser.error('--fx-rates requires an explicit --fx-operator organisation')
    if args.market_prices and args.prices_operator is None:parser.error('--market-prices requires an explicit --prices-operator organisation')
    # These are the owner's explicit source-record rulings, not global heuristics.
    excluded={'202610200000-J2508747'} if args.fund=='FCAGF' else set()
    amcs={'1857'} if args.fund=='FCAGF' else set()
    bundle=load_bundle(args.source_dir,args.fund,args.as_of,excluded_trade_ids=excluded,amc_ids=amcs)
    print(json.dumps(dict(mode='APPLY' if args.apply else 'READ_ONLY_PREFLIGHT',bundleHash=bundle.digest,**bundle.manifest)),flush=True)
    if not args.apply:return
    from sqlalchemy import create_engine
    from apps.reference_api.config import Settings
    from security_master_schema.database_config import local_workspace_database
    settings=Settings.from_environment();engine=create_engine(settings.database_url,pool_pre_ping=True)
    if settings.environment!='local' or engine.url.host not in ('localhost','127.0.0.1') or engine.url.port!=15432 or engine.url.database!=local_workspace_database():
        raise ValueError('Only the explicitly named local operating database is allowed')
    try:
        with engine.begin() as c:
            result=apply_foundation(c,bundle,args.tenant,args.actor,ROOT/'logs'/'reconciliation'/str(args.tenant))
            companies={}
            for entry in args.confirmed_company:
                identifier,separator,label=entry.partition('=')
                if not separator:raise ValueError('Company confirmation must be ID=NAME')
                companies[identifier]=apply_confirmed_company(c,bundle,args.tenant,args.actor,result,identifier,label)
            if companies:result['confirmedCompanyIds']=companies
            if args.bonds:
                from tooling.reconciliation_csv.reconciliation_bonds import stage_bonds
                result['bonds']=stage_bonds(c,bundle,args.tenant,args.actor,result,approve_ready=args.bonds=='approve-ready')
            if args.review_dmo_gilts:
                from tooling.reconciliation_csv.reconciliation_bonds import approve_reviewed_gilts
                result['reviewedGilts']=approve_reviewed_gilts(c,bundle,args.tenant,args.actor,result)
            if args.products:
                from tooling.reconciliation_csv.reconciliation_products import seed_products
                result['products']=seed_products(c,bundle,args.tenant,args.actor,result)
            if args.additional:
                from tooling.reconciliation_csv.reconciliation_products import seed_additional
                result['additional']=seed_additional(c,bundle,args.tenant,args.actor,result)
            if args.book_positions:
                from tooling.reconciliation_csv.reconciliation_postings import prepare_position_metadata,post_positions
                properties={}
                for entry in args.property:
                    code,separator,value=entry.partition('=')
                    if not separator or code in properties:raise ValueError('Use distinct property CODE=VALUE mappings')
                    properties[code]=value
                nodes,parties=prepare_position_metadata(c,bundle,args.tenant,args.actor,result)
                result['positionTrades']=post_positions(c,bundle,args.tenant,args.actor,result,nodes,parties,properties)
            if args.book_bonds:
                from tooling.reconciliation_csv.reconciliation_bond_postings import post_bonds
                properties={}
                for entry in args.property:
                    code,separator,value=entry.partition('=')
                    if not separator or code in properties:raise ValueError('Use distinct property CODE=VALUE mappings')
                    properties[code]=value
                result['bondTrades']=post_bonds(c,bundle,args.tenant,args.actor,result,properties)
            if args.book_spx_option:
                from tooling.reconciliation_csv.reconciliation_option import post_option
                properties={}
                for entry in args.property:
                    code,separator,value=entry.partition('=')
                    if not separator or code in properties:raise ValueError('Use distinct property CODE=VALUE mappings')
                    properties[code]=value
                result['optionTrade']=post_option(c,bundle,args.tenant,args.actor,result,properties)
            if args.cash_balances:
                from tooling.reconciliation_csv.reconciliation_cash import post_cash
                from tooling.reconciliation_csv.reconciliation import source_id
                cash_companies={}
                for company in sorted({source_id(r['counterparty_id']) for r in bundle.tables['cash_balances']}):
                    confirmed=args.fund=='FCAGF' and company=='21'
                    cash_companies[company]=apply_confirmed_company(c,bundle,args.tenant,args.actor,result,company,
                        'Northern Trust' if confirmed else 'Unverified source company '+company,confirmed=confirmed)
                result['cashBalances']=post_cash(c,bundle,args.tenant,args.actor,result,cash_companies)
            if args.forwards:
                if args.fund!='FCAGF':raise ValueError('Forward orientation must be explicitly confirmed for this source')
                from tooling.reconciliation_csv.reconciliation_forwards import post_forwards
                company=apply_confirmed_company(c,bundle,args.tenant,args.actor,result,'21','Northern Trust')
                properties={}
                for entry in args.property:
                    code,separator,value=entry.partition('=')
                    if not separator or code in properties:raise ValueError('Use distinct property CODE=VALUE mappings')
                    properties[code]=value
                result['forwards']=post_forwards(c,bundle,args.tenant,args.actor,result,{'21':company},properties,
                    {'20764':('USD','GBP'),'21105':('USD','GBP')})
            if args.daily_interest:
                from tooling.reconciliation_csv.reconciliation_accruals import post_accruals
                result['dailyInterest']=post_accruals(c,bundle,args.tenant,args.actor,result)
            if args.reset_flows:
                from tooling.reconciliation_csv.reconciliation_flows import post_flows
                result['resetFlows']=post_flows(c,bundle,args.tenant,args.actor,result)
            if args.fx_rates:
                from tooling.reconciliation_csv.reconciliation_fx import import_fx
                result['fxRates']=import_fx(c,bundle,args.tenant,args.actor,result,args.fx_operator)
            if args.market_prices:
                from tooling.reconciliation_csv.reconciliation_prices import import_prices
                result['marketPrices']=import_prices(c,bundle,args.tenant,args.actor,result,args.prices_operator)
        financial=any((args.book_positions,args.book_bonds,args.book_spx_option,args.cash_balances,args.forwards,args.daily_interest,args.reset_flows,args.fx_rates,args.market_prices))
        if financial:result['financialPostingStatus']='PARTIAL_SOURCE_IMPORT'
        print(json.dumps(dict(status='IMPORT_BATCH_COMMITTED' if financial else 'FOUNDATION_COMMITTED',**result),default=str),flush=True)
    finally:engine.dispose()


if __name__=='__main__':main()
