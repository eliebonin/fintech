"""Preview/apply the user-requested tenant-one SPX and UKX unit-swap fixtures.

Reference proposals, approval and trades use normal APIs. New synthetic source,
benchmark reference and owned-data rights use guarded, authorised, audited seed
transactions. No existing strategy, policy, financial evidence or cash is edited.
"""
import argparse
from datetime import date, datetime, time, timezone
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
import sys
from uuid import UUID

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.seed_mock_bond_strategy import api,TENANT,ACTOR
from scripts.mock_unit_swap_data import build_history,START,END,MATURITY,SPECS

PREFIX='MOCK_UNIT_SWAPS_20261015'
STRATEGY=UUID('1df14361-1a24-40f6-aabb-7c0cb86cf5fb')
REFS={'SPX':UUID('01a11297-b41e-75d6-a5d7-698015eb3b6b'),
      'UKX':UUID('01a13518-402b-7c34-a88d-2d6b8cc8d467')}
PROFILE=UUID('01a0773c-9985-7869-ae3e-87acebf487aa')
DAY_COUNTS={'SPX':UUID('01a0672e-65a8-7d44-afcf-eb9241f6b110'),
            'UKX':UUID('01a0672e-65ac-7436-8ba5-c0af22bd0533')}
SONIA=UUID('00000000-0000-7000-8000-000000000193')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    from sqlalchemy import create_engine,select,func
    from security_master_schema.database_config import local_workspace_database
    from apps.reference_api.config import Settings
    from apps.reference_api.reference_authority import require_reference_action
    from apps.reference_api.valuation_policies import authority
    from apps.reference_api.swap_creation_contracts import SwapProposalRequest
    from security_master_schema import models as m
    from security_master_schema.access_management import audit
    from security_master_schema.strategy_access import require_strategy_action
    from security_master_schema.demo_data import DEMO_IDS
    from market_data.rights import load_rights
    from market_data.display_access import assert_dataset_display
    settings=Settings.from_environment();engine=create_engine(settings.database_url)
    if settings.environment!='local' or engine.url.host not in ('localhost','127.0.0.1') or engine.url.port!=15432 or engine.url.database!=local_workspace_database():
        raise ValueError('Only the explicitly requested local platform_secm database is allowed')
    now=datetime.now(timezone.utc)
    histories={code:build_history(code) for code in SPECS}
    artifact=ROOT/'data/mock-unit-swaps-20261015.json'
    content=(json.dumps(dict(synthetic=True,methodologyVersion=1,history=histories),indent=2,sort_keys=True)+'\n').encode()
    digest=sha256(content).hexdigest()
    try:
        with engine.connect() as c:
            require_strategy_action(c,TENANT,ACTOR,'TRADE_WRITE',STRATEGY)
            require_reference_action(c,TENANT,ACTOR,'REFERENCE_PROPOSE')
            require_reference_action(c,TENANT,ACTOR,'REFERENCE_APPROVE')
            authority(c,TENANT,ACTOR,True)
            strategy=c.execute(select(m.strategy).where(m.strategy.c.strategy_id==STRATEGY,m.strategy.c.tenant_id==TENANT,
                m.strategy.c.strategy_code=='STRAT-TEST',m.strategy.c.display_name=='Strat Testing',m.strategy.c.status=='ACTIVE')).mappings().one()
            tenant=c.execute(select(m.tenant).where(m.tenant.c.tenant_id==TENANT,
                m.tenant.c.owning_organisation_id==DEMO_IDS['platform_organisation'])).mappings().one()
            org=tenant['owning_organisation_id']
            currencies={code:c.scalar(select(m.currency.c.currency_id).where(m.currency.c.currency_code==spec['currency'],m.currency.c.status=='ACTIVE')) for code,spec in SPECS.items()}
            if not all(currencies.values()):raise ValueError('Expected active currencies missing')
        properties=[]
        for field in api('trades/booking-context')['data']['properties']:
            if field['required']:
                if field['code']!='ALLOCATION_WEIGHT':raise ValueError('Review new required property '+field['code'])
                properties.append(dict(definitionId=field['definitionId'],value='1'))
        print(json.dumps(dict(strategy=strategy['display_name'],strategyId=str(STRATEGY),apply=args.apply,
            effectiveDate=str(START),maturityDate=str(MATURITY),historyEnd=str(END),
            contracts={code:dict(units=spec['units'],leverage=spec['leverage'],currency=spec['currency'],
                referenceNotional=str(Decimal(spec['units'])*Decimal(spec['initial'])),observations=len(histories[code]['prices'])) for code,spec in SPECS.items()},
            warning='SWAP valuation is not enabled; adding these trades blocks this strategy in the current valuation engine. No cash postings. Synthetic marks only.')))
        if not args.apply:return
        # Generated fixture artifact, not a handwritten code/config edit.
        if artifact.exists() and artifact.read_bytes()!=content:raise ValueError('Retained fixture artifact differs; do not overwrite')
        if not artifact.exists():artifact.write_bytes(content)
        with engine.begin() as c:
            require_reference_action(c,TENANT,ACTOR,'REFERENCE_PROPOSE')
            c.execute(select(func.pg_advisory_xact_lock(int.from_bytes(sha256(PREFIX.encode()).digest()[:8],'big',signed=True))))
            source=c.scalar(select(m.integration_source_system.c.integration_source_system_id).where(m.integration_source_system.c.system_code==PREFIX,m.integration_source_system.c.tenant_id==TENANT))
            if source is None:
                source=c.scalar(m.integration_source_system.insert().values(tenant_id=TENANT,system_code=PREFIX,
                    display_name='MOCK ONLY - unit-swap research fixture',source_kind='INTERNAL',environment='SANDBOX',status='ACTIVE')
                    .returning(m.integration_source_system.c.integration_source_system_id))
            sofr=c.scalar(select(m.financial_reference_node.c.reference_node_id).where(m.financial_reference_node.c.internal_code==PREFIX+'_SOFR'))
            if sofr is None:
                kind=c.scalar(select(m.reference_node_type.c.reference_node_type_id).where(m.reference_node_type.c.type_code=='RATE_INDEX',m.reference_node_type.c.status=='ACTIVE'))
                sofr=c.scalar(m.financial_reference_node.insert().values(reference_node_type_id=kind,canonical_name='SOFR overnight rate - mock-swap reference',
                    internal_code=PREFIX+'_SOFR',status='ACTIVE',is_tradable=False).returning(m.financial_reference_node.c.reference_node_id))
                c.execute(m.reference_node_scope.insert().values(reference_node_id=sofr,scope_type='TENANT_PRIVATE',owner_tenant_id=TENANT,status='ACTIVE'))
            else:
                c.execute(select(m.reference_node_scope).where(m.reference_node_scope.c.reference_node_id==sofr,
                    m.reference_node_scope.c.owner_tenant_id==TENANT,m.reference_node_scope.c.scope_type=='TENANT_PRIVATE',m.reference_node_scope.c.status=='ACTIVE')).one()
            audit(c,ACTOR,TENANT,'MOCK_UNIT_SWAP_SOURCE_PREPARED',dict(sourceId=str(source),sofrReferenceId=str(sofr),artifactHash=digest,
                reason='User-requested invented swaps and marks; no benchmark rate observations or operating policies altered'))
        results=[]
        for code,spec in SPECS.items():
            identity=PREFIX+'_'+code
            benchmark='SOFR' if code=='SPX' else 'SONIA'
            spread='15' if code=='SPX' else '10'
            name=f'MOCK - {code} / {benchmark} + {spread} bps - units - {spec["leverage"]}x'
            terms=dict(schemaVersion=1,tenantIdentifier=identity,quantityUnit='UNITS',contractualUnits=spec['units'],notionalPerUnit=spec['initial'],
                contractualNotional=str(Decimal(spec['units'])*Decimal(spec['initial'])),notionalCurrencyId=str(currencies[code]),
                effectiveDate=str(START),maturityDate=str(MATURITY),performanceDirection='RECEIVE',returnBasis='TOTAL',
                returnProfileId=str(PROFILE),performanceReferenceId=str(REFS[code]),leverage=spec['leverage'],
                quoteCurrencyId=str(currencies[code]),quoteFactor='1',sourceReference=f'User-requested SYNTHETIC ONLY fixture; {artifact.name}; SHA256 {digest}. '
                    'One unit = one currency unit per index point; invented inception reference and whole-swap MTM. Not an actual confirmation.',
                financingTreatment='SEPARATE',fundingReferenceId=str(sofr if code=='SPX' else SONIA),fundingSpread=spec['spread'],
                fundingNotionalBasis='LEVERAGED_NOMINAL',dayCountConventionId=str(DAY_COUNTS[code]),
                interestCalculationMethod='Compounded overnight in arrears; synthetic illustrative fixing path, no actual provider rates.',
                fundingObservationDescription='Synthetic calendar-day compounding without observation lag; both legs settle at maturity. No interim resets.',
                fundingResetFrequency='AT_MATURITY',fundingPaymentFrequency='AT_MATURITY',performanceResetFrequency='AT_MATURITY',redemptionRule='TERMINATE')
            proposed_body=SwapProposalRequest.model_validate(dict(canonicalName=name,tenantIdentifier=identity,terms=terms,idempotencyKey=identity+'-CREATE')).model_dump(mode='json',by_alias=True)
            proposal=api('instruments/swap-proposals',proposed_body)['data']
            if proposal['status']!='APPROVED':
                proposal=api(f"reference-data-proposals/{proposal['proposalId']}/decision",dict(decision='APPROVED',
                    reason='User authorised synthetic swap fixture. Verified units, funding/spread, leverage, whole-swap quote and dates; not a real contract.'))['data']
            node=UUID(proposal['referenceNodeId'])
            context=api(f'trades/product-instruments/{node}?asOfDate={START}')['data']
            if not context['bookingEligible'] or context['convention']['quantityUnit']!='UNITS':raise ValueError('Unit swap not booking-ready: '+str(context))
            key=identity+'-OPEN'
            trade=api('trades/swaps',dict(instrumentId=str(node),executionRoute='OTC',strategyId=str(STRATEGY),side='BUY',quantity=spec['units'],
                executionPrice='0',tradeDatetime=histories[code]['prices'][0]['observedAt'],counterpartyOrganisationId=str(DEMO_IDS['bank_a_organisation']),
                expectedTermsFingerprint=context['termsFingerprint'],properties=properties,externalReference=key,
                comment='SYNTHETIC ONLY. Simulated historical inception at zero whole-swap MTM per unit; no upfront or cash posting. '
                    'Quote includes funding and leverage once. Fixture '+identity),key)['data']['trade']
            economics=trade['productEconomics']
            if trade['quantityUnit']!='UNITS' or Decimal(trade['quantity'])!=Decimal(spec['units']) or Decimal(economics['bookedNotional'])!=Decimal(terms['contractualNotional']):
                raise ValueError('Frozen trade units/notional differ from requested fixture')
            results.append(dict(code=code,instrumentId=str(node),tradeId=trade['tradeId'],units=spec['units'],leverage=spec['leverage'],
                seriesId=str(seed_history(engine,m,source,org,currencies[code],node,identity,histories[code],artifact,digest,now,authority,audit,load_rights,assert_dataset_display))))
        print(json.dumps(dict(strategyId=str(STRATEGY),fixtures=results,artifact=str(artifact),artifactHash=digest)))
    finally:engine.dispose()


