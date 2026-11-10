"""Independent values for held products; no invented Greeks or MTM."""
from decimal import Decimal as D
from sqlalchemy import select
import pytest
from security_master_schema import models as m
from tests.test_valuation_service import valued
from tests.test_measure_inputs import preview
from tests.test_linear_futures_api import linear_future
from tests.test_linear_futures_pnl_integration import linear_inputs
from tests.test_option_booking_api import listing
from tests.test_product_booking_api import structured


def test_spot_crypto_has_three_venue_specific_quote_currency_measures(valued):
    from tests.test_cash_product_pnl_integration import ready
    c,r,_,subject,_,_,execute=ready(valued,'DIGITAL_ASSET')
    execute(quantity='2')
    row=next(x for x in preview(c,r)['items'] if x['subjectId']==str(subject))
    assert {m['localAmount'] for m in row['measures'].values()}=={'220'},row['evidence']['issues']
    assert {m['currency'] for m in row['measures'].values()}=={'GBP'}


def test_linear_crypto_futures_notional_is_not_clearing_market_value(linear_inputs):
    c,r,f,_,_,_=linear_inputs
    row=next(x for x in preview(c,r)['items'] if x['instrumentType']=='FUTURE')
    for name in ('referenceNotional','economicExposure'):
        assert D(row['measures'][name]['localAmount'])==D('202000')*D(f['size']),row['evidence']['issues']
    assert row['measures']['marketValue']['localAmount'] is None
    assert row['measures']['marketValue']['reasonCode']=='NOT_SUPPORTED_YET'


def test_option_premium_value_and_contractual_strike_notional_are_distinct(listing,valued):
    from tests.test_option_valuation_integration import setup_option
    c,r,_,_=setup_option(listing,valued)
    row=next(x for x in preview(c,r)['items'] if x['instrumentType']=='OPTION')
    assert row['measures']['marketValue']['localAmount']=='56000',row['evidence']['issues']
    assert row['measures']['referenceNotional']['localAmount']=='20000'
    assert row['measures']['referenceNotional']['basis']=='STRIKE_NOTIONAL'
    assert row['measures']['economicExposure']['localAmount'] is None
    assert row['measures']['economicExposure']['reasonCode']=='NOT_SUPPORTED_YET'


@pytest.mark.parametrize('unit',['NOMINAL','UNITS'])
def test_fully_funded_note_whole_mark_does_not_become_underlying_risk(valued,structured,unit):
    from tests.test_structured_note_pnl_integration import ready
    c,r,_,_,_=ready(valued,structured,unit=unit)
    row=next(x for x in preview(c,r)['items'] if x['instrumentType']=='STRUCTURED_PRODUCT')
    assert row['measures']['referenceNotional']['localAmount']=='100000',row['evidence']['issues']
    assert row['measures']['marketValue']['localAmount']=='99000',row['evidence']['issues']
    assert row['measures']['economicExposure']['localAmount'] is None
    assert row['measures']['economicExposure']['reasonCode']=='NOT_SUPPORTED_YET'


def test_quantity_reader_recovers_option_type_and_note_unit_multiplier():
    from positions.holdings_repository import holding_conventions
    assert holding_conventions({'kind':'OPTION_BOOKING','economics':{'terms':{'premiumMultiplier':'100','quoteFactor':'1'}}},'CONTRACTS')==('OPTION',D('100'),D('1'))
    payload={'kind':'PRODUCT_BOOKING','economics':{'terms':{'kind':'STRUCTURED_PRODUCT','convention':{'kind':'STRUCTURED_PRODUCT','priceBasis':'PCT_OF_PAR','denomination':'1000','quoteFactor':'100'}}}}
    assert holding_conventions(payload,'UNITS')==('STRUCTURED_PRODUCT',D('1000'),D('100'))


@pytest.mark.parametrize('premium,want',[('0','0'),('28','-5600')])
def test_option_short_sign_and_zero_premium_are_exact(premium,want):
    from valuation.position_measures import vanilla_option
    result=vanilla_option(D('-2'),D(premium),D('100'),D('1'),D('5800'),D('100'))
    assert result['marketValue']==D(want)
    assert result['referenceNotional']==D('-1160000')
    assert result['economicExposure'] is None


def test_missing_option_premium_keeps_known_strike_notional(listing,valued):
    from tests.test_option_valuation_integration import setup_option
    c,r,_,series=setup_option(listing,valued)
    c.execute(m.market_data_series_dimension.update().where(m.market_data_series_dimension.c.market_data_series_id==series,
        m.market_data_series_dimension.c.dimension_code=='PREMIUM_MULTIPLIER').values(dimension_value='1'))
    row=next(x for x in preview(c,r)['items'] if x['instrumentType']=='OPTION')
    assert row['measures']['referenceNotional']['localAmount']=='20000'
    assert row['measures']['marketValue']['localAmount'] is None
    assert row['measures']['marketValue']['reasonCode']=='MISSING_INPUT'


