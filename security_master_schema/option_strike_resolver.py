"""Deterministic resolution of contractual option-strike reset schedules.

This module deliberately resolves already-normalized rules and fixings.  It
does not fetch market data, evaluate formulas, or mutate database rows.  Those
concerns belong to the market-data resolver and the approval/ingestion layer.
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Iterable, Optional
from uuid import UUID


class StrikeResolutionError(ValueError):
    """Raised when an option's applicable strike cannot be resolved safely."""


@dataclass(frozen=True)
class OptionStrikeResetRuleInput:
    """Normalized reset rule and its scheduled event for resolver input."""

    option_strike_reset_rule_id: UUID
    schedule_event_id: UUID
    event_date: date
    event_sequence: int
    determination_method: str
    fixed_strike_value: Optional[Decimal] = None
    floor_value: Optional[Decimal] = None
    cap_value: Optional[Decimal] = None


@dataclass(frozen=True)
class OptionStrikeFixingInput:
    """Immutable fixing fact supplied by the market-data/approval boundary."""

    option_strike_fixing_id: UUID
    option_strike_reset_rule_id: UUID
    fixing_date: date
    resolved_strike_value: Decimal
    status: str
    recorded_at_utc: datetime


@dataclass(frozen=True)
class ResolvedOptionStrike:
    """Strike applicable at an as-of date, including its audit source."""

    strike_value: Decimal
    source: str
    schedule_event_id: Optional[UUID] = None
    reset_rule_id: Optional[UUID] = None
    fixing_id: Optional[UUID] = None


def _positive_decimal(value: Optional[Decimal], label: str) -> Optional[Decimal]:
    if value is None:
        return None
    decimal_value = Decimal(value)
    if decimal_value <= 0:
        raise StrikeResolutionError(f"{label} must be greater than zero")
    return decimal_value


def _apply_bounds(value: Decimal, rule: OptionStrikeResetRuleInput) -> Decimal:
    floor_value = _positive_decimal(rule.floor_value, "strike floor")
    cap_value = _positive_decimal(rule.cap_value, "strike cap")
    if floor_value is not None and cap_value is not None and floor_value > cap_value:
        raise StrikeResolutionError("strike floor cannot exceed strike cap")
    if floor_value is not None:
        value = max(value, floor_value)
    if cap_value is not None:
        value = min(value, cap_value)
    return _positive_decimal(value, "resolved strike") or Decimal("0")


def resolve_option_strike(
    *,
    as_of_date: date,
    strike_mode: str,
    initial_strike_value: Optional[Decimal],
    reset_rules: Iterable[OptionStrikeResetRuleInput],
    fixings: Iterable[OptionStrikeFixingInput],
) -> ResolvedOptionStrike:
    """Return the contractual strike applicable on ``as_of_date``.

    ``FIXED`` options use their static strike.  ``RESET`` options use the
    initial strike until the latest reset event reached by the as-of date.
    ``FORWARD_START`` options require a resolved event once their first event
    has been reached.  Market-derived methods use exactly one accepted fixing;
    ambiguous or missing inputs fail closed.
    """

    normalized_mode = strike_mode.upper()
    if normalized_mode not in {"FIXED", "FORWARD_START", "RESET"}:
        raise StrikeResolutionError("strike mode must be FIXED, FORWARD_START, or RESET")

    initial_value = _positive_decimal(initial_strike_value, "initial strike")
    if normalized_mode == "FIXED":
        if initial_value is None:
            raise StrikeResolutionError("a fixed option requires an initial strike")
        return ResolvedOptionStrike(strike_value=initial_value, source="INITIAL")

    ordered_rules = sorted(
        (rule for rule in reset_rules if rule.event_date <= as_of_date),
        key=lambda rule: (rule.event_date, rule.event_sequence),
    )
    fixing_rows = tuple(fixings)
    current_value = initial_value
    source = "INITIAL"
    current_event_id: Optional[UUID] = None
    current_rule_id: Optional[UUID] = None
    current_fixing_id: Optional[UUID] = None

    for rule in ordered_rules:
        method = rule.determination_method.upper()
        if method == "FORMULA":
            raise StrikeResolutionError("FORMULA strike resets require a separately governed formula contract")

        if method == "FIXED":
            candidate = _positive_decimal(rule.fixed_strike_value, "fixed reset strike")
            if candidate is None:
                raise StrikeResolutionError("FIXED reset rule has no fixed strike")
            candidate_source = "FIXED_RESET"
            fixing_id = None
        else:
            accepted = [
                fixing
                for fixing in fixing_rows
                if fixing.option_strike_reset_rule_id == rule.option_strike_reset_rule_id
                and fixing.fixing_date == rule.event_date
                and fixing.status.upper() == "ACCEPTED"
            ]
            if len(accepted) == 0:
                raise StrikeResolutionError(
                    f"no accepted fixing exists for reset rule {rule.option_strike_reset_rule_id}"
                )
            if len(accepted) > 1:
                raise StrikeResolutionError(
                    f"multiple accepted fixings exist for reset rule {rule.option_strike_reset_rule_id}"
                )
            fixing = accepted[0]
            candidate = _positive_decimal(fixing.resolved_strike_value, "resolved strike")
            if candidate is None:  # pragma: no cover - guarded by _positive_decimal
                raise StrikeResolutionError("resolved strike is missing")
            candidate_source = "MARKET_FIXING"
            fixing_id = fixing.option_strike_fixing_id

        current_value = _apply_bounds(candidate, rule)
        source = candidate_source
        current_event_id = rule.schedule_event_id
        current_rule_id = rule.option_strike_reset_rule_id
        current_fixing_id = fixing_id

    if current_value is None:
        raise StrikeResolutionError("no applicable strike determination exists for the as-of date")

    return ResolvedOptionStrike(
        strike_value=current_value,
        source=source,
        schedule_event_id=current_event_id,
        reset_rule_id=current_rule_id,
        fixing_id=current_fixing_id,
    )
