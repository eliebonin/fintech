"""One authority policy for instrument and reference-data stewardship."""
from datetime import date
from .resource_limits import governance_date
from uuid import UUID
from sqlalchemy import select
from security_master_schema import models as m
from security_master_schema.tenant_workspace import (
    TenantActionForbidden, require_tenant_action, resolve_tenant_workspace,
)


def require_reference_action(connection, tenant_id: UUID, actor_id: UUID, action='REFERENCE_PROPOSE') -> None:
    if connection.scalar(select(m.user_account.c.user_account_id).where(
        m.user_account.c.user_account_id == actor_id, m.user_account.c.status == 'ACTIVE')) is None:
        raise TenantActionForbidden('User account is not active')
    require_tenant_action(resolve_tenant_workspace(connection, tenant_id, actor_id, governance_date()), action)
