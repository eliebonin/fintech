"""Informational schedules only: no trigger evaluation, outcome or financial effects."""
from datetime import date,datetime,time,timezone
from collections import defaultdict
from uuid import UUID
import json
from sqlalchemy import select
from security_master_schema import models as m
from security_master_schema.instrument_terms_schedule import load_terms_schedules
from security_master_schema.instrument_terms_batch import id_chunks
from security_master_schema.errors import RepositoryNotFound
from security_master_schema.evidence import evidence_hash
from security_master_schema.reference_visibility import visible_clause
from security_master_schema.strategy_access import require_strategy_action
from security_master_schema.tenant_workspace import require_tenant_action,resolve_tenant_workspace
from security_master_schema.governance_clock import governance_date
from positions.contracts import ProjectionRequest
from positions.repository import iter_ledger_facts
from positions.allocations import reconstruct_allocations
from trading.allocation_policy import load_allocation_policy
from trading.annotation_snapshots import load_trade_annotations
from .entitlements import lifecycle_lock,lifecycle_subscription_view
from .recording_clock import recording_now
from .worklist_holdings import held_candidates
from .worklist_contracts import WorklistQuery


def information_state(day,now):
    if day is None:return 'SOURCE_UNAVAILABLE','INFORMATION'
    return ('UPCOMING' if day>now.date() else 'SCHEDULED_TODAY' if day==now.date() else 'DATE_PASSED'),'INFORMATION'


def observation_kind(event,first_autocall):
    purpose=event.get('schedule_type','')
    if purpose=='COUPON_OBSERVATION':return 'COUPON_OBSERVATION','NOT_APPLICABLE'
    if purpose=='AUTOCALL_OBSERVATION':
        if first_autocall and event['event_date']<first_autocall:return 'OBSERVATION','BEFORE_FIRST_DATE'
        return 'AUTOCALL_OBSERVATION','ELIGIBLE_DATE' if first_autocall else 'NOT_ASSESSED'
    if purpose=='FINAL_VALUATION' or event.get('event_type')=='FINAL_VALUATION':return 'FINAL_VALUATION','NOT_APPLICABLE'
    return 'OBSERVATION','NOT_APPLICABLE'


INACTIVE_SOURCE_STATES={'CANCELLED','SUPERSEDED','RETIRED','REJECTED','SKIPPED','INACTIVE'}

def _current(row):
    return row.get('status') not in INACTIVE_SOURCE_STATES


def linked_events(facts):
    event_ids={r.get('schedule_event_id') for r in facts.get('conditions',[]) if _current(r)}|{r.get('observation_event_id') for r in facts.get('couponPeriods',[]) if _current(r)}
    schedules={r.get('schedule_id') for key in ('couponProgrammes','componentTerms') for r in facts.get(key,[]) if _current(r)}|{r.get('observation_schedule_id') for r in facts.get('rangeAccrual',[]) if _current(r)}
    event_ids.discard(None);schedules.discard(None)
    return [r for r in facts.get('scheduleEvents',[]) if (r['schedule_event_id'] in event_ids or r['schedule_id'] in schedules) and r.get('event_type','OBSERVATION') in ('OBSERVATION','FIXING','FINAL_VALUATION') and _current(r) and r.get('schedule_status') not in INACTIVE_SOURCE_STATES]


def _layer_notices(layer):
    rows=[];first=layer.economics.get('first_autocall_observation_date')
    for event in linked_events(layer.facts):
        kind,eligibility=observation_kind(event,first)
        rows.append(dict(key=event['schedule_event_id'],kind=kind,day=date.fromisoformat(event['event_date']),paymentDate=event.get('payment_date'),event=event,eligibility=eligibility))
    for kind,field in [('FINAL_VALUATION','final_valuation_date'),('MATURITY','maturity_date')]:
        day=layer.dates.get(field)
        if day and not any(row['kind']==kind and row['day'].isoformat()==day for row in rows):rows.append(dict(key=kind,kind=kind,day=date.fromisoformat(day),paymentDate=None,event=None,eligibility='NOT_APPLICABLE'))
    return rows