def seed_history(engine,m,source,org,currency,node,identity,history,artifact,digest,now,authority,audit,load_rights,assert_dataset_display):
    from sqlalchemy import select,func
    with engine.begin() as c:
        authority(c,TENANT,ACTOR,True)
        c.execute(select(func.pg_advisory_xact_lock(int.from_bytes(sha256(identity.encode()).digest()[:8],'big',signed=True))))
        def put(table,where,values,key):
            row=c.execute(select(table).where(*where)).mappings().one_or_none()
            return row[key] if row else c.scalar(table.insert().values(**values).returning(table.c[key]))
        provider=put(m.data_provider,[m.data_provider.c.provider_code==PREFIX],dict(organisation_id=org,provider_code=PREFIX,
            display_name='MOCK ONLY - invented unit-swap MTM',owner_tenant_id=TENANT,status='ACTIVE'),'data_provider_id')
        product=put(m.provider_product,[m.provider_product.c.data_provider_id==provider,m.provider_product.c.product_code==PREFIX],
            dict(data_provider_id=provider,product_code=PREFIX,display_name='Synthetic SPX and UKX swap histories',status='ACTIVE'),'provider_product_id')
        dataset=put(m.dataset,[m.dataset.c.provider_product_id==product,m.dataset.c.dataset_code==PREFIX],dict(provider_product_id=product,dataset_code=PREFIX,
            display_name='MOCK ONLY - whole-swap MTM per unit',data_domain='MARKET_DATA',coverage_description='Invented marks; not actual indices, benchmark fixings or provider valuations.',
            delivery_channel='MANUAL',valid_from=START,status='ACTIVE'),'dataset_id')
        licence=put(m.data_licence,[m.data_licence.c.licence_code==PREFIX],dict(licensor_organisation_id=org,licensee_organisation_id=org,licence_code=PREFIX,
            display_name='Self-created synthetic research data',licence_reference='User request 2026-10-15; '+artifact.name,
            permitted_use_description='Our invented data only, local personal research; not evidence of rights to any real vendor feed.',valid_from=START,status='ACTIVE'),'data_licence_id')
        assignment=put(m.dataset_licence_assignment,[m.dataset_licence_assignment.c.dataset_id==dataset,m.dataset_licence_assignment.c.data_licence_id==licence],
            dict(dataset_id=dataset,data_licence_id=licence,licence_role='INTERNAL_USE',valid_from=START,status='ACTIVE'),'dataset_licence_assignment_id')
        put(m.dataset_access_profile,[m.dataset_access_profile.c.dataset_id==dataset],dict(dataset_id=dataset,licensee_organisation_id=org,permitted_tenant_id=TENANT,
            usage_scope='PERSONAL',provider_enabled=True,activation_reference='User-requested owned invented values; no third-party content.',status='ACTIVE'),'dataset_id')
        for activity in ('ACQUIRE','STORE','DISPLAY','NON_DISPLAY'):
            put(m.licence_activity_grant,[m.licence_activity_grant.c.dataset_licence_assignment_id==assignment,m.licence_activity_grant.c.activity==activity],
                dict(dataset_licence_assignment_id=assignment,activity=activity,usage_scope='PERSONAL',evidence_basis='PERSONAL_DECLARATION',
                    evidence_reference='Self-created mock values; fixture SHA256 '+digest,valid_from=START,status='ACTIVE'),'grant_id')
            put(m.dataset_right_requirement,[m.dataset_right_requirement.c.dataset_id==dataset,m.dataset_right_requirement.c.activity==activity],
                dict(dataset_id=dataset,activity=activity,requirement_code='SELF_CREATED_MOCK',dataset_licence_assignment_id=assignment),'requirement_id')
        for purpose in ('VALUATION','INTERNAL_REPORTING'):
            put(m.tenant_dataset_entitlement,[m.tenant_dataset_entitlement.c.tenant_id==TENANT,m.tenant_dataset_entitlement.c.dataset_id==dataset,m.tenant_dataset_entitlement.c.use_purpose==purpose],
                dict(tenant_id=TENANT,dataset_id=dataset,dataset_licence_assignment_id=assignment,use_purpose=purpose,coverage_mode='DATASET',valid_from=START,status='ACTIVE'),'tenant_dataset_entitlement_id')
        payload=put(m.source_payload,[m.source_payload.c.integration_source_system_id==source,m.source_payload.c.external_message_reference==PREFIX],
            dict(integration_source_system_id=source,tenant_id=TENANT,payload_format='JSON',external_message_reference=PREFIX,payload_locator=artifact.as_uri(),payload_sha256=digest,
                source_published_at_utc=now,received_at_utc=now,processing_status='MAPPED'),'source_payload_id')
        old_hash=c.scalar(select(m.source_payload.c.payload_sha256).where(m.source_payload.c.source_payload_id==payload))
        if old_hash!=digest:raise ValueError('Retained source hash differs; do not overwrite')
        code=history['code'];is_us=code=='SPX'
        cut=put(m.valuation_cut,[m.valuation_cut.c.cut_code==identity],dict(cut_code=identity,display_name='MOCK '+code+' EOD session close',
            timezone_name='America/New_York' if is_us else 'Europe/London',local_time=time(16) if is_us else time(16,30),status='ACTIVE'),'valuation_cut_id')
        measure=c.scalar(select(m.series_measure_definition.c.series_measure_definition_id).where(m.series_measure_definition.c.measure_code=='PRICE'))
        series=put(m.market_data_series,[m.market_data_series.c.reference_node_id==node,m.market_data_series.c.default_dataset_id==dataset],
            dict(reference_node_id=node,default_dataset_id=dataset,series_type='CLOSE',closing_method='PROVIDER_DEFINED',value_type='PRICE',measure_definition_id=measure,
                currency_id=currency,valuation_cut_id=cut,expected_frequency_code='BUSINESS_DAILY',coverage_start_date=START,coverage_end_date=END,
                source_system_id=PREFIX,status='ACTIVE',is_official=False),'market_data_series_id')
        for dimension,value in [('SWAP_PRICE_BASIS','WHOLE_SWAP_MTM_PER_UNIT'),('QUOTE_FACTOR','1'),('QUANTITY_UNIT','UNITS')]:
            put(m.market_data_series_dimension,[m.market_data_series_dimension.c.market_data_series_id==series,m.market_data_series_dimension.c.dimension_code==dimension],
                dict(market_data_series_id=series,dimension_code=dimension,dimension_value=value),'market_data_series_id')
        vintage=put(m.market_data_vintage,[m.market_data_vintage.c.dataset_id==dataset,m.market_data_vintage.c.source_vintage_key==PREFIX],
            dict(dataset_id=dataset,data_provider_id=provider,source_vintage_key=PREFIX,source_published_at_utc=now,received_at_utc=now,value_basis='RAW',
                vintage_status='CURRENT',content_hash=digest,source_payload_id=payload),'market_data_vintage_id')
        existing={r['market_date']:r for r in c.execute(select(m.market_data_observation).where(m.market_data_observation.c.market_data_series_id==series)).mappings()}
        rows=[]
        for point in history['prices']:
            day=date.fromisoformat(point['date']);stamp=datetime.fromisoformat(point['observedAt']);old=existing.get(day)
            if old:
                if old['value']!=Decimal(point['close']) or old['value_basis']!='RAW' or old['observed_at_utc']!=stamp:
                    raise ValueError('Existing synthetic observation differs; do not overwrite')
                continue
            rows.append(dict(market_data_series_id=series,dataset_id=dataset,market_data_vintage_id=vintage,acquisition_licence_id=licence,source_payload_id=payload,
                market_date=day,valuation_cut_id=cut,observed_at_utc=stamp,received_at_utc=now,source_published_at_utc=now,value=Decimal(point['close']),value_basis='RAW',
                quality_status='ACCEPTED',source_observation_key=identity+'-'+str(day),source_payload_reference=artifact.as_uri()))
        if rows:c.execute(m.market_data_observation.insert(),rows)
        for activity in ('ACQUIRE','STORE','DISPLAY','NON_DISPLAY'):
            if not load_rights(c,dataset,activity,date.today(),'PERSONAL').allowed:raise ValueError('Synthetic rights incomplete: '+activity)
        assert_dataset_display(c,TENANT,{dataset},series_contexts=[(dataset,series)])
        audit(c,ACTOR,TENANT,'MOCK_UNIT_SWAP_HISTORY_PREPARED',dict(instrumentId=str(node),seriesId=str(series),datasetId=str(dataset),
            addedObservations=len(rows),totalObservations=len(history['prices']),artifactHash=digest,synthetic=True))
        return series


if __name__=='__main__':main()
