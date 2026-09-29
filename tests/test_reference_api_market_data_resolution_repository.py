"""Focused tests for replay-safe Market Data snapshot repository operations."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, update

from apps.reference_api.contracts import MarketDataResolutionSnapshotCreate
from apps.reference_api.repository import (
    IdempotencyKeyConflict,
    create_market_data_resolution_snapshot,
    get_market_data_resolution_snapshot,
    list_active_valuation_policies,
)
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS, load_demo_data


DATABASE_URL = "postgresql+psycopg://fortem:fortem_local_only@localhost:54329/fortem_secm"


@pytest.fixture(scope="module")
def seeded_engine():
    engine = create_engine(DATABASE_URL)
    load_demo_data(engine)
    return engine


def _payload(*, subjects=None, as_of=None) -> MarketDataResolutionSnapshotCreate:
    return MarketDataResolutionSnapshotCreate(
        subjectReferenceNodeIds=subjects if subjects is not None else [
            DEMO_IDS["hsbc_xlon_listing_node"],
            DEMO_IDS["demo_share_class_instrument_node"],
        ],
        valuationPolicyId=DEMO_IDS["valuation_policy"],
        valuationDate="2026-08-28",
        valuationCutId=DEMO_IDS["valuation_cut"],
        marketDataAsOfUtc=as_of or datetime.now(timezone.utc),
        usePurpose="VALUATION",
    )


@pytest.mark.parametrize(
    "subjects,as_of",
    [([], None), ([DEMO_IDS["hsbc_xlon_listing_node"]] * 2, None), ([uuid4() for _ in range(51)], None), ([DEMO_IDS["hsbc_xlon_listing_node"]], datetime(2026, 8, 28, 16, 0))],
)
def test_create_contract_rejects_invalid_batch_or_non_utc_cut(subjects, as_of) -> None:
    with pytest.raises(ValidationError):
        _payload(subjects=subjects, as_of=as_of)


def test_create_replay_conflict_and_frozen_read(seeded_engine) -> None:
    with seeded_engine.connect() as connection:
        transaction = connection.begin()
        try:
            payload = _payload()
            key = f"test-{uuid4()}"
            created = create_market_data_resolution_snapshot(
                connection, DEMO_IDS["tenant"], payload, key, "test-request"
            )
            assert [item.subject_reference_node_id for item in created.items] == payload.subject_reference_node_ids
            assert created.use_purpose == "VALUATION"
            assert all(item.market_data_observation_id for item in created.items)

            replay = create_market_data_resolution_snapshot(
                connection, DEMO_IDS["tenant"], payload, key, "test-request"
            )
            assert replay.market_data_resolution_snapshot_id == created.market_data_resolution_snapshot_id

            with pytest.raises(IdempotencyKeyConflict):
                create_market_data_resolution_snapshot(
                    connection,
                    DEMO_IDS["tenant"],
                    _payload(subjects=[DEMO_IDS["hsbc_xlon_listing_node"]]),
                    key,
                    "test-request",
                )

            connection.execute(
                update(m.tenant_dataset_entitlement)
                .where(m.tenant_dataset_entitlement.c.tenant_id == DEMO_IDS["tenant"])
                .values(status="SUSPENDED")
            )
            frozen = get_market_data_resolution_snapshot(
                connection, DEMO_IDS["tenant"], created.market_data_resolution_snapshot_id
            )
            assert frozen == created
        finally:
            transaction.rollback()


def test_active_policy_lookup_is_tenant_scoped(seeded_engine) -> None:
    with seeded_engine.connect() as connection:
        policies = list_active_valuation_policies(
            connection, DEMO_IDS["tenant"], datetime(2026, 8, 28, tzinfo=timezone.utc).date()
        )

    assert any(policy.valuation_policy_id == DEMO_IDS["valuation_policy"] for policy in policies)
    assert all(policy.tenant_id == DEMO_IDS["tenant"] for policy in policies)
