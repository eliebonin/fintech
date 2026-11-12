"""Explicit tenant-owned downgrade preparation; never a platform privilege bypass."""
from sqlalchemy import select,tuple_
from security_master_schema import models as m
from security_master_schema.strategy_access import strategy_predicate
from security_master_schema.booking_controls import lock_trade_configuration
from security_master_schema.evidence import evidence_hash
from security_master_schema.access_management import audit
from .assistance_contracts import TransitionPreview,TransitionApply,EVENT_MAXIMUM
from .assistance import append_selection,native_policy_map,can_configure_population
from .entitlements import lifecycle_lock,lifecycle_subscription_view,current_selections,AssistanceConflict


def preview_assistance_transition(c,tenant,actor,request):
    request=TransitionPreview.model_validate(request)
    lifecycle_lock(c,tenant);lock_trade_configuration(c,tenant)
    current=lifecycle_subscription_view(c,tenant)
    if current['revision']!=request.expectedSubscriptionRevision:raise AssistanceConflict('Subscription changed; review downgrade preparation again.')
    if request.proposedMaximumTier>current['maximumTier']:raise ValueError('Downgrade preparation cannot grant a higher subscription.')
    target=request.targetTier if request.replacement=='EXPLICIT' else request.proposedMaximumTier
    if target>request.proposedMaximumTier or target>current['maximumTier']:raise ValueError('Replacement tier exceeds the proposed or current subscription.')
    statement=current_selections(c,tenant)
    if request.scope!='SELECTED' and not can_configure_population(c,tenant,actor):raise PermissionError('Whole-population preparation requires configure authority for every included strategy. Use an explicit authorised selection.')
    if request.scope=='SELECTED':
        requested={strategy for strategy,event in request.targets}
        permitted=set(c.scalars(select(m.strategy.c.strategy_id).where(m.strategy.c.tenant_id==tenant,m.strategy.c.strategy_id.in_(requested),strategy_predicate(c,tenant,actor,'LIFECYCLE_CONFIGURE',m.strategy.c.strategy_id))))
        if permitted!=requested:raise PermissionError('A selected strategy is unavailable for configuration.')
    if request.scope=='SELECTED':statement=statement.where(tuple_(m.strategy_lifecycle_assistance.c.strategy_id,m.strategy_lifecycle_assistance.c.event_type).in_(request.targets))
    rows=[dict(row) for row in c.execute(statement.order_by(m.strategy_lifecycle_assistance.c.strategy_id,m.strategy_lifecycle_assistance.c.event_type)).mappings()]
    # SELECTED must not disclose any other strategy through result rows or hashes.
    if request.scope=='SELECTED':
        targets=set(request.targets);rows=[r for r in rows if (r['strategy_id'],r['event_type']) in targets]
        if {(r['strategy_id'],r['event_type']) for r in rows}!=targets:raise LookupError('A selected event has no explicit assistance setting.')
    names={r.strategy_id:r.display_name for r in c.execute(select(m.strategy.c.strategy_id,m.strategy.c.display_name).where(m.strategy.c.tenant_id==tenant,m.strategy.c.strategy_id.in_([r['strategy_id'] for r in rows])))}
    policies=native_policy_map(c,tenant,[r['strategy_id'] for r in rows])
    items=[];proof=[]
    for row in rows:
        before=row['selected_tier']
        affected=before>request.proposedMaximumTier
        after=before if request.replacement=='KEEP' else target if affected or request.scope=='ALL_CONFIGURED' else before
        supported_maximum=EVENT_MAXIMUM.get(row['event_type'],3)
        if request.replacement=='HIGHEST_AVAILABLE':after=min(after,supported_maximum)
        elif after>supported_maximum:raise ValueError('Explicit replacement exceeds a selected event support level; select notifications-only events separately with Tier0 or Tier1.')
        policy=policies.get((row['strategy_id'],row['event_type']),dict(mode='MANUAL' if row['event_type'] in EVENT_MAXIMUM else 'REVIEW',revision=0))
        items.append(dict(strategyId=row['strategy_id'],strategyLabel=names[row['strategy_id']],eventType=row['event_type'],beforeTier=before,afterTier=after,revision=row['revision'],changed=before!=after))
        proof.append(dict(row,processingPolicyRevision=policy['revision'],processingMode=policy['mode']))
    digest=evidence_hash(dict(request=request.model_dump(),subscription=current,rows=proof,actorId=str(actor)))
    return dict(items=items,changedCount=sum(r['changed'] for r in items),unchangedCount=sum(not r['changed'] for r in items),blockedCount=sum(r['afterTier']>request.proposedMaximumTier for r in items),inputHash=digest,subscriptionRevision=current['revision'],proposedMaximumTier=request.proposedMaximumTier,commercialSubscriptionChanged=False)


def apply_assistance_transition(c,tenant,actor,real_operator,request):
    request=TransitionApply.model_validate(request)
    if request.replacement=='KEEP':raise ValueError('Keep unchanged is a preview-only choice; no strategy update is needed.')
    if request.scope=='ALL_CONFIGURED' and not request.confirmReplaceAllowed:raise ValueError('Confirm replacing settings that are currently allowed, including lower choices.')
    preview=preview_assistance_transition(c,tenant,actor,TransitionPreview(**{key:value for key,value in request.model_dump().items() if key in TransitionPreview.model_fields}))
    if preview['inputHash']!=request.inputHash:raise AssistanceConflict('Assistance settings changed; review the whole transition again.')
    identities=sorted({r['strategyId'] for r in preview['items']},key=str)
    if identities:c.execute(select(m.strategy.c.strategy_id).where(m.strategy.c.tenant_id==tenant,m.strategy.c.strategy_id.in_(identities)).order_by(m.strategy.c.strategy_id).with_for_update()).all()
    # A nested effect savepoint makes a row/audit failure all-or-nothing even for
    # callers that catch errors and retain their outer transaction.
    with c.begin_nested():
        for row in preview['items']:
            if row['changed']:append_selection(c,tenant,actor,real_operator,row['strategyId'],row['eventType'],row['afterTier'],row['revision'],request.reason)
        audit(c,actor,tenant,'LIFECYCLE_DOWNGRADE_PREPARED',dict(inputHash=preview['inputHash'],changedCount=preview['changedCount'],proposedMaximumTier=request.proposedMaximumTier,reason=request.reason,commercialSubscriptionChanged=False))
    return dict(updatedCount=preview['changedCount'],unchangedCount=preview['unchangedCount'],commercialSubscriptionChanged=False,message='Strategy settings saved. The platform subscription is unchanged; its downgrade is a separate reviewed action.')
