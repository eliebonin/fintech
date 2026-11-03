"""Opening-balance attribution is not a change in translated cash stocks."""
from decimal import Decimal as D
import importlib
import pytest
from valuation.economics import validate_totals
from valuation.rounding import rounded_result


def cash():
    try:return importlib.import_module('valuation.cash_fx')
    except ModuleNotFoundError:pytest.fail('Cash FX opening-balance calculation is not implemented')


@pytest.mark.parametrize('opening,first,last,want',[
    ('100000','0.75','0.76','1000'),('-100000','0.75','0.76','-1000'),
    ('100000','0.76','0.75','-1000'),('100000','1','1','0'),
    ('0',None,None,'0'),('123.456789012','0.750000000001','0.760000000002','1.234567890243456789012'),
])
def test_signed_exact_cash_fx(opening,first,last,want):
    assert cash().cash_fx_amount(D(opening),D(first) if first else None,D(last) if last else None)==D(want)


def test_daily_changing_cash_uses_each_opening_not_period_end_balance():
    # USD 20,000 arrives at day-one close. It is not income and only carries FX
    # from the next day's opening under the explicitly agreed EoD convention.
    amount=cash().cash_fx_amount(D('100000'),D('.75'),D('.76'))+cash().cash_fx_amount(D('120000'),D('.76'),D('.77'))
    assert amount==D('2200')
    assert amount!=D('120000')*D('.02')


@pytest.mark.parametrize('balance,opening,closing',[
    (D('NaN'),D('1'),D('1')),(D('1'),None,D('1')),
    (D('1'),D('0'),D('1')),(D('1'),D('1'),D('Infinity')),
])
def test_nonzero_cash_requires_finite_positive_fx(balance,opening,closing):
    with pytest.raises(ValueError):cash().cash_fx_amount(balance,opening,closing)


def test_cash_component_adds_to_gross_and_net_not_investment_market_bridge():
    parts={'PRICE':D('12'),'CASH_FX':D('1.23456789012345'),'ACCRUAL':D('2'),'OTHER_COST':D('-1')}
    validate_totals(parts,market=D('12'),gross=D('15.23456789012345'),net=D('14.23456789012345'))
    result=rounded_result(parts,market=D('12'),gross=D('15.23456789012345'),net=D('14.23456789012345'))
    assert result['market']==D('12')
    assert result['gross']==D('15.234567890123')
    assert result['net']==D('14.234567890123')
    assert result['evidence']['adjustments']['components']['CASH_FX']==D('-0.00000000000045')


def test_cash_is_standard_and_transport_has_no_exclusion_switch():
    from apps.reference_api.valuation_contracts import ValuationCreate
    from security_master_schema.demo_data import DEMO_IDS as ids
    data=dict(strategyId=ids['strategy'],policyId=ids['valuation_policy'],cutId=ids['valuation_cut'],
        reportingCurrencyId=ids['gbp_currency'],openingDate='2026-10-01',closingDate='2026-10-02')
    assert 'include_cash_balances' not in ValuationCreate.model_validate(data).model_dump()
    for flag in (True,False,'true'):
        with pytest.raises(ValueError):ValuationCreate.model_validate(data|{'includeCashBalances':flag})
