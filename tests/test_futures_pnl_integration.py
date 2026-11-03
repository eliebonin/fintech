"""Real approved contracts, immutable bookings, governed prices and publication."""
from dataclasses import asdict,replace
from datetime import datetime,time,timezone
from decimal import Decimal as D
from uuid import uuid4
import pytest
from sqlalchemy import select
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from tests.test_product_booking_api import future
from tests.test_valuation_service import valued
from tests.test_future_measure_inputs import future_inputs
from tests.test_position_measures_assurance import add_direct_fx


def ready(future_inputs):
    c,r,series,rule,execute=future_inputs
    r=replace(r,opening_cutoff=r.closing_cutoff.replace(day=30,month=9))
    source=dict(c.execute(select(m.market_data_observation).where(m.market_data_observation.c.market_data_observation_id==ids['market_data_observation'])).mappings().one())
    stamp=datetime.combine(r.opening_cutoff.date(),time(16),timezone.utc)
    c.execute(m.market_data_observation.insert().values(**(source|dict(market_data_observation_id=uuid4(),market_date=stamp.date(),
        value=D('1000'),market_data_vintage_id=None,observed_at_utc=stamp,received_at_utc=stamp,source_published_at_utc=stamp,
        source_observation_key='FUTURES_BRIDGE_'+uuid4().hex))))
    c.execute(m.market_data_observation.update().where(m.market_data_observation.c.market_data_series_id==series).values(value=D('6010')))
    add_direct_fx(c,r)
    c.execute(m.valuation_policy_rule.update().where(m.valuation_policy_rule.c.valuation_policy_id==r.policy_id,
        m.valuation_policy_rule.c.series_type=='FX_SPOT').values(allow_inverse_fx=True))
    return c,r,series,rule,execute


@pytest.mark.parametrize('amend',[False,True])
def test_existing_future_booking_calculates_stages_and_publishes(future_inputs,amend):
    from valuation.service import calculate_position
    from valuation import storage,tables as t
    from valuation.economics import canonical_payload,evidence_hash
    from valuation.evidence_access import assert_batch_display
    c,r,_,_,_=ready(future_inputs)
    result=calculate_position(c,r)
    line=next(line for line in result.period.lines if line.bucket.key.product_basis=='FUTURE')
    assert line.attribution.market_pnl==250  # 10 contracts × 5 × 10 points × .5 GBP/USD
    assert line.attribution.fx==0 and line.settlement_variation==250
    actor=ids['demo_user_account']
    attempt=c.scalar(t.attempt.insert().values(tenant_id=r.tenant_id,strategy_id=r.strategy_id,initiated_by=actor,
        request_key=str(uuid4()),request_hash=evidence_hash(dict(request=storage.request_identity(r),actor=actor)),
        request_payload=canonical_payload(asdict(r)),correlation_id=str(uuid4()),status='RUNNING').returning(t.attempt.c.attempt_id))
    batch=storage.stage(c,attempt,actor,result)
    view=storage.batch_view(c,r.tenant_id,batch)
    row=next(item for item in view['items'] if item['evidence']['identity']['bucket']['key']['product_basis']=='FUTURE')
    assert row['evidence']['identity']['openingValue'] is None
    assert row['evidence']['identity']['closingValue'] is None
    assert D(view['summary']['futuresVariationPnl'])==250
    assert any(rule['code']=='FUTURES_DAILY_VARIATION' for rule in row['evidence']['appliedRules'])
    assert_batch_display(c,r.tenant_id,view)
    reviewer=c.scalar(select(m.user_account.c.user_account_id).where(m.user_account.c.user_account_id!=actor,m.user_account.c.status=='ACTIVE').limit(1))
    assert reviewer is not None
    if amend:
        from valuation.amendments import request_component_change,approve_component_change
        change=request_component_change(c,r.tenant_id,batch,row['attribution_id'],actor,
            dict(component='BROKER_FEE',amount=D('-1'),reason='Synthetic exchange fee',sourceReference='Synthetic broker statement'),str(uuid4()))
        batch=approve_component_change(c,r.tenant_id,change,reviewer,'Reviewed synthetic fee.')
        after=storage.batch_view(c,r.tenant_id,batch)
        amended=next(item for item in after['items'] if item['evidence']['identity']['bucket']['key']['product_basis']=='FUTURE')
        assert amended['market_pnl']==250 and amended['net_pnl']==249
        assert D(after['summary']['futuresVariationPnl'])==250
    storage.publish(c,r.tenant_id,batch,reviewer,'Reviewed synthetic futures daily variation.')
    assert storage.batch_view(c,r.tenant_id,batch)['status']=='PUBLISHED'


@pytest.mark.parametrize('dimension,value',[
    ('CONTRACT_INSTRUMENT_ID',str(uuid4())),('QUOTE_FACTOR','100'),('FUTURE_PRICE_BASIS','UNDERLYING_UNIT')])
def test_wrong_contract_or_price_units_are_rejected(future_inputs,dimension,value):
    from valuation.service import calculate_position,ValuationBlocked
    c,r,series,_,_=ready(future_inputs)
    c.execute(m.market_data_series_dimension.update().where(m.market_data_series_dimension.c.market_data_series_id==series,
        m.market_data_series_dimension.c.dimension_code==dimension).values(dimension_value=value))
    with pytest.raises(ValuationBlocked):calculate_position(c,r)
