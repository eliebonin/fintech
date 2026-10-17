"""Action-bound strategy authorization shared by reads, writes and explanations."""
from datetime import date
from security_master_schema.governance_clock import governance_date
from sqlalchemy import select,or_,true,false
from . import models as m
from .access_control import ACTION_MODULES
from .tenant_workspace import resolve_tenant_workspace,require_tenant_action,TenantActionForbidden

SCOPED_ACTIONS=frozenset({'STRATEGY_READ','STRATEGY_WRITE','TRADE_READ','TRADE_WRITE','TRADE_CORRECT',
    'VALUATION_READ','VALUATION_RUN','VALUATION_REVIEW','VALUATION_SELF_PUBLISH','CALENDAR_READ','CALENDAR_MANAGE',
    'LIFECYCLE_READ','LIFECYCLE_PREPARE','LIFECYCLE_BOOK','LIFECYCLE_APPROVE','LIFECYCLE_CONFIGURE'})


def strategy_predicate(c,tenant,actor,action,column):
    """Correlated SQL filter; scope and action must come from the same group."""
    workspace=resolve_tenant_workspace(c,tenant,actor,governance_date())
    if action not in workspace.permission_codes: return false()
    if action not in SCOPED_ACTIONS: return true()
    group=m.access_group.alias('scope_group')
    member=m.access_group_member.alias('scope_member')
    grant=m.access_group_grant.alias('scope_grant')
    assigned=m.access_group_strategy.alias('scope_strategy')
    selected=select(assigned.c.strategy_id).where(assigned.c.tenant_id==tenant,
        assigned.c.group_id==group.c.group_id,assigned.c.strategy_id==column).correlate(group,column.table).exists()
    return select(group.c.group_id).join(member,(member.c.tenant_id==group.c.tenant_id)&(member.c.group_id==group.c.group_id))\
        .join(grant,(grant.c.tenant_id==group.c.tenant_id)&(grant.c.group_id==group.c.group_id)).where(
        group.c.tenant_id==tenant,group.c.status=='ACTIVE',member.c.user_account_id==actor,grant.c.action_code==action,
        or_(group.c.scope_mode=='ALL',(group.c.scope_mode=='SELECTED')&selected)).exists()


def require_strategy_action(c,tenant,actor,action,strategy):
    permitted=c.scalar(select(m.strategy.c.strategy_id).where(m.strategy.c.tenant_id==tenant,
        m.strategy.c.strategy_id==strategy,strategy_predicate(c,tenant,actor,action,m.strategy.c.strategy_id)))
    if permitted is None: raise TenantActionForbidden('Strategy is unavailable for this action')


def request_strategy_predicate(c,tenant,action,column):
    """Only API reads bind an actor; trusted internal calculations retain full inputs."""
    actor=c.info.get('request_actor')
    return strategy_predicate(c,tenant,actor,action,column) if actor else true()


def has_all_strategy_scope(c,tenant,actor,action):
    workspace=resolve_tenant_workspace(c,tenant,actor,governance_date())
    if action not in workspace.permission_codes: return False
    return bool(c.scalar(select(m.access_group.c.group_id).join(m.access_group_member,
        (m.access_group_member.c.tenant_id==m.access_group.c.tenant_id)&(m.access_group_member.c.group_id==m.access_group.c.group_id))
        .join(m.access_group_grant,(m.access_group_grant.c.tenant_id==m.access_group.c.tenant_id)&(m.access_group_grant.c.group_id==m.access_group.c.group_id))
        .where(m.access_group.c.tenant_id==tenant,m.access_group.c.status=='ACTIVE',m.access_group.c.scope_mode=='ALL',
        m.access_group_member.c.user_account_id==actor,m.access_group_grant.c.action_code==action).limit(1)))
