"""Strategy creation authority and initial group scope, committed atomically."""
from datetime import date
from security_master_schema.governance_clock import governance_date
from sqlalchemy import select
from . import models as m
from .tenant_workspace import resolve_tenant_workspace,require_tenant_action,TenantActionForbidden


def creation_groups(c,tenant,actor):
    workspace=resolve_tenant_workspace(c,tenant,actor,governance_date())
    require_tenant_action(workspace,'STRATEGY_CREATE')
    query=select(m.access_group).where(m.access_group.c.tenant_id==tenant,m.access_group.c.status=='ACTIVE')
    if 'ACCESS_MANAGE' not in workspace.permission_codes:
        query=query.where(m.access_group.c.group_id.in_(select(m.access_group_member.c.group_id).where(
            m.access_group_member.c.tenant_id==tenant,m.access_group_member.c.user_account_id==actor)))
    return [dict(groupId=str(row['group_id']),name=row['display_name'],scopeMode=row['scope_mode'])
        for row in c.execute(query.order_by(m.access_group.c.display_name)).mappings()]


def initialize_strategy_access(c,tenant,actor,strategy,groups):
    from .access_management import audit
    allowed={row['groupId'] for row in creation_groups(c,tenant,actor)}
    if not set(map(str,groups))<=allowed: raise TenantActionForbidden('Initial access group is unavailable')
    for group in sorted(set(groups),key=str):
        mode=c.scalar(select(m.access_group.c.scope_mode).where(m.access_group.c.tenant_id==tenant,
            m.access_group.c.group_id==group).with_for_update())
        if mode=='SELECTED':
            c.execute(m.access_group_strategy.insert().values(tenant_id=tenant,group_id=group,strategy_id=strategy))
            c.execute(m.access_group.update().where(m.access_group.c.tenant_id==tenant,m.access_group.c.group_id==group)
                .values(version_no=m.access_group.c.version_no+1))
    audit(c,actor,tenant,'STRATEGY_ACCESS_INITIALIZED',dict(strategyId=str(strategy),groupIds=sorted(map(str,groups)),
        reason='Explicit initial group access; ALL groups already cover new tenant strategies'))
