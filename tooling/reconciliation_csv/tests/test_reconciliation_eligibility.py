"""Personal file use is explicit, tenant-scoped and never a provider contract."""
from datetime import date
from uuid import uuid4
import pytest
from sqlalchemy import select,func
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from tooling.reconciliation_csv.tests.test_reconciliation_seed import connection


def test_date_only_policy_has_no_invented_fixing_or_implicit_carry():
    from tooling.reconciliation_csv.reconciliation_eligibility import build_policy
    strategy,cut,calendar,prices,fx=[uuid4() for _ in range(5)]
    types={kind:uuid4() for kind in ('BOND','ACTIVELY_MANAGED_CERTIFICATE','OPTION','SWAP','FX_FORWARD')}
    policy=build_policy(strategy,cut,calendar,prices,fx,date(2026,9,21),types)
    assert policy.selection_mode=='STRICT' and not policy.default_rules
    assert {r.series_type for r in policy.rules}=={'CLOSE','MARK','FX_FORWARD','FX_SPOT'}
    for rule in policy.rules:
        assert rule.instrument_type_id is not None or rule.subject_type=='FX_PAIR'
        assert rule.pricing_convention=='EXPLICIT_TIME' and rule.fixing_code is None
        assert rule.value_basis=='RAW' and rule.pricing_date_rule=='SAME_DAY' and rule.max_staleness_business_days==0
        assert rule.missing_data_action=='FAIL' and not rule.allow_inverse_fx


