"""Cross-product writer boundaries; run only through the isolated database runner."""
from uuid import uuid4

import pytest
from sqlalchemy import func, select, update

from apps.reference_api import repository, fx_forward_booking, option_booking, product_booking
from apps.reference_api.contracts import TradeBookingRequest, OptionBookingRequest, FxForwardBookingRequest
from apps.reference_api.product_booking_contracts import ProductBookingRequest
from apps.reference_api.db import get_engine
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS
from security_master_schema.tenant_workspace import TenantActionForbidden


@pytest.fixture
def connection():
    with get_engine().connect() as c:
        transaction = c.begin()
        try:
            yield c
        finally:
            transaction.rollback()


def cash_request():
    return TradeBookingRequest(listingId=DEMO_IDS['hsbc_xlon_listing_node'], strategyId=DEMO_IDS['strategy'],
        side='BUY', quantity='1250', executionPrice='10.23', tradeDatetime='2026-09-30T14:32:00Z', settlementDate='2026-10-02')


def test_historical_cash_fingerprint_and_lock_namespace_are_preserved():
    assert repository._trade_booking_fingerprint(cash_request(), None, DEMO_IDS['tenant']) == '71e4ebfb5effd6f2751c6d3e648929841e40524f3996cdb9106bed9c2cdae311'
    assert repository._trade_booking_idempotency_lock_key(DEMO_IDS['tenant'], 'controls-compatibility') == 6579829877238748373


def test_shared_lock_preserves_historical_hash_and_separates_endpoints():
    from apps.reference_api import booking_controls
    assert booking_controls.booking_lock_key(DEMO_IDS['tenant'], '/v1/trades', 'controls-compatibility') == 6579829877238748373
    assert booking_controls.booking_lock_key(DEMO_IDS['tenant'], '/v1/trades/options', 'controls-compatibility') != 6579829877238748373


def test_shared_replay_is_scoped_and_conflicts_on_changed_fingerprint(connection):
    from apps.reference_api import booking_controls
    key = str(uuid4())
    trade = call_writer('CASH', connection, DEMO_IDS['demo_user_account'], key).data.trade.trade_id
    fingerprint = repository._trade_booking_fingerprint(cash_request(), connection, DEMO_IDS['tenant'])
    assert booking_controls.find_booking_replay(connection, DEMO_IDS['tenant'], '/v1/trades', key, fingerprint) == trade
    assert booking_controls.find_booking_replay(connection, DEMO_IDS['tenant'], '/v1/trades/options', key, fingerprint) is None
    with pytest.raises(repository.IdempotencyKeyConflict):
        booking_controls.find_booking_replay(connection, DEMO_IDS['tenant'], '/v1/trades', key, 'b'*64)


def call_writer(kind, c, actor, key):
    tenant = DEMO_IDS['tenant']
    common = cash_request().model_dump(by_alias=True)
    if kind == 'CASH':
        return repository.book_listed_cash_trade(c, tenant, actor, cash_request(), key, 'controls')
    if kind == 'OPTION':
        request = OptionBookingRequest(**(common | {'positionEffect': 'OPEN', 'expectedTermsFingerprint': 'a'*64}))
        return option_booking.book(c, tenant, actor, request, key, 'controls')
    if kind == 'FX_FORWARD':
        request = FxForwardBookingRequest(instrumentId=uuid4(), strategyId=DEMO_IDS['strategy'], side='BUY',
            quantity='100', tradeDatetime='2026-10-01T10:00:00Z',
            counterpartyOrganisationId=DEMO_IDS['bank_a_organisation'], expectedTermsFingerprint='a'*64)
        return fx_forward_booking.book_fx_forward_trade(c, tenant, actor, request, key, 'controls')
    request = ProductBookingRequest(**(common | {'instrumentId': uuid4(), 'listingId': None,
        'executionRoute': 'OTC', 'expectedTermsFingerprint': 'a'*64}))
    return product_booking.book(c, tenant, actor, request, key, kind, 'controls')


