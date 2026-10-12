"""Tenant-membership and module authority resolution for workspace services."""

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlalchemy import Connection, select

from . import models as m
from .tenancy import AmbiguousMappingError, ModuleEntitlementRecord, resolve_effective_module_codes
from .access_control import effective_permissions, effective_modules


class TenantActionForbidden(PermissionError):
    """Raised when an active tenant membership cannot perform an action."""


@dataclass(frozen=True)
class TenantMembershipView:
    tenant_id: UUID
    tenant_code: str
    tenant_name: str
    membership_role: str


@dataclass(frozen=True)
class TenantWorkspaceView:
    tenant_id: UUID
    tenant_code: str
    tenant_name: str
    membership_role: str
    module_codes: frozenset[str]
    platform_role: str | None
    permission_codes: frozenset[str] = frozenset()
    tenant_module_codes: frozenset[str] = frozenset()


def _is_effective(valid_from: date, valid_to: date | None, as_of_date: date) -> bool:
    return valid_from <= as_of_date and (valid_to is None or as_of_date <= valid_to)


def list_active_tenant_memberships(connection: Connection, user_account_id: UUID, as_of_date: date) -> list[TenantMembershipView]:
    rows = connection.execute(
        select(m.tenant.c.tenant_id, m.tenant.c.tenant_code, m.tenant.c.display_name, m.tenant_user_account.c.membership_role, m.tenant_user_account.c.valid_from, m.tenant_user_account.c.valid_to)
        .join(m.tenant_user_account, m.tenant_user_account.c.tenant_id == m.tenant.c.tenant_id)
        .join(m.user_account, m.user_account.c.user_account_id == m.tenant_user_account.c.user_account_id)
        .where(m.tenant_user_account.c.user_account_id == user_account_id)
        .where(m.tenant_user_account.c.status == "ACTIVE")
        .where(m.tenant.c.status == "ACTIVE")
        .where(m.user_account.c.status == 'ACTIVE')
        .order_by(m.tenant.c.tenant_code)
    ).mappings().all()
    return [
        TenantMembershipView(row["tenant_id"], row["tenant_code"], row["display_name"], row["membership_role"])
        for row in rows
        if _is_effective(row["valid_from"], row["valid_to"], as_of_date)
    ]


def resolve_platform_role(connection: Connection, user_account_id: UUID, as_of_date: date) -> str | None:
    if connection.scalar(select(m.user_account.c.user_account_id).where(
            m.user_account.c.user_account_id == user_account_id, m.user_account.c.status == 'ACTIVE')) is None:
        return None
    rows = connection.execute(
        select(m.platform_user_account.c.platform_role, m.platform_user_account.c.valid_from, m.platform_user_account.c.valid_to)
        .where(m.platform_user_account.c.user_account_id == user_account_id)
        .where(m.platform_user_account.c.status == "ACTIVE")
    ).mappings().all()
    roles = [row["platform_role"] for row in rows if _is_effective(row["valid_from"], row["valid_to"], as_of_date)]
    if len(roles) > 1:
        raise AmbiguousMappingError("More than one platform role applies on the requested date")
    return roles[0] if roles else None


def resolve_tenant_workspace(connection: Connection, tenant_id: UUID, user_account_id: UUID, as_of_date: date) -> TenantWorkspaceView:
    memberships = [row for row in list_active_tenant_memberships(connection, user_account_id, as_of_date) if row.tenant_id == tenant_id]
    if len(memberships) != 1:
        raise TenantActionForbidden("Tenant is outside the actor's active memberships or membership history is ambiguous")
    membership = memberships[0]
    entitlement_rows = connection.execute(
        select(m.platform_module.c.module_code, m.tenant_module_entitlement.c.tenant_module_entitlement_id, m.tenant_module_entitlement.c.valid_from, m.tenant_module_entitlement.c.valid_to, m.tenant_module_entitlement.c.entitlement_state)
        .join(m.tenant_module_entitlement, m.tenant_module_entitlement.c.platform_module_id == m.platform_module.c.platform_module_id)
        .where(m.tenant_module_entitlement.c.tenant_id == tenant_id)
    ).mappings().all()
    module_codes = resolve_effective_module_codes(
        tuple(
            ModuleEntitlementRecord(
                row["tenant_module_entitlement_id"], row["module_code"], row["valid_from"], row["valid_to"], row["entitlement_state"]
            )
            for row in entitlement_rows
        ),
        as_of_date,
    )
    grants = set(connection.scalars(select(m.access_group_grant.c.action_code)
        .join(m.access_group, (m.access_group.c.tenant_id == m.access_group_grant.c.tenant_id)
              & (m.access_group.c.group_id == m.access_group_grant.c.group_id))
        .join(m.access_group_member, (m.access_group_member.c.tenant_id == m.access_group.c.tenant_id)
              & (m.access_group_member.c.group_id == m.access_group.c.group_id))
        .where(m.access_group.c.tenant_id == tenant_id, m.access_group.c.status == 'ACTIVE',
               m.access_group_member.c.user_account_id == user_account_id)))
    permissions = effective_permissions(role=membership.membership_role, tenant_modules=module_codes, grants=grants)
    return TenantWorkspaceView(membership.tenant_id, membership.tenant_code, membership.tenant_name,
        membership.membership_role, effective_modules(module_codes, permissions),
        resolve_platform_role(connection, user_account_id, as_of_date), permissions, module_codes)


def require_tenant_action(workspace: TenantWorkspaceView, action: str) -> None:
    if action in workspace.permission_codes:
        return
    raise TenantActionForbidden("Tenant membership is not permitted to perform this action")
