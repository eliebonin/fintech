"""Native linear futures through governed price/FX selection and publication."""
from dataclasses import replace
from datetime import datetime,time,timezone
from decimal import Decimal as D
from uuid import UUID,uuid4
import pytest
from sqlalchemy import select
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from tests.test_linear_futures_api import linear_future
from tests.test_valuation_service import valued
from tests.test_position_measures_assurance import add_direct_fx
from tests.test_cash_product_pnl_integration import stage


@pytest.fixture
def linear_inputs(linear_future,valued):
    from apps.reference_api.product_booking import load_context,book
    from apps.reference_api.product_booking_contracts import ProductBookingRequest
    c,r,_=valued;f=linear_future;node=UUID(f['node']);listing=UUID(f['listing'])
    r=replace(r,opening_cutoff=r.closing_cutoff.replace(day=30,month=9))
    def execute(side='BUY',quantity='2',price='100000',day='2026-09-29'):
        context=load_context(c,r.tenant_id,node,listing,datetime.fromisoformat(day).date())
        return book(c,r.tenant_id,ids['demo_user_account'],ProductBookingRequest.model_validate(dict(
            instrumentId=str(node),listingId=str(listing),strategyId=str(r.strategy_id),executionRoute='LISTED',
            side=side,quantity=quantity,executionPrice=price,tradeDatetime=day+'T10:00:00Z',
            positionEffect='OPEN' if side=='BUY' else 'CLOSE',expectedTermsFingerprint=context.terms_fingerprint)),
            str(uuid4()),'FUTURE','synthetic-linear-future')
    execute()
    rule=dict(c.execute(select(m.valuation_policy_rule).where(m.valuation_policy_rule.c.valuation_policy_rule_id==ids['valuation_policy_rule'])).mappings().one())
    cut=uuid4();c.execute(m.valuation_cut.insert().values(valuation_cut_id=cut,cut_code='LINEAR_'+cut.hex,
        display_name='Synthetic contract exchange cut',timezone_name='UTC',local_time=time(16),market_calendar_id=rule['market_calendar_id']))
    series=uuid4();source=dict(c.execute(select(m.market_data_series).where(m.market_data_series.c.market_data_series_id==ids['market_data_series'])).mappings().one())
    c.execute(m.market_data_series.insert().values(**(source|dict(market_data_series_id=series,reference_node_id=listing,
        currency_id=ids['usd_currency'],series_type='SETTLEMENT',closing_method='UNKNOWN',is_official=False,valuation_cut_id=cut))))
    for code,value in [('CONTRACT_INSTRUMENT_ID',str(node)),('FUTURE_PRICE_BASIS','UNDERLYING_UNIT'),('QUOTE_FACTOR','1')]:
        c.execute(m.market_data_series_dimension.insert().values(market_data_series_id=series,dimension_code=code,dimension_value=value))
    rule_id=uuid4();c.execute(m.valuation_policy_rule.insert().values(**(rule|dict(valuation_policy_rule_id=rule_id,rule_sequence=210,
        subject_reference_node_id=listing,market_data_series_id=series,series_type='SETTLEMENT',value_basis='RAW',price_requirement=None,
        require_official_close=False,pricing_convention='EXPLICIT_TIME',pricing_cut_id=cut))))
    observation=dict(c.execute(select(m.market_data_observation).where(m.market_data_observation.c.market_data_observation_id==ids['market_data_observation'])).mappings().one())
    for cutoff,value in [(r.opening_cutoff,'100000'),(r.closing_cutoff,'101000')]:
        stamp=datetime.combine(cutoff.date(),time(16),timezone.utc)
        c.execute(m.market_data_observation.insert().values(**(observation|dict(market_data_observation_id=uuid4(),market_data_series_id=series,
            valuation_cut_id=cut,market_date=stamp.date(),value=D(value),market_data_vintage_id=None,
            observed_at_utc=stamp,received_at_utc=stamp,source_published_at_utc=stamp,source_observation_key='LINEAR_'+uuid4().hex))))
        if cutoff==r.opening_cutoff:
            c.execute(m.market_data_observation.insert().values(**(observation|dict(market_data_observation_id=uuid4(),market_date=stamp.date(),
                market_data_vintage_id=None,observed_at_utc=stamp,received_at_utc=stamp,source_published_at_utc=stamp,source_observation_key='LINEAR_EQUITY_'+uuid4().hex))))
    add_direct_fx(c,r)
    c.execute(m.valuation_policy_rule.update().where(m.valuation_policy_rule.c.valuation_policy_id==r.policy_id,m.valuation_policy_rule.c.series_type=='FX_SPOT').values(allow_inverse_fx=True))
    return c,r,f,series,rule_id,execute


