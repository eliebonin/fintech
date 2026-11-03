"""DIRTY quote component is not daily earned interest or a position balance."""
from datetime import date
from decimal import Decimal as D
import pytest


@pytest.mark.parametrize('dirty,accrued,want',[('101','1','100'),('101.02','1.02','100'),('99.8','-.2','100'),('100','0','100'),
    ('100.000000000002','.000000000001','100.000000000001')])
def test_exact_clean_quote_preserves_signed_components_and_precision(dirty,accrued,want):
    from market_data.bond_quotes import clean_quote
    assert clean_quote(D(dirty),D(accrued))==D(want)


@pytest.mark.parametrize('dirty,accrued',[('101',None),('101','NaN'),('Infinity','1'),('101','102'),('0','0')])
def test_unknown_or_invalid_quote_component_is_not_zero(dirty,accrued):
    from market_data.bond_quotes import clean_quote
    with pytest.raises(ValueError):clean_quote(D(dirty),D(accrued) if accrued is not None else None)


def test_dirty_movement_is_not_added_as_daily_interest_again():
    from market_data.bond_quotes import clean_quote
    nominal=D('100000');first=clean_quote(D('101'),D('1'));last=clean_quote(D('101.02'),D('1.02'))
    price_pnl=nominal*(last-first)/100
    assert price_pnl==0 and price_pnl+D(20)==20


def test_coupon_detachment_does_not_look_like_a_price_loss_after_normalization():
    from market_data.bond_quotes import clean_quote
    assert clean_quote(D('100.99'),D('.99'))==clean_quote(D('100'),D(0))==100


def test_quoted_accrual_contract_requires_an_explicit_source_and_exact_amount():
    from market_data.bond_quotes import BondQuoteAccrual,validate_quote_accrual
    validate_quote_accrual(BondQuoteAccrual(D('-.2'),date(2026,10,5),'Provider ex-coupon quotation'))
    for amount,reference in [(D('NaN'),'Source'),(D('.0000000000001'),'Source'),(D('1'),' ')]:
        with pytest.raises(ValueError):validate_quote_accrual(BondQuoteAccrual(amount,date(2026,10,5),reference))


def test_applied_rule_explains_quoted_normalization_not_generated_daily_income():
    from valuation.decisions import applied_decisions
    rules=applied_decisions(dict(selections=[dict(valuation_date='2026-10-01',selected_value='101.02',valuation_value='100',
        pricing_evidence=dict(bondPriceNormalization=dict(dirtyPrice='101.02',accruedPer100='1.02',cleanPrice='100',quoteSettlementDate='2026-10-05')))]))
    rule=next(item for item in rules if item['code']=='BOND_DIRTY_TO_CLEAN')
    assert 'daily' in rule['explanation'].lower() and '101.02' in rule['explanation']
