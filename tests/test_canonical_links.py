"""Cross-database canonical UUID link validation tests."""

from datetime import date
from uuid import UUID

import pytest

from security_master_schema.canonical_links import (
    CanonicalLinkError,
    CanonicalObject,
    validate_canonical_link,
)


LOCAL_ID = UUID("00000000-0000-7000-8000-000000000301")
CANONICAL_ID = UUID("00000000-0000-7000-8000-000000000015")


def test_validated_link_keeps_central_identity_and_version_evidence() -> None:
    link = validate_canonical_link(
        local_object_id=LOCAL_ID,
        local_object_type="TRADE_SUBJECT",
        canonical=CanonicalObject(CANONICAL_ID, "INSTRUMENT", "ACTIVE", 4),
        as_of_date=date(2026, 9, 1),
    )
    assert link.canonical_reference_node_id == CANONICAL_ID
    assert link.canonical_version == 4


def test_retired_or_incompatible_canonical_object_is_rejected() -> None:
    with pytest.raises(CanonicalLinkError):
        validate_canonical_link(
            local_object_id=LOCAL_ID,
            local_object_type="TRADE_SUBJECT",
            canonical=CanonicalObject(CANONICAL_ID, "PERSON", "RETIRED", 1),
            as_of_date=date(2026, 9, 1),
        )
