"""Whole-swap mark P&L: signed units, one divisor, independent reporting FX."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
from uuid import UUID
import pytest
from tests.test_position_reconstruction import booked,request,OPEN,CLOSE,CURRENCY
from positions.reconstruction import reconstruct
from valuation.position_calculation import attribute_projection,required_marks,MarkKey


def swap(n,quantity,when,price='0',**changes):
    return booked(n,quantity,when,price,**(dict(product_basis='SWAP',quantity_unit='UNITS')|changes))


@pytest.mark.parametrize('quantity,expected',[('100','78'),('-100','-78')])
def test_whole_swap_negative_mark_and_fx_match_signed_quantity_formula(quantity,expected):
    reporting=UUID(int=200)
    projection=reconstruct([swap(1,quantity,OPEN,'-3')],request())
    subject=projection.buckets[0].key.subject_id
    result=attribute_projection(projection,{MarkKey(subject,OPEN):D('-2'),MarkKey(subject,CLOSE):D('-1')},reporting,
        {(CURRENCY,OPEN):D('.8'),(CURRENCY,CLOSE):D('.82')})
    assert result.market_pnl==D(expected)
    if quantity=='100':assert result.lines[0].attribution.components()=={'PRICE':D(80),'FX':D(-4),'PRICE_FX_CROSS':D(2)}


def test_nominal_percentage_swap_applies_quote_factor_once():
    projection=reconstruct([swap(1,'1000000',OPEN,quantity_unit='NOMINAL',quote_factor=D(100))],request())
    subject=projection.buckets[0].key.subject_id
    result=attribute_projection(projection,{MarkKey(subject,OPEN):D(2),MarkKey(subject,CLOSE):D(3)},CURRENCY)
    assert result.market_pnl==10000


def test_new_swap_uses_zero_execution_price_and_only_closing_day_fx():
    projection=reconstruct([swap(1,'100',CLOSE,'0')],request())
    subject=projection.buckets[0].key.subject_id
    assert len(required_marks(projection))==1
    result=attribute_projection(projection,{MarkKey(subject,CLOSE):D('-2')},UUID(int=200),{(CURRENCY,CLOSE):D('.8')})
    assert result.market_pnl==-160 and result.lines[0].attribution.fx==0


def test_partial_and_full_closure_keep_realized_pnl_without_fabricated_marks():
    facts=[swap(1,'100',OPEN,'-3'),swap(2,'-40',CLOSE,'-1.5')]
    p=reconstruct(facts,request());subject=p.buckets[0].key.subject_id
    r=attribute_projection(p,{MarkKey(subject,OPEN):D('-2'),MarkKey(subject,CLOSE):D('-1')},CURRENCY)
    assert r.market_pnl==80 and r.execution_value==60
    p=reconstruct([facts[0],swap(2,'-100',CLOSE,'-1')],request())
    assert len(required_marks(p))==1
    assert attribute_projection(p,{MarkKey(subject,OPEN):D('-2')},CURRENCY).market_pnl==100


def test_reset_is_separate_dated_income_not_extra_exposure_or_cash():
    from valuation.flows import EconomicFlow,attach_flows,flow_component
    p=reconstruct([swap(1,'100',OPEN)],request());subject=p.buckets[0].key.subject_id
    r=attribute_projection(p,{MarkKey(subject,OPEN):D(1),MarkKey(subject,CLOSE):D(0)},CURRENCY)
    component,amount=flow_component('RESET','INCOME',D(100),D(1))
    flow=EconomicFlow(UUID(int=900),subject,CLOSE.date(),component,D(100),amount,CURRENCY,{},(),None)
    projected,period=attach_flows(p,r,(flow,))
    assert period.market_pnl==-100 and sum(line.net_pnl for line in period.lines)==0
    assert projected.buckets[0].closing_quantity==100
    assert flow_component('RESET','PAYMENT_ONLY',D(100),D(1))==(None,D(0))


def test_negative_equity_prices_are_still_refused():
    with pytest.raises(ValueError):reconstruct([booked(1,'100',OPEN,'-1')],request())


def test_swap_selection_requires_whole_mark_basis_units_and_divisor():
    from valuation.product_inputs import swap_mark_dimensions
    proof=dict(swapPriceBasis='WHOLE_SWAP_MTM_PER_UNIT',quoteFactor='100.00',unitMultiplier='1',
        maturityDate='2026-12-01',priceBasis='SWAP_VALUE_PER_UNIT')
    p=reconstruct([swap(1,'100',OPEN,quote_factor=D(100),product_evidence=proof)],request())
    assert dict(swap_mark_dimensions(p,p.buckets[0].key.subject_id,CLOSE))==dict(
        SWAP_PRICE_BASIS='WHOLE_SWAP_MTM_PER_UNIT',QUANTITY_UNIT='UNITS',QUOTE_FACTOR='100')
    with pytest.raises(ValueError,match='maturity'):
        swap_mark_dimensions(p,p.buckets[0].key.subject_id,CLOSE+timedelta(days=100))
    p=reconstruct([swap(1,'100',OPEN,product_evidence={})],request())
    with pytest.raises(ValueError,match='Frozen'):
        swap_mark_dimensions(p,p.buckets[0].key.subject_id,CLOSE)
