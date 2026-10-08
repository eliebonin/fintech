"""Authoritative cash reference checks; no UI filtering is trusted."""
from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy import select, update, func, text
from apps.reference_api.db import get_engine
from apps.reference_api import repository as r
from apps.reference_api.contracts import TradeBookingRequest
from apps.reference_api.trade_properties import TradeFieldError
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids


@pytest.fixture
def connection():
    with get_engine().connect() as c:
        transaction = c.begin()
        try:
            yield c
        finally:
            transaction.rollback()


def payload(listing=None):
    return TradeBookingRequest(listingId=listing or ids['hsbc_xlon_listing_node'], strategyId=ids['strategy'],
        side='BUY', quantity='10', executionPrice='1.23', tradeDatetime='2026-09-30T10:00:00Z', settlementDate='2026-10-02')


def book(c, request=None, key=None):
    return r.book_listed_cash_trade(c, ids['tenant'], ids['demo_user_account'], request or payload(), key or str(uuid4()), 'cash-integrity')


CASES = {
    'foreign_listing': (m.reference_node_scope, 'reference_node_id', 'hsbc_xlon_listing_node', dict(scope_type='TENANT_PRIVATE', owner_tenant_id=ids['second_tenant'])),
    'foreign_parent': (m.reference_node_scope, 'reference_node_id', 'hsbc_instrument_node', dict(scope_type='TENANT_PRIVATE', owner_tenant_id=ids['second_tenant'])),
    'inactive_listing_scope': (m.reference_node_scope, 'reference_node_id', 'hsbc_xlon_listing_node', dict(status='INACTIVE')),
    'inactive_parent_scope': (m.reference_node_scope, 'reference_node_id', 'hsbc_instrument_node', dict(status='INACTIVE')),
    'untradable_listing': (m.financial_reference_node, 'reference_node_id', 'hsbc_xlon_listing_node', dict(is_tradable=False)),
    'inactive_parent': (m.financial_reference_node, 'reference_node_id', 'hsbc_instrument_node', dict(status='INACTIVE')),
    'inactive_listing': (m.listing, 'listing_node_id', 'hsbc_xlon_listing_node', dict(status='SUSPENDED')),
    'not_current': (m.instrument, 'instrument_node_id', 'hsbc_instrument_node', dict(is_current=False)),
    'inactive_currency': (m.currency, 'currency_id', 'gbp_currency', dict(status='INACTIVE')),
    'inactive_venue': (m.market_venue, 'market_venue_id', 'xlon_venue', dict(status='INACTIVE')),
    'future_listing_date': (m.listing, 'listing_node_id', 'hsbc_xlon_listing_node', dict(effective_from=date(2027,1,1))),
    'changed_quote_factor': (m.listing, 'listing_node_id', 'hsbc_xlon_listing_node', dict(quote_factor='1')),
    'changed_multiplier': (m.listing, 'listing_node_id', 'hsbc_xlon_listing_node', dict(unit_multiplier='2')),
    'changed_currency': (m.listing, 'listing_node_id', 'hsbc_xlon_listing_node', dict(trading_currency_id=ids['usd_currency'])),
    'changed_parent_currency': (m.instrument, 'instrument_node_id', 'hsbc_instrument_node', dict(base_currency_id=ids['usd_currency'])),
}


def change(c, case):
    table, key, identifier, values = CASES[case]
    c.execute(update(table).where(table.c[key] == ids[identifier]).values(**values))


@pytest.mark.parametrize('case', CASES)
def test_invalid_cash_reference_refused_atomically(connection, case):
    change(connection, case)
    before = connection.scalar(select(func.count()).select_from(m.trade))
    with pytest.raises((r.RepositoryNotFound, TradeFieldError)):
        book(connection)
    assert connection.scalar(select(func.count()).select_from(m.trade)) == before


def clone(c, table, key, old, new, changes=None):
    values = dict(c.execute(select(table).where(table.c[key] == old)).mappings().one())
    for pk in table.primary_key.columns:
        if pk.name != key:
            values[pk.name] = uuid4()
    values[key] = new
    values.update(changes or {})
    c.execute(table.insert().values(**values))


def cloned_listing(c, *, parent_status='APPROVED', listing_status='APPROVED', product=None, start=None):
    parent, listing = uuid4(), uuid4()
    clone(c, m.financial_reference_node, 'reference_node_id', ids['hsbc_instrument_node'], parent, dict(internal_code=None))
    parent_changes = {}
    if product:
        parent_changes['instrument_type_id'] = c.scalar(select(m.instrument_type.c.instrument_type_id).where(m.instrument_type.c.type_code == product))
    clone(c, m.instrument, 'instrument_node_id', ids['hsbc_instrument_node'], parent, parent_changes)
    clone(c, m.instrument_definition_version, 'instrument_node_id', ids['hsbc_instrument_node'], parent,
          parent_changes | dict(status=parent_status))
    clone(c, m.financial_reference_node, 'reference_node_id', ids['hsbc_xlon_listing_node'], listing, dict(internal_code=None))
    listing_changes = dict(instrument_node_id=parent, trading_symbol='CI'+uuid4().hex[:12])
    if start:
        listing_changes['effective_from'] = start
    clone(c, m.listing, 'listing_node_id', ids['hsbc_xlon_listing_node'], listing, listing_changes)
    version_changes = {key:value for key,value in listing_changes.items() if key != 'instrument_node_id'}
    clone(c, m.listing_definition_version, 'listing_node_id', ids['hsbc_xlon_listing_node'], listing, version_changes | dict(status=listing_status))
    for node in (parent, listing):
        c.execute(m.reference_node_scope.insert().values(reference_node_id=node, scope_type='TENANT_PRIVATE', owner_tenant_id=ids['tenant'], status='ACTIVE'))
    return listing


