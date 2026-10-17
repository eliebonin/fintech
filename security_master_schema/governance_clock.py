"""UTC authority dates, separate from financial value dates and venue clocks."""
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import date, datetime, timezone

_request_day: ContextVar[date | None] = ContextVar('governance_day', default=None)


def governance_date(now: datetime | None = None) -> date:
    if now is None and (pinned := _request_day.get()) is not None:
        return pinned
    instant = now or datetime.now(timezone.utc)
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError('Governance instants must include a timezone')
    return instant.astimezone(timezone.utc).date()


@contextmanager
def governance_scope(now: datetime | None = None):
    """Context propagates into worker threads; no global cross-request cache."""
    token = _request_day.set(governance_date(now))
    try:
        yield
    finally:
        _request_day.reset(token)
