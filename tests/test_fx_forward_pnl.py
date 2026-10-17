from decimal import Decimal as D
from dataclasses import replace
from datetime import timedelta
from tests.test_position_reconstruction import booked,request,OPEN,CLOSE,CURRENCY
from positions.reconstruction import reconstruct
from valuation.position_calculation import attribute_projection,MarkKey
import pytest


def forward(n,quantity,when,rate='1.10'):
    return booked(n,quantity,when,rate,quantity_unit='CURRENCY_AMOUNT',product_basis='FX_FORWARD',
        product_evidence=dict(agreedRate='1.10',maturityDate=CLOSE.date().isoformat()))


@pytest.mark.parametrize('quantity,expected',[('1000000','10000'),('-1000000','-10000')])
def test_daily_forward_pnl_is_signed_notional_times_rate_change(quantity,expected):
    p=reconstruct([forward(1,quantity,OPEN)],request())
    subject=p.buckets[0].key.subject_id
    result=attribute_projection(p,{MarkKey(subject,OPEN):D('1.11'),MarkKey(subject,CLOSE):D('1.12')},CURRENCY)
    assert result.market_pnl==D(expected)
    assert result.opening_value==D(expected) and result.closing_value==D(expected)*2


def test_new_trade_uses_booked_rate_and_has_zero_initial_net_contract_value():
    p=reconstruct([forward(1,'1000000',OPEN+timedelta(hours=1))],request())
    result=attribute_projection(p,{MarkKey(p.buckets[0].key.subject_id,CLOSE):D('1.12')},CURRENCY)
    assert result.execution_value==0 and result.market_pnl==20000


def test_maturity_unwind_uses_closing_execution_rate_without_closing_mark():
    p=reconstruct([forward(1,'1000000',OPEN),forward(2,'-1000000',CLOSE,'1.125')],request())
    result=attribute_projection(p,{MarkKey(p.buckets[0].key.subject_id,OPEN):D('1.12')},CURRENCY)
    assert result.closing_value==0 and result.market_pnl==5000


def test_reporting_fx_moves_apply_to_net_contract_value_not_gross_notional():
    from uuid import UUID
    reporting=UUID(int=999)
    p=reconstruct([forward(1,'1000000',OPEN)],request())
    subject=p.buckets[0].key.subject_id
    result=attribute_projection(p,{MarkKey(subject,OPEN):D('1.11'),MarkKey(subject,CLOSE):D('1.12')},reporting,
        {(CURRENCY,OPEN):D('.80'),(CURRENCY,CLOSE):D('.81')})
    assert result.market_pnl==8200  # 10,000*.81 + opening net value 10,000*.01.
    assert result.lines[0].attribution.fx==100


def test_negative_net_contract_value_is_permitted_for_a_positive_rate():
    p=reconstruct([forward(1,'1000000',OPEN)],request())
    subject=p.buckets[0].key.subject_id
    result=attribute_projection(p,{MarkKey(subject,OPEN):D('1.09'),MarkKey(subject,CLOSE):D('1.08')},CURRENCY)
    assert result.opening_value==-10000 and result.market_pnl==-10000
