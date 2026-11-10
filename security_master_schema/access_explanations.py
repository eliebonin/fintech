"""Read-only explanations of current tenant access; never an authorization gate.

Delivery labels describe bounded product support, separately from subscriptions.
Keep them aligned with docs/product/features/access-and-strategies.md and future-modules.md.
"""
from datetime import date
from security_master_schema.governance_clock import governance_date
from sqlalchemy import select
from . import models as m
from .access_control import ACTION_MODULES, effective_permissions
from .access_management import membership_row
from .tenant_workspace import resolve_tenant_workspace, require_tenant_action

MODULE_DELIVERY = {
    'LIFECYCLE_MANAGEMENT': ('PARTIAL','Tiered bond/FX assistance controls and bond-maturity worklist; other event discovery is planned. Trading actions, strategy scope and review rules remain separate.'),
    'REGULATORY_REPORTING': ('BOUNDED_ALPHA', 'UK transaction preparation/review and frozen preparation exports; no regulatory submission acceptance.'),
    'SECURITY_MASTER': ('BOUNDED_ALPHA', 'Governed instruments, listings and proposal workflow.'),
    'MARKET_DATA': ('BOUNDED_ALPHA', 'Governed EoD acquisition, policies and evidence; not a live terminal.'),
    'TRADING': ('BOUNDED_ALPHA', 'Supported booking profiles, history and corrections; not settlement/accounting.'),
    'VALUATION': ('BOUNDED_ALPHA', 'Staged economic P&L and review; not full fund NAV/accounting.'),
    'FUND_MANAGEMENT': ('FOUNDATION', 'Strategy classification and calendars, not full fund management.'),
    'STRUCTURED_PRODUCTS': ('PARTIAL', 'Terms and supported booking exist under security master/trading; no standalone module workflow.'),
    'AMC_MANAGEMENT': ('FOUNDATION', 'Strategy classification only; dedicated AMC management is not delivered.'),
    'FUND_OPERATIONS': ('FOUNDATION', 'Operational mapping foundations exist; dedicated feed/reconciliation workflows are not delivered.'),
    'UCITS_CONTROLS': ('PLANNED', 'UCITS controls workflow is not delivered.'),
    'STRUCTURED_PRODUCT_DISTRIBUTION': ('PLANNED', 'Distribution workflow is not delivered.'),
}


def explain_actions(*, role, tenant_modules, groups, account_status='ACTIVE', membership_status='ACTIVE'):
    """Use the real resolver, then explain why its actions are allowed/blocked."""
    modules = set(tenant_modules)
    active = [group for group in groups if group['status'] == 'ACTIVE']
    permissions = effective_permissions(role=role, tenant_modules=modules,
        grants={code for group in active for code in group['actions']})
    restrictions = []
    if account_status != 'ACTIVE': restrictions.append('ACCOUNT_INACTIVE')
    if membership_status != 'ACTIVE': restrictions.append('MEMBERSHIP_INACTIVE')
    rows = []
    for code, required in ACTION_MODULES.items():
        sources = (['Tenant administrator role'] if role == 'TENANT_ADMIN' else []) if code == 'ACCESS_MANAGE' else sorted({
            group['name'] for group in active if code in group['actions']})
        blockers = list(restrictions)
        if required and not required & modules: blockers.append('MODULE_NOT_ENABLED')
        if not sources: blockers.append('NO_ACTIVE_ACTION_GRANT')
        rows.append(dict(code=code, moduleCodes=sorted(required), grantSources=sources,
                         allowed=code in permissions and not restrictions, blockers=blockers))
    return rows


def effective_access_view(c, tenant, actor, user=None):
    """Self inspection or tenant-admin inspection; foreign IDs disclose nothing."""
    workspace = resolve_tenant_workspace(c, tenant, actor, governance_date())
    user = user or actor
    if user != actor: require_tenant_action(workspace, 'ACCESS_MANAGE')
    member = membership_row(c, tenant, user)
    account = c.execute(select(m.user_account.c.status, m.person.c.display_name)
        .outerjoin(m.person, m.person.c.person_id == m.user_account.c.person_id)
        .where(m.user_account.c.user_account_id == user)).mappings().one()
    group_rows = c.execute(select(m.access_group).join(m.access_group_member,
        (m.access_group_member.c.tenant_id == m.access_group.c.tenant_id) &
        (m.access_group_member.c.group_id == m.access_group.c.group_id))
        .where(m.access_group.c.tenant_id == tenant, m.access_group_member.c.user_account_id == user)
        .order_by(m.access_group.c.display_name)).mappings().all()
    group_ids = [row['group_id'] for row in group_rows]
    grants = c.execute(select(m.access_group_grant.c.group_id, m.access_group_grant.c.action_code)
        .where(m.access_group_grant.c.tenant_id == tenant,
               m.access_group_grant.c.group_id.in_(group_ids))).all()
    groups = [dict(groupId=str(row['group_id']), name=row['display_name'], status=row['status'],
        actions=sorted(grant.action_code for grant in grants if grant.group_id == row['group_id'])) for row in group_rows]
    actions = explain_actions(role=member['membership_role'], tenant_modules=workspace.tenant_module_codes,
        groups=groups, account_status=account['status'], membership_status=member['status'])
    from .strategy_access import SCOPED_ACTIONS,strategy_predicate
    if member['status']=='ACTIVE' and account['status']=='ACTIVE':
        for action in actions:
            if action['code'] in SCOPED_ACTIONS and action['allowed']:
                names=list(c.scalars(select(m.strategy.c.display_name).where(m.strategy.c.tenant_id==tenant,
                    strategy_predicate(c,tenant,user,action['code'],m.strategy.c.strategy_id)).order_by(m.strategy.c.display_name)))
                action['strategyNames']=names
                if not names:
                    action['allowed']=False;action['blockers'].append('NO_STRATEGY_SCOPE')
    modules = []
    for row in c.execute(select(m.platform_module).where(m.platform_module.c.status == 'ACTIVE')
                         .order_by(m.platform_module.c.sort_order)).mappings():
        code = row['module_code']
        delivery, note = MODULE_DELIVERY.get(code, ('UNASSESSED', 'Delivery has not been assessed.'))
        module_actions = [action for action in actions if code in action['moduleCodes'] or code=='LIFECYCLE_MANAGEMENT' and action['code'].startswith('LIFECYCLE_')]
        modules.append(dict(code=code, name=row['display_name'], enabled=code in workspace.tenant_module_codes,
            accessible=code in workspace.tenant_module_codes and any(action['allowed'] for action in module_actions), deliveryStatus=delivery,
            deliveryNote=note, actions=module_actions))
    return dict(tenantId=str(tenant), userId=str(user), name=account['display_name'] or str(user),
        role=member['membership_role'], accountStatus=account['status'], membershipStatus=member['status'],
        groups=groups, modules=modules, actions=actions,
        strategyScope='Strategy actions apply only within the scope of the same granting group. ALL includes future strategies; SELECTED includes explicit assignments only.',
        asOfDate=governance_date().isoformat())
