"""Pure resolution rules for tenant operational fund-data mappings."""

from datetime import date
from uuid import UUID

import pytest

from security_master_schema.tenancy import (
    AmbiguousMappingError,
    OperationalMappingRecord,
    normalize_external_id,
    select_effective_operational_mapping,
)


def test_case_insensitive_profile_normalises_only_outer_whitespace() -> None:
    assert normalize_external_id("  nav-i-gbp  ", "TRIM_UPPER") == "NAV-I-GBP"


def test_exact_profile_preserves_received_value() -> None:
    assert normalize_external_id(" NAV-i-gbp ", "EXACT") == " NAV-i-gbp "


def test_effective_operational_mapping_requires_approved_status() -> None:
    record = OperationalMappingRecord(
        mapping_id=UUID("00000000-0000-7000-8000-000000000801"),
        valid_from=date(2026, 1, 1),
        valid_to=None,
        status="PROPOSED",
    )

    assert select_effective_operational_mapping((record,), date(2026, 6, 1)) is None


def test_effective_operational_mapping_uses_report_business_date() -> None:
    record = OperationalMappingRecord(
        mapping_id=UUID("00000000-0000-7000-8000-000000000802"),
        valid_from=date(2026, 1, 1),
        valid_to=date(2026, 6, 30),
        status="APPROVED",
    )

    assert select_effective_operational_mapping((record,), date(2026, 6, 30)) == record
    assert select_effective_operational_mapping((record,), date(2026, 7, 1)) is None


def test_overlapping_approved_operational_mappings_are_ambiguous() -> None:
    records = (
        OperationalMappingRecord(UUID("00000000-0000-7000-8000-000000000803"), date(2026, 1, 1), None, "APPROVED"),
        OperationalMappingRecord(UUID("00000000-0000-7000-8000-000000000804"), date(2026, 6, 1), None, "APPROVED"),
    )

    with pytest.raises(AmbiguousMappingError):
        select_effective_operational_mapping(records, date(2026, 8, 1))