def test_option_native_and_strategy_values_use_governed_fx(listing,valued):
    from dataclasses import replace
    from security_master_schema.demo_data import DEMO_IDS as ids
    from tests.test_option_valuation_integration import setup_option
    from tests.test_position_measures_assurance import add_direct_fx
    c,r,_,_=setup_option(listing,valued);add_direct_fx(c,r)
    row=next(x for x in preview(c,replace(r,reporting_currency_id=ids['usd_currency']))['items'] if x['instrumentType']=='OPTION')
    assert row['measures']['referenceNotional']['strategyAmount']=='40000'
    assert row['measures']['marketValue']['localAmount']=='56000'
    assert row['measures']['marketValue']['strategyAmount']=='112000'


def test_note_dirty_value_requires_no_separate_accrued_stock(valued,structured):
    from tests.test_structured_note_pnl_integration import ready
    c,r,_,_,_=ready(valued,structured,basis='DIRTY')
    row=next(x for x in preview(c,r)['items'] if x['instrumentType']=='STRUCTURED_PRODUCT')
    assert row['measures']['marketValue']['localAmount']=='99000',row['evidence']['issues']
    assert row['evidence']['route']=='NOTE_DIRTY_PRICE'
    assert 'accruedBalance' not in row['evidence']['selections']


def test_note_clean_value_needs_assessed_closing_stock_not_daily_earnings(valued,structured):
    from uuid import uuid4
    from security_master_schema.demo_data import DEMO_IDS as ids
    from tests.test_structured_note_pnl_integration import ready
    from valuation.accruals import record_accrual,accrual_amounts
    c,r,node,_,_=ready(valued,structured,basis='CLEAN')
    row=next(x for x in preview(c,r)['items'] if x['instrumentType']=='STRUCTURED_PRODUCT')
    assert row['measures']['referenceNotional']['localAmount']=='100000'
    assert row['measures']['marketValue']['localAmount'] is None
    values=dict(openingBalance=D('125'),dailyEarned=D('0'),closingBalance=D('125'),balanceMovements=D('0'),openingFx=D('1'),closingFx=D('1'))
    record_accrual(c,r.tenant_id,ids['demo_user_account'],dict(strategyId=r.strategy_id,instrumentId=node,
        currencyId=ids['gbp_currency'],reportingCurrencyId=ids['gbp_currency'],valueDate=r.closing_cutoff.date(),
        inputType='DAILY_INTEREST',dailyEarned=D('0'),eligibleNominal=D('100000'),inputs=values,amounts=accrual_amounts(values),
        sourceReference='Synthetic assessed note closing bridge',policyId=str(r.policy_id),cutId=str(r.cut_id)),uuid4().hex)
    row=next(x for x in preview(c,r)['items'] if x['instrumentType']=='STRUCTURED_PRODUCT')
    assert row['measures']['marketValue']['localAmount']=='99125',row['evidence']['issues']
    assert row['evidence']['selections']['accruedBalance']['nominalBasis']=='CURRENT_SCOPED_NOTE_HOLDING'


def test_periodic_non_index_swap_still_has_reference_and_whole_mark_value(valued,tmp_path):
    from tests.test_swap_valuation_integration import setup_swap
    c,r,_,series=setup_swap(valued,tmp_path)
    row=next(x for x in preview(c,r)['items'] if x['instrumentType']=='SWAP')
    assert row['measures']['referenceNotional']['localAmount']=='10000',row['evidence']['issues']
    assert row['measures']['marketValue']['localAmount']=='0',row['evidence']['issues']
    assert row['measures']['economicExposure']['reasonCode']=='NOT_SUPPORTED_YET'
    c.execute(m.market_data_observation.update().where(m.market_data_observation.c.market_data_series_id==series).values(value=D('-2')))
    row=next(x for x in preview(c,r)['items'] if x['instrumentType']=='SWAP')
    assert row['measures']['marketValue']['localAmount']=='-200'
    assert row['measures']['referenceNotional']['localAmount']=='10000'


