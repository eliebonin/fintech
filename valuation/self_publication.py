"""Audited continuity exception: never a waiver of financial or amendment checks."""
from datetime import datetime,timezone
from sqlalchemy import select
from security_master_schema import access_management as access,models as m
from security_master_schema.strategy_access import require_strategy_action
from . import tables as t
from .review_authority import batch_operator_lineage

def policy_active(policy,now=None):
    now=now or datetime.now(timezone.utc)
    return bool(policy and policy['enabled'] and (policy['valid_until'] is None or policy['valid_until']>now))

def latest_policy(c,tenant):
    return c.execute(select(t.publication_policy).where(t.publication_policy.c.tenant_id==tenant)
        .order_by(t.publication_policy.c.revision.desc()).limit(1)).mappings().one_or_none()

def policy_view(c,tenant):
    policy=latest_policy(c,tenant)
    return {'enabled':bool(policy and policy['enabled']),'active':policy_active(policy),
        'validUntil':policy['valid_until'].isoformat() if policy and policy['valid_until'] else None,
        'revision':policy['revision'] if policy else 0,'reason':policy['reason'] if policy else ''}

def change_policy(c,tenant,actor,payload,real_operator_id=None):
    access.require_admin(c,tenant,actor);access.lock_tenant(c,tenant)
    previous=latest_policy(c,tenant);revision=previous['revision'] if previous else 0
    if revision!=payload.expectedRevision:raise access.AccessVersionConflict('Publication policy changed. Reload before saving.')
    if payload.enabled and payload.validUntil and payload.validUntil<=datetime.now(timezone.utc):raise ValueError('Temporary cover expiry must be in the future')
    c.execute(t.publication_policy.insert().values(tenant_id=tenant,revision=revision+1,enabled=payload.enabled,
        valid_until=payload.validUntil,reason=payload.reason,updated_by=actor))
    access.audit(c,real_operator_id or actor,tenant,'VALUATION_PUBLICATION_POLICY_CHANGED',
        {'enabled':payload.enabled,'revision':revision+1,'validUntil':payload.validUntil.isoformat() if payload.validUntil else None,
         'reason':payload.reason,'selectedActorId':str(actor),'previousRevision':revision})
    return policy_view(c,tenant)

def authorize_self_publication(c,tenant,header,actor,real_operator_id=None,*,lock=False):
    if lock:access.lock_tenant(c,tenant)
    policy=latest_policy(c,tenant)
    if not policy_active(policy):raise PermissionError('Tenant self-publication is disabled or expired')
    operator=real_operator_id or actor
    # A selected test identity cannot manufacture this exception for its real operator.
    for identity in {actor,operator}:
        for action in ('VALUATION_REVIEW','VALUATION_SELF_PUBLISH'):
            require_strategy_action(c,tenant,identity,action,header['strategy_id'])
    lineage=batch_operator_lineage(c,tenant,header['batch_id'])
    if not lineage.complete:raise PermissionError('Complete real-operator lineage is required; recalculate before self-publication')
    return {'reviewMode':'SELF_REVIEWED','permission':'VALUATION_SELF_PUBLISH','policyRevision':policy['revision'],
        'policyValidUntil':policy['valid_until'].isoformat() if policy['valid_until'] else None,
        'contributorOperatorIds':sorted(map(str,lineage.operators))}

def publication_authority(c,tenant,header,actor,real_operator_id=None):
    operator=real_operator_id or actor
    try:lineage=batch_operator_lineage(c,tenant,header['batch_id'])
    except (ValueError,KeyError,TypeError):return {'requiresSelfReview':True,'canSelfPublish':False,'unavailableReason':'Operator lineage is incomplete; recalculate before publication.'}
    requires=actor==header['staged_by'] or operator in lineage.operators
    try:authorize_self_publication(c,tenant,header,actor,operator)
    except (PermissionError,ValueError) as exc:return {'requiresSelfReview':requires,'canSelfPublish':False,'unavailableReason':str(exc)}
    return {'requiresSelfReview':requires,'canSelfPublish':True}
