"""Futures market notional is exposure, never a fabricated NAV asset or zero MTM."""
from decimal import Decimal as D
import pytest


@pytest.mark.parametrize('quantity,price,multiplier,factor,want',[
    ('10','6000','50','1','3000000'),('-4','6000','50','1','-1200000'),
    ('2','600000','50','100','600000'),('10','0','50','1','0')])
def test_current_futures_notional_and_exposure_apply_multiplier_once(quantity,price,multiplier,factor,want):
    from valuation.position_measures import linear_future
    result=linear_future(D(quantity),D(price),D(multiplier),D(factor))
    assert result==dict(referenceNotional=D(want),economicExposure=D(want),marketValue=None)


def test_missing_futures_price_is_not_entry_price_or_zero():
    from valuation.position_measures import linear_future
    assert linear_future(D('10'),None,D('50'),D('1'))==dict(referenceNotional=None,economicExposure=None,marketValue=None)


def test_negative_futures_price_requires_explicit_approved_permission():
    from valuation.position_measures import linear_future
    with pytest.raises(ValueError):linear_future(D('10'),D('-5'),D('50'),D('1'))
    assert linear_future(D('10'),D('-5'),D('50'),D('1'),allow_negative=True)['economicExposure']==D('-2500')


@pytest.mark.parametrize('quantity,multiplier,factor',[('1.5','50','1'),('1','0','1'),('1','50','0'),('1','NaN','1')])
def test_invalid_frozen_contract_units_or_factors_do_not_produce_measures(quantity,multiplier,factor):
    from valuation.position_measures import linear_future
    with pytest.raises(ValueError):linear_future(D(quantity),D('6000'),D(multiplier),D(factor))
