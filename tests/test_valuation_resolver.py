"""Tests for deterministic pricing-date selection used by Soft NAV."""

from datetime import date, datetime, timezone
from uuid import UUID

from security_master_schema.valuation_resolver import (
    MissingDataAction,
    ObservationCandidate,
    PricingDateRule,
    ResolutionStatus,
    resolve_price,
)


def test_fixed_one_business_day_lag_selects_t_minus_one_fund_nav() -> None:
    result = resolve_price(
        valuation_date=date(2026, 9, 1),
        information_cutoff_utc=datetime(2026, 9, 1, 17, tzinfo=timezone.utc),
        pricing_date_rule=PricingDateRule.FIXED_LAG,
        lag_business_days=1,
        max_staleness_business_days=5,
        missing_data_action=MissingDataAction.FAIL,
        candidates=(
            ObservationCandidate(
                observation_id=UUID("00000000-0000-7000-8000-000000000101"),
                market_date=date(2026, 8, 31),
                received_at_utc=datetime(2026, 9, 1, 9, tzinfo=timezone.utc),
                value=101.25,
            ),
        ),
    )

    assert result.status is ResolutionStatus.SELECTED
    assert result.pricing_date_requested == date(2026, 8, 31)
    assert result.pricing_date_used == date(2026, 8, 31)
    assert result.staleness_business_days == 0
    assert result.selected_value == 101.25


def test_resolver_excludes_price_received_after_information_cutoff() -> None:
    result = resolve_price(
        valuation_date=date(2026, 9, 1),
        information_cutoff_utc=datetime(2026, 9, 1, 17, tzinfo=timezone.utc),
        pricing_date_rule=PricingDateRule.SAME_DAY,
        lag_business_days=0,
        max_staleness_business_days=0,
        missing_data_action=MissingDataAction.FAIL,
        candidates=(
            ObservationCandidate(
                observation_id=UUID("00000000-0000-7000-8000-000000000102"),
                market_date=date(2026, 9, 1),
                received_at_utc=datetime(2026, 9, 1, 18, tzinfo=timezone.utc),
                value=99.0,
            ),
        ),
    )

    assert result.status is ResolutionStatus.MISSING
    assert result.selected_observation_id is None
    assert result.exception_code == "NO_ELIGIBLE_OBSERVATION"
