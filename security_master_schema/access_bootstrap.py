"""One-time, audited operational groups for pre-separation/local fixture admins.

Never called by user creation, login or role changes. Repeat runs cannot restore
revoked membership/grants. No ACCESS_MANAGE or future action is stored in groups.
"""
from datetime import date
from security_master_schema.governance_clock import governance_date
from uuid import UUID, uuid5
from sqlalchemy import select, text, inspect
from . import models as m
from .tenancy import ModuleEntitlementRecord, resolve_effective_module_codes

# Frozen transition catalogue: adding future actions must not expand old grants.
TRANSITION_ACTIONS = {
    'STRATEGY_READ': {'TRADING','FUND_MANAGEMENT'}, 'STRATEGY_WRITE': {'TRADING','FUND_MANAGEMENT'},
    'TRADE_READ': {'TRADING'}, 'TRADE_WRITE': {'TRADING'}, 'TRADE_CORRECT': {'TRADING'},
    'TRADE_CONFIGURE': {'TRADING'}, 'REFERENCE_READ': {'SECURITY_MASTER'},
    'REFERENCE_PROPOSE': {'SECURITY_MASTER'}, 'REFERENCE_APPROVE': {'SECURITY_MASTER'},
    'MARKET_DATA_READ': {'MARKET_DATA'}, 'MARKET_DATA_MANAGE': {'MARKET_DATA'},
    'VALUATION_READ': {'VALUATION'}, 'VALUATION_RUN': {'VALUATION'}, 'VALUATION_REVIEW': {'VALUATION'},
    'CALENDAR_READ': {'FUND_MANAGEMENT','VALUATION'}, 'CALENDAR_MANAGE': {'FUND_MANAGEMENT','VALUATION'},
}
NAMESPACE = UUID('5fca69bb-e01a-4f28-a79b-1e7186cbb044')


def bootstrap_admin_operations(c, tenant, user, actor, *, as_of=None,include_creation=True):
    """Snapshot enabled-module operational access, once per existing admin."""
    as_of=as_of or governance_date()
    # Coordinate seed/migration reruns without broad table locks.
    c.execute(text('SELECT pg_advisory_xact_lock(2026101384)'))
    memberships=c.execute(select(m.tenant_user_account).where(
        m.tenant_user_account.c.tenant_id==tenant,m.tenant_user_account.c.user_account_id==user,
        m.tenant_user_account.c.valid_from<=as_of,
        m.tenant_user_account.c.valid_to.is_(None)|(m.tenant_user_account.c.valid_to>=as_of))).mappings().all()
    if len(memberships)!=1 or memberships[0]['membership_role']!='TENANT_ADMIN': return False
    marker=c.scalar(select(m.access_audit_event.c.event_id).where(
        m.access_audit_event.c.tenant_id==tenant,m.access_audit_event.c.subject_id==user,
        m.access_audit_event.c.action=='ADMIN_OPERATIONAL_ACCESS_BOOTSTRAPPED'))
    if marker: return False
    rows=c.execute(select(m.tenant_module_entitlement,m.platform_module.c.module_code).join(m.platform_module,
        m.platform_module.c.platform_module_id==m.tenant_module_entitlement.c.platform_module_id)
        .where(m.tenant_module_entitlement.c.tenant_id==tenant)).mappings()
    enabled=resolve_effective_module_codes(tuple(ModuleEntitlementRecord(row['tenant_module_entitlement_id'],
        row['module_code'],row['valid_from'],row['valid_to'],row['entitlement_state']) for row in rows),as_of)
    actions=sorted(code for code,modules in TRANSITION_ACTIONS.items() if modules & enabled)
    if include_creation and 'STRATEGY_WRITE' in actions: actions.append('STRATEGY_CREATE')
    group=uuid5(NAMESPACE,f'{tenant}:{user}')
    values=dict(group_id=group,tenant_id=tenant,code='ADMIN_OPS_'+str(user),
        display_name='Existing administrator operational access',
        description='Explicit one-time compatibility grants. Review or remove; administrator role alone grants no operations.')
    # Revision 84 may run on populated databases before revision 85 adds scope.
    if any(col['name']=='scope_mode' for col in inspect(c).get_columns('access_group',schema='ten')):
        values['scope_mode']='ALL'
    c.execute(m.access_group.insert().values(**values))
    for action in actions:
        c.execute(m.access_group_grant.insert().values(tenant_id=tenant,group_id=group,action_code=action))
    c.execute(m.access_group_member.insert().values(tenant_id=tenant,group_id=group,user_account_id=user))
    c.execute(m.access_audit_event.insert().values(tenant_id=tenant,actor_id=actor,subject_id=user,
        action='ADMIN_OPERATIONAL_ACCESS_BOOTSTRAPPED',details={'groupId':str(group),'actions':actions,
        'moduleCodes':sorted(enabled),'asOfDate':as_of.isoformat(),'transitionRevision':'20261013_84',
        'reason':'Explicit replacement of legacy administrator operational authority'}))
    return True
