from dataclasses import replace
from datetime import datetime,time,timezone,timedelta
from decimal import Decimal as D
from uuid import uuid4
from sqlalchemy import select
from tests.test_valuation_service import valued
from tests.test_fx_maturity_service import setup
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids


def rates(c,r,instrument):
    source=dict(c.execute(select(m.market_data_observation).where(m.market_data_observation.c.market_data_observation_id==ids['market_data_observation'])).mappings().one())
    rule=dict(c.execute(select(m.valuation_policy_rule).where(m.valuation_policy_rule.c.valuation_policy_rule_id==ids['valuation_policy_rule'])).mappings().one())
    series=uuid4();measure=c.scalar(select(m.series_measure_definition.c.series_measure_definition_id).where(m.series_measure_definition.c.measure_code=='FX_RATE'))
    c.execute(m.market_data_series.insert().values(market_data_series_id=series,reference_node_id=instrument,series_type='FX_FORWARD',value_type='RATE',
        currency_id=ids['usd_currency'],default_dataset_id=source['dataset_id'],source_system_id='MOCK_FORWARD_RATES',valuation_cut_id=r.cut_id,measure_definition_id=measure))
    for code,value in [('BASE_CURRENCY','GBP'),('QUOTE_CURRENCY','USD'),('RATE_BASIS','FORWARD_OUTRIGHT'),('MATURITY_DATE','2026-10-01')]:
        c.execute(m.market_data_series_dimension.insert().values(market_data_series_id=series,dimension_code=code,dimension_value=value))
    c.execute(m.valuation_policy_rule.insert().values(**(rule|dict(valuation_policy_rule_id=uuid4(),rule_sequence=98,subject_type='INSTRUMENT',
        subject_reference_node_id=instrument,market_data_series_id=series,series_type='FX_FORWARD',pricing_convention='EXPLICIT_TIME',pricing_cut_id=r.cut_id))))
    for day,value in [(r.opening_cutoff.date(),'1.11'),(r.closing_cutoff.date(),'1.12')]:
        # The fixture policy's London cut is 15:00 UTC during BST.
        stamp=datetime.combine(day,time(14),timezone.utc)
        c.execute(m.market_data_observation.insert().values(**(source|dict(market_data_observation_id=uuid4(),market_data_series_id=series,
            market_date=day,value=D(value),market_data_vintage_id=None,received_at_utc=stamp,observed_at_utc=stamp,source_published_at_utc=stamp,source_observation_key='FWDRATE_'+uuid4().hex))))
    return series


def test_real_booked_forward_rate_pnl_stages_without_spot_substitution(valued):
    from valuation.service import calculate_position
    from valuation import storage
    from apps.reference_api.db import get_engine
    c,r,equity=valued
    r=replace(r,opening_cutoff=datetime(2026,9,30,23,59,59,999999,tzinfo=timezone.utc),closing_cutoff=datetime(2026,10,1,23,59,59,999999,tzinfo=timezone.utc),reporting_currency_id=ids['usd_currency'],daily=True)
    attempt=storage.begin_attempt(get_engine(),r,ids['demo_user_account'],str(uuid4()))
    instrument,group,cut,spot=setup(c,r)
    original=c.execute(select(m.trade).where(m.trade.c.trade_id==equity)).mappings().one()
    c.execute(m.trade_lifecycle_event.insert().values(trade_id=equity,sequence_no=2,event_type='CANCELLED',event_datetime_utc=original['trade_datetime_utc'],
        recorded_by_user_account_id=ids['demo_user_account'],event_payload='{}'))
    series=rates(c,r,instrument)
    result=calculate_position(c,r)
    assert result.period.market_pnl==10000 and result.period.opening_value==10000 and result.period.closing_value==20000
    assert all(s['market_data_series_id']==str(series) for s in result.evidence['selections'])
    batch=storage.stage(c,attempt,ids['demo_user_account'],result)
    staged=storage.batch_view(c,r.tenant_id,batch)
    assert D(staged['summary']['marketPnl'])==10000
    assert any(rule['code']=='FX_FORWARD_RATE_PNL' for item in staged['items'] for rule in item['evidence']['appliedRules'])
    from valuation.amendments import request_component_change,approve_component_change
    from tests.test_position_attribution_storage import reviewer
    revision=request_component_change(c,r.tenant_id,batch,staged['items'][0]['attribution_id'],ids['demo_user_account'],
        dict(component='OTHER_COST',amount=D('-10'),reason='Mock reviewed fee',sourceReference='OPS'),str(uuid4()))
    revised=approve_component_change(c,r.tenant_id,revision,reviewer(c),'Mock fee evidence checked')
    assert D(storage.batch_view(c,r.tenant_id,revised)['items'][0]['net_pnl'])==9990
    storage.publish(c,r.tenant_id,revised,reviewer(c),'Mock forward rate P&L and amendment checked')
    assert storage.batch_view(c,r.tenant_id,revised)['status']=='PUBLISHED'

    # Spot observations still exist, but may not replace missing contract rates.
    # Retain observations referenced by published snapshots; make them ineligible
    # only for the new calculation's input-selection check in this mock fixture.
    c.execute(m.market_data_observation.update().where(m.market_data_observation.c.market_data_series_id==series).values(quality_status='REJECTED'))
    import pytest
    with pytest.raises(ValueError,match='Forward contract-rate input blocked'):calculate_position(c,r)


