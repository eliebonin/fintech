"""Real futures approval/booking and governed exact-expiry price/FX selection."""
from dataclasses import replace
from datetime import time,timedelta
from decimal import Decimal as D
from uuid import UUID,uuid4
import pytest
from sqlalchemy import select
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from tests.test_product_booking_api import future
from tests.test_valuation_service import valued
from tests.test_measure_inputs import preview
from tests.test_position_measures_assurance import add_direct_fx


@pytest.fixture
def future_inputs(future,valued):
    from apps.reference_api.product_booking import load_context,book
    from apps.reference_api.product_booking_contracts import ProductBookingRequest
    c,r,_=valued;node,listing=map(UUID,future)
    context=load_context(c,r.tenant_id,node,listing,r.closing_cutoff.date())
    def execute(side,quantity):
        return book(c,r.tenant_id,ids['demo_user_account'],ProductBookingRequest.model_validate(dict(
            instrumentId=str(node),listingId=str(listing),strategyId=str(r.strategy_id),executionRoute='LISTED',
            side=side,quantity=quantity,executionPrice='6000',tradeDatetime='2026-10-01T10:00:00Z',
            positionEffect='OPEN' if side=='BUY' else 'CLOSE',expectedTermsFingerprint=context.terms_fingerprint)),
            str(uuid4()),'FUTURE','measure-future')
    execute('BUY','10')
    source=dict(c.execute(select(m.market_data_series).where(m.market_data_series.c.market_data_series_id==ids['market_data_series'])).mappings().one())
    rule=dict(c.execute(select(m.valuation_policy_rule).where(m.valuation_policy_rule.c.valuation_policy_rule_id==ids['valuation_policy_rule'])).mappings().one())
    cut=uuid4()
    c.execute(m.valuation_cut.insert().values(valuation_cut_id=cut,cut_code='FUTURE_MEASURE_'+cut.hex,display_name='Synthetic futures cut',
        timezone_name='UTC',local_time=time(16),market_calendar_id=rule['market_calendar_id']))
    series=uuid4()
    c.execute(m.market_data_series.insert().values(**(source|dict(market_data_series_id=series,reference_node_id=listing,
        currency_id=ids['usd_currency'],series_type='CLOSE',closing_method='UNKNOWN',is_official=False,valuation_cut_id=cut))))
    for code,value in [('CONTRACT_INSTRUMENT_ID',str(node)),('FUTURE_PRICE_BASIS','INDEX_POINTS'),('QUOTE_FACTOR','1')]:
        c.execute(m.market_data_series_dimension.insert().values(market_data_series_id=series,dimension_code=code,dimension_value=value))
    rule_id=uuid4()
    c.execute(m.valuation_policy_rule.insert().values(**(rule|dict(valuation_policy_rule_id=rule_id,rule_sequence=210,
        subject_reference_node_id=listing,market_data_series_id=series,series_type='CLOSE',value_basis='RAW',price_requirement=None,
        require_official_close=False,pricing_convention='EXPLICIT_TIME',pricing_cut_id=cut))))
    source=dict(c.execute(select(m.market_data_observation).where(m.market_data_observation.c.market_data_observation_id==ids['market_data_observation'])).mappings().one())
    stamp=r.closing_cutoff.replace(hour=16,minute=0,second=0,microsecond=0)
    c.execute(m.market_data_observation.insert().values(**(source|dict(market_data_observation_id=uuid4(),market_data_series_id=series,
        valuation_cut_id=cut,market_date=stamp.date(),value=D('6000'),market_data_vintage_id=None,observed_at_utc=stamp,
        received_at_utc=stamp,source_published_at_utc=stamp,source_observation_key='FUTURE_MEASURE_'+uuid4().hex))))
    return c,r,series,rule_id,execute


def future_row(c,r):return next(x for x in preview(c,r)['items'] if x['instrumentType']=='FUTURE')