def setup_files(c,tmp_path,*,forward=False):
    import csv
    from tooling.reconciliation_csv.tests.test_reconciliation_option import option_bundle
    from tooling.reconciliation_csv.reconciliation import load_bundle
    from tooling.reconciliation_csv.seed_reconciliation_bundle import apply_foundation
    from tooling.reconciliation_csv.reconciliation_products import seed_products,seed_additional
    from tooling.reconciliation_csv.reconciliation_option import post_option
    from tooling.reconciliation_csv.reconciliation_prices import import_prices
    from tooling.reconciliation_csv.reconciliation_fx import import_fx
    option_bundle(tmp_path)
    rows=[dict(id='opt',instrument_id='20265',date='2026-10-20',price='28')]
    if forward:
        rows.append(dict(id='fwd',instrument_id='20764',date='2026-10-20',price='0.76'))
        for kind in ('trades','all_instruments'):
            path=tmp_path/f'SAMPLE-2026-10-20-{kind}.csv'
            with path.open(newline='') as handle:items=list(csv.DictReader(handle))
            if kind=='trades':items.append(dict(items[0])|dict(trade_id='fwd',instrument_id='20764',quantity='1000',price='0.75',
                trade_currency='USD',trade_type='Investment',trade_datetime_utc='2026-10-19 12:00:00',settlement_date='2026-10-23'))
            else:items.append(dict(instrument_id='20764',instrument_type='FXFWD',currency='GBP',short_name='Synthetic forward',
                effective_date='2026-10-19',maturity_date='2026-10-23',cash_settlement_date='2026-10-23',price_type='notional'))
            fields=list(dict.fromkeys(k for item in items for k in item))
            with path.open('w',newline='') as handle:
                writer=csv.DictWriter(handle,fieldnames=fields);writer.writeheader();writer.writerows(items)
    with (tmp_path/'SAMPLE-2026-10-20-prices.csv').open('w',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    bundle=load_bundle(tmp_path,'SAMPLE',date(2026,10,20),excluded_trade_ids={'exclude'},amc_ids={'1857'})
    actor=ids['demo_user_account'];tenant=ids['tenant']
    foundation=apply_foundation(c,bundle,tenant,actor,tmp_path/'evidence')
    seed_products(c,bundle,tenant,actor,foundation);seed_additional(c,bundle,tenant,actor,foundation)
    post_option(c,bundle,tenant,actor,foundation,{})
    if forward:
        from tooling.reconciliation_csv.seed_reconciliation_bundle import apply_confirmed_company
        from tooling.reconciliation_csv.reconciliation_forwards import post_forwards
        company=apply_confirmed_company(c,bundle,tenant,actor,foundation,'21','Unverified source company 21',confirmed=False)
        post_forwards(c,bundle,tenant,actor,foundation,{'21':company},{},{'20764':('USD','GBP')})
    prices=import_prices(c,bundle,tenant,actor,foundation,ids['bank_a_organisation'])
    fx=import_fx(c,bundle,tenant,actor,foundation,ids['bank_a_organisation'],selected=('GBP','SGD'))
    return foundation,prices['datasetId'],fx['datasetId']


def test_private_activation_replays_without_rewriting_source_or_granting_commercial_use(connection,tmp_path):
    from tooling.reconciliation_csv.reconciliation_eligibility import prepare
    from market_data.rights import load_rights
    from security_master_schema.governance_clock import governance_date
    from market_data.entitlements import tenant_series_entitlement_clause
    from security_master_schema.market_data_resolver import ResolutionRequest,resolve_market_data
    c=connection;foundation,prices,fx=setup_files(c,tmp_path)
    source=[dict(r) for r in c.execute(select(m.market_data_observation).where(m.market_data_observation.c.dataset_id.in_([prices,fx]))).mappings()]
    args=(c,ids['tenant'],ids['demo_user_account'],ids['platform_admin_user_account'],foundation['strategyId'],foundation['sourceId'],prices,fx,
        'Test owner instruction: local personal historical valuation only, no provider contract or commercial permission.')
    result=prepare(*args);again=prepare(*args)
    assert result==again
    assert [dict(r) for r in c.execute(select(m.market_data_observation).where(m.market_data_observation.c.dataset_id.in_([prices,fx]))).mappings()]==source
    for dataset in (prices,fx):
        assert load_rights(c,dataset,'NON_DISPLAY',governance_date(),'PERSONAL').allowed
        assert not load_rights(c,dataset,'NON_DISPLAY',governance_date(),'COMMERCIAL').allowed
        assert not load_rights(c,dataset,'REDISTRIBUTE',governance_date()).allowed
        assert c.scalar(select(func.count()).select_from(m.dataset).where(m.dataset.c.dataset_id==dataset,
            tenant_series_entitlement_clause(dataset,None,ids['second_tenant'],'VALUATION',date(2026,10,20))))==0
    option=next(row for row in source if row['dataset_id']==prices)
    subject=c.scalar(select(m.market_data_series.c.reference_node_id).where(m.market_data_series.c.market_data_series_id==option['market_data_series_id']))
    request=ResolutionRequest(ids['tenant'],subject,result['policyId'],date(2026,10,20),result['cutId'],c.scalar(select(func.clock_timestamp())),'VALUATION',foundation['strategyId'])
    selected=resolve_market_data(c,request)
    assert selected.status=='SELECTED' and selected.selected_value==28
    assert selected.pricing_evidence['calendarEvidence']['sealed'] is True
    with pytest.raises((PermissionError,ValueError)):
        prepare(c,ids['second_tenant'],ids['demo_user_account'],ids['platform_admin_user_account'],foundation['strategyId'],foundation['sourceId'],prices,fx,args[-1])
    # An unresolved upstream prerequisite still wins over personal declarations.
    with c.begin_nested() as guard:
        c.execute(m.dataset_right_requirement.insert().values(dataset_id=prices,activity='NON_DISPLAY',requirement_code='UPSTREAM_REQUIRED'))
        with pytest.raises(PermissionError):prepare(*args)
        guard.rollback()
    c.execute(m.licence_activity_grant.update().where(m.licence_activity_grant.c.activity=='NON_DISPLAY',
        m.licence_activity_grant.c.dataset_licence_assignment_id.in_(select(m.dataset_licence_assignment.c.dataset_licence_assignment_id).where(m.dataset_licence_assignment.c.dataset_id==prices))).values(status='REVOKED'))
    with pytest.raises((PermissionError,ValueError)):prepare(*args)


def test_forward_label_normalization_keeps_values_orientation_and_original_evidence(connection,tmp_path):
    from datetime import datetime,time,timezone
    from decimal import Decimal
    from tooling.reconciliation_csv.reconciliation_eligibility import prepare
    from valuation.forward_inputs import select_forward_rate
    from valuation.service import ValuationRequest
    from positions.fx_forward import normalize_booking
    import json
    c=connection;foundation,prices,fx=setup_files(c,tmp_path,forward=True)
    originals=[dict(r) for r in c.execute(select(m.market_data_observation,m.market_data_series.c.reference_node_id)
        .join(m.market_data_series).where(m.market_data_observation.c.dataset_id==prices,m.market_data_series.c.series_type=='FORWARD_RATE')).mappings()]
    args=(c,ids['tenant'],ids['demo_user_account'],ids['platform_admin_user_account'],foundation['strategyId'],foundation['sourceId'],prices,fx,
        'Test owner instruction: personal local valuation only; neither upstream contract nor redistribution clearance.')
    result=prepare(*args);assert result['normalizedForwardSeries']==1
    assert prepare(*args)==result
    original=originals[0];subject=original['reference_node_id']
    trade=c.execute(select(m.trade).where(m.trade.c.strategy_id==foundation['strategyId'],m.trade.c.reference_instrument_node_id==subject)).mappings().one()
    event=c.execute(select(m.trade_lifecycle_event).where(m.trade_lifecycle_event.c.trade_id==trade['trade_id'],m.trade_lifecycle_event.c.event_type=='BOOKED')).mappings().one()
    proof=normalize_booking(c,trade,json.loads(event['event_payload']),event)
    close=datetime.combine(date(2026,10,20),time.max,timezone.utc)
    request=ValuationRequest(ids['tenant'],foundation['strategyId'],result['policyId'],result['cutId'],ids['gbp_currency'],
        datetime.combine(date(2026,10,19),time.max,timezone.utc),close,c.scalar(select(func.clock_timestamp())))
    _,selected=select_forward_rate(c,request,subject,close,proof)
    assert selected.selected_value==Decimal('.76')
    assert [dict(r) for r in c.execute(select(m.market_data_observation,m.market_data_series.c.reference_node_id)
        .join(m.market_data_series).where(m.market_data_observation.c.dataset_id==prices,m.market_data_series.c.series_type=='FORWARD_RATE')).mappings()]==originals
    # A later source correction cannot silently reuse yesterday's normalization.
    c.execute(m.market_data_observation.update().where(m.market_data_observation.c.market_data_observation_id==original['market_data_observation_id']).values(value=Decimal('.77')))
    with pytest.raises(ValueError,match='history changed'):prepare(*args)
