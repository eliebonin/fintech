"""Readiness must describe the real writer boundary, without writes or row locks."""
import asyncio
from datetime import date, datetime, timezone
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, update, func, text
from apps.reference_api.main import create_app
from apps.reference_api.db import get_engine
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from tests.test_cash_booking_integrity import connection, cloned_listing


def request(c, path):
    app = create_app()
    route = next(r for r in app.routes if getattr(r, 'path', None) == '/v1/trades')
    dependency = next(d.call for d in route.dependant.dependencies if d.call.__name__ == 'connection_dependency')
    def injected():
        yield c
    app.dependency_overrides[dependency] = injected
    async def run():
        async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
            return await client.get(path, headers={'X-Tenant-Id': str(ids['tenant']), 'X-User-Account-Id': str(ids['demo_user_account'])})
    return asyncio.run(run())


def detail(c, listing=None, when='2026-09-30'):
    return request(c, f"/v1/trades/cash-listings/{listing or ids['hsbc_xlon_listing_node']}?asOfDate={when}")


def test_ready_cash_read_does_not_book_or_hold_writer_locks(connection):
    before = connection.scalar(select(func.count()).select_from(m.trade))
    response = detail(connection)
    assert response.status_code == 200, response.text
    data = response.json()['data']
    assert data['bookingEligible'] is True
    assert data['readinessStatus'] == 'READY'
    assert data['marketVenueMic'] == 'XLON'
    assert data['parentReferenceNodeId'] == str(ids['hsbc_instrument_node'])
    assert connection.scalar(select(func.count()).select_from(m.trade)) == before
    with get_engine().begin() as other:
        other.execute(text("SET LOCAL lock_timeout = '200ms'"))
        other.execute(select(m.currency).where(m.currency.c.currency_id == ids['gbp_currency']).with_for_update()).all()


def test_draft_cash_is_inspectable_but_not_ready(connection):
    listing = cloned_listing(connection, listing_status='DRAFT')
    response = detail(connection, listing)
    assert response.status_code == 200, response.text
    data = response.json()['data']
    assert data['bookingEligible'] is False
    assert data['readinessStatus'] == 'MISSING_CONFIGURATION'
    assert data['ineligibilityMessage']


def test_cash_readiness_changes_with_selected_date(connection):
    listing = cloned_listing(connection, start=date(2026, 10, 1))
    assert detail(connection, listing).json()['data']['bookingEligible'] is False
    assert detail(connection, listing, '2026-10-01').json()['data']['bookingEligible'] is True


def test_inactive_visible_cash_is_explained(connection):
    connection.execute(update(m.listing).where(m.listing.c.listing_node_id == ids['hsbc_xlon_listing_node']).values(status='SUSPENDED'))
    data = detail(connection).json()['data']
    assert data['bookingEligible'] is False
    assert data['readinessStatus'] == 'INACTIVE'


def test_foreign_parent_is_neither_searchable_nor_inspectable(connection):
    connection.execute(update(m.reference_node_scope).where(m.reference_node_scope.c.reference_node_id == ids['hsbc_instrument_node']).values(scope_type='TENANT_PRIVATE', owner_tenant_id=ids['second_tenant']))
    assert detail(connection).status_code == 404
    response = request(connection, '/v1/trades/cash-listings?q=HSBC&asOfDate=2026-09-30')
    assert response.status_code == 200, response.text
    assert response.json()['data'] == []
    assert response.json()['meta']['total'] == 0


def test_cash_search_paginates_and_reports_unavailable_without_filtering_it_away(connection):
    draft = cloned_listing(connection, listing_status='DRAFT')
    response = request(connection, f'/v1/trades/cash-listings?q={draft}&asOfDate=2026-09-30&limit=1')
    assert response.status_code == 200, response.text
    assert response.json()['meta']['total'] == 1
    assert response.json()['data'][0]['bookingEligible'] is False
    assert request(connection, f'/v1/trades/cash-listings?q={draft}&offset=1&limit=1').json()['data'] == []


def test_default_readiness_date_uses_utc_not_server_local_calendar(connection, monkeypatch):
    from apps.reference_api import cash_booking_readiness as readiness
    class UtcClock:
        @staticmethod
        def now(tz):
            assert tz is timezone.utc
            return datetime(2026, 10, 4, 23, 30, tzinfo=timezone.utc)
    monkeypatch.setattr(readiness, 'datetime', UtcClock, raising=False)
    response = request(connection, f"/v1/trades/cash-listings/{ids['hsbc_xlon_listing_node']}")
    assert response.status_code == 200, response.text
    assert response.json()['data']['asOfDate'] == '2026-10-04'
