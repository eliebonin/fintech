"""Explicit, retry-safe local tenant-one fixture; no valuations or cash posting.

Run without --apply to preview. Trades and reference approvals use the normal
API. Only the newly owned synthetic strategy's historical start-date metadata
is set directly, with authority checks and an audit event; existing data is not
reclassified or backdated.
"""
import argparse
from datetime import date
import json
from pathlib import Path
import sys
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
TENANT=UUID('00000000-0000-7000-8000-000000000011')
ACTOR=UUID('00000000-0000-7000-8000-000000000083')
CODE='MOCK_BOND_CYCLE_20261015'
NAME='MOCK — Bond valuation cycle (GBP)'
BOND_CODE='MOCK_BOND_MATURITY_20261001'
BOND_NAME='MOCK ONLY — GBP 2% bond maturing 2026-10-01'
PREFIX='MOCK-BOND-CYCLE-20261015'


def api(path, body=None, key=None):
    headers={'X-Tenant-Id':str(TENANT),'X-User-Account-Id':str(ACTOR),'Content-Type':'application/json'}
    if key: headers['Idempotency-Key']=key
    request=Request('http://127.0.0.1:8000/v1/'+path,headers=headers,
        data=json.dumps(body).encode() if body is not None else None)
    try:
        with urlopen(request,timeout=30) as response:return json.load(response)
    except HTTPError as exc:
        raise RuntimeError(f'{request.get_method()} {path}: {exc.code} {exc.read().decode()}') from exc


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    from sqlalchemy import create_engine,select,func
    from security_master_schema.database_config import local_workspace_database
    from apps.reference_api.config import Settings
    from security_master_schema import models as m
    from security_master_schema.demo_data import DEMO_IDS
    from security_master_schema.strategy_access import require_strategy_action
    from security_master_schema.access_management import audit
    from apps.reference_api.reference_authority import require_reference_action
    GBP=DEMO_IDS['gbp_currency']
    settings=Settings.from_environment();engine=create_engine(settings.database_url)
    if settings.environment!='local' or engine.url.host not in ('localhost','127.0.0.1') or engine.url.port!=15432 or engine.url.database!=local_workspace_database():
        raise ValueError('Only the explicitly requested local app database is allowed')
    try:
        with engine.connect() as c:
            tenant=c.execute(select(m.tenant).where(m.tenant.c.tenant_id==TENANT)).mappings().one()
            if tenant['owning_organisation_id']!=DEMO_IDS['platform_organisation']:raise ValueError('Tenant-one ownership changed')
            counterparty=c.scalar(select(m.organisation.c.organisation_id).where(
                m.organisation.c.organisation_id==DEMO_IDS['bank_a_organisation'],m.organisation.c.status=='ACTIVE'))
            if not counterparty:raise ValueError('Expected synthetic counterparty unavailable')
        properties=[]
        for field in api('trades/booking-context')['data']['properties']:
            if field['required']:
                if field['code']!='ALLOCATION_WEIGHT':raise ValueError('Review new required trade field: '+field['code'])
                properties.append(dict(definitionId=field['definitionId'],value='1'))
        print(json.dumps(dict(tenant=tenant['display_name'],strategy=NAME,bond=BOND_NAME,
            fills=[dict(nominal='60000',cleanPrice='98.5',accrued='750'),dict(nominal='40000',cleanPrice='98.5',accrued='500')],
            executionDate='2026-09-30',settlementDate='2026-09-30',maturity='2026-10-01',
            writesEnabled=args.apply,scope='STRATEGY_AND_OPENING_TRADES_ONLY_NO_VALUATION_OR_PAYMENT'),ensure_ascii=False))
        if not args.apply:return
        found=next((s for s in api('strategies')['data'] if s['strategyCode']==CODE),None)
        if found:
            if found['displayName']!=NAME or found['baseCurrencyCode']!='GBP':raise ValueError('Seed code belongs to an unexpected strategy')
            strategy=found['strategyId']
        else:
            strategy=api('strategies',dict(strategyCode=CODE,displayName=NAME,strategyType='PROP_SLEEVE',baseCurrencyCode='GBP'))['data']['strategyId']
        with engine.begin() as c:
            require_strategy_action(c,TENANT,ACTOR,'STRATEGY_WRITE',UUID(strategy))
            require_reference_action(c,TENANT,ACTOR,'REFERENCE_PROPOSE')
            # Source-scoped retries need their own clearly synthetic identity;
            # never attribute these made-up terms to a real provider or issuer.
            source=c.scalar(select(m.integration_source_system.c.integration_source_system_id).where(
                m.integration_source_system.c.system_code==CODE,m.integration_source_system.c.tenant_id==TENANT))
            if source is None:
                source=c.scalar(m.integration_source_system.insert().values(tenant_id=TENANT,system_code=CODE,
                    display_name='MOCK ONLY - manual bond-cycle fixture',source_kind='INTERNAL',environment='SANDBOX',status='ACTIVE')
                    .returning(m.integration_source_system.c.integration_source_system_id))
                audit(c,ACTOR,TENANT,'SYNTHETIC_SOURCE_CREATED',dict(sourceId=str(source),reason='User-requested mock bond trades; no market-data entitlement created'))
            row=c.execute(select(m.strategy).where(m.strategy.c.strategy_id==UUID(strategy),m.strategy.c.tenant_id==TENANT,
                m.strategy.c.strategy_code==CODE,m.strategy.c.created_by_user_account_id==ACTOR).with_for_update()).mappings().one()
            if row['effective_from']>date(2026,9,1):
                if c.scalar(select(func.count()).select_from(m.trade).where(m.trade.c.strategy_id==UUID(strategy))):
                    raise ValueError('Do not change historical availability after trades exist')
                c.execute(m.strategy.update().where(m.strategy.c.strategy_id==UUID(strategy),m.strategy.c.tenant_id==TENANT)
                    .values(effective_from=date(2026,9,1)))
                audit(c,ACTOR,TENANT,'SYNTHETIC_STRATEGY_HISTORY_SET',dict(strategyId=strategy,effectiveFrom='2026-09-01',
                    reason='User-requested mock historical bond bookings; no prior operating strategy changed'))
            node=c.scalar(select(m.financial_reference_node.c.reference_node_id).join(m.reference_node_scope,
                m.reference_node_scope.c.reference_node_id==m.financial_reference_node.c.reference_node_id).where(
                    m.financial_reference_node.c.internal_code==BOND_CODE,m.reference_node_scope.c.scope_type=='TENANT_PRIVATE',
                    m.reference_node_scope.c.owner_tenant_id==TENANT))
        if node is None:
            proposed=api('bond-proposals',dict(canonicalName=BOND_NAME,internalCode=BOND_CODE,baseCurrencyId=str(GBP),
                effectiveFrom='2026-04-01',issueDate='2026-04-01',interestAccrualDate='2026-04-01',firstCouponDate='2026-10-01',
                maturityDate='2026-10-01',couponType='FIXED',parAmount='100',couponRate='0.02',couponFrequencyPerYear=2,
                dayCountConvention='30E_360',redemptionAmountPerPar='100',submissionMode='MANUAL',sourceSystemId=str(source),idempotencyKey=PREFIX+'-BOND'))['data']
            if proposed['status']!='APPROVED':
                proposed=api(f"bond-proposals/{proposed['proposalId']}/decision",dict(decision='APPROVED',
                    reason='User-requested synthetic UI fixture only. Not an actual issuer security.'))['data']
            node=UUID(proposed['instrumentId'])
        context=api(f'trades/product-instruments/{node}?asOfDate=2026-09-30')['data']
        if not context['bookingEligible']:
            proposal=api('instrument-booking-convention-proposals',dict(instrumentId=str(node),idempotencyKey=PREFIX+'-CONVENTION',
                convention=dict(kind='BOND',effectiveFrom='2026-04-01',priceCurrencyId=str(GBP),quoteFactor='100',
                    sourceReference=PREFIX+' synthetic contract terms; no actual issuer',quantityUnit='NOMINAL',priceBasis='PCT_OF_PAR',
                    principalBasis='UNADJUSTED_NOMINAL',quantityMinimum='1000',quantityIncrement='1000',accrual='MANUAL_CONFIRMATION',otcAllowed=True)))['data']
            api(f"reference-data-proposals/{proposal['proposalId']}/decision",dict(decision='APPROVED',reason='Verified explicit synthetic nominal/clean-price conventions.'))
            context=api(f'trades/product-instruments/{node}?asOfDate=2026-09-30')['data']
        if not context['bookingEligible']:raise ValueError('Synthetic bond is not booking-ready: '+str(context))
        trades=[]
        for index,(quantity,accrued) in enumerate((('60000','750'),('40000','500')),1):
            key=PREFIX+f'-FILL-{index}'
            result=api('trades/bonds',dict(instrumentId=str(node),listingId=None,strategyId=strategy,side='BUY',quantity=quantity,
                executionPrice='98.5',executionRoute='OTC',tradeDatetime=f'2026-09-30T10:0{index}:00Z',settlementDate='2026-09-30',
                counterpartyOrganisationId=str(counterparty),expectedTermsFingerprint=context['termsFingerprint'],priceType='CLEAN',
                accruedInterestAmount=accrued,settlementEvidence='SYNTHETIC ONLY: explicitly agreed T+0 settlement on 2026-09-30, before 2026-10-01 maturity.',
                externalReference=key,properties=properties,comment='SYNTHETIC UI FIXTURE ONLY. User requested 2026-10-15. '
                    'Simulated historical opening fill; manual clean quote and bought accrual, not a real execution. '
                    'Maturity, coupon receipt, daily earnings and cash snapshots are separate, not auto-booked.'),key)['data']['trade']
            trades.append(dict(tradeId=result['tradeId'],quantity=result['quantity'],executionPrice=result['executionPrice']))
        print(json.dumps(dict(strategyId=strategy,strategyCode=CODE,instrumentId=str(node),trades=trades),ensure_ascii=False))
    finally:engine.dispose()


if __name__=='__main__':main()