def test_maturity_closure_uses_manual_rate_in_valuation(valued):
    from lifecycle import fx_service
    from valuation.service import calculate_position
    c,r,equity=valued
    r=replace(r,opening_cutoff=datetime(2026,9,30,23,59,59,999999,tzinfo=timezone.utc),closing_cutoff=datetime(2026,10,1,23,59,59,999999,tzinfo=timezone.utc),reporting_currency_id=ids['usd_currency'],daily=True)
    instrument,group,cut,spot=setup(c,r);series=rates(c,r,instrument)
    original=c.execute(select(m.trade).where(m.trade.c.trade_id==equity)).mappings().one()
    c.execute(m.trade_lifecycle_event.insert().values(trade_id=equity,sequence_no=2,event_type='CANCELLED',event_datetime_utc=original['trade_datetime_utc'],recorded_by_user_account_id=ids['demo_user_account'],event_payload='{}'))
    fx_service.configure(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,'DIRECT',0,'Mock final rate',r.policy_id,cut)
    override=dict(rate='1.125',sourceReference='Mock counterparty',reason='Confirmed final closing rate')
    _,fingerprint,_,_=fx_service.candidate(c,r.tenant_id,r.strategy_id,instrument,rate_override=override)
    fx_service.post(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,instrument,fingerprint,str(uuid4()),rate_override=override)
    result=calculate_position(c,r)
    assert result.period.closing_value==0 and result.period.market_pnl==15000
    assert result.evidence['requiredMarkCount']==1


def test_cancelled_and_rebooked_maturity_uses_only_corrected_rate(valued):
    from lifecycle import fx_service
    from valuation.service import calculate_position
    from uuid import UUID
    c, r, equity = valued
    r = replace(r, opening_cutoff=datetime(2026,9,30,23,59,59,999999,tzinfo=timezone.utc), closing_cutoff=datetime(2026,10,1,23,59,59,999999,tzinfo=timezone.utc), reporting_currency_id=ids['usd_currency'], daily=True)
    instrument, group, cut, spot = setup(c, r)
    rates(c, r, instrument)
    original = c.execute(select(m.trade).where(m.trade.c.trade_id==equity)).mappings().one()
    c.execute(m.trade_lifecycle_event.insert().values(trade_id=equity,sequence_no=2,event_type='CANCELLED',event_datetime_utc=original['trade_datetime_utc'],recorded_by_user_account_id=ids['demo_user_account'],event_payload='{}'))
    fx_service.configure(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,'DIRECT',0,'Mock correction',r.policy_id,cut)
    _, fingerprint, _, _ = fx_service.candidate(c,r.tenant_id,r.strategy_id,instrument)
    posted = fx_service.post(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,instrument,fingerprint,str(uuid4()))
    assert calculate_position(c,r).period.market_pnl == 10000
    fx_service.cancel(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,UUID(posted['posting_id']),'Incorrect final rate',str(uuid4()))
    assert calculate_position(c,r).period.closing_value == 20000
    override = dict(rate='1.125',sourceReference='Synthetic corrected confirmation',reason='Correct final rate')
    _, fingerprint, _, _ = fx_service.candidate(c,r.tenant_id,r.strategy_id,instrument,rate_override=override)
    fx_service.post(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,instrument,fingerprint,str(uuid4()),rate_override=override)
    corrected = calculate_position(c,r)
    assert corrected.period.market_pnl == 15000
    assert corrected.period.closing_value == 0


def test_real_forward_reporting_currency_conversion_and_wrong_maturity_proof(valued):
    from valuation.service import calculate_position
    import pytest
    c,r,equity=valued
    r=replace(r,opening_cutoff=datetime(2026,9,30,23,59,59,999999,tzinfo=timezone.utc),closing_cutoff=datetime(2026,10,1,23,59,59,999999,tzinfo=timezone.utc),daily=True)
    instrument,group,cut,spot=setup(c,r);series=rates(c,r,instrument)
    original=c.execute(select(m.trade).where(m.trade.c.trade_id==equity)).mappings().one()
    c.execute(m.trade_lifecycle_event.insert().values(trade_id=equity,sequence_no=2,event_type='CANCELLED',event_datetime_utc=original['trade_datetime_utc'],recorded_by_user_account_id=ids['demo_user_account'],event_payload='{}'))
    c.execute(m.valuation_policy_rule.update().where(m.valuation_policy_rule.c.rule_sequence==99,m.valuation_policy_rule.c.valuation_policy_id==r.policy_id).values(allow_inverse_fx=True))
    # Quote USD -> strategy GBP uses explicitly permitted reciprocal GBP/USD.
    # Equal FX at opening/close means 10,000 / 1.12, rounded only in inverse proof.
    source=dict(c.execute(select(m.market_data_observation).where(m.market_data_observation.c.market_data_series_id==spot)).mappings().one())
    stamp=datetime(2026,9,30,16,tzinfo=timezone.utc)
    c.execute(m.market_data_observation.insert().values(**(source|dict(market_data_observation_id=uuid4(),market_date=stamp.date(),received_at_utc=stamp,
        observed_at_utc=stamp,source_published_at_utc=stamp,source_observation_key='FX_PREVIOUS_'+uuid4().hex))))
    result=calculate_position(c,r)
    assert result.period.market_pnl==D('8928.571428570000')
    assert any(s.get('conversion',{}).get('method')=='RECIPROCAL' for s in result.evidence['selections'])
    c.execute(m.market_data_series_dimension.update().where(m.market_data_series_dimension.c.market_data_series_id==series,
        m.market_data_series_dimension.c.dimension_code=='MATURITY_DATE').values(dimension_value='2026-12-01'))
    with pytest.raises(ValueError,match='contract-specific outright rate'):calculate_position(c,r)
