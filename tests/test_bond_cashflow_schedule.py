from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select, func

from lifecycle import coupon_service as service
from lifecycle.coupon_contracts import ScheduleCreate, PaymentCreate
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from tests.test_bond_coupons import grant_coupon_ops, schedule_data
from tests.test_valuation_service import valued
from valuation import tables as vt


PRINCIPAL = dict(cashflowKey='Redemption', cashflowType='PRINCIPAL', paymentDate='2026-10-01', amountPer100='100')


def test_full_schedule_is_ordered_versioned_and_not_a_financial_posting(valued):
    c, r, _ = valued
    data = schedule_data()
    data['cashflows'].insert(0, PRINCIPAL)
    tables = (m.trade, m.cash_balance, vt.accrual_input)
    counts = lambda: tuple(c.scalar(select(func.count()).select_from(t)) for t in tables)
    before = counts()
    saved = service.save_schedule(c, r.tenant_id, ids['demo_user_account'], ScheduleCreate.model_validate(data), str(uuid4()))
    assert [row['cashflow_type'] for row in saved['cashflows']] == ['COUPON', 'PRINCIPAL']
    assert saved['amountBasis'] == 'PER_100_ORIGINAL_NOMINAL' and saved['currencyCode'] == 'GBP'
    assert saved['cashflows'][1]['amount_per_100'] == Decimal('100')
    grant_coupon_ops(c, r.tenant_id, r.strategy_id)
    view = service.read_schedule(c, r.tenant_id, ids['demo_user_account'], r.strategy_id, ids['bond_instrument_node'])
    assert view['schedule']['cashflows'] == saved['cashflows']
    assert counts() == before
    with pytest.raises(Exception, match='immutable'):
        with c.begin_nested():
            c.execute(service.t.cashflow.update().values(amount_per_100=0))


def test_principal_is_rejected_as_coupon_by_service_and_database(valued):
    c, r, _ = valued
    grant_coupon_ops(c, r.tenant_id, r.strategy_id)
    saved = service.save_schedule(c, r.tenant_id, ids['demo_user_account'],
        ScheduleCreate.model_validate(schedule_data(cashflows=[PRINCIPAL])), str(uuid4()))
    row = saved['cashflows'][0]
    payment = PaymentCreate(strategyId=r.strategy_id, periodId=row['cashflow_id'], paymentDate='2026-10-01',
        amount='100', currencyId=ids['gbp_currency'], sourceReference='Synthetic receipt', confirmPayment=True)
    with pytest.raises(ValueError, match='Principal'):
        service.record_payment(c, r.tenant_id, ids['demo_user_account'], payment, str(uuid4()))
    with pytest.raises(Exception, match='scope/type mismatch'):
        with c.begin_nested():
            c.execute(service.t.payment.insert().values(logical_payment_id=uuid4(), tenant_id=r.tenant_id,
                strategy_id=r.strategy_id, period_id=row['cashflow_id'], revision=1, status='CONFIRMED',
                payment_date='2026-10-01', amount=100, currency_id=ids['gbp_currency'],
                source_reference='Synthetic direct insert', note='', request_key=uuid4().hex,
                request_hash='retained-test', actor_id=ids['demo_user_account'], real_operator_id=ids['demo_user_account']))


def test_zero_coupon_bond_accepts_principal_only_and_unknown_formula_remains_unknown(valued):
    c, r, _ = valued
    c.execute(m.bond_terms.update().where(m.bond_terms.c.instrument_node_id==ids['bond_instrument_node']).values(coupon_type='ZERO', coupon_rate=0))
    saved = service.save_schedule(c, r.tenant_id, ids['demo_user_account'],
        ScheduleCreate.model_validate(schedule_data(cashflows=[PRINCIPAL | dict(amountPer100=None, amountFormula='Contractual indexed redemption')])), str(uuid4()))
    assert saved['cashflows'][0]['amount_per_100'] is None
    assert saved['cashflows'][0]['amount_formula'] == 'Contractual indexed redemption'
    with pytest.raises(ValueError, match='principal cashflows only'):
        service.save_schedule(c, r.tenant_id, ids['demo_user_account'], ScheduleCreate.model_validate(schedule_data(expectedRevision=1)), str(uuid4()))
