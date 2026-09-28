"""Behavioural validation tests for vanilla option terms."""

from dataclasses import replace
from decimal import Decimal
from uuid import UUID

import pytest

from security_master_schema.option_validation import (
    OptionTermsDraft,
    OptionTermsValidationError,
    validate_option_terms,
)


UNDERLYING_ID = UUID("00000000-0000-7000-8000-000000000301")
GBP_ID = UUID("00000000-0000-7000-8000-000000000302")
EXERCISE_SCHEDULE_ID = UUID("00000000-0000-7000-8000-000000000303")
STRIKE_RESET_SCHEDULE_ID = UUID("00000000-0000-7000-8000-000000000304")


def _valid_equity_call() -> OptionTermsDraft:
    return OptionTermsDraft(
        underlying_reference_node_id=UNDERLYING_ID,
        option_type="CALL",
        exercise_style="EUROPEAN",
        strike_value=Decimal("8.50"),
        strike_basis="ABSOLUTE",
        strike_currency_id=GBP_ID,
        settlement_method="PHYSICAL",
        settlement_currency_id=None,
        exercise_schedule_id=None,
    )


def test_valid_european_physical_call_is_accepted() -> None:
    """Catches regressions that reject the ordinary listed-equity option shape."""

    draft = _valid_equity_call()

    assert validate_option_terms(draft) == draft


def test_cash_settled_option_requires_a_settlement_currency() -> None:
    """Catches a cash option whose payoff currency is not identifiable."""

    draft = replace(_valid_equity_call(), settlement_method="CASH")

    with pytest.raises(OptionTermsValidationError, match="settlement currency"):
        validate_option_terms(draft)


def test_bermudan_option_requires_an_exercise_schedule() -> None:
    """Catches a Bermudan option without its permitted exercise dates."""

    draft = replace(_valid_equity_call(), exercise_style="BERMUDAN")

    with pytest.raises(OptionTermsValidationError, match="exercise schedule"):
        validate_option_terms(draft)


def test_index_point_strike_does_not_require_a_currency() -> None:
    """Catches an incorrect assumption that every index strike is monetary."""

    draft = replace(
        _valid_equity_call(),
        option_type="PUT",
        strike_value=Decimal("5000"),
        strike_basis="INDEX_POINTS",
        strike_currency_id=None,
        settlement_method="CASH",
        settlement_currency_id=GBP_ID,
    )

    assert validate_option_terms(draft) == draft


@pytest.mark.parametrize("option_type", ["DIGITAL", "FORWARD", ""])
def test_vanilla_terms_reject_non_vanilla_option_types(option_type: str) -> None:
    """Catches digital and non-option values entering the first vanilla slice."""

    draft = replace(_valid_equity_call(), option_type=option_type)

    with pytest.raises(OptionTermsValidationError, match="CALL or PUT"):
        validate_option_terms(draft)


def test_bermudan_option_with_schedule_is_accepted() -> None:
    """Catches regressions that make valid scheduled exercise impossible."""

    draft = replace(_valid_equity_call(), exercise_style="BERMUDAN", exercise_schedule_id=EXERCISE_SCHEDULE_ID)

    assert validate_option_terms(draft) == draft


def test_reset_option_can_defer_its_strike_to_a_contractual_schedule() -> None:
    """A scheduled reset option is valid without pretending its future strike is current."""

    draft = replace(
        _valid_equity_call(),
        strike_value=None,
        strike_mode="RESET",
        strike_reset_schedule_id=STRIKE_RESET_SCHEDULE_ID,
    )

    assert validate_option_terms(draft) == draft


def test_dynamic_strike_requires_a_reset_schedule() -> None:
    """Dynamic options need a contractual determination schedule."""

    draft = replace(_valid_equity_call(), strike_value=None, strike_mode="FORWARD_START")

    with pytest.raises(OptionTermsValidationError, match="reset schedule"):
        validate_option_terms(draft)


def test_fixed_strike_requires_a_strike_value() -> None:
    """A fixed option cannot silently use a missing strike."""

    draft = replace(_valid_equity_call(), strike_value=None)

    with pytest.raises(OptionTermsValidationError, match="strike value"):
        validate_option_terms(draft)
