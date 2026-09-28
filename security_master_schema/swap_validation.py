"""Validation primitives for contractual swap legs."""

from dataclasses import dataclass
from uuid import UUID


class SwapLegValidationError(ValueError):
    """Raised when a swap leg cannot describe coherent contractual economics."""


SUPPORTED_SWAP_LEG_ROLES = frozenset({"PERFORMANCE", "FUNDING", "COUPON", "PROTECTION", "FEE"})


@dataclass(frozen=True)
class SwapLegDraft:
    """Minimal leg information required before persisting a contractual swap leg."""

    leg_role: str
    pay_receive: str
    reference_node_id: UUID | None
    return_profile_id: UUID | None
    currency_id: UUID | None


def validate_swap_leg(draft: SwapLegDraft) -> SwapLegDraft:
    """Validate the first-slice PERFORMANCE and FUNDING leg contract."""

    if draft.leg_role not in SUPPORTED_SWAP_LEG_ROLES:
        raise SwapLegValidationError("Swap leg role is unsupported")

    if draft.pay_receive not in {"PAY", "RECEIVE"}:
        raise SwapLegValidationError("Swap leg direction must be PAY or RECEIVE")

    if draft.leg_role == "PERFORMANCE":
        if draft.reference_node_id is None:
            raise SwapLegValidationError("A performance leg requires a reference node")
        if draft.return_profile_id is None:
            raise SwapLegValidationError("A performance leg requires a return profile")

    if draft.leg_role == "FUNDING":
        if draft.reference_node_id is None:
            raise SwapLegValidationError("A funding leg requires a reference node")
        if draft.currency_id is None:
            raise SwapLegValidationError("A funding leg requires a currency")

    return draft
