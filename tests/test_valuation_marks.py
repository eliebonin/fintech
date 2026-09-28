"""Generic valuation-mark evidence tests."""

from decimal import Decimal
from uuid import UUID

import pytest

from security_master_schema.valuation_marks import MarkEvidenceError, ValuationMarkDraft, validate_mark


def test_mark_requires_snapshot_or_approved_override_lineage() -> None:
    draft = ValuationMarkDraft(
        tenant_id=UUID("00000000-0000-7000-8000-000000000011"),
        subject_reference_node_id=UUID("00000000-0000-7000-8000-000000000015"),
        value=Decimal("101.25"),
        currency_id=UUID("00000000-0000-7000-8000-000000000013"),
        mark_type="FAIR_VALUE",
        market_data_resolution_snapshot_id=UUID("00000000-0000-7000-8000-000000000037"),
        override_id=None,
    )
    assert validate_mark(draft).value == Decimal("101.25")


def test_mark_without_input_lineage_is_rejected() -> None:
    with pytest.raises(MarkEvidenceError):
        validate_mark(
            ValuationMarkDraft(
                tenant_id=UUID("00000000-0000-7000-8000-000000000011"),
                subject_reference_node_id=UUID("00000000-0000-7000-8000-000000000015"),
                value=Decimal("101.25"),
                currency_id=UUID("00000000-0000-7000-8000-000000000013"),
                mark_type="FAIR_VALUE",
                market_data_resolution_snapshot_id=None,
                override_id=None,
            )
        )
