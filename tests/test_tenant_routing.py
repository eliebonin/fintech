"""Tenant database routing contract tests."""

from uuid import UUID

import pytest

from security_master_schema.tenant_routing import (
    TenantRoutingError,
    TenantRoute,
    select_tenant_route,
)


TENANT_ID = UUID("00000000-0000-7000-8000-000000000011")


def test_route_is_selected_from_registry_not_client_database_input() -> None:
    route = select_tenant_route(
        tenant_id=TENANT_ID,
        registry=(
            TenantRoute(TENANT_ID, "tenant_fortem", "cluster-a", "ACTIVE", 12),
        ),
        requested_database=None,
    )
    assert route.database_name == "tenant_fortem"


def test_client_cannot_override_registry_database_or_use_inactive_route() -> None:
    with pytest.raises(TenantRoutingError):
        select_tenant_route(
            tenant_id=TENANT_ID,
            registry=(
                TenantRoute(TENANT_ID, "tenant_fortem", "cluster-a", "SUSPENDED", 12),
            ),
            requested_database="another_client_database",
        )
