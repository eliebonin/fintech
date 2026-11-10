"""Scoped strategy/event choices; commercial access never grants trading authority."""
from sqlalchemy import select,func
from security_master_schema import models as m
from security_master_schema.strategy_access import require_strategy_action,strategy_predicate
from security_master_schema.booking_controls import lock_trade_configuration
from security_master_schema.access_management import audit
from .assistance_contracts import EVENT_TYPES,TIERS,AssistanceChange
from .entitlements import lifecycle_lock,lifecycle_subscription_view,current_selections,AssistanceConflict

OPERATIONS={'PREVIEW':'LIFECYCLE_READ','PREPARE':'LIFECYCLE_PREPARE','CONFIRM':'LIFECYCLE_BOOK','APPROVE':'LIFECYCLE_APPROVE','DIRECT':'LIFECYCLE_BOOK'}


def assistance_decision(maximum,selected,operation,mode):
    if operation not in OPERATIONS:raise ValueError('Unsupported assistance operation.')
    if maximum not in TIERS or selected not in TIERS:raise ValueError('Unsupported assistance tier.')
    reasons=[]
    if selected>maximum:reasons.append('Selected assistance exceeds the current subscription. Review the strategy settings.')
    elif selected<2:reasons.append('Assisted preparation requires selected Tier2 or higher.')
    elif operation=='DIRECT' and (selected!=3 or mode!='DIRECT'):reasons.append('One-click booking needs selected Tier3 and a direct-execution policy. Required independent review cannot be bypassed.')
    elif operation=='APPROVE' and mode!='REVIEW':reasons.append('Independent approval applies only to review-required preparations.')
    elif operation=='CONFIRM' and mode=='REVIEW':reasons.append('This preparation requires independent approval.')
    return dict(allowed=not reasons,reasons=reasons)


def native_policy(c,tenant,strategy,event):
    if event not in EVENT_TYPES:raise ValueError('Unsupported lifecycle event.')
    t=m.bond_redemption_policy if event=='BOND_MATURITY' else m.fx_maturity_policy
    row=c.execute(select(t).where(t.c.tenant_id==tenant,t.c.strategy_id==strategy).order_by(t.c.revision.desc()).limit(1)).mappings().first()
    return dict(row) if row else dict(mode='REVIEW',revision=0)


def selection(c,tenant,strategy,event):
    if event not in EVENT_TYPES:raise ValueError('Unsupported lifecycle event.')
    t=m.strategy_lifecycle_assistance
    return c.execute(select(t).where(t.c.tenant_id==tenant,t.c.strategy_id==strategy,t.c.event_type==event).order_by(t.c.revision.desc()).limit(1)).mappings().first()


def _view(c,tenant,actor,strategy,event):
    subscription=lifecycle_subscription_view(c,tenant);row=selection(c,tenant,strategy,event);native=native_policy(c,tenant,strategy,event)
    tier=row['selected_tier'] if row else 0
    try:require_strategy_action(c,tenant,actor,'LIFECYCLE_CONFIGURE',strategy)
    except PermissionError:configure=False
    else:configure=True
    return dict(tenantId=tenant,strategyId=strategy,eventType=event,maximumTier=subscription['maximumTier'],selectedTier=tier,
        subscriptionRevision=subscription['revision'],assistanceRevision=row['revision'] if row else 0,processingPolicyRevision=native['revision'],processingMode=native['mode'],
        availableTiers=list(range(subscription['maximumTier']+1)),status='BLOCKED_BY_SUBSCRIPTION' if tier>subscription['maximumTier'] else 'AVAILABLE',canConfigure=configure,
        handlerSupported=True,notificationDiscoveryAvailable=event=='BOND_MATURITY' and subscription['maximumTier']>=1,
        operations={operation:assistance_decision(subscription['maximumTier'],tier,operation,native['mode']) for operation in OPERATIONS})


def assistance_view(c,tenant,actor,strategy,event):
    require_strategy_action(c,tenant,actor,'LIFECYCLE_READ',strategy)
    return _view(c,tenant,actor,strategy,event)


def assistance_options(c,tenant,actor,query='',offset=0,limit=25):
    if offset<0 or not 1<=limit<=100:raise ValueError('Invalid assistance page.')
    from security_master_schema.tenant_workspace import resolve_tenant_workspace,require_tenant_action
    from security_master_schema.governance_clock import governance_date
    require_tenant_action(resolve_tenant_workspace(c,tenant,actor,governance_date()),'LIFECYCLE_READ')
    t=m.strategy
    statement=select(t.c.strategy_id.label('strategyId'),t.c.display_name.label('label'),t.c.strategy_code.label('code'),strategy_predicate(c,tenant,actor,'LIFECYCLE_CONFIGURE',t.c.strategy_id).label('canConfigure')).where(t.c.tenant_id==tenant,strategy_predicate(c,tenant,actor,'LIFECYCLE_READ',t.c.strategy_id))
    if query:statement=statement.where(t.c.display_name.icontains(query,autoescape=True))
    items=[dict(r) for r in c.execute(statement.order_by(t.c.display_name,t.c.strategy_id).offset(offset).limit(limit)).mappings()]
    current=current_selections(c,tenant).where(m.strategy_lifecycle_assistance.c.strategy_id.in_([r['strategyId'] for r in items]))
    settings={}
    for row in c.execute(current).mappings():settings.setdefault(row['strategy_id'],{})[row['event_type']]=row['selected_tier']
    for row in items:row['configuredEvents']=settings.get(row['strategyId'],{})
    return dict(items=items,total=c.scalar(select(func.count()).select_from(statement.subquery())),offset=offset,limit=limit,subscription=lifecycle_subscription_view(c,tenant),canConfigureAll=can_configure_population(c,tenant,actor))


