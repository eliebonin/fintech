from datetime import date
from decimal import Decimal as D
from uuid import uuid4
import pytest
from sqlalchemy import select,func
from tests.test_valuation_service import valued
from security_master_schema.demo_data import DEMO_IDS as ids


def schedule_data(**changes):
    return dict(instrumentId=ids['bond_instrument_node'],expectedRevision=0,sourceReference='Synthetic bond terms',
        reason='Initial sourced schedule',confirmSchedule=True,
        cashflows=[dict(cashflowKey='2026-10',cashflowType='COUPON',accrualStart='2026-04-01',accrualEnd='2026-10-01',paymentDate='2026-10-01',
                      couponRate='0.02',amountPer100='1')])|changes


def grant_coupon_ops(c,tenant,strategy):
    from security_master_schema import models as m,access_management as am
    group=am.save_group(c,tenant,ids['demo_user_account'],code='COUPON_'+uuid4().hex,name='Synthetic coupon Ops',
        actions=['LIFECYCLE_READ','LIFECYCLE_BOOK','TRADE_CORRECT'],scope_mode='SELECTED',strategy_ids=[strategy])
    c.execute(m.access_group_member.insert().values(tenant_id=tenant,group_id=group,user_account_id=ids['demo_user_account']))


def test_coupon_periods_preserve_unknown_amount_zero_and_explicit_adjusted_dates():
    from lifecycle.coupon_contracts import ScheduleCreate
    from pydantic import ValidationError
    base=schedule_data()
    model=ScheduleCreate.model_validate(base)
    assert model.cashflows[0].amount_per_100==1
    floating=base|dict(cashflows=[dict(cashflowKey='FLOAT',cashflowType='COUPON',accrualStart='2026-04-01',accrualEnd='2026-10-01',
        paymentDate='2026-09-30',amountFormula='SONIA + contractual spread')])
    assert ScheduleCreate.model_validate(floating).cashflows[0].amount_per_100 is None
    assert ScheduleCreate.model_validate(base|dict(cashflows=[base['cashflows'][0]|dict(amountPer100='0')])).cashflows[0].amount_per_100==0
    for row in [base['cashflows'][0]|dict(amountPer100=1.2),base['cashflows'][0]|dict(accrualEnd='2026-01-01')]:
        with pytest.raises(ValidationError): ScheduleCreate.model_validate(base|dict(cashflows=[row]))
    with pytest.raises(ValidationError): ScheduleCreate.model_validate(base|dict(cashflows=base['cashflows']*2))


def test_schedule_versions_and_payments_are_immutable_and_financially_inert(valued):
    from lifecycle.coupon_contracts import ScheduleCreate,PaymentCreate
    from lifecycle import coupon_service as s
    from security_master_schema import models as m
    from valuation import tables as vt
    c,r,_=valued
    grant_coupon_ops(c,r.tenant_id,r.strategy_id)
    counts=lambda:tuple(c.scalar(select(func.count()).select_from(table)) for table in (m.trade,m.cash_balance,vt.accrual_input))
    before=counts()
    saved=s.save_schedule(c,r.tenant_id,ids['demo_user_account'],ScheduleCreate.model_validate(schedule_data()),str(uuid4()))
    with pytest.raises(ValueError,match='revision changed'):
        s.save_schedule(c,r.tenant_id,ids['demo_user_account'],ScheduleCreate.model_validate(schedule_data()),str(uuid4()))
    key=str(uuid4())
    payload=PaymentCreate.model_validate(dict(strategyId=r.strategy_id,periodId=saved['cashflows'][0]['cashflow_id'],paymentDate='2026-10-01',
        amount='1000',currencyId=ids['gbp_currency'],sourceReference='Synthetic custodian payment 1',note='Receipt only',confirmPayment=True))
    receipt=s.record_payment(c,r.tenant_id,ids['demo_user_account'],payload,key)
    assert receipt['amount']==D(1000) and receipt['status']=='CONFIRMED'
    assert s.record_payment(c,r.tenant_id,ids['demo_user_account'],payload,key)['payment_id']==receipt['payment_id']
    with pytest.raises(ValueError,match='already'):
        s.record_payment(c,r.tenant_id,ids['demo_user_account'],payload,str(uuid4()))
    newer=s.save_schedule(c,r.tenant_id,ids['demo_user_account'],ScheduleCreate.model_validate(schedule_data(expectedRevision=1,reason='Corrected schedule')),str(uuid4()))
    assert newer['revision']==2
    assert receipt['period_id']==saved['cashflows'][0]['cashflow_id']
    corrected=payload.model_copy(update={'amount':D(900),'supersedes_payment_id':receipt['payment_id'],'note':'Corrected statement'})
    correction=s.record_payment(c,r.tenant_id,ids['demo_user_account'],corrected,str(uuid4()),correction=True)
    assert correction['revision']==2 and correction['logical_payment_id']==receipt['logical_payment_id']
    with pytest.raises(ValueError,match='revision changed'):
        s.record_payment(c,r.tenant_id,ids['demo_user_account'],corrected,str(uuid4()),correction=True)
    with pytest.raises(ValueError,match='reason'):
        s.record_payment(c,r.tenant_id,ids['demo_user_account'],corrected.model_copy(update={'note':''}),str(uuid4()),correction=True)
    reversed_row=s.reverse_payment(c,r.tenant_id,ids['demo_user_account'],r.strategy_id,correction['payment_id'],'Duplicate statement',str(uuid4()))
    assert reversed_row['status']=='REVERSED' and reversed_row['revision']==3
    rows,total=s.payment_report(c,r.tenant_id,ids['demo_user_account'],r.strategy_id,date(2026,10,1),date(2026,10,1),25,0)
    assert total==1 and rows[0]['status']=='REVERSED'
    assert counts()==before
    with pytest.raises(Exception,match='immutable'):
        with c.begin_nested(): c.execute(s.t.payment.update().where(s.t.payment.c.payment_id==receipt['payment_id']).values(amount=0))


def test_payment_confirmation_does_not_change_existing_interest_pnl(valued):
    from lifecycle.coupon_contracts import ScheduleCreate,PaymentCreate
    from lifecycle import coupon_service as s
    from valuation.service import calculate_position
    from tests.test_economic_pnl_acceptance import add_bond
    from valuation.accruals import record_accrual
    c,r,trade=valued;add_bond(c,r,trade)
    grant_coupon_ops(c,r.tenant_id,r.strategy_id)
    for day in (date(2026,9,30),date(2026,10,1)):
        record_accrual(c,r.tenant_id,ids['demo_user_account'],dict(strategyId=r.strategy_id,instrumentId=ids['bond_instrument_node'],
            valueDate=day,inputType='DAILY_INTEREST',dailyEarned=D(10),currencyId=ids['gbp_currency'],balanceReconciliation='NOT_PROVIDED'),str(uuid4()))
    before=calculate_position(c,r)
    contract=s.save_schedule(c,r.tenant_id,ids['demo_user_account'],ScheduleCreate.model_validate(schedule_data()),str(uuid4()))
    s.record_payment(c,r.tenant_id,ids['demo_user_account'],PaymentCreate.model_validate(dict(strategyId=r.strategy_id,
        periodId=contract['cashflows'][0]['cashflow_id'],paymentDate='2026-10-01',amount='1000',currencyId=ids['gbp_currency'],
        sourceReference='Synthetic received coupon',confirmPayment=True)),str(uuid4()))
    after=calculate_position(c,r)
    assert after.gross_pnl==before.gross_pnl
    assert [l.components().get('ACCRUAL') for l in after.period.lines]==[l.components().get('ACCRUAL') for l in before.period.lines]
