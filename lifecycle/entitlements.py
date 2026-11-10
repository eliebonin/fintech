"""Platform-owned lifecycle ceilings; payments and tenant strategy choices are separate."""
from hashlib import sha256
from sqlalchemy import select,func,or_,exists
from security_master_schema import models as m
from security_master_schema.governance_clock import governance_date
from security_master_schema.evidence import evidence_hash
from security_master_schema.access_management import require_platform,audit,AccessVersionConflict
from .assistance_contracts import MODULE,SubscriptionPreview,SubscriptionChange

class AssistanceConflict(AccessVersionConflict):pass


def lifecycle_lock(c,tenant,*,exclusive=False):
    key=int.from_bytes(sha256(f'lifecycle-subscription:{tenant}'.encode()).digest()[:8],'big',signed=True)
    c.execute(select((func.pg_advisory_xact_lock if exclusive else func.pg_advisory_xact_lock_shared)(key)))


def current_selections(c,tenant):
    t=m.strategy_lifecycle_assistance
    current=select(t.c.strategy_id,t.c.event_type,func.max(t.c.revision).label('revision')).where(t.c.tenant_id==tenant).group_by(t.c.strategy_id,t.c.event_type).subquery()
    return select(t).join(current,(current.c.strategy_id==t.c.strategy_id)&(current.c.event_type==t.c.event_type)&(current.c.revision==t.c.revision)).where(t.c.tenant_id==tenant)


def lifecycle_subscription_view(c,tenant_id):
    status=c.scalar(select(m.tenant.c.status).where(m.tenant.c.tenant_id==tenant_id))
    if status is None:raise LookupError('Tenant unavailable.')
    t=m.tenant_lifecycle_subscription
    row=c.execute(select(t).where(t.c.tenant_id==tenant_id).order_by(t.c.revision.desc()).limit(1)).mappings().first()
    module=c.scalar(select(m.platform_module.c.platform_module_id).where(m.platform_module.c.module_code==MODULE,m.platform_module.c.status=='ACTIVE'))
    e=m.tenant_module_entitlement;day=governance_date()
    grants=c.execute(select(e).where(e.c.tenant_id==tenant_id,e.c.platform_module_id==module,e.c.valid_from<=day,or_(e.c.valid_to.is_(None),e.c.valid_to>=day))).mappings().all() if module else []
    if len(grants)>1:raise AssistanceConflict('Ambiguous lifecycle subscription history; resolve it before proceeding.')
    enabled=status=='ACTIVE' and bool(grants and grants[0]['entitlement_state']=='GRANTED')
    maximum=row['maximum_tier'] if row and enabled else 0
    return dict(tenantId=tenant_id,maximumTier=maximum,configuredMaximumTier=row['maximum_tier'] if row else 0,revision=row['revision'] if row else 0,source=row['source'] if row else None,moduleActive=enabled,notificationDiscoveryAvailable=maximum>=1,
        entitlementFingerprint=evidence_hash([dict(g) for g in grants]))


def _impact(c,tenant,tier):
    rows=[dict(r) for r in c.execute(current_selections(c,tenant).order_by(m.strategy_lifecycle_assistance.c.strategy_id,m.strategy_lifecycle_assistance.c.event_type)).mappings()]
    native=[];pending=[]
    for policy,proposal,posting in ((m.bond_redemption_policy,m.bond_redemption_proposal,m.bond_redemption_posting),(m.fx_maturity_policy,m.fx_maturity_proposal,m.fx_maturity_posting)):
        native.extend([dict(r) for r in c.execute(select(policy.c.strategy_id,policy.c.revision,policy.c.mode).where(policy.c.tenant_id==tenant).order_by(policy.c.strategy_id,policy.c.revision)).mappings()])
        pending.extend([dict(r) for r in c.execute(select(proposal.c.proposal_id,proposal.c.input_hash,proposal.c.policy_revision).where(proposal.c.tenant_id==tenant,~exists(select(1).where(posting.c.tenant_id==tenant,posting.c.proposal_id==proposal.c.proposal_id))).order_by(proposal.c.proposal_id)).mappings()])
    return rows,native,pending


def preview_subscription_change(c,platform_actor,tenant_id,maximum_tier,expected_revision):
    require_platform(c,platform_actor)
    values=SubscriptionPreview(maximumTier=maximum_tier,expectedRevision=expected_revision)
    lifecycle_lock(c,tenant_id,exclusive=True)
    current=lifecycle_subscription_view(c,tenant_id)
    if current['revision']!=expected_revision:raise AssistanceConflict('Lifecycle subscription changed; reload and review again.')
    rows,native,pending=_impact(c,tenant_id,maximum_tier)
    blocked=sum(r['selected_tier']>maximum_tier for r in rows)
    digest=evidence_hash(dict(current=current,maximumTier=maximum_tier,selections=rows,nativePolicies=native,pending=pending))
    return dict(current=current,proposedMaximumTier=maximum_tier,affectedEventCount=blocked,pendingPreparationCount=len(pending),inputHash=digest)


def change_subscription(c,platform_actor,real_operator,tenant_id,request):
    request=SubscriptionChange.model_validate(request)
    preview=preview_subscription_change(c,platform_actor,tenant_id,request.maximumTier,request.expectedRevision)
    if preview['inputHash']!=request.expectedImpactHash:raise AssistanceConflict('Lifecycle settings changed since preview; review the subscription change again.')
    if preview['affectedEventCount'] and not request.confirmBlockedWorkflows:raise ValueError('Confirm that unavailable strategy workflows will be blocked; their choices are retained.')
    from security_master_schema.access_management import _set_module
    _set_module(c,tenant_id,platform_actor,MODULE,request.maximumTier>0)
    revision=request.expectedRevision+1
    c.execute(m.tenant_lifecycle_subscription.insert().values(tenant_id=tenant_id,revision=revision,previous_revision=request.expectedRevision or None,maximum_tier=request.maximumTier,source='MANUAL',reason=request.reason,actor_id=platform_actor,real_operator_id=real_operator))
    audit(c,platform_actor,tenant_id,'LIFECYCLE_SUBSCRIPTION_CHANGED',dict(before=preview['current']['configuredMaximumTier'],after=request.maximumTier,revision=revision,reason=request.reason,realOperatorId=str(real_operator),blockedEvents=preview['affectedEventCount']))
    return lifecycle_subscription_view(c,tenant_id)
