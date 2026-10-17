"""Hand-calculated monetary amounts, independent of NAV and daily P&L."""
from decimal import Decimal as D
import pytest


def test_cash_security_measures_are_equal_with_factors_and_short_sign():
    from valuation.position_measures import cash_security
    result=cash_security(D('-100'),D('150'),D('2'),D('100'))
    assert result==dict(referenceNotional=D('-300'),economicExposure=D('-300'),marketValue=D('-300'))


def test_bond_prefers_dirty_and_never_adds_accrual_twice():
    from valuation.position_measures import bond
    value=bond(D('100000'),dirty=D('99.2'),clean=D('98'),accrued=D('1200'))
    assert value['referenceNotional']==value['economicExposure']==D('100000')
    assert value['marketValue']==D('99200') and value['route']=='DIRTY_PRICE'


def test_bond_clean_plus_balance_not_daily_interest():
    from valuation.position_measures import bond
    value=bond(D('100000'),clean=D('98'),accrued=D('1200'))
    assert value['cleanMarketValue']==D('98000') and value['marketValue']==D('99200')
    assert bond(D('100000'),clean=D('98'))['marketValue'] is None
    assert bond(D('-100000'),clean=D('98'),accrued=D('-1200'))['marketValue']==D('-99200')


def test_unit_swap_reference_exposure_and_mtm_are_different_and_leverage_once():
    from valuation.position_measures import unit_swap
    value=unit_swap(D('25000'),D('8250'),D('1.5'),D('9000'),D('20'),D('1'),orientation='RECEIVE')
    assert value==dict(referenceNotional=D('206250000'),economicExposure=D('337500000'),marketValue=D('500000'))
    pay=unit_swap(D('25000'),D('8250'),D('1.5'),D('9000'),D('-20'),D('1'),orientation='PAY')
    assert pay['economicExposure']==D('-337500000') and pay['marketValue']==D('-500000')
    zero=unit_swap(D('25000'),D('8250'),D('1.5'),None,D('0'),D('1'))
    assert zero['economicExposure'] is None and zero['marketValue']==0


@pytest.mark.parametrize('bad',[D('NaN'),D('Infinity')])
def test_measures_reject_nonfinite_inputs(bad):
    from valuation.position_measures import cash_security
    with pytest.raises(ValueError):cash_security(D('1'),bad)


def test_nominal_swap_does_not_invent_underlying_units():
    from valuation.position_measures import nominal_swap
    assert nominal_swap(D('1000000'),D('-2'),D('100'))==dict(referenceNotional=D('1000000'),economicExposure=None,marketValue=D('-20000'))
