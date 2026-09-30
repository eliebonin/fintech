"""Database constraints for durable listed-cash trade booking."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, insert, select
from sqlalchemy.exc import IntegrityError

from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS, load_demo_data


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
