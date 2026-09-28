"""Validated evidence linking tenant-local objects to central canonical UUIDs."""

from dataclasses import dataclass
from datetime import date
from uuid import UUID


class CanonicalLinkError(ValueError):
    """Raised when a central canonical lookup cannot safely back a tenant link."""


@dataclass(frozen=True)
class CanonicalObject:
    canonical_reference_node_id: UUID
    object_type: str
    status: str
    canonical_version: int


@dataclass(frozen=True)
class CanonicalLink:
    local_object_id: UUID
    local_object_type: str
    canonical_reference_node_id: UUID
    canonical_object_type: str
    canonical_status: str
    canonical_version: int
    validated_as_of: date


def validate_canonical_link(
    *,
    local_object_id: UUID,
    local_object_type: str,
    canonical: CanonicalObject,
    as_of_date: date,
) -> CanonicalLink:
    """Validate a canonical API response before persisting tenant link evidence."""

    if not local_object_type:
        raise CanonicalLinkError("Local object type is required")
    if canonical.object_type not in {"INSTRUMENT", "LISTING", "REFERENCE_NODE", "CURRENCY"}:
        raise CanonicalLinkError("Canonical object type is not a supported financial reference object")
    if canonical.status not in {"ACTIVE", "MATURED"}:
        raise CanonicalLinkError("Canonical object is not active for a tenant link")
    if canonical.canonical_version < 1:
        raise CanonicalLinkError("Canonical version must be positive")
    return CanonicalLink(
        local_object_id=local_object_id,
        local_object_type=local_object_type,
        canonical_reference_node_id=canonical.canonical_reference_node_id,
        canonical_object_type=canonical.object_type,
        canonical_status=canonical.status,
        canonical_version=canonical.canonical_version,
        validated_as_of=as_of_date,
    )
