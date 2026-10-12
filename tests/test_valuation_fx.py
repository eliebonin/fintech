"""Hand-calculated FX bridge, including new and fully closed positions."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
from uuid import UUID
import pytest
from tests.test_position_reconstruction import booked, request, OPEN, CLOSE, CURRENCY
from positions.reconstruction import reconstruct
from valuation.position_calculation import attribute_projection, MarkKey

GBP=UUID(int=888)


def test_open_holding_decomposes_price_fx_and_cross():
    p=reconstruct([booked(1,'100',OPEN,'75')],request())
    subject=p.buckets[0].key.subject_id
    marks={MarkKey(subject,OPEN):D('75'),MarkKey(subject,CLOSE):D('76')}
    result=attribute_projection(p,marks,GBP,{(CURRENCY,OPEN):D('.85'),(CURRENCY,CLOSE):D('.86')})
    assert result.market_pnl==D('161')
    assert result.lines[0].attribution.components()==dict(PRICE=D('85'),FX=D('75'),PRICE_FX_CROSS=D('1'))


def test_today_execution_uses_daily_end_fx_not_yesterday_fx():
    p=reconstruct([booked(1,'100',CLOSE,'75')],request())
    subject=p.buckets[0].key.subject_id
    result=attribute_projection(p,{MarkKey(subject,CLOSE):D('76')},GBP,{(CURRENCY,CLOSE):D('.86')})
    assert result.market_pnl==D('86')
    assert result.lines[0].attribution.fx==0
    assert result.lines[0].attribution.cross==0


def test_flat_round_trip_converts_realized_pnl_without_market_marks():
    p=reconstruct([booked(1,'100',OPEN+timedelta(hours=1),'75'),booked(2,'-100',CLOSE,'76')],request())
    result=attribute_projection(p,{},GBP,{(CURRENCY,CLOSE):D('.86')})
    assert result.market_pnl==D('86')
    assert result.closing_value==result.opening_value==0
    assert result.execution_value==D('-86')


def test_missing_fx_is_not_an_identity_conversion():
    p=reconstruct([booked(1,'100',CLOSE,'75')],request())
    with pytest.raises(ValueError,match='FX'):
        attribute_projection(p,{MarkKey(p.buckets[0].key.subject_id,CLOSE):D('76')},GBP,{})


def test_inverse_requires_explicit_orientation_and_rounding_evidence():
    from valuation.fx import conversion_rate
    assert conversion_rate(D('2'),inverse=True)==D('.500000000000')
    with pytest.raises(ValueError): conversion_rate(D('0'),inverse=True)


def test_service_freezes_independent_fx_inputs_and_uses_execution_day_rate(valued):
    from sqlalchemy import select
    from datetime import date,datetime,time,timezone
    from uuid import uuid4
    from security_master_schema import models as m
    from security_master_schema.demo_data import DEMO_IDS as ids
    from tests.test_valuation_service import service
    c,r,_=valued
    rule=c.execute(select(m.valuation_policy_rule).where(m.valuation_policy_rule.c.valuation_policy_rule_id==ids['valuation_policy_rule'])).mappings().one()
    cut=uuid4()
    c.execute(m.valuation_cut.insert().values(valuation_cut_id=cut,cut_code='FX_TEST_'+cut.hex,display_name='Synthetic FX cut',
        timezone_name='UTC',local_time='16:00',market_calendar_id=rule['market_calendar_id']))
    source=dict(c.execute(select(m.market_data_observation).where(m.market_data_observation.c.market_data_observation_id==ids['market_data_observation'])).mappings().one())
    series=uuid4()
    c.execute(m.market_data_series.insert().values(market_data_series_id=series,reference_node_id=ids['gbpusd_fx_pair_node'],
        default_dataset_id=source['dataset_id'],series_type='FX_SPOT',value_type='RATE',currency_id=ids['usd_currency'],
        source_system_id='SYNTHETIC_FX_TEST',
        valuation_cut_id=cut,measure_definition_id=c.scalar(select(m.series_measure_definition.c.series_measure_definition_id).where(m.series_measure_definition.c.measure_code=='FX_RATE'))))
    for code,value in [('BASE_CURRENCY','GBP'),('QUOTE_CURRENCY','USD')]:
        c.execute(m.market_data_series_dimension.insert().values(market_data_series_id=series,dimension_code=code,dimension_value=value))
    c.execute(m.valuation_policy_rule.insert().values(valuation_policy_id=r.policy_id,rule_sequence=99,subject_type='FX_PAIR',
        series_type='FX_SPOT',value_basis='RAW',market_data_series_id=series,pricing_convention='EXPLICIT_TIME',pricing_cut_id=cut,
        market_calendar_id=rule['market_calendar_id'],selection_method='LAST_BEFORE_CUT',max_staleness_business_days=0))
    # Execution is Sep30. Using Oct1 FX for it would incorrectly subtract .246
    # rather than .1845, losing .0615 of economic FX P&L.
    for day,rate in [(date(2026,9,30),'1.5'),(date(2026,10,1),'2')]:
        stamp=datetime.combine(day,time(16),timezone.utc)
        c.execute(m.market_data_observation.insert().values(**(source|dict(market_data_observation_id=uuid4(),market_data_series_id=series,
            market_date=day,value=D(rate),market_data_vintage_id=None,observed_at_utc=stamp,received_at_utc=stamp,source_published_at_utc=stamp,
            source_observation_key='SYNTHETIC_FX_'+uuid4().hex))))
    # Held overnight: requires Sep30 close in addition to final close.
    stamp=datetime(2026,9,30,16,tzinfo=timezone.utc)
    c.execute(m.market_data_observation.insert().values(**(source|dict(market_data_observation_id=uuid4(),market_date=stamp.date(),value=D('1050'),
        market_data_vintage_id=None,observed_at_utc=stamp,received_at_utc=stamp,source_published_at_utc=stamp,source_observation_key='MID_'+uuid4().hex))))
    result=service().calculate(c,replace(r,reporting_currency_id=ids['usd_currency']))
    assert result.period.closing_value==D('220')
    assert result.period.execution_value==D('.1845')
    assert result.period.market_pnl==D('219.8155')
    assert len([s for s in result.evidence['selections'] if s.get('input_role')=='FX'])==2


from tests.test_valuation_service import valued
