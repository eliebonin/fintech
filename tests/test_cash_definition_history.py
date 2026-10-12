"""Date selection is tested without a database before isolated booking checks."""
from datetime import date
from types import SimpleNamespace

import pytest
from apps.reference_api import cash_booking_integrity as cash


def version(start, end=None, current=False, status='APPROVED'):
    return SimpleNamespace(effective_from=date.fromisoformat(start),
        effective_to=date.fromisoformat(end) if end else None,
        is_current=current, status=status)


def pick(monkeypatch, rows, day):
    monkeypatch.setattr(cash, '_locked', lambda *a, **k: rows)
    return cash._definition(None, None, None, None, date.fromisoformat(day))


def test_historical_approved_definition_selected_instead_of_future_current(monkeypatch):
    history = version('1980-12-12', '2026-10-05')
    current = version('2026-10-06', current=True)
    assert pick(monkeypatch, [history, current], '2026-05-08') is history
    assert pick(monkeypatch, [history, current], '2026-10-06') is current


def test_overlapping_approved_versions_are_refused_even_when_current_exists(monkeypatch):
    with pytest.raises(cash.CashBookingRefusal, match='Ambiguous'):
        pick(monkeypatch, [version('1980-12-12'), version('2026-10-06', current=True)], '2026-10-07')


@pytest.mark.parametrize('day', ['1980-12-11', '2026-10-05'])
def test_gaps_and_dates_before_inception_remain_blocked(monkeypatch, day):
    with pytest.raises(cash.CashBookingRefusal, match='outside'):
        pick(monkeypatch, [version('1980-12-12', '2026-10-04'), version('2026-10-06', current=True)], day)


def test_historical_approval_does_not_replace_current_operational_approval(monkeypatch):
    with pytest.raises(cash.CashBookingRefusal, match='current approved'):
        pick(monkeypatch, [version('1980-12-12', '2026-10-05')], '2026-05-08')


def test_draft_historical_definition_cannot_enable_booking(monkeypatch):
    with pytest.raises(cash.CashBookingRefusal, match='outside'):
        pick(monkeypatch, [version('1980-12-12', '2026-10-05', status='DRAFT'),
                          version('2026-10-06', current=True)], '2026-05-08')
