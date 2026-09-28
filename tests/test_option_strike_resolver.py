"""Behavioural tests for scheduled option-strike resolution."""

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

import pytest

from security_master_schema.option_strike_resolver import (
    OptionStrikeFixingInput,
    OptionStrikeResetRuleInput,
    StrikeResolutionError,
    resolve_option_strike,
)


RULE_ONE = UUID("00000000-0000-7000-8000-000000000401")
RULE_TWO = UUID("00000000-0000-7000-8000-000000000402")
EVENT_ONE = UUID("00000000-0000-7000-8000-000000000411")
EVENT_TWO = UUID("00000000-0000-7000-8000-000000000412")
FIXING_ONE = UUID("00000000-0000-7000-8000-000000000421")


def _rule(
    rule_id: UUID,
    event_id: UUID,
    event_date: date,
    event_sequence: int,
    method: str,
    *,
    fixed_value: Decimal | None = None,
    floor_value: Decimal | None = None,
    cap_value: Decimal | None = None,
) -> OptionStrikeResetRuleInput:
    return OptionStrikeResetRuleInput(
        option_strike_reset_rule_id=rule_id,
        schedule_event_id=event_id,
        event_date=event_date,
        event_sequence=event_sequence,
        determination_method=method,
        fixed_strike_value=fixed_value,
        floor_value=floor_value,
        cap_value=cap_value,
    )


def test_fixed_option_returns_its_static_strike() -> None:
    resolved = resolve_option_strike(
        as_of_date=date(2027, 1, 1),
        strike_mode="FIXED",
        initial_strike_value=Decimal("100"),
        reset_rules=(),
        fixings=(),
    )

    assert resolved.strike_value == Decimal("100")
    assert resolved.source == "INITIAL"


def test_reset_option_uses_initial_strike_until_first_reset() -> None:
    resolved = resolve_option_strike(
        as_of_date=date(2027, 1, 1),
        strike_mode="RESET",
        initial_strike_value=Decimal("100"),
        reset_rules=(
            _rule(RULE_ONE, EVENT_ONE, date(2027, 2, 1), 1, "FIXED", fixed_value=Decimal("105")),
        ),
        fixings=(),
    )

    assert resolved.strike_value == Decimal("100")
    assert resolved.source == "INITIAL"


def test_fixed_reset_is_selected_by_event_date_and_sequence() -> None:
    resolved = resolve_option_strike(
        as_of_date=date(2027, 3, 1),
        strike_mode="RESET",
        initial_strike_value=Decimal("100"),
        reset_rules=(
            _rule(RULE_ONE, EVENT_ONE, date(2027, 2, 1), 1, "FIXED", fixed_value=Decimal("105")),
            _rule(RULE_TWO, EVENT_TWO, date(2027, 3, 1), 2, "FIXED", fixed_value=Decimal("110")),
        ),
        fixings=(),
    )

    assert resolved.strike_value == Decimal("110")
    assert resolved.schedule_event_id == EVENT_TWO
    assert resolved.source == "FIXED_RESET"


def test_market_derived_reset_uses_the_accepted_fixing_and_bounds() -> None:
    resolved = resolve_option_strike(
        as_of_date=date(2027, 2, 1),
        strike_mode="FORWARD_START",
        initial_strike_value=None,
        reset_rules=(
            _rule(RULE_ONE, EVENT_ONE, date(2027, 2, 1), 1, "SPOT_AT_RESET", floor_value=Decimal("95"), cap_value=Decimal("105")),
        ),
        fixings=(
            OptionStrikeFixingInput(
                option_strike_fixing_id=FIXING_ONE,
                option_strike_reset_rule_id=RULE_ONE,
                fixing_date=date(2027, 2, 1),
                resolved_strike_value=Decimal("110"),
                status="SUPERSEDED",
                recorded_at_utc=datetime(2027, 2, 1, 12, tzinfo=timezone.utc),
            ),
            OptionStrikeFixingInput(
                option_strike_fixing_id=UUID("00000000-0000-7000-8000-000000000422"),
                option_strike_reset_rule_id=RULE_ONE,
                fixing_date=date(2027, 2, 1),
                resolved_strike_value=Decimal("103"),
                status="ACCEPTED",
                recorded_at_utc=datetime(2027, 2, 1, 13, tzinfo=timezone.utc),
            ),
        ),
    )

    assert resolved.strike_value == Decimal("103")
    assert resolved.fixing_id == UUID("00000000-0000-7000-8000-000000000422")
    assert resolved.source == "MARKET_FIXING"


def test_dynamic_option_without_applicable_fixing_fails_closed() -> None:
    with pytest.raises(StrikeResolutionError, match="no accepted fixing"):
        resolve_option_strike(
            as_of_date=date(2027, 2, 1),
            strike_mode="FORWARD_START",
            initial_strike_value=None,
            reset_rules=(
                _rule(RULE_ONE, EVENT_ONE, date(2027, 2, 1), 1, "SPOT_AT_RESET"),
            ),
            fixings=(),
        )


def test_formula_reset_is_deferred_until_a_formula_contract_exists() -> None:
    with pytest.raises(StrikeResolutionError, match="FORMULA"):
        resolve_option_strike(
            as_of_date=date(2027, 2, 1),
            strike_mode="RESET",
            initial_strike_value=Decimal("100"),
            reset_rules=(
                _rule(RULE_ONE, EVENT_ONE, date(2027, 2, 1), 1, "FORMULA"),
            ),
            fixings=(),
        )
