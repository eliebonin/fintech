"""Whole-wrapper/spot units use their own quote, not underlying exposure."""
from dataclasses import replace
from decimal import Decimal as D
from uuid import UUID
import pytest
from tests.test_position_reconstruction import booked,request,OPEN,CLOSE,SUBJECT,CURRENCY
from positions.reconstruction import reconstruct
from valuation.position_calculation import attribute_projection,MarkKey

WRAPPERS=('ETC','ETN','ETV','ETI','EXCHANGE_TRADED_VEHICLE','EXCHANGE_TRADED_CERTIFICATE')


def test_generic_etp_requires_a_unique_effective_concrete_kind_and_preserves_original_binding():
    from datetime import date
    from security_master_schema.cash_products import cash_product_basis
    day=OPEN.date();term=dict(etp_terms_id=UUID(int=88),etp_kind='ETN',effective_from=day,effective_to=None,status='ACTIVE')
    assert cash_product_basis('ETP',[term],day)==('ETN',term['etp_terms_id'])
    for terms in ([],[term,term|dict(etp_terms_id=UUID(int=89))]):
        with pytest.raises(ValueError):cash_product_basis('ETP',terms,day)
    with pytest.raises(ValueError):cash_product_basis('ETP',[term],day,dict(productBasis='ETF',etpTermsId=str(term['etp_terms_id'])))
    with pytest.raises(ValueError):cash_product_basis('ETN',[],day,dict(productBasis='ETC'))


def test_prior_share_label_and_new_unit_label_are_the_same_wrapper_unit_without_rescaling():
    from security_master_schema.cash_products import canonical_cash_unit
    for product in (*WRAPPERS,'DIGITAL_ASSET','FUND'):
        assert canonical_cash_unit(product,'SHARES')==canonical_cash_unit(product,'UNITS')=='UNITS'
    assert canonical_cash_unit('EQUITY','SHARES')=='SHARES'


def test_native_raw_zero_survives_as_traded_selection_but_positive_underflow_does_not_become_zero():
    from market_data.price_basis import normalise_as_traded
    assert normalise_as_traded(D(0),'RAW',None,allow_split_conversion=False).valuation_value==0
    for value in (D('-1'),D('NaN'),D('1e-20')):
        with pytest.raises(ValueError):normalise_as_traded(value,'RAW',None,allow_split_conversion=False)


@pytest.mark.parametrize('kind,code',[('ETN','QUOTED_WRAPPER_PRICE'),('DIGITAL_ASSET','SPOT_DIGITAL_ASSET_PRICE')])
def test_readable_rules_explain_the_product_without_repricing(kind,code):
    from valuation.decisions import applied_decisions
    rules=applied_decisions(dict(identity=dict(bucket=dict(key=dict(product_basis=kind,unit_multiplier='1',quote_factor='1',quantity_unit='UNITS')))))
    assert code in {rule['code'] for rule in rules}


@pytest.mark.parametrize('product',WRAPPERS)
@pytest.mark.parametrize('unit',['SHARES','UNITS'])
def test_actual_wrapper_type_and_frozen_factors_are_used_once(product,unit):
    from valuation.product_inputs import supported_product
    assert supported_product(product,unit)=='PRICE'
    p=reconstruct([booked(1,'1000',OPEN,product_basis=product,quantity_unit=unit,unit_multiplier=D(3),quote_factor=D(100))],request())
    line=attribute_projection(p,{MarkKey(SUBJECT,OPEN):D(100),MarkKey(SUBJECT,CLOSE):D(102)},UUID(int=99),
        {(CURRENCY,OPEN):D('.75'),(CURRENCY,CLOSE):D('.76')}).lines[0]
    assert line.bucket.key.product_basis==product
    assert line.attribution.market_pnl==D('75.60')


@pytest.mark.parametrize('product',WRAPPERS)
def test_wrapper_unit_consolidation_reuses_reviewed_ratio_without_rewriting_trades(product):
    from tests.test_position_split_replay import split
    trade=booked(1,'100',OPEN,price='10',product_basis=product)
    p=reconstruct([trade],request(),splits=[split(ratio='.5')])
    assert p.buckets[0].closing_quantity==50 and trade.booking.quantity==100
    assert attribute_projection(p,{MarkKey(SUBJECT,OPEN):D(10),MarkKey(SUBJECT,CLOSE):D(20)},CURRENCY).market_pnl==0


@pytest.mark.parametrize('product',WRAPPERS)
def test_supplied_zero_wrapper_price_is_not_missing_or_negative(product):
    p=reconstruct([booked(1,'10',OPEN,product_basis=product)],request())
    assert attribute_projection(p,{MarkKey(SUBJECT,OPEN):D(100),MarkKey(SUBJECT,CLOSE):D(0)},CURRENCY).market_pnl==-1000
    with pytest.raises(ValueError):attribute_projection(p,{MarkKey(SUBJECT,OPEN):D(100),MarkKey(SUBJECT,CLOSE):D(-1)},CURRENCY)


@pytest.mark.parametrize('product',WRAPPERS)
def test_wrapper_distribution_is_explicit_income_and_later_payment_is_not_new_income(product):
    from valuation.flows import flow_component
    assert flow_component('COUPON','INCOME',D(20),D('.75'),instrument_type=product)==('COUPON',D(15))
    assert flow_component('COUPON','PAYMENT_ONLY',D(20),D('.75'),instrument_type=product)==(None,D(0))


@pytest.mark.parametrize('unit',['UNITS','SHARES'])
def test_spot_token_fraction_uses_trade_quote_currency_and_reporting_fx(unit):
    from valuation.product_inputs import supported_product
    assert supported_product('DIGITAL_ASSET',unit)=='PRICE'
    p=reconstruct([booked(1,'.125',OPEN,price='60000',product_basis='DIGITAL_ASSET',quantity_unit=unit)],request())
    assert attribute_projection(p,{MarkKey(SUBJECT,OPEN):D(60000),MarkKey(SUBJECT,CLOSE):D(62000)},UUID(int=99),
        {(CURRENCY,OPEN):D('.75'),(CURRENCY,CLOSE):D('.76')}).market_pnl==265


def test_two_crypto_venues_remain_separate_positions_with_individual_marks():
    other=UUID(int=999)
    p=reconstruct([booked(1,'.1',OPEN,product_basis='DIGITAL_ASSET'),
        booked(2,'.2',OPEN,product_basis='DIGITAL_ASSET',subject_id=other)],request())
    assert len(p.buckets)==2
    marks={MarkKey(SUBJECT,OPEN):D(100),MarkKey(SUBJECT,CLOSE):D(110),MarkKey(other,OPEN):D(100),MarkKey(other,CLOSE):D(120)}
    assert attribute_projection(p,marks,CURRENCY).market_pnl==5
    del marks[MarkKey(other,CLOSE)]
    with pytest.raises(ValueError,match='Missing required'):attribute_projection(p,marks,CURRENCY)


def test_stablecoin_depeg_is_price_pnl_and_crypto_fork_is_not_a_stock_split():
    from tests.test_position_split_replay import split
    from positions.contracts import PositionError
    facts=[booked(1,'1000',OPEN,price='1',product_basis='DIGITAL_ASSET')]
    p=reconstruct(facts,request())
    assert attribute_projection(p,{MarkKey(SUBJECT,OPEN):D(1),MarkKey(SUBJECT,CLOSE):D('.98')},CURRENCY).market_pnl==-20
    with pytest.raises(PositionError):reconstruct(facts,request(),splits=[split()])