@pytest.mark.parametrize('kind', ['CASH', 'FX_FORWARD', 'OPTION', 'STRUCTURED_PRODUCT', 'FUTURE', 'BOND', 'SWAP'])
@pytest.mark.parametrize('denial', ['inactive_actor', 'inactive_membership', 'missing_module'])
def test_direct_writer_rejects_unauthorized_actor_before_economic_lookup(connection, kind, denial):
    actor = DEMO_IDS['demo_user_account']
    if denial == 'inactive_actor':
        connection.execute(update(m.user_account).where(m.user_account.c.user_account_id == actor).values(status='INACTIVE'))
    elif denial == 'inactive_membership':
        connection.execute(update(m.tenant_user_account).where(m.tenant_user_account.c.tenant_id == DEMO_IDS['tenant'],
            m.tenant_user_account.c.user_account_id == actor).values(status='INACTIVE'))
    else:
        connection.execute(update(m.tenant_module_entitlement).where(m.tenant_module_entitlement.c.tenant_id == DEMO_IDS['tenant']).values(entitlement_state='REVOKED'))
    before = connection.scalar(select(func.count()).select_from(m.trade))
    with pytest.raises(TenantActionForbidden):
        call_writer(kind, connection, actor, str(uuid4()))
    assert connection.scalar(select(func.count()).select_from(m.trade)) == before


def test_direct_cash_late_failure_rolls_back_booking_and_preserves_outer_transaction(connection, monkeypatch):
    before = connection.scalar(select(func.count()).select_from(m.trade))
    def fail_after_trade(*args):
        raise ValueError('forced late annotation failure')
    monkeypatch.setattr(repository, 'persist_trade_annotations', fail_after_trade)
    with pytest.raises(ValueError, match='forced late annotation failure'):
        call_writer('CASH', connection, DEMO_IDS['demo_user_account'], str(uuid4()))
    assert connection.scalar(select(func.count()).select_from(m.trade)) == before
    assert connection.scalar(select(m.strategy.c.strategy_id).where(m.strategy.c.strategy_id == DEMO_IDS['strategy'])) == DEMO_IDS['strategy']


def test_authorized_cash_replay_survives_strategy_retirement_but_revoked_actor_cannot_replay(connection):
    key = str(uuid4())
    first = call_writer('CASH', connection, DEMO_IDS['demo_user_account'], key)
    connection.execute(update(m.strategy).where(m.strategy.c.strategy_id == DEMO_IDS['strategy']).values(status='INACTIVE'))
    assert call_writer('CASH', connection, DEMO_IDS['demo_user_account'], key).data.trade.trade_id == first.data.trade.trade_id
    connection.execute(update(m.user_account).where(m.user_account.c.user_account_id == DEMO_IDS['demo_user_account']).values(status='INACTIVE'))
    with pytest.raises(TenantActionForbidden):
        call_writer('CASH', connection, DEMO_IDS['demo_user_account'], key)


def test_opposite_party_roles_across_tenants_do_not_deadlock():
    """A tenant-local catalogue lock cannot serialize shared organisation rows."""
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from sqlalchemy import event, text
    from apps.reference_api.trade_properties import validate_trade_annotations
    first_locked, second_locked, release_first = Event(), Event(), Event()

    def validate(tenant, counterparty, broker, first):
        with get_engine().connect() as c:
            transaction = c.begin()
            seen = False
            def after_execute(conn, cursor, statement, parameters, context, many):
                nonlocal seen
                if not seen and 'organisation' in statement and 'FOR UPDATE' in statement:
                    seen = True
                    if first:
                        first_locked.set()
                        assert release_first.wait(4)
                    else:
                        second_locked.set()
            event.listen(c, 'after_cursor_execute', after_execute)
            try:
                c.execute(text("SET LOCAL lock_timeout = '5s'"))
                request = cash_request().model_copy(update={'counterparty_organisation_id': counterparty,
                    'executing_broker_organisation_id': broker})
                validate_trade_annotations(c, tenant, request)
                return 'OK'
            except Exception as error:
                return getattr(getattr(error, 'orig', None), 'sqlstate', None) or str(error)
            finally:
                event.remove(c, 'after_cursor_execute', after_execute)
                transaction.rollback()

    with ThreadPoolExecutor(max_workers=2) as pool:
        a = pool.submit(validate, DEMO_IDS['tenant'], DEMO_IDS['hsbc_organisation'], DEMO_IDS['bank_a_organisation'], True)
        assert first_locked.wait(4)
        b = pool.submit(validate, DEMO_IDS['second_tenant'], DEMO_IDS['bank_a_organisation'], DEMO_IDS['hsbc_organisation'], False)
        # Old role ordering acquires B's other row; corrected UUID order waits on A.
        second_locked.wait(0.5)
        release_first.set()
        assert [a.result(timeout=8), b.result(timeout=8)] == ['OK', 'OK']
