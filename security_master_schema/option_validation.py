"""Validation for the first, deliberately small vanilla-option contract slice.

The database keeps source/staging rows permissive enough to support incomplete
provider payloads.  This module is the stricter gate used before a row is
promoted to a validated canonical option instrument.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional
from uuid import UUID


class OptionTermsValidationError(ValueError):
    """Raised when a vanilla option draft is not contractually identifiable."""


@dataclass(frozen=True)
class OptionTermsDraft:
    """Provider/UI-neutral input for a vanilla option's economic terms."""

    underlying_reference_node_id: UUID
    option_type: str
    exercise_style: str
    strike_value: Optional[Decimal]
    strike_basis: str
    strike_currency_id: Optional[UUID]
    settlement_method: str
    settlement_currency_id: Optional[UUID]
    exercise_schedule_id: Optional[UUID]
    strike_mode: str = "FIXED"
    strike_reset_schedule_id: Optional[UUID] = None


_OPTION_TYPES = {"CALL", "PUT"}
_EXERCISE_STYLES = {"EUROPEAN", "AMERICAN", "BERMUDAN"}
_SETTLEMENT_METHODS = {"CASH", "PHYSICAL", "ELECTION", "CASH_OR_PHYSICAL"}
_STRIKE_BASES = {"ABSOLUTE", "INDEX_POINTS", "FX_RATE", "PERCENT_OF_SPOT"}
_STRIKE_MODES = {"FIXED", "FORWARD_START", "RESET"}


def validate_option_terms(draft: OptionTermsDraft) -> OptionTermsDraft:
    """Validate and return ``draft`` unchanged when it is a vanilla option.

    ``BERMUDAN`` is the internal spelling; the standards mapping is FpML's
    ``Bermuda``.  This function intentionally does not validate premium amount
    or option entitlement: those are trade/contract-unit concerns rather than
    the shared option terms row.
    """

    if draft.underlying_reference_node_id is None:
        raise OptionTermsValidationError("an underlying reference is required")

    if draft.option_type.upper() not in _OPTION_TYPES:
        raise OptionTermsValidationError("option type must be CALL or PUT")
    if draft.exercise_style.upper() not in _EXERCISE_STYLES:
        raise OptionTermsValidationError("exercise style must be EUROPEAN, AMERICAN, or BERMUDAN")
    if draft.settlement_method.upper() not in _SETTLEMENT_METHODS:
        raise OptionTermsValidationError(
            "settlement method must be CASH, PHYSICAL, ELECTION, or CASH_OR_PHYSICAL"
        )
    if draft.strike_basis.upper() not in _STRIKE_BASES:
        raise OptionTermsValidationError(
            "strike basis must be ABSOLUTE, INDEX_POINTS, FX_RATE, or PERCENT_OF_SPOT"
        )
    strike_mode = draft.strike_mode.upper()
    if strike_mode not in _STRIKE_MODES:
        raise OptionTermsValidationError("strike mode must be FIXED, FORWARD_START, or RESET")

    if strike_mode == "FIXED":
        if draft.strike_value is None:
            raise OptionTermsValidationError("strike value is required for a fixed-strike option")
        if draft.strike_value <= 0:
            raise OptionTermsValidationError("strike value must be greater than zero")
    elif draft.strike_reset_schedule_id is None:
        raise OptionTermsValidationError("a reset schedule is required for a dynamic-strike option")

    if draft.strike_value is not None and draft.strike_value <= 0:
        raise OptionTermsValidationError("strike value must be greater than zero")

    if draft.strike_basis.upper() in {"ABSOLUTE", "FX_RATE"} and draft.strike_currency_id is None:
        raise OptionTermsValidationError("a strike currency is required for a monetary strike")

    if draft.settlement_method.upper() in {"CASH", "CASH_OR_PHYSICAL"} and draft.settlement_currency_id is None:
        raise OptionTermsValidationError("a settlement currency is required for cash settlement")

    if draft.exercise_style.upper() == "BERMUDAN" and draft.exercise_schedule_id is None:
        raise OptionTermsValidationError("a Bermudan option requires an exercise schedule")

    return draft
