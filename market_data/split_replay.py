"""Reviewed unit-change evidence, separate from unreviewed provider ingestion.

An append-only decision freezes one source version. Changing a child date/effect
invalidates eligibility instead of silently changing historical financial inputs.
The caller owns its transaction. No source/trade record is mutated here.
"""
from datetime import datetime, time, timezone, date
from decimal import Decimal, localcontext, Inexact, InvalidOperation
from zoneinfo import ZoneInfo
from uuid import UUID
from sqlalchemy import select, func
from security_master_schema import models as m
from positions.contracts import SplitEvent
from positions.reconstruction import canonical, digest, utc


def subject_parents(c,subjects):
    parents={r.listing_node_id:(r.instrument_node_id,r.timezone_name) for r in c.execute(
        select(m.listing.c.listing_node_id,m.listing.c.instrument_node_id,m.market_venue.c.timezone_name)
        .select_from(m.listing.outerjoin(m.market_venue)).where(m.listing.c.listing_node_id.in_(subjects)))}
    parents.update({identity:(identity,None) for identity in c.scalars(select(m.instrument.c.instrument_node_id)
        .where(m.instrument.c.instrument_node_id.in_(set(subjects)-parents.keys())))})
    return parents


def action_query(parents,information_cutoff,scope_tenant):
    """Shared scope predicate for current and historical action evidence."""
    table=m.corporate_action
    query=select(table).where(table.c.affected_instrument_node_id.in_(parents),
        table.c.recorded_at_utc<=information_cutoff)
    if scope_tenant is not ...:
        payload=m.source_payload; source=m.integration_source_system; node=m.reference_node_scope
        query=query.select_from(table.outerjoin(node,node.c.reference_node_id==table.c.affected_instrument_node_id)
            .outerjoin(payload,table.c.source_payload_id==payload.c.source_payload_id)
            .outerjoin(source,payload.c.integration_source_system_id==source.c.integration_source_system_id))
        for owner in (node.c.owner_tenant_id,payload.c.tenant_id,source.c.tenant_id):
            query=query.where(owner.is_(None) if scope_tenant is None else (owner.is_(None)|(owner==scope_tenant)))
    return query


def current_actions(c,parents,information_cutoff,*,scope_tenant=...):
    """Latest visible source version, including cancellations before filtering.

    Distinct provider identities remain distinct; conflicts fail in positions.
    """
    table=m.corporate_action; latest={}
    query=action_query(parents,information_cutoff,scope_tenant)
    rows=c.execute(query.order_by(table.c.sequence_no,
            table.c.recorded_at_utc,table.c.corporate_action_id)).mappings()
    for row in rows:
        key=(row['affected_instrument_node_id'],row['external_event_reference'] or row['corporate_action_id'])
        latest[key]=dict(row)
    return tuple(latest.values())


def historical_guard_ids(c,current,information_cutoff,reviewed_events,scope_tenant):
    """Unreviewed source corrections cannot erase a reviewed unit change.

    A changed date/type or cancellation is not an economic reversal. Retain
    the historical safety check until a valid reviewed successor explains it.
    Apply the identical ownership predicate, not a cross-tenant history search.
    """
    table=m.corporate_action; decisions=m.corporate_action_replay_decision
    by_key={(r['affected_instrument_node_id'],r['external_event_reference'] or r['corporate_action_id']):r for r in current}
    trusted={e.action_id for e in reviewed_events}; result=set()
    query=action_query({r['affected_instrument_node_id'] for r in current},information_cutoff,scope_tenant)
    query=query.join(decisions,decisions.c.corporate_action_id==table.c.corporate_action_id).where(
        decisions.c.status=='APPROVED',decisions.c.recorded_at_utc<=information_cutoff,
        table.c.event_type.in_(['STOCK_SPLIT','BONUS_ISSUE'])).distinct()
    for row in c.execute(query).mappings():
        key=(row['affected_instrument_node_id'],row['external_event_reference'] or row['corporate_action_id'])
        latest=by_key.get(key)
        if latest and latest['corporate_action_id'] not in trusted:
            result.add(row['corporate_action_id'])
    return result


