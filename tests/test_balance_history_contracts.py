"""Maintained stocks are local money, independent from daily earnings and FX."""
from datetime import date
from decimal import Decimal
from uuid import uuid4
import pytest


def anchor(**changes):
    return dict(strategyId=str(uuid4()),instrumentId=str(uuid4()),currencyId=str(uuid4()),
        valueDate='2026-10-19',closingBalance='1000.123456789012',sourceReference='Synthetic custodian statement',
        reason='Assessed closing accrued-interest balance')|changes


def test_supplied_balance_is_an_exact_independent_stock():
    from valuation.balance_history_contracts import BalanceInputCreate
    value=BalanceInputCreate.model_validate(anchor())
    assert value.closing_balance==Decimal('1000.123456789012')
    assert value.value_date==date(2026,10,19)
    assert 'dailyEarned' not in value.model_dump(by_alias=True)
    assert BalanceInputCreate.model_validate(anchor(closingBalance='-12.50')).closing_balance==Decimal('-12.50')


@pytest.mark.parametrize('amount',[1000,0.1,'NaN','Infinity','0.1234567890123'])
def test_supplied_balance_rejects_lossy_or_invalid_amounts(amount):
    from valuation.balance_history_contracts import BalanceInputCreate
    with pytest.raises(ValueError):BalanceInputCreate.model_validate(anchor(closingBalance=amount))


def test_withdrawal_requires_the_superseded_revision_and_no_replacement_amount():
    from valuation.balance_history_contracts import BalanceInputCreate
    with pytest.raises(ValueError):BalanceInputCreate.model_validate(anchor(status='WITHDRAWN',closingBalance=None))
    value=BalanceInputCreate.model_validate(anchor(status='WITHDRAWN',closingBalance=None,supersedesInputId=str(uuid4())))
    assert value.status=='WITHDRAWN' and value.closing_balance is None


def test_refresh_interval_is_explicit_and_does_not_require_reporting_fx():
    from valuation.balance_history_contracts import BalanceHistoryRefresh
    value=BalanceHistoryRefresh(strategyId=uuid4(),fromDate='2026-10-19',toDate='2026-10-20')
    assert value.from_date==date(2026,10,19)
    with pytest.raises(ValueError):BalanceHistoryRefresh(strategyId=uuid4(),fromDate='2026-10-20',toDate='2026-10-19')


def test_previous_closing_stock_can_price_fx_without_todays_history():
    from valuation.balance_history import stored_balance_day
    previous=dict(value_date=date(2026,10,19),closing_balance=Decimal('1000'),history_id=uuid4(),evidence={})
    day=stored_balance_day(date(2026,10,20),None,previous)
    assert day.opening==1000 and day.closing is None
    assert 'CLOSING_BALANCE_NOT_UPDATED' in day.warnings
    assert stored_balance_day(date(2026,10,21),None,previous).opening is None


def test_full_coupon_preserves_new_period_interest_and_partial_receipts():
    from valuation.accrued_balance import replay_balances
    day=date(2026,10,20)
    full=replay_balances(day,day,opening=Decimal('1000'),earnings={day:Decimal('20')},movements={},payments={day:Decimal('1000')})[0]
    partial=replay_balances(day,day,opening=Decimal('1000'),earnings={day:Decimal('20')},movements={},payments={day:Decimal('600')})[0]
    assert full.closing==20 and partial.closing==420
