"""Governed historical source continuity is not inferred from today's ticker."""
from datetime import date
from sqlalchemy import select,exists
from security_master_schema import models as m
from security_master_schema.tenant_workspace import resolve_tenant_workspace
from .storage import insert_returning


def require_admin(c,tenant_id,actor_id):
    workspace=resolve_tenant_workspace(c,tenant_id,actor_id,date.today())
    if workspace.membership_role!='TENANT_ADMIN' or 'MARKET_DATA' not in workspace.module_codes:
        raise PermissionError('An active MARKET_DATA tenant administrator is required')


def history_status(c,mapping_id,start,end):
    review=m.market_data_mapping_history_review
    newer=review.alias('newer_history_review')
    rows=c.execute(select(review).where(review.c.mapping_id==mapping_id,
        review.c.market_from<=end,review.c.market_to>=start,
        ~exists(select(1).select_from(newer).where(newer.c.supersedes_review_id==review.c.review_id))).order_by(review.c.market_from)).mappings().all()
    if any(r['decision']=='REJECTED' for r in rows):
        return 'REJECTED'
    cursor=start
    from datetime import timedelta
    for r in rows:
        if r['market_from']>cursor:
            break
        if r['market_to']>=end:
            return 'REVIEWED'
        cursor=max(cursor,r['market_to']+timedelta(days=1))
    return 'REVIEW_REQUIRED'


def review_history(c,mapping_id,tenant_id,actor_id,start,end,decision,evidence,*,supersedes=None):
    require_admin(c,tenant_id,actor_id)
    if decision not in {'APPROVED','REJECTED'} or end<start or not evidence.strip():
        raise ValueError('Ordered dates, controlled decision and nonblank evidence required')
    mapping=c.execute(select(m.external_object_mapping).where(
        m.external_object_mapping.c.external_object_mapping_id==mapping_id).with_for_update()).mappings().one()
    profile=c.execute(select(m.dataset_access_profile).where(
        m.dataset_access_profile.c.external_id_namespace_id==mapping['external_id_namespace_id'],
        m.dataset_access_profile.c.permitted_tenant_id==tenant_id,
        m.dataset_access_profile.c.status=='ACTIVE')).mappings().one_or_none()
    if not profile:
        raise PermissionError('Mapping is outside the reviewed tenant dataset scope')
    review=m.market_data_mapping_history_review
    newer=review.alias('newer_review_check')
    if supersedes is not None:
        previous=c.execute(select(review).where(review.c.review_id==supersedes,
            ~exists(select(1).select_from(newer).where(newer.c.supersedes_review_id==review.c.review_id)))).mappings().one_or_none()
        if not previous or previous['mapping_id']!=mapping_id or previous['market_from']!=start or previous['market_to']!=end:
            raise ValueError('Review predecessor must be current with the same mapping/period')
    if c.scalar(select(review.c.review_id).where(review.c.mapping_id==mapping_id,
        review.c.market_from<=end,review.c.market_to>=start,
        review.c.review_id.is_distinct_from(supersedes),
        ~exists(select(1).select_from(newer).where(newer.c.supersedes_review_id==review.c.review_id))).limit(1)):
        raise ValueError('Historical review periods overlap')
    return insert_returning(c,review,'review_id',mapping_id=mapping_id,tenant_id=tenant_id,
        actor_id=actor_id,market_from=start,market_to=end,decision=decision,evidence_reference=evidence.strip(),supersedes_review_id=supersedes)