def test_rate_exchange_swap_whole_value_is_not_duplicated_across_legs(valued):
    from uuid import uuid4
    from datetime import datetime,time,timezone
    from security_master_schema.demo_data import DEMO_IDS as ids
    from tests.test_rate_swap_booking import create,request,book
    c,r,_=valued;node=create(c,request(c));book(c,r,node,quantity='100',price='0')
    source=dict(c.execute(select(m.market_data_series).where(m.market_data_series.c.market_data_series_id==ids['market_data_series'])).mappings().one())
    series=uuid4();c.execute(m.market_data_series.insert().values(**(source|dict(market_data_series_id=series,reference_node_id=node,series_type='MARK',closing_method='UNKNOWN',is_official=False))))
    for code,value in [('SWAP_PRICE_BASIS','WHOLE_SWAP_MTM_PER_NOTIONAL'),('QUANTITY_UNIT','NOMINAL'),('QUOTE_FACTOR','1')]:
        c.execute(m.market_data_series_dimension.insert().values(market_data_series_id=series,dimension_code=code,dimension_value=value))
    rule=dict(c.execute(select(m.valuation_policy_rule).where(m.valuation_policy_rule.c.valuation_policy_rule_id==ids['valuation_policy_rule'])).mappings().one())
    c.execute(m.valuation_policy_rule.insert().values(**(rule|dict(valuation_policy_rule_id=uuid4(),rule_sequence=540,
        subject_type='INSTRUMENT',subject_reference_node_id=node,instrument_type_id=None,market_venue_id=None,is_default=False,
        market_data_series_id=series,series_type='MARK',value_basis='RAW',price_requirement=None,require_official_close=False,
        pricing_convention='EXPLICIT_TIME',pricing_cut_id=ids['valuation_cut']))))
    obs=dict(c.execute(select(m.market_data_observation).where(m.market_data_observation.c.market_data_observation_id==ids['market_data_observation'])).mappings().one())
    stamp=datetime.combine(r.closing_cutoff.date(),time(14),timezone.utc)
    c.execute(m.market_data_observation.insert().values(**(obs|dict(market_data_observation_id=uuid4(),market_data_series_id=series,market_date=stamp.date(),
        value=D('-.25'),value_basis='RAW',market_data_vintage_id=None,observed_at_utc=stamp,received_at_utc=stamp,
        source_published_at_utc=stamp,source_observation_key='RATE_MEASURES_'+uuid4().hex))))
    row=next(x for x in preview(c,r)['items'] if x['subjectId']==str(node))
    assert row['measures']['referenceNotional']['localAmount']=='100',row['evidence']['issues']
    assert row['measures']['marketValue']['localAmount']=='-25',row['evidence']['issues']
    assert row['measures']['economicExposure']['reasonCode']=='NOT_SUPPORTED_YET'


@pytest.mark.parametrize('basis',['NONE','DIRTY','CLEAN'])
def test_native_unit_price_note_value_and_explicit_stock_nominal_mapping(valued,structured,monkeypatch,basis):
    import tests.test_structured_note_pnl_integration as fixture
    original=fixture.structured_convention
    monkeypatch.setattr(fixture,'structured_convention',lambda **kw:original(**(kw|dict(priceBasis='UNIT_PRICE',quoteFactor='1',denomination=None))))
    c,r,_,series,_=fixture.ready(valued,structured,unit='UNITS',basis=basis)
    for code,value in [('STRUCTURED_PRICE_BASIS','UNIT_PRICE'),('QUOTE_FACTOR','1')]:
        c.execute(m.market_data_series_dimension.update().where(m.market_data_series_dimension.c.market_data_series_id==series,
            m.market_data_series_dimension.c.dimension_code==code).values(dimension_value=value))
    row=next(x for x in preview(c,r)['items'] if x['instrumentType']=='STRUCTURED_PRODUCT')
    if basis=='CLEAN':
        assert row['measures']['marketValue']['localAmount'] is None
        assert 'nominal mapping' in row['evidence']['issues']['accruedBalance']
    else:
        assert row['measures']['referenceNotional']['localAmount']=='9900',row['evidence']['issues']
        assert row['measures']['marketValue']['localAmount']=='9900'
        assert row['measures']['referenceNotional']['basis']=='FUNDED_MARKET_VALUE_PROXY'


def test_equivalent_option_decimal_scales_do_not_change_contract_identity():
    from types import SimpleNamespace
    from datetime import date
    from uuid import uuid4
    from valuation.measure_contracts import option_terms
    node,subject,currency=uuid4(),uuid4(),uuid4()
    bucket=SimpleNamespace(key=SimpleNamespace(quantity_unit='CONTRACTS',subject_id=subject,unit_multiplier=D('100'),quote_factor=D('1')))
    terms=dict(instrumentId=str(node),listingId=str(subject),optionType='PUT',underlyingId=str(uuid4()),strike='10',
        strikeCurrency='USD',deliverableUnits='100',expiryDate='2027-01-01',premiumCurrency='USD',premiumMultiplier='100',quoteFactor='1')
    _,actual=option_terms(bucket,[terms,terms|dict(strike='10.00',premiumMultiplier='100.0',quoteFactor='1.00')],{currency:'USD'},date(2026,10,1))
    assert actual==currency


@pytest.mark.parametrize('action',['WARN','MANUAL_OVERRIDE'])
def test_policy_permitted_missing_mark_is_an_unavailable_measure_not_a_page_failure(valued,action):
    from uuid import uuid4
    from security_master_schema.demo_data import DEMO_IDS as ids
    c,r,_=valued;empty=uuid4()
    source=dict(c.execute(select(m.market_data_series).where(m.market_data_series.c.market_data_series_id==ids['market_data_series'])).mappings().one())
    c.execute(m.market_data_series.insert().values(**(source|dict(market_data_series_id=empty,source_system_id='SYNTHETIC_EMPTY_'+empty.hex))))
    c.execute(m.valuation_policy_rule.update().where(m.valuation_policy_rule.c.valuation_policy_rule_id==ids['valuation_policy_rule']).values(market_data_series_id=empty,missing_data_action=action))
    row=preview(c,r)['items'][0]
    assert all(value['localAmount'] is None and value['reasonCode']=='MISSING_INPUT' for value in row['measures'].values())
