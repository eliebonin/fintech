from datetime import datetime, date, timezone
from types import SimpleNamespace
import pytest

from apps.reference_api.valuation_recognition import recognition

def ticket(stamp='2026-10-06T23:30:00-04:00', day=None, reason=None):
    return SimpleNamespace(trade_datetime=datetime.fromisoformat(stamp), valuation_effective_date=day, valuation_override_reason=reason)

def test_default_is_explicit_utc_business_date():
    assert recognition(ticket()) == dict(date='2026-10-07', timezone='UTC', basis='UTC_TRADE_DATE', reason=None)

def test_deferred_recognition_requires_and_freezes_reason():
    with pytest.raises(ValueError, match='reason'):
        recognition(ticket(day=date(2026,10,8)))
    assert recognition(ticket(day=date(2026,10,8),reason='  After reporting boundary  ')) == dict(date='2026-10-08',timezone='UTC',basis='EXPLICIT_OVERRIDE',reason='After reporting boundary')

def test_recognition_cannot_precede_actual_execution_date():
    with pytest.raises(ValueError, match='before'):
        recognition(ticket(day=date(2026,10,6),reason='not allowed'))

def test_naive_execution_cannot_define_business_date():
    with pytest.raises(ValueError, match='timezone'):
        recognition(ticket(stamp='2026-10-06T23:30:00'))