def source_snapshot(c,action):
    identity=action['corporate_action_id']
    dates=[dict(r) for r in c.execute(select(m.corporate_action_date).where(
        m.corporate_action_date.c.corporate_action_id==identity)
        .order_by(m.corporate_action_date.c.corporate_action_date_id)).mappings()]
    effects=[dict(r) for r in c.execute(select(m.corporate_action_effect).where(
        m.corporate_action_effect.c.corporate_action_id==identity)
        .order_by(m.corporate_action_effect.c.corporate_action_effect_id)).mappings()]
    scope=None
    if action['source_payload_id']:
        scope=c.execute(select(m.source_payload.c.tenant_id.label('payloadTenantId'),
            m.source_payload.c.payload_sha256.label('payloadSha256'),
            m.integration_source_system.c.tenant_id.label('sourceTenantId'),
            m.integration_source_system.c.integration_source_system_id.label('sourceSystemId'))
            .select_from(m.source_payload.join(m.integration_source_system))
            .where(m.source_payload.c.source_payload_id==action['source_payload_id'])).mappings().one()
    return canonical(dict(action=dict(action),dates=dates,effects=effects,sourceScope=dict(scope) if scope else None))


def require_reviewer(c,actor):
    from security_master_schema.tenant_workspace import resolve_platform_role
    now=datetime.now(timezone.utc)
    if (resolve_platform_role(c,actor,now.date())!='PLATFORM_ADMIN' or
        c.scalar(select(m.user_account.c.status).where(m.user_account.c.user_account_id==actor))!='ACTIVE'):
        raise PermissionError('Active platform reference administrator required')


def reviewed_payload(snapshot,review):
    action=snapshot['action']; dates=snapshot['dates']; effects=snapshot['effects']
    if action['event_type'] not in {'STOCK_SPLIT','BONUS_ISSUE'} or action['status'] not in {'ANNOUNCED','CONFIRMED','COMPLETED'}:
        raise ValueError('Supported active share-ratio source event required')
    if (len(effects)!=1 or effects[0]['effect_type']!='QUANTITY_CHANGE' or
        effects[0]['target_reference_node_id']!=action['affected_instrument_node_id'] or
        effects[0]['cash_amount'] is not None or effects[0]['currency_id'] is not None or effects[0]['rounding_rule'] is not None):
        raise ValueError('One unchanged-security quantity effect without other economic effects required')
    ex=[row for row in dates if row['date_role']=='EX']
    if len(ex)!=1 or not ex[0]['date_value'] or not ex[0]['timezone_name']:
        raise ValueError('Unique explicit ex-date and source timezone required')
    refs=review.get('sourceReferences')
    if not isinstance(refs,list) or not refs or any(not isinstance(v,str) or not v.strip() for v in refs):
        raise ValueError('Reviewed source references required')
    if not isinstance(review.get('reviewReason'),str) or not review['reviewReason'].strip():
        raise ValueError('Explicit source and entitlement review reason required')
    if review.get('entitlementScope')!='BASIC_RATIO_ONLY' or not isinstance(review.get('wholeSharesOnly'),bool):
        raise ValueError('Explicit basic-ratio entitlement and fraction policy required')
    try:
        with localcontext() as context:
            context.prec=512; context.traps[Inexact]=True
            if any(isinstance(review.get(k),(float,bool)) for k in ('numerator','denominator')):
                raise ValueError('Exact ratio values required')
            numerator=Decimal(review['numerator']); denominator=Decimal(review['denominator'])
            if not numerator.is_finite() or not denominator.is_finite() or numerator<=0 or denominator<=0:
                raise ValueError('Positive finite ratio values required')
            ratio=numerator/denominator
            if ratio!=Decimal(effects[0]['ratio']): raise ValueError('Reviewed ratio disagrees with source effect')
    except (KeyError,TypeError,InvalidOperation,Inexact) as exc:
        raise ValueError('Exact supported source ratio required; rounded fractions cannot be replayed') from exc
    day=date.fromisoformat(ex[0]['date_value']); zone=ZoneInfo(ex[0]['timezone_name'])
    if review.get('boundaryConvention')=='EX_DATE_START' and ex[0]['timestamp_value_utc'] is None:
        instant=datetime.combine(day,time.min,zone).astimezone(timezone.utc)
    elif review.get('boundaryConvention')=='EX_TIMESTAMP' and ex[0]['timestamp_value_utc']:
        instant=datetime.fromisoformat(ex[0]['timestamp_value_utc']); utc(instant)
        if instant.astimezone(zone).date()!=day: raise ValueError('Source timestamp/ex-date disagree')
    else: raise ValueError('Explicit source-compatible unit-change boundary required')
    return canonical(dict(schemaVersion=1,sourceSnapshot=snapshot,sourceSnapshotHash=digest(snapshot),
        review=review,ratio=ratio,effectiveAt=instant,effectiveDate=day,wholeSharesOnly=review['wholeSharesOnly']))


