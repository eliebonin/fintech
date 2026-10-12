"""Product unit semantics, not a derivative pricing model."""
from decimal import Decimal as D
import pytest


def test_dirty_bond_quote_is_cleaned_once_with_per_nominal_accrual():
    from valuation.product_inputs import clean_bond_price
    assert clean_bond_price(D('99.75'),'DIRTY',D('1.25'))==D('98.50')
    assert clean_bond_price(D('98.5'),'CLEAN',None)==D('98.5')
    with pytest.raises(ValueError): clean_bond_price(D('99.75'),'DIRTY',None)


def test_cash_is_unit_mark_and_derivatives_have_explicit_readiness_gate():
    from valuation.product_inputs import supported_product
    assert supported_product('CASH','CURRENCY_AMOUNT')=='FX_ONLY'
    assert supported_product('BOND','NOMINAL')=='CLEAN_PLUS_ACCRUAL'
    assert supported_product('FUND','UNITS')=='NAV'
    for product in ('SWAP','OPTION','FX_FORWARD','FUTURE','STRUCTURED_PRODUCT'):
        with pytest.raises(ValueError,match='not valuation-ready'): supported_product(product,'NOMINAL')
