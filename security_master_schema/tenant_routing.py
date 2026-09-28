"""Validated tenant-to-overlay database routing primitives."""

from dataclasses import dataclass
from uuid import UUID


class TenantRoutingError(PermissionError):
    """Raised when no active registry route exists or the caller supplies a target."""


@dataclass(frozen=True)
class TenantRoute:
    tenant_id: UUID
    database_name: str
    cluster_id: str
    status: str
    schema_version: int


def select_tenant_route(
    *,
    tenant_id: UUID,
    registry: tuple[TenantRoute, ...],
    requested_database: str | None,
) -> TenantRoute:
    """Select the active route from trusted registry facts, never user routing input."""

    if requested_database is not None:
        raise TenantRoutingError("Database target is selected by the trusted tenant registry")
    matches = tuple(route for route in registry if route.tenant_id == tenant_id and route.status == "ACTIVE")
    if len(matches) != 1:
        raise TenantRoutingError("Tenant has no unique active database route")
    return matches[0]
