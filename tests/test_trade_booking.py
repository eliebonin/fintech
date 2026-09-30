"""Database constraints for durable listed-cash trade booking."""

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, insert, select
from sqlalchemy.exc import IntegrityError

from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS, load_demo_data
from apps.reference_api.contracts import TradeBookingRequest
from apps.reference_api.repository import IdempotencyKeyConflict, book_listed_cash_trade


DATABASE_URL = "postgresql+psycopg://fortem:fortem_local_only@localhost:54329/fortem_secm"


def test_trade_booking_idempotency_is_unique_per_tenant_endpoint_and_key() -> None:
    """The same command key must never create two immutable booked trades."""

    engine = create_engine(DATABASE_URL)
    load_demo_data(engine)
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            trade_id = connection.scalar(select(m.trade.c.trade_id).limit(1))
            assert trade_id is not None
            values = {
                "tenant_id": DEMO_IDS["tenant"],
                "endpoint": "/v1/trades",
                "idempotency_key": f"trade-booking-{uuid4()}",
                "request_fingerprint": "a" * 64,
                "trade_id": trade_id,
                "created_at_utc": datetime.now(timezone.utc),
            }
            connection.execute(insert(m.trade_booking_idempotency).values(**values))
            with pytest.raises(IntegrityError):
                connection.execute(insert(m.trade_booking_idempotency).values(**values))
        finally:
            transaction.rollback()


def _booking_request(*, side: str = "BUY") -> TradeBookingRequest:
    return TradeBookingRequest(
        listingId=DEMO_IDS["hsbc_xlon_listing_node"],
        strategyId=DEMO_IDS["strategy"],
        side=side,
        quantity=Decimal("1250"),
        executionPrice=Decimal("10.23"),
        tradeDatetime=datetime(2026, 9, 30, 14, 32, tzinfo=timezone.utc),
        settlementDate=date(2026, 10, 2),
    )


def test_books_listing_buy_with_derived_parent_currency_venue_and_lifecycle() -> None:
    engine = create_engine(DATABASE_URL)
    load_demo_data(engine)
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            detail = book_listed_cash_trade(
                connection,
                DEMO_IDS["tenant"],
                DEMO_IDS["demo_user_account"],
                _booking_request(),
                f"booking-buy-{uuid4()}",
                "request-buy",
            )
            assert detail.data.trade.listing_id == DEMO_IDS["hsbc_xlon_listing_node"]
            assert detail.data.trade.instrument_id == DEMO_IDS["hsbc_instrument_node"]
            assert Decimal(detail.data.trade.quantity) == Decimal("1250")
            assert detail.data.trade.price_currency == "GBP"
            assert detail.data.lifecycle_events[0].event_type == "BOOKED"
        finally:
            transaction.rollback()


def test_books_sell_as_negative_quantity_and_replays_the_same_key() -> None:
    engine = create_engine(DATABASE_URL)
    load_demo_data(engine)
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            request = _booking_request(side="SELL")
            key = f"booking-sell-{uuid4()}"
            first = book_listed_cash_trade(connection, DEMO_IDS["tenant"], DEMO_IDS["demo_user_account"], request, key, "request-sell-1")
            replay = book_listed_cash_trade(connection, DEMO_IDS["tenant"], DEMO_IDS["demo_user_account"], request, key, "request-sell-2")
            assert Decimal(first.data.trade.quantity) == Decimal("-1250")
            assert replay.data.trade.trade_id == first.data.trade.trade_id
        finally:
            transaction.rollback()


def test_rejects_a_reused_booking_key_with_changed_execution_facts() -> None:
    engine = create_engine(DATABASE_URL)
    load_demo_data(engine)
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            key = f"booking-conflict-{uuid4()}"
            book_listed_cash_trade(connection, DEMO_IDS["tenant"], DEMO_IDS["demo_user_account"], _booking_request(), key, "request-1")
            with pytest.raises(IdempotencyKeyConflict, match="Idempotency key was already used"):
                book_listed_cash_trade(
                    connection,
                    DEMO_IDS["tenant"],
                    DEMO_IDS["demo_user_account"],
                    _booking_request(side="SELL"),
                    key,
                    "request-2",
                )
        finally:
            transaction.rollback()
