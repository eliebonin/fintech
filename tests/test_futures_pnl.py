"""Hand-calculated futures variation; contract notional is not a NAV asset."""
from dataclasses import replace
from decimal import Decimal as D
from uuid import UUID
import pytest
from positions.reconstruction import reconstruct
from tests.test_position_reconstruction import booked, request, OPEN, CLOSE, SUBJECT, CURRENCY
from valuation.position_calculation import attribute_projection, MarkKey


def future(n, quantity, when, price='6000'):
    return booked(n, quantity, when, price, product_basis='FUTURE', quantity_unit='CONTRACTS',
                  unit_multiplier=D('50'), product_evidence={'allowNegativePrice':False})


@pytest.mark.parametrize('held,execution,price,want',[
    ('2',None,None,'1000'),('0','2','6005','500'),('2','1','6005','1250'),
    ('2','-1','6005','750'),('2','-2','6005','500'),('-2',None,None,'-1000')])
def test_futures_variation_uses_contract_multiplier_once(held,execution,price,want):
    facts=[] if held=='0' else [future(1,held,OPEN)]
    if execution:facts.append(future(2,execution,CLOSE,price))
    projection=reconstruct(facts,request())
    result=attribute_projection(projection,{MarkKey(SUBJECT,OPEN):D('6000'),MarkKey(SUBJECT,CLOSE):D('6010')},CURRENCY)
    assert result.market_pnl==D(want)
    assert result.settlement_variation==D(want)
    assert result.opening_value==result.closing_value==result.execution_value==0
    assert result.market_pnl==result.closing_value-result.opening_value-result.execution_value+result.settlement_variation
    assert result.lines[0].economic_evidence[0]['kind']=='FUTURES_DAILY_VARIATION'


def test_foreign_futures_translate_variation_without_fx_on_gross_notional():
    p=reconstruct([future(1,'2',OPEN)],request())
    # No opening FX required: margin cash is assessed independently.
    result=attribute_projection(p,{MarkKey(SUBJECT,OPEN):D('6000'),MarkKey(SUBJECT,CLOSE):D('6010')},UUID(int=99),
        {(CURRENCY,CLOSE):D('.8')})
    assert result.lines[0].components()=={'PRICE':D('800'),'FX':D(0),'PRICE_FX_CROSS':D(0)}
    flat=attribute_projection(p,{MarkKey(SUBJECT,OPEN):D('6000'),MarkKey(SUBJECT,CLOSE):D('6000')},UUID(int=99),
        {(CURRENCY,CLOSE):D('.8')})
    assert flat.market_pnl==0


def test_futures_round_trip_requires_no_boundary_prices():
    p=reconstruct([future(1,'2',CLOSE.replace(hour=10),'6000'),future(2,'-2',CLOSE,'6005')],request())
    result=attribute_projection(p,{},CURRENCY)
    assert result.market_pnl==500 and result.settlement_variation==500


def test_mixed_security_and_future_keeps_asset_bridge_separate():
    equity=booked(3,'10',OPEN,'100',subject_id=UUID(int=88))
    p=reconstruct([future(1,'2',OPEN),equity],request())
    marks={MarkKey(SUBJECT,OPEN):D('6000'),MarkKey(SUBJECT,CLOSE):D('6010'),
        MarkKey(UUID(int=88),OPEN):D('100'),MarkKey(UUID(int=88),CLOSE):D('110')}
    result=attribute_projection(p,marks,CURRENCY)
    assert result.opening_value==1000 and result.closing_value==1100
    assert result.market_pnl==1100 and result.settlement_variation==1000


def test_fractional_futures_contracts_are_rejected():
    with pytest.raises(ValueError,match='whole|integer'):
        reconstruct([future(1,'1.5',OPEN)],request())


def test_negative_market_price_requires_the_original_contract_permission():
    facts=[future(1,'2',OPEN)]
    p=reconstruct(facts,request())
    with pytest.raises(ValueError,match='Negative'):
        attribute_projection(p,{MarkKey(SUBJECT,OPEN):D('10'),MarkKey(SUBJECT,CLOSE):D('-1')},CURRENCY)
    permitted=replace(facts[0],booking=replace(facts[0].booking,product_evidence={'allowNegativePrice':True}))
    result=attribute_projection(reconstruct([permitted],request()),{MarkKey(SUBJECT,OPEN):D('10'),MarkKey(SUBJECT,CLOSE):D('-1')},CURRENCY)
    assert result.market_pnl==-1100


def test_multi_day_foreign_futures_use_each_daily_variation_fx():
    from datetime import timedelta
    from valuation.service import aggregate_daily_periods
    facts=[future(1,'2',OPEN)];last=CLOSE+timedelta(days=1)
    projection=reconstruct(facts,request(closing_cutoff=last))
    rows=[]
    for first,end,p0,p1,fx in [(OPEN,CLOSE,'6000','6010','.8'),(CLOSE,last,'6010','6020','.9')]:
        daily=reconstruct(facts,request(opening_cutoff=first,closing_cutoff=end))
        rows.append(attribute_projection(daily,{MarkKey(SUBJECT,first):D(p0),MarkKey(SUBJECT,end):D(p1)},UUID(int=99),{(CURRENCY,end):D(fx)}))
    result=aggregate_daily_periods(projection,rows)
    assert result.market_pnl==1700 and result.settlement_variation==1700
    assert len(result.lines[0].economic_evidence[0]['days'])==2


def test_opening_price_does_not_validate_a_later_trade_convention_before_its_effective_date():
    from copy import deepcopy
    from tests.test_future_frozen_valuation import frozen
    from valuation.futures_pnl import future_mark_context
    _,snapshot,_=frozen();cv=deepcopy(snapshot['economics']['terms']['convention']);cv['priceCurrencyId']=str(CURRENCY)
    first=future(1,'2',OPEN);first=replace(first,booking=replace(first.booking,product_evidence={'instrumentId':str(SUBJECT),'futureConvention':cv}))
    later=deepcopy(cv);later['effectiveFrom']=CLOSE.date().isoformat()
    second=future(2,'1',CLOSE);second=replace(second,booking=replace(second.booking,product_evidence={'instrumentId':str(SUBJECT),'futureConvention':later}))
    dimensions,_=future_mark_context(reconstruct([first,second],request()),SUBJECT,OPEN)
    assert ('CONTRACT_INSTRUMENT_ID',str(SUBJECT)) in dimensions


def test_calculation_rules_explain_futures_even_without_a_single_position_identity():
    from valuation.decisions import applied_decisions
    rules=applied_decisions({'projection':{'buckets':[{'key':{'product_basis':'FUTURE'}}]}})
    assert any(rule['code']=='FUTURES_DAILY_VARIATION' for rule in rules)
