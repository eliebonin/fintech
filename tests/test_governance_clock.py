"""Authority dates are UTC and stable for one request, not host-local dates."""
from datetime import datetime, timezone, timedelta, date
import asyncio
import pytest


def test_request_governance_date_is_pinned_and_restored_across_thread_offload():
    from security_master_schema.governance_clock import governance_date, governance_scope
    from starlette.concurrency import run_in_threadpool
    async def run():
        with governance_scope(datetime(2026,10,17,0,30,tzinfo=timezone(timedelta(hours=14)))):
            assert governance_date()==date(2026,10,16)
            assert await run_in_threadpool(governance_date)==date(2026,10,16)
            with governance_scope(datetime(2026,10,18,tzinfo=timezone.utc)):
                assert governance_date()==date(2026,10,18)
            assert governance_date()==date(2026,10,16)
    asyncio.run(run())


def test_naive_governance_instant_is_rejected_not_interpreted_in_host_zone():
    from security_master_schema.governance_clock import governance_date
    with pytest.raises(ValueError):governance_date(datetime(2026,10,17))


@pytest.mark.parametrize('offset,expected',[(14,'2026-10-16'),(-7,'2026-10-17'),(0,'2026-10-17')])
def test_explicit_governance_instant_uses_utc(offset,expected):
    from security_master_schema.governance_clock import governance_date
    assert governance_date(datetime(2026,10,17,0,30,tzinfo=timezone(timedelta(hours=offset)))).isoformat()==expected