def append_selection(c,tenant,actor,operator,strategy,event,tier,revision,reason):
    c.execute(m.strategy_lifecycle_assistance.insert().values(tenant_id=tenant,strategy_id=strategy,event_type=event,revision=revision+1,previous_revision=revision or None,selected_tier=tier,reason=reason,actor_id=actor,real_operator_id=operator))
    audit(c,actor,tenant,'LIFECYCLE_ASSISTANCE_CHANGED',dict(strategyId=str(strategy),eventType=event,selectedTier=tier,revision=revision+1,reason=reason,realOperatorId=str(operator)))


def configure_assistance(c,tenant,actor,real_operator,request):
    request=AssistanceChange.model_validate(request)
    require_strategy_action(c,tenant,actor,'LIFECYCLE_CONFIGURE',request.strategyId)
    lifecycle_lock(c,tenant);lock_trade_configuration(c,tenant)
    if c.scalar(select(m.strategy.c.strategy_id).where(m.strategy.c.tenant_id==tenant,m.strategy.c.strategy_id==request.strategyId,m.strategy.c.status=='ACTIVE').with_for_update()) is None:raise LookupError('Active strategy unavailable.')
    current=_view(c,tenant,actor,request.strategyId,request.eventType)
    if current['subscriptionRevision']!=request.expectedSubscriptionRevision or current['assistanceRevision']!=request.expectedRevision:raise AssistanceConflict('Lifecycle configuration changed; reload and review again.')
    if request.selectedTier>current['maximumTier']:raise ValueError('Requested assistance exceeds the current subscription.')
    if current['assistanceRevision'] and current['selectedTier']==request.selectedTier:return current
    append_selection(c,tenant,actor,real_operator,request.strategyId,request.eventType,request.selectedTier,current['assistanceRevision'],request.reason)
    return _view(c,tenant,actor,request.strategyId,request.eventType)


def require_assistance(c,tenant,actor,strategy,event,operation):
    if operation not in OPERATIONS:raise ValueError('Unsupported assistance operation.')
    require_strategy_action(c,tenant,actor,OPERATIONS[operation],strategy)
    lifecycle_lock(c,tenant)
    current=_view(c,tenant,actor,strategy,event)
    decision=current['operations'][operation]
    if not decision['allowed']:raise PermissionError(' '.join(decision['reasons']))
    return {key:current[key] for key in ('maximumTier','selectedTier','subscriptionRevision','assistanceRevision','processingPolicyRevision','processingMode','eventType')}


def current_assistance_proof(c,tenant,strategy,event,operation='PREVIEW',*,mode=None):
    """Commercial guard for trusted native reconstruction; callers own actor checks."""
    lifecycle_lock(c,tenant)
    subscription=lifecycle_subscription_view(c,tenant);choice=selection(c,tenant,strategy,event);policy=native_policy(c,tenant,strategy,event)
    selected=choice['selected_tier'] if choice else 0
    result=assistance_decision(subscription['maximumTier'],selected,operation,policy['mode'] if mode is None else mode)
    if not result['allowed']:raise PermissionError(' '.join(result['reasons']))
    return dict(eventType=event,selectedTier=selected,maximumTier=subscription['maximumTier'],subscriptionRevision=subscription['revision'],assistanceRevision=choice['revision'],entitlementFingerprint=subscription['entitlementFingerprint'])


def can_configure_population(c,tenant,actor):
    """Coverage of current explicit settings, not a demand for future ALL scope."""
    from security_master_schema.tenant_workspace import resolve_tenant_workspace
    from security_master_schema.governance_clock import governance_date
    if 'LIFECYCLE_CONFIGURE' not in resolve_tenant_workspace(c,tenant,actor,governance_date()).permission_codes:return False
    targets=current_selections(c,tenant).subquery()
    denied=select(m.strategy.c.strategy_id).where(m.strategy.c.tenant_id==tenant,m.strategy.c.strategy_id.in_(select(targets.c.strategy_id)),~strategy_predicate(c,tenant,actor,'LIFECYCLE_CONFIGURE',m.strategy.c.strategy_id))
    return not c.scalar(select(denied.exists()))


def native_policy_map(c,tenant,strategies):
    """Two batched reads for downgrade previews, independent of target count."""
    result={}
    for table,event in ((m.bond_redemption_policy,'BOND_MATURITY'),(m.fx_maturity_policy,'FX_FORWARD_MATURITY')):
        latest=select(table.c.strategy_id,func.max(table.c.revision).label('revision')).where(table.c.tenant_id==tenant,table.c.strategy_id.in_(strategies)).group_by(table.c.strategy_id).subquery()
        for row in c.execute(select(table).join(latest,(latest.c.strategy_id==table.c.strategy_id)&(latest.c.revision==table.c.revision)).where(table.c.tenant_id==tenant)).mappings():result[(row['strategy_id'],event)]=row
    return result
