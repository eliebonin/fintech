"""Small deterministic pricing-date resolver used by the Soft-NAV boundary.

The production data-access layer supplies entitled candidates.  This module makes
the date, information-cut and staleness decision explicit and independently testable.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import StrEnum
from uuid import UUID


class PricingDateRule(StrEnum):
    """Controlled ways to derive an eligible market date from a valuation date."""

    SAME_DAY = "SAME_DAY"
    PRIOR_AVAILABLE = "PRIOR_AVAILABLE"
    FIXED_LAG = "FIXED_LAG"


class MissingDataAction(StrEnum):
    """Policy outcome when no eligible price can be selected."""

    FAIL = "FAIL"
    WARN = "WARN"
    MANUAL_OVERRIDE = "MANUAL_OVERRIDE"


class ResolutionStatus(StrEnum):
    """Resolver result status persisted by its caller in the audit snapshot."""

    SELECTED = "SELECTED"
    MISSING = "MISSING"
    STALE = "STALE"
    NEEDS_OVERRIDE = "NEEDS_OVERRIDE"


@dataclass(frozen=True)
class ObservationCandidate:
    """An already-entitled immutable candidate observation."""

    observation_id: UUID
    market_date: date
    received_at_utc: datetime
    value: float


@dataclass(frozen=True)
class PriceResolution:
    """Complete selection evidence required by a frozen valuation snapshot."""

    status: ResolutionStatus
    pricing_date_requested: date
    pricing_date_used: date | None
    staleness_business_days: int | None
    selected_observation_id: UUID | None
    selected_value: float | None
    exception_code: str | None


def _subtract_weekdays(start_date: date, days: int) -> date:
    """Subtract weekdays; callers may later replace this with a market-calendar service."""

    result = start_date
    remaining = days
    while remaining:
        result -= timedelta(days=1)
        if result.weekday() < 5:
            remaining -= 1
    return result


def _weekday_distance(start_date: date, end_date: date) -> int:
    """Return weekday count from ``start_date`` through ``end_date`` in chronological order."""

    distance = 0
    current_date = start_date
    while current_date < end_date:
        current_date += timedelta(days=1)
        if current_date.weekday() < 5:
            distance += 1
    return distance


def resolve_price(
    *,
    valuation_date: date,
    information_cutoff_utc: datetime,
    pricing_date_rule: PricingDateRule,
    lag_business_days: int,
    max_staleness_business_days: int | None,
    missing_data_action: MissingDataAction,
    candidates: tuple[ObservationCandidate, ...],
) -> PriceResolution:
    """Resolve one value without looking beyond the stated historic information cut.

    ``SAME_DAY`` accepts only the requested market date. ``PRIOR_AVAILABLE``
    accepts the latest observation on or before the valuation date. ``FIXED_LAG``
    first moves the requested date back by the stated number of weekdays, then
    accepts the latest observation on or before that date.
    """

    if information_cutoff_utc.tzinfo is None:
        raise ValueError("information_cutoff_utc must be timezone-aware")
    if lag_business_days < 0:
        raise ValueError("lag_business_days cannot be negative")
    if max_staleness_business_days is not None and max_staleness_business_days < 0:
        raise ValueError("max_staleness_business_days cannot be negative")

    requested_date = (
        _subtract_weekdays(valuation_date, lag_business_days)
        if pricing_date_rule is PricingDateRule.FIXED_LAG
        else valuation_date
    )
    eligible = [candidate for candidate in candidates if candidate.received_at_utc <= information_cutoff_utc]
    if pricing_date_rule is PricingDateRule.SAME_DAY:
        eligible = [candidate for candidate in eligible if candidate.market_date == requested_date]
    else:
        eligible = [candidate for candidate in eligible if candidate.market_date <= requested_date]

    if not eligible:
        status = ResolutionStatus.NEEDS_OVERRIDE if missing_data_action is MissingDataAction.MANUAL_OVERRIDE else ResolutionStatus.MISSING
        return PriceResolution(status, requested_date, None, None, None, None, "NO_ELIGIBLE_OBSERVATION")

    selected = max(eligible, key=lambda candidate: (candidate.market_date, candidate.received_at_utc, str(candidate.observation_id)))
    staleness = _weekday_distance(selected.market_date, requested_date)
    if max_staleness_business_days is not None and staleness > max_staleness_business_days:
        status = ResolutionStatus.NEEDS_OVERRIDE if missing_data_action is MissingDataAction.MANUAL_OVERRIDE else ResolutionStatus.STALE
        return PriceResolution(status, requested_date, selected.market_date, staleness, selected.observation_id, selected.value, "MAX_STALENESS_EXCEEDED")

    return PriceResolution(ResolutionStatus.SELECTED, requested_date, selected.market_date, staleness, selected.observation_id, selected.value, None)