def publish_split_decision(c,actor,action_id,review):
    require_reviewer(c,actor)
    action=c.execute(select(m.corporate_action).where(m.corporate_action.c.corporate_action_id==action_id)
        .with_for_update()).mappings().one_or_none()
    if action is None: raise ValueError('Known source action required')
    c.execute(select(func.pg_advisory_xact_lock(int.from_bytes(action_id.bytes[:8],'big',signed=True))))
    latest=current_actions(c,{action['affected_instrument_node_id']},datetime.now(timezone.utc))
    if action_id not in {r['corporate_action_id'] for r in latest}: raise ValueError('Review the current source version')
    payload=reviewed_payload(source_snapshot(c,action),review)
    table=m.corporate_action_replay_decision
    prior=c.execute(select(table).where(table.c.corporate_action_id==action_id)
        .order_by(table.c.recorded_at_utc.desc(),table.c.replay_decision_id.desc()).limit(1)).mappings().one_or_none()
    if prior and prior['status']=='APPROVED' and prior['decision_payload']==payload: return prior['replay_decision_id']
    return c.scalar(table.insert().values(corporate_action_id=action_id,reviewed_by_user_account_id=actor,
        status='APPROVED',decision_payload=payload).returning(table.c.replay_decision_id))


def revoke_split_decision(c,actor,action_id,reason):
    require_reviewer(c,actor)
    if not isinstance(reason,str) or not reason.strip(): raise ValueError('Revocation reason required')
    c.execute(select(m.corporate_action).where(m.corporate_action.c.corporate_action_id==action_id).with_for_update()).one()
    table=m.corporate_action_replay_decision
    return c.scalar(table.insert().values(corporate_action_id=action_id,reviewed_by_user_account_id=actor,
        status='REVOKED',decision_payload={'reason':reason}).returning(table.c.replay_decision_id))


def load_reviewed_splits(c,subjects,information_cutoff,*,tenant_id=None):
    utc(information_cutoff)
    parents=subject_parents(c,subjects)
    actions=current_actions(c,{parent for parent,_ in parents.values()},information_cutoff,scope_tenant=tenant_id)
    eligible={row['corporate_action_id']:row for row in actions if row['status']!='CANCELLED'
        and row['event_type'] in {'STOCK_SPLIT','BONUS_ISSUE'}}
    if not eligible: return ()
    table=m.corporate_action_replay_decision; decisions={}
    for row in c.execute(select(table).where(table.c.corporate_action_id.in_(eligible),
        table.c.recorded_at_utc<=information_cutoff).order_by(table.c.recorded_at_utc,table.c.replay_decision_id)).mappings():
        decisions[row['corporate_action_id']]=row
    events=[]
    for identity,action in eligible.items():
        decision=decisions.get(identity)
        if not decision or decision['status']!='APPROVED': continue
        payload=decision['decision_payload']; snapshot=source_snapshot(c,action)
        if payload.get('sourceSnapshotHash')!=digest(snapshot): continue
        # Verify the immutable record too; incomplete manual DB inserts never
        # turn into a permissive action whitelist.
        try:
            if reviewed_payload(snapshot,payload['review'])!=payload: continue
        except (KeyError,ValueError,TypeError):
            continue
        for subject,(parent,_) in parents.items():
            if parent!=action['affected_instrument_node_id']: continue
            events.append(SplitEvent(identity,decision['replay_decision_id'],subject,
                datetime.fromisoformat(payload['effectiveAt']),date.fromisoformat(payload['effectiveDate']),
                decision['recorded_at_utc'],Decimal(payload['ratio']),payload['wholeSharesOnly'],
                payload|{'reviewerId':str(decision['reviewed_by_user_account_id'])}))
    return tuple(events)
