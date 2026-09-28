"""Behavioural validation tests for the initial total-return swap slice."""

from dataclasses import replace
from uuid import UUID

import pytest

from security_master_schema.swap_validation import (
    SwapLegDraft,
    SwapLegValidationError,
    validate_swap_leg,
)


REFERENCE_NODE_ID = UUID("00000000-0000-7000-8000-000000000201")
RETURN_PROFILE_ID = UUID("00000000-0000-7000-8000-000000000202")
GBP_CURRENCY_ID = UUID("00000000-0000-7000-8000-000000000203")


def test_performance_leg_requires_a_reference_and_return_profile() -> None:
    """Catches a performance leg that cannot identify the return being exchanged."""

    draft = SwapLegDraft(
        leg_role="PERFORMANCE",
        pay_receive="RECEIVE",
        reference_node_id=REFERENCE_NODE_ID,
        return_profile_id=None,
        currency_id=None,
    )

    with pytest.raises(SwapLegValidationError, match="return profile"):
        validate_swap_leg(draft)


def test_funding_leg_requires_reference_and_currency() -> None:
    """Catches a funding leg without a rate reference or payment currency."""

    draft = SwapLegDraft(
        leg_role="FUNDING",
        pay_receive="PAY",
        reference_node_id=REFERENCE_NODE_ID,
        return_profile_id=None,
        currency_id=None,
    )

    with pytest.raises(SwapLegValidationError, match="currency"):
        validate_swap_leg(draft)


def test_valid_total_return_swap_legs_are_accepted() -> None:
    """Catches regressions that reject the standard performance/funding pair."""

    performance = SwapLegDraft(
        leg_role="PERFORMANCE",
        pay_receive="RECEIVE",
        reference_node_id=REFERENCE_NODE_ID,
        return_profile_id=RETURN_PROFILE_ID,
        currency_id=None,
    )
    funding = replace(
        performance,
        leg_role="FUNDING",
        pay_receive="PAY",
        return_profile_id=None,
        currency_id=GBP_CURRENCY_ID,
    )

    assert validate_swap_leg(performance) == performance
    assert validate_swap_leg(funding) == funding


@pytest.mark.parametrize("pay_receive", ["", "HOLD", "BUY"])
def test_swap_leg_rejects_unknown_direction(pay_receive: str) -> None:
    """Catches a leg direction outside the holder-perspective PAY/RECEIVE contract."""

    draft = SwapLegDraft(
        leg_role="FUNDING",
        pay_receive=pay_receive,
        reference_node_id=REFERENCE_NODE_ID,
        return_profile_id=None,
        currency_id=GBP_CURRENCY_ID,
    )

    with pytest.raises(SwapLegValidationError, match="PAY or RECEIVE"):
        validate_swap_leg(draft)


def test_swap_leg_rejects_unknown_role() -> None:
    """Catches a persisted leg role outside the governed first-slice vocabulary."""

    draft = SwapLegDraft(
        leg_role="COLLATERAL",
        pay_receive="PAY",
        reference_node_id=REFERENCE_NODE_ID,
        return_profile_id=None,
        currency_id=GBP_CURRENCY_ID,
    )

    with pytest.raises(SwapLegValidationError, match="unsupported"):
        validate_swap_leg(draft)
