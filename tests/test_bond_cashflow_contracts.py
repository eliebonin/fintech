"""The complete contractual schedule is independent of strategy entitlements."""
from uuid import uuid4

import pytest
from pydantic import ValidationError

from lifecycle.coupon_contracts import ScheduleCreate


def schedule(*cashflows):
    return dict(instrumentId=str(uuid4()), expectedRevision=0,
                sourceReference='Synthetic termsheet', reason='Complete sourced schedule',
                confirmSchedule=True, cashflows=list(cashflows))


COUPON = dict(cashflowKey='C1', cashflowType='COUPON', accrualStart='2026-04-15',
              accrualEnd='2026-10-15', paymentDate='2026-10-15', amountPer100='2.5')
PRINCIPAL = dict(cashflowKey='P1', cashflowType='PRINCIPAL', paymentDate='2026-10-15', amountPer100='100')


def test_final_coupon_and_principal_are_separate_same_day_cashflows():
    value = ScheduleCreate.model_validate(schedule(COUPON, PRINCIPAL))
    assert [r.cashflow_type for r in value.cashflows] == ['COUPON', 'PRINCIPAL']
    assert value.cashflows[1].accrual_start is None
    assert value.cashflows[1].amount_per_100 == 100


def test_principal_only_and_unknown_floating_amount_are_preserved():
    assert len(ScheduleCreate.model_validate(schedule(PRINCIPAL)).cashflows) == 1
    floating = {k: v for k, v in COUPON.items() if k != 'amountPer100'} | dict(amountFormula='SOFR + 15 bps, ACT/360')
    row = ScheduleCreate.model_validate(schedule(floating, PRINCIPAL)).cashflows[0]
    assert row.amount_per_100 is None and row.amount_formula == 'SOFR + 15 bps, ACT/360'


@pytest.mark.parametrize('row', [PRINCIPAL | dict(amountPer100='0'), PRINCIPAL | dict(amountPer100='-1'),
    PRINCIPAL | dict(accrualStart='2026-01-01'), PRINCIPAL | dict(couponRate='0.05'),
    PRINCIPAL | dict(amountPer100=100), COUPON | dict(accrualEnd='2026-01-01'),
    COUPON | dict(amountPer100=None)])
def test_rejects_invalid_or_ambiguous_cashflow_economics(row):
    with pytest.raises(ValidationError):
        ScheduleCreate.model_validate(schedule(row))


def test_interleaving_principal_does_not_hide_overlapping_coupons_or_duplicate_keys():
    with pytest.raises(ValidationError, match='overlapping'):
        ScheduleCreate.model_validate(schedule(COUPON, PRINCIPAL, COUPON | dict(cashflowKey='C2')))
    with pytest.raises(ValidationError, match='Unique'):
        ScheduleCreate.model_validate(schedule(COUPON, PRINCIPAL | dict(cashflowKey='C1')))
