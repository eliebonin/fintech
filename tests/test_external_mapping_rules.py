"""Validation behaviour for external identifiers resolved under an as-of date."""

from datetime import date
from uuid import UUID

import pytest

from security_master_schema.tenancy import AmbiguousMappingError, MappingRecord, select_effective_mapping


def test_overlapping_verified_mappings_are_ambiguous() -> None:
    records = (
        MappingRecord(UUID("00000000-0000-7000-8000-000000000201"), date(2026, 1, 1), None, "VERIFIED"),
        MappingRecord(UUID("00000000-0000-7000-8000-000000000202"), date(2026, 6, 1), None, "VERIFIED"),
    )

    with pytest.raises(AmbiguousMappingError):
        select_effective_mapping(records, date(2026, 8, 1))


def test_retired_mapping_is_not_selected_after_its_effective_end() -> None:
    records = (
        MappingRecord(UUID("00000000-0000-7000-8000-000000000203"), date(2026, 1, 1), date(2026, 6, 30), "RETIRED"),
    )

    assert select_effective_mapping(records, date(2026, 7, 1)) is None