def _conditions(layer,event,labels):
    if event is None:return []
    groups=[]
    for group in layer.facts.get('conditions',[]):
        if not _current(group) or group.get('schedule_event_id')!=event['schedule_event_id']:continue
        identity=group['condition_group_id'];barriers=[]
        for row in layer.facts.get('barriers',[]):
            if not _current(row) or row['condition_group_id']!=identity:continue
            barriers.append(dict(underlyingName=labels.get(row.get('underlying_reference_node_id')),comparison=row['comparison_operator'],basis=row['level_reference_type'],lowerLevel=row.get('lower_level_value'),upperLevel=row.get('upper_level_value'),measure=row.get('underlying_measure'),lowerInclusive=row.get('lower_bound_inclusive'),upperInclusive=row.get('upper_bound_inclusive')))
        actions=[row['action_type']+' · '+row['target_scope'] for row in layer.facts.get('actions',[]) if row['condition_group_id']==identity and _current(row)]
        groups.append(dict(groupCode=group['group_code'],combination=group['logical_operator'],aggregation=group['underlying_aggregation'],scope=group['underlying_scope'],sourceStatus=group['status'],barriers=barriers,actions=actions))
    return groups


def _structured_views(c,tenant,actor,query,now,subscription,*,event_key=None):
    from .worklist import _quantities
    # Search observed references only after their visibility is established;
    # never narrow root candidates by a name that belongs to a child contract.
    candidates=query.model_copy(update={'q':''})
    pairs=held_candidates(c,tenant,actor,candidates,now,instrument_type='STRUCTURED_PRODUCT',event_type='STRUCTURED_OBSERVATION')+held_candidates(c,tenant,actor,candidates,now,instrument_type='SWAP',event_type='STRUCTURED_OBSERVATION')
    if not pairs:return []
    roots={r['instrument_id'] for r in pairs};subjects={identity:identity for identity in roots}
    for chunk in id_chunks(roots):
        subjects.update(dict(c.execute(select(m.listing.c.listing_node_id,m.listing.c.instrument_node_id).where(m.listing.c.instrument_node_id.in_(chunk),visible_clause(m.listing.c.listing_node_id,tenant))).all()))
    currencies=dict(c.execute(select(m.currency.c.currency_id,m.currency.c.currency_code)).all())
    # Batch all source tables over the scoped roots before per-position work.
    source_cache=load_terms_schedules(c,tenant,roots)
    schedule_ids={UUID(event['schedule_id']) for view in source_cache.values() if view for layer in view.layers for event in layer.facts.get('scheduleEvents',[])}
    states={}
    for chunk in id_chunks(schedule_ids):
        states.update({str(identity):state for identity,state in c.execute(select(m.schedule.c.schedule_id,m.schedule.c.status).where(m.schedule.c.schedule_id.in_(chunk)))})
    for view in source_cache.values():
        if view:
            for layer in view.layers:
                for event in layer.facts.get('scheduleEvents',[]):event['schedule_status']=states.get(event['schedule_id'])
    identifiers=defaultdict(list)
    def search_labels(row,projection):
        labels={str(row['instrument_id']):row['instrument_name']}
        if projection:
            relevant_ids={layer.instrumentId for layer in projection.layers if layer.instrumentType=='STRUCTURED_PRODUCT'}
            relevant_ids.update(rule.get('underlying_reference_node_id') for layer in projection.layers if layer.instrumentType=='STRUCTURED_PRODUCT' for rule in layer.facts.get('barriers',[]))
            labels.update({key:value for key,value in projection.referenceLabels.items() if key in relevant_ids})
        return labels
    # Preserve the existing historical-identifier semantics. Both canonical and
    # visible listing identifiers are fetched once per bounded ID chunk.
    if query.q.strip():
        visible_ids={UUID(key) for row in pairs for key in search_labels(row,source_cache[row['instrument_id']])}
        identifier_owners={identity:identity for identity in visible_ids}
        for chunk in id_chunks(visible_ids):
            for listing,owner in c.execute(select(m.listing.c.listing_node_id,m.listing.c.instrument_node_id).where(m.listing.c.instrument_node_id.in_(chunk),visible_clause(m.listing.c.listing_node_id,tenant))):identifier_owners[listing]=owner
        for chunk in id_chunks(identifier_owners):
            for identity,value in c.execute(select(m.financial_reference_identifier.c.reference_node_id,m.financial_reference_identifier.c.identifier_value).where(m.financial_reference_identifier.c.reference_node_id.in_(chunk))):identifiers[str(identifier_owners[identity])].append(value)
    def search_match(row,projection):
        needle=query.q.strip().casefold()
        if not needle:return True
        labels=search_labels(row,projection)
        return any(needle in value.casefold() for value in [*labels.keys(),*labels.values(),*[v for key in labels for v in identifiers[key]]])
    by_strategy=defaultdict(list)
    for row in pairs:by_strategy[row['strategy_id']].append(row)
    result=[]
    for strategy,rows in by_strategy.items():
        request=ProjectionRequest(tenant,strategy,now,now);relevant={r['instrument_id'] for r in rows}
        grouped=defaultdict(list);originals={};error=None
        try:
            facts=tuple(iter_ledger_facts(c,request,subject_ids=[s for s,i in subjects.items() if i in relevant]))
            allocation=load_allocation_policy(c,tenant,strategy)
            annotations=load_trade_annotations(c,tenant,[f.trade_id for f in facts],allocation)
            parents={f.trade_id:subjects[f.booking.subject_id] for f in facts if f.booking and f.booking.subject_id in subjects}
            for fact in facts:
                if fact.trade_id in parents:grouped[parents[fact.trade_id]].append(fact)
            for identity,payload in c.execute(select(m.trade_lifecycle_event.c.trade_id,m.trade_lifecycle_event.c.event_payload).where(m.trade_lifecycle_event.c.trade_id.in_(parents),m.trade_lifecycle_event.c.event_type=='BOOKED',m.trade_lifecycle_event.c.recorded_at_utc<=now)):originals[identity]=json.loads(payload)
        except (ValueError,LookupError) as exc:error='Position evidence is unavailable; no quantity has been assumed.'
        for row in rows:
            root=row['instrument_id'];projection=None;source_issue=None
            projection=source_cache[root]
            if projection is None:source_issue='Current approved schedule/dependency information is unavailable. No event or outcome has been inferred.'
            event_facts=tuple(grouped.get(root,[]))
            if projection and row['instrument_type']=='SWAP':
                current=projection.layers[0].economics.get('performanceReferenceId')
                retained={originals.get(f.trade_id,{}).get('economics',{}).get('terms',{}).get('swapDetails',{}).get('genericTerms',{}).get('performanceReferenceId') for f in event_facts if f.booking}
                retained.discard(None)
                if retained and retained!={current}:source_issue='Current and original booked swap performance references differ; structured-schedule relevance is not assessed.'
            layers=[layer for layer in projection.layers if layer.instrumentType=='STRUCTURED_PRODUCT'] if projection else []
            if not layers and not source_issue:continue  # Rate/index/bond swaps do not become structured notices.
            if not search_match(row,projection):continue
            if row['reference_status']!='ACTIVE':source_issue='Held reference is inactive or retired; current schedule information is unavailable.'
            notices=[]
            if source_issue:notices=[(None,dict(key='SOURCE_UNAVAILABLE',kind='SOURCE_UNAVAILABLE',day=None,paymentDate=None,event=None,eligibility='NOT_ASSESSED'))]
            else:
                for layer in layers:
                    entries=_layer_notices(layer)
                    if not entries:entries=[dict(key='SOURCE_UNAVAILABLE',kind='SOURCE_UNAVAILABLE',day=None,paymentDate=None,event=None,eligibility='NOT_ASSESSED')]
                    for entry in entries:notices.append((layer,entry))
            fingerprint=evidence_hash(projection.model_dump() if projection else dict(rootId=root,source='UNAVAILABLE'))
            for layer,notice in notices:
                observed=UUID(layer.instrumentId) if layer else None
                key='STRUCTURED_OBSERVATION:'+str(strategy)+':'+str(root)+':'+str(observed or 'UNASSESSED')+':'+str(notice['key'])
                if event_key is not None and key!=event_key:continue
                day=notice['day']
                if day is not None and not query.fromDate<=day<=query.toDate:continue
                if row['instrument_type']=='SWAP' and projection and day and day>now.date():
                    end=projection.layers[0].dates.get('maturity_date')
                    if end and day>date.fromisoformat(end):continue
                cutoff=min(now,datetime.combine(day,time.max,timezone.utc)) if day else now
                known=error is None;buckets=[];reasons=[]
                if error:reasons.append(error)
                else:
                    try:buckets=[b for b in reconstruct_allocations(event_facts,ProjectionRequest(tenant,strategy,cutoff,now),allocation,annotations).buckets if b.closing_quantity]
                    except (ValueError,LookupError):known=False;reasons.append('Position evidence is unavailable; no quantity has been assumed.')
                if known and not buckets:continue
                if source_issue:reasons.append(source_issue)
                if row['selected_tier']>subscription['maximumTier']:reasons.append('Selected notifications exceed the current subscription.')
                if notice['eligibility']=='BEFORE_FIRST_DATE':reasons.append('This observation precedes the sourced first-autocall eligibility date.')
                if notice['eligibility']=='NOT_ASSESSED' and notice['kind']=='AUTOCALL_OBSERVATION':reasons.append('Autocall schedule exists, but first-autocall eligibility is not recorded.')
                reasons.append('Information only. No fixing, condition result, coupon entitlement, autocall, payment or financial closure is assessed.')
                if row['instrument_type']=='SWAP':reasons.append('Quantities belong to the held swap, not the observed structured product. No swap termination is inferred.')
                if projection and any(g.get('observation_style')=='CONTINUOUS' for g in (layer.facts.get('conditions',[]) if layer else [])):reasons.append('Continuous barriers are source terms, not daily observations generated by this feature.')
                status,attention=information_state(day,now)
                if source_issue or not known or notice['kind']=='SOURCE_UNAVAILABLE':status='SOURCE_UNAVAILABLE'
                quantities=_quantities(buckets,currencies) if known else []
                event=dict(eventKey=key,eventType='STRUCTURED_OBSERVATION',instrumentType=row['instrument_type'],strategyId=strategy,strategyName=row['strategy_name'],instrumentId=root,instrumentName=row['instrument_name'],identifier=None,eventDate=day,milestoneKind=notice['kind'],sourceFingerprint=fingerprint,maturityDate=None,relatedInstrumentId=observed if observed!=root else None,relatedInstrumentName=layer.canonicalName if layer and observed!=root else None,status=status,attention=attention,quantities=quantities,remainingEntries=len(buckets) if known else None,selectedTier=row['selected_tier'],maximumTier=subscription['maximumTier'],processingMode='MANUAL',reasons=reasons,actionLabel='Inspect schedule',actionHref='/instruments/'+str(root),positionAssessed=known)
                view=None
                if event_key is not None:view=dict(eventKey=key,strategyId=strategy,instrumentId=root,instrumentType=row['instrument_type'],instrumentName=row['instrument_name'],observedInstrumentId=observed,observedInstrumentName=layer.canonicalName if layer else None,relation=layer.relation if layer else None,sourceFingerprint=fingerprint,evaluatedAt=now,noticeKind=notice['kind'],eventDate=day,conditionalPaymentDate=notice['paymentDate'],firstAutocallDate=layer.economics.get('first_autocall_observation_date') if layer else None,autocallEligibility=notice['eligibility'],issuer=layer.issuer if layer else None,currency=layer.currency if layer else None,definitionVersion=layer.version if layer else None,termsVersion=layer.economics.get('version_no') if layer else None,scheduleEventId=notice['event']['schedule_event_id'] if notice['event'] else None,sourceEventStatus=notice['event'].get('status') if notice['event'] else None,positionDate=cutoff.date(),positionAssessed=known,quantities=quantities,conditions=_conditions(layer,notice['event'],projection.referenceLabels) if layer and projection else [],reasons=reasons)
                result.append((event,view))
    return result


def structured_events(c,tenant,actor,query,now,subscription):
    return [event for event,view in _structured_views(c,tenant,actor,query,now,subscription)]


def inspect_structured(c,tenant,actor,strategy,instrument,event_key):
    require_tenant_action(resolve_tenant_workspace(c,tenant,actor,governance_date()),'LIFECYCLE_READ')
    require_strategy_action(c,tenant,actor,'LIFECYCLE_READ',strategy)
    lifecycle_lock(c,tenant);subscription=lifecycle_subscription_view(c,tenant)
    if subscription['maximumTier']<1:raise LookupError('Structured schedule notifications are unavailable.')
    query=WorklistQuery(fromDate=date.min,toDate=date.max,strategyId=strategy,instrumentId=instrument,eventType='STRUCTURED_OBSERVATION')
    for event,view in _structured_views(c,tenant,actor,query,recording_now(c),subscription,event_key=event_key):
        if event['eventKey']==event_key:return view
    raise LookupError('Schedule information is unavailable or changed; refresh Lifecycle.')