@pytest.mark.parametrize('kind', ['parent', 'listing'])
def test_draft_definition_is_not_bookable(connection, kind):
    listing = cloned_listing(connection, **{f'{kind}_status':'DRAFT'})
    with pytest.raises(TradeFieldError):
        book(connection, payload(listing))


@pytest.mark.parametrize('product', ['FORWARD', 'CONVERTIBLE_BOND', 'WARRANT', 'REPO'])
def test_unsupported_cash_product_does_not_fall_through(connection, product):
    listing = cloned_listing(connection, product=product)
    with pytest.raises(TradeFieldError):
        book(connection, payload(listing))


def test_execution_before_approved_listing_start_is_refused(connection):
    listing = cloned_listing(connection, start=date(2026,10,1))
    with pytest.raises(TradeFieldError):
        book(connection, payload(listing))


def test_exact_replay_preserves_history_after_reference_retirement(connection):
    key = str(uuid4())
    first = book(connection, key=key)
    change(connection, 'foreign_listing')
    change(connection, 'inactive_parent')
    replay = book(connection, key=key)
    assert replay.data.trade.trade_id == first.data.trade.trade_id
    assert r.get_booked_trade_detail(connection, ids['tenant'], first.data.trade.trade_id, 'v1', 'test') is not None
    with pytest.raises(r.RepositoryNotFound):
        book(connection)


def test_valid_listing_preserves_native_quote_and_approved_factors(connection):
    import json
    from decimal import Decimal
    # Canonical equity is intentionally not directly tradable; listing is.
    assert connection.scalar(select(m.financial_reference_node.c.is_tradable).where(m.financial_reference_node.c.reference_node_id == ids['hsbc_instrument_node'])) is False
    booked = book(connection)
    assert Decimal(booked.data.trade.execution_price) == Decimal('1.23')
    raw = connection.scalar(select(m.trade_lifecycle_event.c.event_payload).where(m.trade_lifecycle_event.c.trade_id == booked.data.trade.trade_id))
    snapshot = json.loads(raw)
    assert snapshot['kind'] == 'CASH_BOOKING'
    assert snapshot['quoteFactor'] == '100.00000000'
    assert snapshot['unitMultiplier'] == '1.00000000'
    assert snapshot['listingDefinitionId']


def test_locked_cash_scope_cannot_be_revoked_concurrently(connection):
    from sqlalchemy.exc import OperationalError
    from apps.reference_api.cash_booking_integrity import load_cash_booking_listing
    load_cash_booking_listing(connection, ids['tenant'], ids['hsbc_xlon_listing_node'], date(2026,9,30))
    with get_engine().begin() as other:
        other.execute(text("SET LOCAL lock_timeout = '200ms'"))
        with pytest.raises(OperationalError) as error:
            other.execute(update(m.reference_node_scope).where(m.reference_node_scope.c.reference_node_id == ids['hsbc_xlon_listing_node']).values(status='INACTIVE'))
        assert error.value.orig.sqlstate == '55P03'


def test_http_cannot_book_foreign_private_listing(connection):
    import asyncio
    from httpx import ASGITransport, AsyncClient
    from apps.reference_api.main import create_app
    change(connection, 'foreign_listing')
    before = connection.scalar(select(func.count()).select_from(m.trade))
    app = create_app()
    route = next(v for v in app.routes if getattr(v,'path',None) == '/v1/trades' and 'POST' in getattr(v,'methods',set()))
    dependency = next(d.call for d in route.dependant.dependencies if d.call.__name__ == 'connection_dependency')
    def injected():
        yield connection
    app.dependency_overrides[dependency] = injected
    async def run():
        async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
            return await client.post('/v1/trades', json=payload().model_dump(mode='json',by_alias=True), headers={
                'X-Tenant-Id':str(ids['tenant']), 'X-User-Account-Id':str(ids['demo_user_account']), 'Idempotency-Key':str(uuid4())})
    response = asyncio.run(run())
    assert response.status_code == 404, response.text
    assert connection.scalar(select(func.count()).select_from(m.trade)) == before


def test_cash_revocation_while_waiting_refuses_new_booking():
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from time import monotonic, sleep
    ready = Event()
    worker_pid = []
    def submit():
        with get_engine().begin() as worker:
            worker_pid.append(worker.scalar(text('SELECT pg_backend_pid()')))
            ready.set()
            with pytest.raises(r.RepositoryNotFound):
                book(worker)
    with get_engine().connect() as revoker, ThreadPoolExecutor(max_workers=1) as pool:
        transaction = revoker.begin()
        original = revoker.scalar(select(m.reference_node_scope.c.status).where(m.reference_node_scope.c.reference_node_id == ids['hsbc_xlon_listing_node']))
        future = None
        try:
            revoker.execute(update(m.reference_node_scope).where(m.reference_node_scope.c.reference_node_id == ids['hsbc_xlon_listing_node']).values(status='INACTIVE'))
            future = pool.submit(submit)
            assert ready.wait(5)
            deadline = monotonic() + 5
            with get_engine().connect() as observer:
                while monotonic() < deadline:
                    if observer.scalar(text('SELECT cardinality(pg_blocking_pids(:pid))'), {'pid':worker_pid[0]}):
                        break
                    sleep(0.01)
                else:
                    pytest.fail('Cash booking did not wait for the scope lock')
            transaction.commit()
        finally:
            if transaction.is_active:
                transaction.rollback()
            if future is not None:
                try:
                    future.result(timeout=5)
                finally:
                    with get_engine().begin() as restore:
                        restore.execute(update(m.reference_node_scope).where(m.reference_node_scope.c.reference_node_id == ids['hsbc_xlon_listing_node']).values(status=original))
