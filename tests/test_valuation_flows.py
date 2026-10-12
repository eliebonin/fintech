from decimal import Decimal as D
import pytest


def test_dividend_is_signed_income_but_later_payment_is_not_income_again():
    from valuation.flows import flow_component
    assert flow_component('DIVIDEND','INCOME',D('100'),D('.86'))==('DIVIDEND',D('86'))
    assert flow_component('COUPON','PAYMENT_ONLY',D('1000'),D('.86'))==(None,D('0'))


def test_arbitrary_labels_do_not_implicitly_recognize_income():
    from valuation.flows import flow_component
    with pytest.raises(ValueError): flow_component('SOMETHING','INCOME',D('10'),D('1'))
    with pytest.raises(ValueError): flow_component('COUPON','INCOME',D('1000'),D('.86'))


def test_booked_flow_changes_economic_not_share_position_pnl(valued):
    from datetime import datetime,timezone
    from uuid import uuid4
    from security_master_schema.demo_data import DEMO_IDS as ids
    from tests.test_valuation_service import service
    from valuation.flows import book_flow
    c,r,_=valued
    identity=book_flow(c,r.tenant_id,ids['demo_user_account'],dict(strategyId=r.strategy_id,
        instrumentId=ids['hsbc_instrument_node'],currencyId=ids['gbp_currency'],amount=D('100'),
        component='DIVIDEND',recognitionRole='INCOME',economicDate=r.closing_cutoff.date(),paymentDate=None,
        sourceReference='SYNTHETIC DIVIDEND'),str(uuid4()))
    result=service().calculate(c,r)
    assert result.period.market_pnl==D('109.877')
    assert result.gross_pnl==D('209.877')
    assert any(line.components().get('DIVIDEND')==D('100') for line in result.period.lines)
    assert result.evidence['economicFlows'][0]['tradeId']==str(identity)


from tests.test_valuation_service import valued


def test_flow_cancel_removes_income_without_mutating_booking(valued):
    from uuid import uuid4
    from sqlalchemy import select
    from security_master_schema import models as m
    from security_master_schema.demo_data import DEMO_IDS as ids
    from valuation.flows import book_flow,cancel_flow,load_economic_flows
    c,r,_=valued
    data=dict(strategyId=r.strategy_id,instrumentId=ids['hsbc_instrument_node'],currencyId=ids['gbp_currency'],
        amount=D('100'),component='DIVIDEND',recognitionRole='INCOME',economicDate=r.closing_cutoff.date(),
        paymentDate=None,sourceReference='SYNTHETIC')
    identity=book_flow(c,r.tenant_id,ids['demo_user_account'],data,str(uuid4()))
    assert len(load_economic_flows(c,r))==1
    key=str(uuid4())
    cancel_flow(c,r.tenant_id,ids['demo_user_account'],identity,'Wrong dividend',key)
    cancel_flow(c,r.tenant_id,ids['demo_user_account'],identity,'Wrong dividend',key)
    assert load_economic_flows(c,r)==()
    assert c.scalar(select(m.trade.c.quantity).where(m.trade.c.trade_id==identity))==D('100')


def test_flow_api_records_actual_trade_with_exact_amount():
    from tests.test_composite_policy_api import call
    from security_master_schema.demo_data import DEMO_IDS as ids
    from uuid import uuid4
    data=dict(strategyId=str(ids['strategy']),instrumentId=str(ids['hsbc_instrument_node']),currencyId=str(ids['gbp_currency']),
        amount='100',component='DIVIDEND',recognitionRole='INCOME',economicDate='2026-10-01',paymentDate=None,sourceReference='SYNTHETIC')
    key=str(uuid4())
    response=call('POST','/v1/valuation/economic-flows',data,key)
    assert response.status_code==201,response.text
    assert call('POST','/v1/valuation/economic-flows',data,key).json()==response.json()
    identity=response.json()['tradeId']
    response=call('POST',f'/v1/valuation/economic-flows/{identity}/cancel',{'reason':'Wrong dividend'},str(uuid4()))
    assert response.status_code==200,response.text


@pytest.mark.parametrize('actions,allowed', [(['TRADE_WRITE'], False), (['TRADE_CORRECT'], True)])
def test_flow_cancellation_uses_correction_permission(valued,actions,allowed):
    from uuid import uuid4
    from tests.test_access_management import delegated_user
    from security_master_schema.demo_data import DEMO_IDS as ids
    from valuation.flows import book_flow,cancel_flow
    c,r,_=valued
    identity=book_flow(c,r.tenant_id,ids['demo_user_account'],dict(strategyId=r.strategy_id,
        instrumentId=ids['hsbc_instrument_node'],currencyId=ids['gbp_currency'],amount=D('100'),
        component='DIVIDEND',recognitionRole='INCOME',economicDate=r.closing_cutoff.date(),
        paymentDate=None,sourceReference='SYNTHETIC'),str(uuid4()))
    user=delegated_user(c,actions)
    if allowed:
        assert cancel_flow(c,r.tenant_id,user,identity,'Wrong flow',str(uuid4()))==identity
    else:
        with pytest.raises(PermissionError): cancel_flow(c,r.tenant_id,user,identity,'Wrong flow',str(uuid4()))
