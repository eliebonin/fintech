"""Database constraints for frozen market-data resolution evidence."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, insert, select, update
from sqlalchemy.exc import DBAPIError, IntegrityError

from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS, load_demo_data


DATABASE_URL = "postgresql+psycopg://fortem:fortem_local_only@localhost:54329/fortem_secm"


def test_resolution_snapshot_item_preserves_frozen_vintage_evidence() -> None:
    """Removing frozen vintage evidence would make a later replay unauditable."""

    engine = create_engine(DATABASE_URL)
    load_demo_data(engine)
    frozen_at = datetime(2026, 8, 28, 16, 0, tzinfo=timezone.utc)

    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            snapshot_id = uuid4()
            item_id = uuid4()
            vintage_id = connection.scalar(
                select(m.market_data_vintage.c.market_data_vintage_id).limit(1)
            )
            assert vintage_id is not None
            connection.execute(
                insert(m.market_data_resolution_snapshot).values(
                    market_data_resolution_snapshot_id=snapshot_id,
                    tenant_id=DEMO_IDS["tenant"],
                    valuation_policy_id=DEMO_IDS["valuation_policy"],
                    valuation_date=datetime(2026, 8, 28, tzinfo=timezone.utc).date(),
                    valuation_cut_id=DEMO_IDS["valuation_cut"],
                    market_data_as_of_utc=frozen_at,
                    resolver_version="schema-test",
                    status="COMPLETED",
                    use_purpose="VALUATION",
                )
            )
            connection.execute(
                insert(m.market_data_resolution_snapshot_item).values(
                    market_data_resolution_snapshot_item_id=item_id,
                    market_data_resolution_snapshot_id=snapshot_id,
                    subject_reference_node_id=DEMO_IDS["hsbc_xlon_listing_node"],
                    selection_reason="ENTITLED_PROVIDER",
                    entitlement_decision="ALLOWED",
                    market_data_vintage_id=vintage_id,
                    source_published_at_utc=frozen_at,
                    received_at_utc=frozen_at + timedelta(minutes=1),
                    acquisition_licence_id=DEMO_IDS["data_licence"],
                )
            )
            row = connection.execute(
                select(
                    m.market_data_resolution_snapshot_item.c.market_data_vintage_id,
                    m.market_data_resolution_snapshot_item.c.source_published_at_utc,
                    m.market_data_resolution_snapshot_item.c.received_at_utc,
                    m.market_data_resolution_snapshot_item.c.acquisition_licence_id,
                ).where(
                    m.market_data_resolution_snapshot_item.c.market_data_resolution_snapshot_item_id
                    == item_id
                )
            ).one()
            use_purpose = connection.scalar(
                select(m.market_data_resolution_snapshot.c.use_purpose).where(
                    m.market_data_resolution_snapshot.c.market_data_resolution_snapshot_id
                    == snapshot_id
                )
            )
        finally:
            transaction.rollback()

    assert use_purpose == "VALUATION"
    assert row.market_data_vintage_id == vintage_id
    assert row.source_published_at_utc == frozen_at
    assert row.received_at_utc == frozen_at + timedelta(minutes=1)
    assert row.acquisition_licence_id == DEMO_IDS["data_licence"]


def test_idempotency_key_is_unique_within_tenant_and_endpoint() -> None:
    """Dropping the unique scope would permit duplicate immutable snapshots."""

    engine = create_engine(DATABASE_URL)
    load_demo_data(engine)
    values = {
        "tenant_id": DEMO_IDS["tenant"],
        "endpoint": "/v1/market-data-resolution-snapshots",
        "idempotency_key": "schema-test-key",
        "request_fingerprint": "a" * 64,
        "market_data_resolution_snapshot_id": DEMO_IDS["resolution_snapshot"],
        "expires_at_utc": datetime.now(timezone.utc) + timedelta(days=1),
    }

    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            connection.execute(insert(m.market_data_resolution_idempotency).values(**values))
            with pytest.raises(IntegrityError):
                connection.execute(insert(m.market_data_resolution_idempotency).values(**values))
        finally:
            transaction.rollback()


def test_snapshot_rows_reject_direct_mutation() -> None:
    """Removing append-only protection would allow audit evidence to be altered."""

    engine = create_engine(DATABASE_URL)
    load_demo_data(engine)
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            with pytest.raises(DBAPIError):
                connection.execute(
                    update(m.market_data_resolution_snapshot_item)
                    .where(
                        m.market_data_resolution_snapshot_item.c.market_data_resolution_snapshot_item_id
                        == DEMO_IDS["resolution_item"]
                    )
                    .values(selection_reason="MUTATED")
                )
        finally:
            transaction.rollback()
