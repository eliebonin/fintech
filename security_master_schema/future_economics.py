"""Supported dated linear quotations, independent of the underlying asset class."""
from .booking_conventions import FutureConvention


def require_linear_future(convention: FutureConvention) -> None:
    """Validate the complete convention; never coerce an inverse/quanto payoff.

    UNDERLYING_UNIT multiplies price movement by sourced asset units per contract.
    CASH/PHYSICAL describes delivery, not another pre-delivery variation formula.
    Revalidation also protects callers holding copied/unvalidated model objects.
    """
    FutureConvention.model_validate(convention.model_dump(mode='python'))
    if convention.price_basis not in ('INDEX_POINTS','UNDERLYING_UNIT') or convention.settlement_method not in ('CASH','PHYSICAL'):
        raise ValueError('Supported dated linear futures quotation required')
