"""Cutoff-specific synthetic market-data scenarios."""

from datetime import datetime, timezone

import os
from sqlalchemy import create_engine, select, text

from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS, load_demo_data
from security_master_schema.market_data_resolver import ResolutionRequest, resolve_market_data


DATABASE_URL = os.environ["DATABASE_URL"]


def _request(*, policy_id, cut_id, as_of_utc):
    return ResolutionRequest(
        tenant_id=DEMO_IDS["tenant"],
        subject_reference_node_id=DEMO_IDS["gbpusd_fx_pair_node"],
        valuation_policy_id=policy_id,
        valuation_date=datetime(2026, 8, 28, tzinfo=timezone.utc).date(),
        valuation_cut_id=cut_id,
        market_data_as_of_utc=as_of_utc,
        use_purpose="VALUATION",
    )


def test_cutoff_fixture_registers_london_and_new_york_fund_contexts() -> None:
    engine = create_engine(DATABASE_URL)
    load_demo_data(engine)

    with engine.connect() as connection:
        cuts = connection.execute(
            select(m.valuation_cut.c.cut_code, m.valuation_cut.c.timezone_name, m.valuation_cut.c.local_time)
            .where(m.valuation_cut.c.valuation_cut_id.in_((DEMO_IDS["uk_fx_cut"], DEMO_IDS["us_fx_cut"])))
        ).mappings().all()
        policies = connection.execute(
            select(m.valuation_policy.c.valuation_policy_id, m.valuation_policy.c.valuation_cut_id)
            .where(m.valuation_policy.c.valuation_policy_id.in_((DEMO_IDS["uk_fund_policy"], DEMO_IDS["us_fund_policy"])))
        ).mappings().all()

    assert {(row["timezone_name"], row["local_time"]) for row in cuts} == {
        ("Europe/London", "16:00:00"),
        ("America/New_York", "16:00:00"),
    }
    assert {row["valuation_cut_id"] for row in policies} == {
        DEMO_IDS["uk_fx_cut"],
        DEMO_IDS["us_fx_cut"],
    }


def test_london_and_new_york_cutoffs_select_different_fx_observations() -> None:
    engine = create_engine(DATABASE_URL)
    load_demo_data(engine)

    with engine.connect() as connection:
        uk_before_cut = resolve_market_data(
            connection,
            _request(
                policy_id=DEMO_IDS["uk_fund_policy"],
                cut_id=DEMO_IDS["uk_fx_cut"],
                as_of_utc=datetime(2026, 8, 28, 15, 0, tzinfo=timezone.utc),
            ),
        )
        uk_after_cut = resolve_market_data(
            connection,
            _request(
                policy_id=DEMO_IDS["uk_fund_policy"],
                cut_id=DEMO_IDS["uk_fx_cut"],
                as_of_utc=datetime(2026, 8, 28, 15, 10, tzinfo=timezone.utc),
            ),
        )
        us_before_cut = resolve_market_data(
            connection,
            _request(
                policy_id=DEMO_IDS["us_fund_policy"],
                cut_id=DEMO_IDS["us_fx_cut"],
                as_of_utc=datetime(2026, 8, 28, 20, 0, tzinfo=timezone.utc),
            ),
        )
        us_after_cut = resolve_market_data(
            connection,
            _request(
                policy_id=DEMO_IDS["us_fund_policy"],
                cut_id=DEMO_IDS["us_fx_cut"],
                as_of_utc=datetime(2026, 8, 28, 20, 10, tzinfo=timezone.utc),
            ),
        )

    assert uk_before_cut.market_data_observation_id == DEMO_IDS["uk_fx_observation_before_cut"]
    assert uk_after_cut.market_data_observation_id == DEMO_IDS["uk_fx_observation_after_cut"]
    assert us_before_cut.market_data_observation_id == DEMO_IDS["us_fx_observation_before_cut"]
    assert us_after_cut.market_data_observation_id == DEMO_IDS["us_fx_observation_after_cut"]


def test_listing_and_bond_series_have_multiple_market_dates() -> None:
    engine = create_engine(DATABASE_URL)
    load_demo_data(engine)

    with engine.connect() as connection:
        rows = connection.execute(
            text(
                """
                SELECT s.market_data_series_id, count(DISTINCT o.market_date) AS market_dates
                FROM md.market_data_series s
                JOIN md.market_data_observation o
                  ON o.market_data_series_id = s.market_data_series_id
                WHERE s.market_data_series_id IN (:listing_series, :bond_series)
                GROUP BY s.market_data_series_id
                """
            ),
            {"listing_series": DEMO_IDS["market_data_series"], "bond_series": DEMO_IDS["bond_series"]},
        ).mappings().all()

    assert {row["market_data_series_id"] for row in rows} == {
        DEMO_IDS["market_data_series"],
        DEMO_IDS["bond_series"],
    }
    assert all(row["market_dates"] >= 3 for row in rows)
