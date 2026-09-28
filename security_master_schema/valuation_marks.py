"""Validation primitives for tenant-scoped valuation marks."""

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID


class MarkEvidenceError(ValueError):
    """Raised when a valuation conclusion lacks reproducible input evidence."""


@dataclass(frozen=True)
class ValuationMarkDraft:
    tenant_id: UUID
    subject_reference_node_id: UUID
    value: Decimal
    currency_id: UUID
    mark_type: str
    market_data_resolution_snapshot_id: UUID | None
    override_id: UUID | None


def validate_mark(draft: ValuationMarkDraft) -> ValuationMarkDraft:
    """Require an immutable resolver snapshot or explicitly approved override."""

    if not draft.mark_type:
        raise MarkEvidenceError("Mark type is required")
    if draft.value.is_nan() or draft.value.is_infinite():
        raise MarkEvidenceError("Mark value must be finite")
    if (draft.market_data_resolution_snapshot_id is None) == (draft.override_id is None):
        raise MarkEvidenceError("A mark requires exactly one resolver snapshot or approved override")
    return draft