@pytest.mark.parametrize('price_type',['CLOSE','SETTLEMENT'])
def test_futures_current_notional_uses_exact_expiry_and_converts_to_fund_currency(future_inputs,price_type):
    c,r,series,rule,execute=future_inputs
    c.execute(m.market_data_series.update().where(m.market_data_series.c.market_data_series_id==series).values(series_type=price_type))
    c.execute(m.valuation_policy_rule.update().where(m.valuation_policy_rule.c.valuation_policy_rule_id==rule).values(series_type=price_type))
    add_direct_fx(c,r)
    c.execute(m.valuation_policy_rule.update().where(m.valuation_policy_rule.c.valuation_policy_id==r.policy_id,
        m.valuation_policy_rule.c.series_type=='FX_SPOT').values(allow_inverse_fx=True))
    row=future_row(c,r)
    for name in ('referenceNotional','economicExposure'):
        assert row['measures'][name]==dict(localAmount='300000',currency='USD',strategyAmount='150000',strategyCurrency='GBP',status='AVAILABLE'),row['evidence']['issues']
    assert row['measures']['marketValue']['localAmount'] is None
    assert row['measures']['marketValue']['strategyAmount'] is None
    assert row['measures']['marketValue']['reasonCode']=='NOT_SUPPORTED_YET'
    assert 'variation' in row['evidence']['issues']['marketValue'].lower()
    # Listing metadata is 5, but quantity already counts canonical contracts:
    # apply monetary multiplier 5 once, not 5*5. The normal sell closes only 14.
    execute('SELL','14')
    row=future_row(c,r)
    assert row['quantity']=='-4'
    assert row['measures']['economicExposure']['localAmount']=='-120000'
    assert row['measures']['economicExposure']['strategyAmount']=='-60000'


def test_missing_fx_keeps_native_exposure_and_mtm_unavailable(future_inputs):
    c,r,_,_,_=future_inputs;row=future_row(c,r)
    assert row['measures']['economicExposure']['status']=='LOCAL_ONLY',row['evidence']['issues']
    assert row['measures']['economicExposure']['localAmount']=='300000'
    assert row['measures']['marketValue']['status']=='UNAVAILABLE'


@pytest.mark.parametrize('dimension,value',[('CONTRACT_INSTRUMENT_ID',str(uuid4())),('FUTURE_PRICE_BASIS','CONTINUOUS'),('QUOTE_FACTOR','100')])
def test_incompatible_contract_price_metadata_never_becomes_exposure(future_inputs,dimension,value):
    c,r,series,_,_=future_inputs
    assert future_row(c,r)['measures']['economicExposure']['localAmount']=='300000'
    c.execute(m.market_data_series_dimension.update().where(m.market_data_series_dimension.c.market_data_series_id==series,
        m.market_data_series_dimension.c.dimension_code==dimension).values(dimension_value=value))
    assert future_row(c,r)['measures']['economicExposure']['localAmount'] is None


def test_unclosed_expired_future_is_not_valued_or_silently_zeroed(future_inputs):
    c,r,_,_,_=future_inputs
    r=replace(r,closing_cutoff=r.closing_cutoff+timedelta(days=200))
    row=future_row(c,r)
    assert row['quantity']=='10'
    assert row['measures']['economicExposure']['localAmount'] is None
    assert 'final settlement' in row['evidence']['issues']['contract'].lower()


@pytest.mark.parametrize('changes',[
    {'monetaryMultiplier':'6'}, {'quoteFactor':'100'}, {'priceCurrencyId':str(ids['gbp_currency'])},
    {'priceBasis':'UNDERLYING_UNIT','contractSize':'5','contractSizeCurrencyId':str(ids['usd_currency'])}])
def test_incompatible_or_creation_only_frozen_conventions_block_measures(future_inputs,changes):
    # Challenge the adapter's retained-input boundary in memory; never rewrite
    # immutable BOOKED events, even in the owned synthetic database.
    from positions.contracts import ProjectionRequest
    from positions.holdings_repository import load_holdings_facts
    from positions.holdings import project_holdings
    from apps.reference_api.strategy_workspace import position_rows
    from valuation.measure_inputs import preview_measures
    c,r,_,_,_=future_inputs
    request=ProjectionRequest(r.tenant_id,r.strategy_id,r.closing_cutoff,r.information_cutoff)
    facts,descriptions=load_holdings_facts(c,request)
    projection=project_holdings(facts,request)
    for description in descriptions.values():
        terms=description['bookingEvidence'].get('economics',{}).get('terms',{})
        if terms.get('kind')=='FUTURE':terms['convention'].update(changes)
    row=next(x for x in preview_measures(c,r,projection,descriptions,position_rows(projection,descriptions))['items'] if x['instrumentType']=='FUTURE')
    assert all(m['localAmount'] is None for m in row['measures'].values())
    assert row['evidence']['issues']['contract']
