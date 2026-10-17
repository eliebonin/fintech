"""Hand-calculated economic bridges; not expectations derived by another pricer."""
from datetime import date, timedelta
from decimal import Decimal as D
from uuid import UUID

import pytest
from positions.reconstruction import reconstruct
from tests.test_position_reconstruction import booked, request, OPEN, CLOSE, SUBJECT, CURRENCY
from valuation.position_calculation import attribute_projection, MarkKey


@pytest.mark.parametrize('held,execution,price,want', [
    ('10',None,None,'200'),          # 10 * (120 - 100)
    ('-10',None,None,'-200'),
    ('0','10','110','100'),         # new buy: 10 * (120 - 110)
    ('10','5','110','250'),         # old holding 200 + new buy 50
    ('10','-4','110','160'),        # remaining 120 + sold 40
    ('10','-10','110','100'),       # full closure retains today's gain
    ('0','-10','110','-100'),       # new short at 110, mark 120
])
def test_execution_bridge_keeps_prior_holding_and_T_execution_pnl(held,execution,price,want):
    facts=[] if held=='0' else [booked(1,held,OPEN)]
    if execution: facts.append(booked(2,execution,CLOSE,price))
    p=reconstruct(facts,request())
    result=attribute_projection(p,{MarkKey(SUBJECT,OPEN):D(100),MarkKey(SUBJECT,CLOSE):D(120)},CURRENCY)
    assert result.market_pnl==D(want)
    assert result.market_pnl==result.closing_value-result.opening_value-result.execution_value


def test_foreign_opening_holding_separates_price_fx_and_cross_exactly():
    p=reconstruct([booked(1,'10',OPEN)],request())
    result=attribute_projection(p,{MarkKey(SUBJECT,OPEN):D(100),MarkKey(SUBJECT,CLOSE):D(110)},UUID(int=888),
        {(CURRENCY,OPEN):D('.80'),(CURRENCY,CLOSE):D('.85')})
    assert result.lines[0].components()=={'PRICE':D(80),'FX':D(50),'PRICE_FX_CROSS':D(5)}
    assert (result.opening_value,result.closing_value,result.market_pnl)==(D(800),D(935),D(135))


def test_new_fund_uses_booked_cost_not_prior_nav_or_overnight_fx():
    p=reconstruct([booked(1,'10',CLOSE,'98',product_basis='FUND',quantity_unit='UNITS')],request())
    result=attribute_projection(p,{MarkKey(SUBJECT,CLOSE):D(100)},UUID(int=888),{(CURRENCY,CLOSE):D('.86')})
    assert result.lines[0].components()=={'PRICE':D('17.20'),'FX':D(0),'PRICE_FX_CROSS':D(0)}
    assert result.execution_value==D('842.80')


def test_closed_foreign_round_trip_requires_execution_fx_but_no_marks():
    p=reconstruct([booked(1,'10',OPEN+timedelta(hours=1),'100'),booked(2,'-10',CLOSE,'110')],request())
    result=attribute_projection(p,{},UUID(int=888),{(CURRENCY,CLOSE):D('.85')})
    assert result.market_pnl==85 and result.opening_value==result.closing_value==0
    with pytest.raises(ValueError,match='Missing frozen FX'):
        attribute_projection(p,{},UUID(int=888))


def test_bond_clean_market_gain_and_daily_earnings_do_not_add_balance_again():
    from valuation.accruals import AccrualInput,accrual_amounts,attach_accruals
    p=reconstruct([booked(1,'100000',OPEN,'99',product_basis='BOND',quantity_unit='NOMINAL',quote_factor=D(100))],request())
    market=attribute_projection(p,{MarkKey(SUBJECT,OPEN):D(99),MarkKey(SUBJECT,CLOSE):D(100)},CURRENCY)
    amounts=accrual_amounts(dict(openingBalance=D(990),dailyEarned=D(10),closingBalance=D(1000),
        balanceMovements=D(0),openingFx=D(1),closingFx=D(1)))
    result=attach_accruals(market,(AccrualInput('interest',SUBJECT,date(2026,10,7),1,dict(amounts=amounts),p.buckets[0].key),))
    assert result.market_pnl==1000
    assert result.lines[0].gross_pnl==1010
    assert result.lines[0].components()['ACCRUAL']==10
    assert amounts['balanceLocal']==1000  # stock retained, not added as daily earnings


def test_forward_maturity_rate_close_enters_T_pnl_without_a_closing_mark():
    conventions=dict(agreedRate='1.10')
    p=reconstruct([booked(1,'1000000',OPEN,'1.10',product_basis='FX_FORWARD',quantity_unit='CURRENCY_AMOUNT',product_evidence=conventions),
        booked(2,'-1000000',CLOSE,'1.125',product_basis='FX_FORWARD',quantity_unit='CURRENCY_AMOUNT',product_evidence=conventions)],request())
    result=attribute_projection(p,{MarkKey(SUBJECT,OPEN):D('1.11')},CURRENCY)
    assert (result.opening_value,result.closing_value,result.execution_value,result.market_pnl)==(D(10000),D(0),D(-25000),D(15000))


def test_missing_nonzero_boundary_mark_does_not_become_zero():
    p=reconstruct([booked(1,'10',OPEN)],request())
    with pytest.raises(ValueError,match='Missing required position mark'):
        attribute_projection(p,{MarkKey(SUBJECT,OPEN):D(100)},CURRENCY)


@pytest.mark.parametrize('product', ['OPTION','FUTURE','SWAP','STRUCTURED_PRODUCT'])
def test_booking_support_does_not_enable_unimplemented_valuation(product):
    from valuation.product_inputs import supported_product
    with pytest.raises(ValueError,match='not valuation-ready'):
        supported_product(product,'NOMINAL')