def line(result):return next(item for item in result.period.lines if item.bucket.key.product_basis=='FUTURE')


def test_cash_and_physical_crypto_native_bookings_use_actual_dimensions_and_can_publish(linear_inputs):
    from valuation.service import calculate_position
    from valuation import storage
    from valuation.amendments import request_component_change,approve_component_change
    from tests.test_position_attribution_storage import reviewer
    c,r,f,_,_,_=linear_inputs;result=calculate_position(c,r)
    assert line(result).attribution.market_pnl==D('1000')*D(f['size']) # 2 contracts × delta 1000 × multiplier × closing FX .5
    assert line(result).attribution.fx==0
    batch=stage(c,r,result);other=reviewer(c);view=storage.batch_view(c,r.tenant_id,batch)
    row=next(item for item in view['items'] if item['subject_id']==UUID(f['listing']))
    change=request_component_change(c,r.tenant_id,batch,row['attribution_id'],ids['demo_user_account'],
        dict(component='BROKER_FEE',amount=D('-1'),reason='Synthetic fee',sourceReference='Synthetic broker statement'),str(uuid4()))
    batch=approve_component_change(c,r.tenant_id,change,other,'Reviewed fee')
    storage.publish(c,r.tenant_id,batch,other,'Reviewed synthetic linear variation')
    assert storage.batch_view(c,r.tenant_id,batch)['status']=='PUBLISHED'


@pytest.mark.parametrize('dimension,value',[('CONTRACT_INSTRUMENT_ID',str(uuid4())),('FUTURE_PRICE_BASIS','INDEX_POINTS'),('QUOTE_FACTOR','100')])
def test_crypto_futures_cannot_use_spot_or_wrong_contract_dimensions(linear_inputs,dimension,value):
    from valuation.service import calculate_position,ValuationBlocked
    c,r,_,series,_,_=linear_inputs
    c.execute(m.market_data_series_dimension.update().where(m.market_data_series_dimension.c.market_data_series_id==series,
        m.market_data_series_dimension.c.dimension_code==dimension).values(dimension_value=value))
    with pytest.raises(ValuationBlocked):calculate_position(c,r)


@pytest.mark.parametrize('sell,want',[('1','750'),('2','500'),('3','250')])
def test_crypto_partial_full_and_short_crossings_keep_same_day_pnl(linear_inputs,sell,want):
    from valuation.service import calculate_position
    c,r,f,_,_,execute=linear_inputs;execute('SELL',sell,'100500',r.closing_cutoff.date().isoformat())
    assert line(calculate_position(c,r)).attribution.market_pnl==D(want)*D(f['size'])


def test_crypto_futures_do_not_gain_rights_or_visibility_from_the_underlying(linear_inputs):
    from valuation.service import calculate_position,ValuationBlocked
    c,r,_,series,_,_=linear_inputs
    with pytest.raises((ValueError,PermissionError)):calculate_position(c,replace(r,tenant_id=ids['second_tenant']))
    dataset=c.scalar(select(m.market_data_series.c.default_dataset_id).where(m.market_data_series.c.market_data_series_id==series))
    c.execute(m.tenant_dataset_entitlement.update().where(m.tenant_dataset_entitlement.c.tenant_id==r.tenant_id,
        m.tenant_dataset_entitlement.c.dataset_id==dataset,m.tenant_dataset_entitlement.c.use_purpose=='VALUATION').values(status='INACTIVE'))
    with pytest.raises(ValuationBlocked):calculate_position(c,r)


