"""Canonical definition-version selection tests."""

from datetime import date
from uuid import UUID

import pytest

from security_master_schema.reference_versioning import (
    DefinitionVersion,
    VersioningError,
    select_current_version,
)


NODE_ID = UUID("00000000-0000-7000-8000-000000000015")


def test_select_current_version_uses_effective_date_and_sequence() -> None:
    selected = select_current_version(
        (
            DefinitionVersion(UUID("00000000-0000-7000-8000-000000000201"), NODE_ID, 1, date(2020, 1, 1), date(2025, 12, 31), "APPROVED"),
            DefinitionVersion(UUID("00000000-0000-7000-8000-000000000202"), NODE_ID, 2, date(2026, 1, 1), None, "APPROVED"),
        ),
        as_of_date=date(2026, 9, 1),
    )
    assert selected.sequence_no == 2


def test_overlapping_current_definition_versions_are_rejected() -> None:
    with pytest.raises(VersioningError):
        select_current_version(
            (
                DefinitionVersion(UUID("00000000-0000-7000-8000-000000000203"), NODE_ID, 1, date(2026, 1, 1), None, "APPROVED"),
                DefinitionVersion(UUID("00000000-0000-7000-8000-000000000204"), NODE_ID, 2, date(2026, 6, 1), None, "APPROVED"),
            ),
            as_of_date=date(2026, 9, 1),
        )
