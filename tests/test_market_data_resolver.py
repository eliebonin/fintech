"""Database-backed valuation selection tests."""

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, select, update
from sqlalchemy.exc import DBAPIError

from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS, load_demo_data
from security_master_schema.market_data_resolver import (
    ResolutionRequest,
    persist_resolution_snapshot,
    resolve_market_data,
)


DATABASE_URL = "postgresql+psycopg://fortem:fortem_local_only@localhost:54329/fortem_secm"


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


def test_exact_series_rule_selects_entitled_observation() -> None:
    engine = create_engine(DATABASE_URL)
    load_demo_data(engine)
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


def test_unentitled_dataset_is_never_selected() -> None:
    engine = create_engine(DATABASE_URL)
    load_demo_data(engine)
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
                .where(m.tenant_dataset_entitlement.c.dataset_id == DEMO_IDS["dataset"])
                .values(status="SUSPENDED")
            )
            result = resolve_market_data(connection, _request(valuation_date))
            assert result.status == "MISSING"
            assert result.exception_code == "NO_ENTITLED_OBSERVATION"
        finally:
            transaction.rollback()


def test_t_minus_one_fund_nav_uses_previous_business_day_observation() -> None:
    engine = create_engine(DATABASE_URL)
    load_demo_data(engine)
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


def test_resolution_snapshot_freezes_selected_observation_and_policy_rule() -> None:
    engine = create_engine(DATABASE_URL)
    load_demo_data(engine)
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
                ).where(
                    m.market_data_resolution_snapshot_item.c.market_data_resolution_snapshot_id
                    == snapshot_id
                )
            ).one()
            assert item.market_data_observation_id == DEMO_IDS["market_data_observation"]
            assert item.policy_rule_id == DEMO_IDS["valuation_policy_rule"]
        finally:
            transaction.rollback()


def test_existing_resolution_snapshot_cannot_be_mutated() -> None:
    engine = create_engine(DATABASE_URL)
    load_demo_data(engine)
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