def test_changed_current_family_cannot_change_original_booked_pnl(linear_inputs):
    import json
    from valuation.service import calculate_position
    from apps.reference_api.product_booking import load_context
    c,r,f,_,_,_=linear_inputs
    family=c.execute(select(m.future_family).join(m.future_terms,m.future_terms.c.future_family_id==m.future_family.c.future_family_id)
        .where(m.future_terms.c.instrument_node_id==UUID(f['node']))).mappings().one()
    original=calculate_position(c,r)
    spec=json.loads(family['specification_payload']);spec.update(contractSize='99',monetaryMultiplier='99')
    c.execute(m.future_family.update().where(m.future_family.c.future_family_id==family['future_family_id']).values(specification_payload=json.dumps(spec)))
    context=load_context(c,r.tenant_id,UUID(f['node']),UUID(f['listing']),r.closing_cutoff.date())
    assert not context.booking_eligible and 'family' in context.ineligibility_message.lower()
    assert line(calculate_position(c,r)).attribution==line(original).attribution


def test_inactive_governed_crypto_role_blocks_new_booking_context(linear_inputs):
    from apps.reference_api.product_booking import load_context
    c,r,f,_,_,_=linear_inputs
    c.execute(m.currency.update().where(m.currency.c.currency_id==ids['mvp_btc_currency']).values(status='INACTIVE'))
    context=load_context(c,r.tenant_id,UUID(f['node']),UUID(f['listing']),r.closing_cutoff.date())
    assert not context.booking_eligible and 'cryptoasset' in context.ineligibility_message.lower()


def test_crypto_future_uses_its_governed_weekend_calendar_not_spot_or_bank_assumptions(linear_inputs):
    from datetime import date
    from valuation.service import _selection
    c,r,f,series,rule,_=linear_inputs;calendar,cut=uuid4(),uuid4()
    c.execute(m.market_calendar.insert().values(market_calendar_id=calendar,calendar_code='FUTURE_WEEKEND_'+calendar.hex,
        display_name='Synthetic futures Saturday settlement calendar',timezone_name='UTC',calendar_kind='TRADING'))
    c.execute(m.market_calendar_session.insert().values(market_calendar_id=calendar,session_date=date(2026,10,3),
        session_status='OPEN',open_local_time=time.min,close_local_time=time(23,59,59)))
    c.execute(m.market_calendar.update().where(m.market_calendar.c.market_calendar_id==calendar).values(sealed=True))
    c.execute(m.valuation_cut.insert().values(valuation_cut_id=cut,cut_code='FUTURE_WEEKEND_'+cut.hex,
        display_name='Synthetic futures Saturday cut',timezone_name='UTC',local_time=time(16),market_calendar_id=calendar))
    c.execute(m.valuation_policy_rule.update().where(m.valuation_policy_rule.c.valuation_policy_rule_id==rule).values(market_calendar_id=calendar,pricing_cut_id=cut))
    c.execute(m.market_data_series.update().where(m.market_data_series.c.market_data_series_id==series).values(valuation_cut_id=cut))
    source=dict(c.execute(select(m.market_data_observation).where(m.market_data_observation.c.market_data_series_id==series)).mappings().first())
    stamp=datetime(2026,10,3,16,tzinfo=timezone.utc)
    c.execute(m.market_data_observation.insert().values(**(source|dict(market_data_observation_id=uuid4(),market_date=stamp.date(),
        valuation_cut_id=cut,observed_at_utc=stamp,received_at_utc=stamp,source_published_at_utc=stamp,source_observation_key='FUTURE_WEEKEND_'+uuid4().hex))))
    r=replace(r,information_cutoff=max(r.information_cutoff,datetime.now(timezone.utc)))
    _,selected=_selection(c,r,UUID(f['listing']),stamp,'FUTURE',dimension_filters=(('CONTRACT_INSTRUMENT_ID',f['node']),('FUTURE_PRICE_BASIS','UNDERLYING_UNIT'),('QUOTE_FACTOR','1')))
    assert selected.pricing_date_used==stamp.date()
