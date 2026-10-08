"""Database-backed valuation selection tests."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, insert, select, update
from sqlalchemy.exc import DBAPIError

from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS, load_demo_data
from security_master_schema.market_data_resolver import (
    ResolutionRequest,
    ValuationPolicyScopeError,
    persist_resolution_snapshot,
    resolve_market_data,
    resolve_market_data_batch,
)


DATABASE_URL = "postgresql+psycopg://fortem:fortem_local_only@localhost:54329/fortem_secm"


def test_legacy_selection_and_snapshot_preserve_database_decimal(seeded_engine):
    with seeded_engine.connect() as connection:
        transaction=connection.begin()
        try:
            day=connection.scalar(select(m.valuation_policy.c.valid_from).where(
                m.valuation_policy.c.valuation_policy_id==DEMO_IDS['valuation_policy']))
            expected=Decimal('123456789.123456789123')
            connection.execute(update(m.market_data_observation).where(
                m.market_data_observation.c.market_data_observation_id==DEMO_IDS['market_data_observation']).values(value=expected))
            request=_request(day)
            result=resolve_market_data(connection,request)
            assert result.status=='SELECTED'
            assert result.selected_value==expected
            snapshot=persist_resolution_snapshot(connection,request,(result,))
            stored=connection.scalar(select(m.market_data_resolution_snapshot_item.c.selected_value).where(
                m.market_data_resolution_snapshot_item.c.market_data_resolution_snapshot_id==snapshot))
            assert stored==expected
        finally:
            transaction.rollback()


def _request(valuation_date) -> ResolutionRequest:
    return ResolutionRequest(
        tenant_id=DEMO_IDS["tenant"],
        subject_reference_node_id=DEMO_IDS["hsbc_xlon_listing_node"],
        valuation_policy_id=DEMO_IDS["valuation_policy"],
        valuation_date=valuation_date,
        valuation_cut_id=DEMO_IDS["valuation_cut"],
        market_data_as_of_utc=datetime.now(timezone.utc),
        use_purpose="VALUATION",
    )


@pytest.fixture(scope="module")
def seeded_engine():
    """Load the expensive synthetic fixture once; each mutation rolls back."""

    engine = create_engine(DATABASE_URL)
    load_demo_data(engine)
    return engine


def test_exact_series_rule_selects_entitled_observation(seeded_engine) -> None:
    engine = seeded_engine
    with engine.connect() as connection:
        valuation_date = connection.scalar(
            select(m.valuation_policy.c.valid_from).where(
                m.valuation_policy.c.valuation_policy_id == DEMO_IDS["valuation_policy"]
            )
        )
        result = resolve_market_data(connection, _request(valuation_date))

    assert result.status == "SELECTED"
    assert result.policy_rule_id == DEMO_IDS["valuation_policy_rule"]
    assert result.market_data_observation_id == DEMO_IDS["market_data_observation"]
    assert result.entitlement_decision == "ALLOWED"


def test_unentitled_dataset_is_never_selected(seeded_engine) -> None:
    engine = seeded_engine
    with engine.connect() as connection:
        valuation_date = connection.scalar(
            select(m.valuation_policy.c.valid_from).where(
                m.valuation_policy.c.valuation_policy_id == DEMO_IDS["valuation_policy"]
            )
        )
        transaction = connection.begin_nested()
        try:
            connection.execute(
                update(m.tenant_dataset_entitlement)
                .where(m.tenant_dataset_entitlement.c.tenant_id == DEMO_IDS["tenant"])
                .values(status="SUSPENDED")
            )
            result = resolve_market_data(connection, _request(valuation_date))
            assert result.status == "DENIED"
            assert result.selection_reason == "ENTITLEMENT_DENIED"
            assert result.exception_code == "NO_VALID_ENTITLEMENT"
        finally:
            transaction.rollback()


def test_policy_valuation_cut_must_match_request(seeded_engine) -> None:
    """Allowing a policy to select against another cut changes replay meaning."""

    engine = seeded_engine
    with engine.connect() as connection:
        valuation_date = connection.scalar(
            select(m.valuation_policy.c.valid_from).where(
                m.valuation_policy.c.valuation_policy_id == DEMO_IDS["valuation_policy"]
            )
        )
        request = ResolutionRequest(
            **{
                **_request(valuation_date).__dict__,
                "valuation_cut_id": DEMO_IDS["uk_fx_cut"],
            }
        )
        with pytest.raises(ValuationPolicyScopeError):
            resolve_market_data(connection, request)


def test_late_source_publication_is_ineligible(seeded_engine) -> None:
    """A vendor mark published after the cut cannot enter a historic replay."""

    engine = seeded_engine
    with engine.connect() as connection:
        valuation_date = connection.scalar(
            select(m.valuation_policy.c.valid_from).where(
                m.valuation_policy.c.valuation_policy_id == DEMO_IDS["valuation_policy"]
            )
        )
        transaction = connection.begin_nested()
        try:
            request = _request(valuation_date)
            connection.execute(
                update(m.market_data_observation)
                .where(m.market_data_observation.c.market_data_observation_id == DEMO_IDS["market_data_observation"])
                .values(source_published_at_utc=request.market_data_as_of_utc.replace(year=request.market_data_as_of_utc.year + 1))
            )
            result = resolve_market_data(connection, request)
            assert result.status == "MISSING"
            assert result.exception_code == "NO_ELIGIBLE_OBSERVATION"
        finally:
            transaction.rollback()


def test_late_source_vintage_is_ineligible(seeded_engine) -> None:
    """A linked vintage must itself have been published and received by the cut."""

    engine = seeded_engine
    with engine.connect() as connection:
        valuation_date = connection.scalar(
            select(m.valuation_policy.c.valid_from).where(
                m.valuation_policy.c.valuation_policy_id == DEMO_IDS["valuation_policy"]
            )
        )
        transaction = connection.begin_nested()
        try:
            request = _request(valuation_date)
            original_dataset_id = connection.scalar(
                select(m.market_data_observation.c.dataset_id).where(
                    m.market_data_observation.c.market_data_observation_id
                    == DEMO_IDS["market_data_observation"]
                )
            )
            original_vintage = connection.execute(
                select(m.market_data_vintage)
                .where(m.market_data_vintage.c.dataset_id == original_dataset_id)
                .limit(1)
            ).mappings().one()
            late_vintage_id = uuid4()
            connection.execute(
                insert(m.market_data_vintage).values(
                    market_data_vintage_id=late_vintage_id,
                    dataset_id=original_vintage["dataset_id"],
                    data_provider_id=original_vintage["data_provider_id"],
                    source_vintage_key=f"TEST_LATE_VINTAGE:{late_vintage_id}",
                    source_published_at_utc=request.market_data_as_of_utc + timedelta(seconds=1),
                    received_at_utc=request.market_data_as_of_utc + timedelta(seconds=2),
                    value_basis="RAW",
                    vintage_status="CURRENT",
                )
            )
            connection.execute(
                update(m.market_data_observation)
                .where(
                    m.market_data_observation.c.market_data_series_id
                    == DEMO_IDS["market_data_series"]
                )
                .values(market_data_vintage_id=late_vintage_id)
            )
            result = resolve_market_data(connection, request)
            assert result.status == "MISSING"
            assert result.exception_code == "NO_ELIGIBLE_OBSERVATION"
        finally:
            transaction.rollback()


def test_correction_received_after_cut_does_not_rewrite_historic_replay(seeded_engine) -> None:
    """An accepted correction is only superseding after it was knowable."""

    engine = seeded_engine
    with engine.connect() as connection:
        valuation_date = connection.scalar(
            select(m.valuation_policy.c.valid_from).where(
                m.valuation_policy.c.valuation_policy_id == DEMO_IDS["valuation_policy"]
            )
        )
        transaction = connection.begin_nested()
        try:
            request = _request(valuation_date)
            original = connection.execute(
                select(m.market_data_observation).where(
                    m.market_data_observation.c.market_data_observation_id
                    == DEMO_IDS["market_data_observation"]
                )
            ).mappings().one()
            connection.execute(
                insert(m.market_data_observation).values(
                    market_data_observation_id=uuid4(),
                    market_data_series_id=original["market_data_series_id"],
                    dataset_id=original["dataset_id"],
                    market_data_vintage_id=None,
                    acquisition_licence_id=original["acquisition_licence_id"],
                    market_date=original["market_date"],
                    valuation_cut_id=original["valuation_cut_id"],
                    observed_at_utc=original["observed_at_utc"],
                    received_at_utc=request.market_data_as_of_utc + timedelta(seconds=1),
                    source_published_at_utc=request.market_data_as_of_utc + timedelta(seconds=1),
                    value=original["value"],
                    value_basis=original["value_basis"],
                    quality_status="ACCEPTED",
                    supersedes_observation_id=original["market_data_observation_id"],
                )
            )
            result = resolve_market_data(connection, request)
            assert result.status == "SELECTED"
            assert result.market_data_observation_id == DEMO_IDS["market_data_observation"]
        finally:
            transaction.rollback()


def test_t_minus_one_fund_nav_uses_previous_business_day_observation(seeded_engine) -> None:
    engine = seeded_engine
    with engine.connect() as connection:
        request = ResolutionRequest(
            tenant_id=DEMO_IDS["tenant"],
            subject_reference_node_id=DEMO_IDS["demo_share_class_instrument_node"],
            valuation_policy_id=DEMO_IDS["valuation_policy"],
            valuation_date=datetime(2026, 8, 28, tzinfo=timezone.utc).date(),
            valuation_cut_id=DEMO_IDS["valuation_cut"],
            market_data_as_of_utc=datetime(2026, 8, 28, 16, 30, tzinfo=timezone.utc),
            use_purpose="VALUATION",
        )
        result = resolve_market_data(connection, request)

    assert result.status == "SELECTED"
    assert result.policy_rule_id == DEMO_IDS["demo_fund_nav_policy_rule"]
    assert result.market_data_observation_id == DEMO_IDS["demo_fund_nav_observation"]
    assert result.pricing_date_requested.isoformat() == "2026-08-27"
    assert result.pricing_date_used.isoformat() == "2026-08-27"


def test_resolution_snapshot_freezes_selected_observation_and_policy_rule(seeded_engine) -> None:
    engine = seeded_engine
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            valuation_date = connection.scalar(
                select(m.valuation_policy.c.valid_from).where(
                    m.valuation_policy.c.valuation_policy_id == DEMO_IDS["valuation_policy"]
                )
            )
            request = _request(valuation_date)
            result = resolve_market_data(connection, request)
            snapshot_id = persist_resolution_snapshot(connection, request, (result,))
            item = connection.execute(
                select(
                    m.market_data_resolution_snapshot_item.c.market_data_observation_id,
                    m.market_data_resolution_snapshot_item.c.policy_rule_id,
                    m.market_data_resolution_snapshot_item.c.market_data_vintage_id,
                    m.market_data_resolution_snapshot_item.c.acquisition_licence_id,
                    m.market_data_resolution_snapshot_item.c.source_published_at_utc,
                    m.market_data_resolution_snapshot_item.c.received_at_utc,
                ).where(
                    m.market_data_resolution_snapshot_item.c.market_data_resolution_snapshot_id
                    == snapshot_id
                )
            ).one()
            assert item.market_data_observation_id == DEMO_IDS["market_data_observation"]
            assert item.policy_rule_id == DEMO_IDS["valuation_policy_rule"]
            assert item.market_data_vintage_id == result.market_data_vintage_id
            assert item.acquisition_licence_id == result.acquisition_licence_id
            assert item.source_published_at_utc == result.source_published_at_utc
            assert item.received_at_utc == result.received_at_utc
            use_purpose = connection.scalar(
                select(m.market_data_resolution_snapshot.c.use_purpose).where(
                    m.market_data_resolution_snapshot.c.market_data_resolution_snapshot_id == snapshot_id
                )
            )
            assert use_purpose == "VALUATION"
        finally:
            transaction.rollback()


def test_batch_resolution_preserves_subject_order(seeded_engine) -> None:
    engine = seeded_engine
    with engine.connect() as connection:
        valuation_date = connection.scalar(
            select(m.valuation_policy.c.valid_from).where(
                m.valuation_policy.c.valuation_policy_id == DEMO_IDS["valuation_policy"]
            )
        )
        request = _request(valuation_date)
        subjects = (DEMO_IDS["hsbc_xlon_listing_node"], DEMO_IDS["demo_share_class_instrument_node"])
        results = resolve_market_data_batch(connection, request, subjects)

    assert tuple(result.subject_reference_node_id for result in results) == subjects
    assert all(result.status == "SELECTED" for result in results)


def test_batch_resolution_rejects_duplicate_subjects(seeded_engine) -> None:
    engine = seeded_engine
    with engine.connect() as connection:
        valuation_date = connection.scalar(
            select(m.valuation_policy.c.valid_from).where(
                m.valuation_policy.c.valuation_policy_id == DEMO_IDS["valuation_policy"]
            )
        )
        request = _request(valuation_date)
        with pytest.raises(ValueError, match="distinct"):
            resolve_market_data_batch(
                connection,
                request,
                (DEMO_IDS["hsbc_xlon_listing_node"], DEMO_IDS["hsbc_xlon_listing_node"]),
            )


def test_existing_resolution_snapshot_cannot_be_mutated(seeded_engine) -> None:
    engine = seeded_engine
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            with pytest.raises(DBAPIError):
                connection.execute(
                    update(m.market_data_resolution_snapshot)
                    .where(
                        m.market_data_resolution_snapshot.c.market_data_resolution_snapshot_id
                        == DEMO_IDS["resolution_snapshot"]
                    )
                    .values(status="SUPERSEDED")
                )
        finally:
            transaction.rollback()
