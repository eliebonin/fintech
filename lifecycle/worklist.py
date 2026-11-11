"""Current lifecycle worklist: read model only; native commands own every effect."""
from collections import defaultdict
from .recording_clock import recording_now
from datetime import datetime,time,timezone
from decimal import Decimal,localcontext
from uuid import UUID
from sqlalchemy import select,func
from security_master_schema import models as m
from security_master_schema.strategy_access import require_strategy_action,strategy_predicate
from security_master_schema.tenant_workspace import resolve_tenant_workspace,require_tenant_action
from security_master_schema.governance_clock import governance_date
from security_master_schema.evidence import evidence_hash
from positions.contracts import ProjectionRequest
from positions.repository import iter_ledger_facts
from positions.allocations import reconstruct_allocations
from trading.allocation_policy import load_allocation_policy
from trading.annotation_snapshots import load_trade_annotations
from .assistance import native_policy_map
from .entitlements import lifecycle_subscription_view,lifecycle_lock,current_selections
from .worklist_contracts import WorklistQuery
from .worklist_repository import candidate_pairs,source_maps


def event_state(day,today,entries,*,known=True,posted=False,prepared=False,stale=False,blocked=False):
    attention='INFORMATION' if day is not None and day>today else 'ACTIONABLE'
    if known and posted and not entries:return 'BOOKED','INFORMATION'
    if not known or blocked:return 'BLOCKED',attention
    if stale or posted and entries:return 'REASSESSMENT',attention
    if prepared:return 'PREPARED',attention
    if day is None:return 'BLOCKED','ACTIONABLE'
    return ('UPCOMING' if day>today else 'DUE' if day==today else 'OVERDUE'),attention


def strategy_options(c,tenant,actor,query='',offset=0,limit=25):
    require_tenant_action(resolve_tenant_workspace(c,tenant,actor,governance_date()),'LIFECYCLE_READ')
    if offset<0 or not 1<=limit<=100:raise ValueError('Invalid strategy page.')
    s=m.strategy
    statement=select(s.c.strategy_id.label('strategyId'),s.c.display_name.label('label')).where(s.c.tenant_id==tenant,strategy_predicate(c,tenant,actor,'LIFECYCLE_READ',s.c.strategy_id))
    if query:statement=statement.where(s.c.display_name.icontains(query,autoescape=True))
    return dict(items=[dict(r) for r in c.execute(statement.order_by(s.c.display_name,s.c.strategy_id).offset(offset).limit(limit)).mappings()],total=c.scalar(select(func.count()).select_from(statement.subquery())),offset=offset,limit=limit)


def _quantities(buckets,currencies):
    amounts=defaultdict(lambda:dict(net=Decimal(0),gross=Decimal(0),entries=0))
    with localcontext() as ctx:
        ctx.prec=512
        for bucket in buckets:
            key=(bucket.key.currency_id,bucket.key.quantity_unit);row=amounts[key]
            row['net']+=bucket.closing_quantity;row['gross']+=abs(bucket.closing_quantity);row['entries']+=1
    return [dict(currency=currencies.get(key[0],'Unknown currency'),unit=key[1],netQuantity=format(value['net'],'f'),grossQuantity=format(value['gross'],'f'),entries=value['entries']) for key,value in sorted(amounts.items(),key=lambda item:str(item[0]))]


def list_worklist(c,tenant,actor,query,*,now=None):
    query=WorklistQuery.model_validate(query)
    require_tenant_action(resolve_tenant_workspace(c,tenant,actor,governance_date()),'LIFECYCLE_READ')
    if query.strategyId:require_strategy_action(c,tenant,actor,'LIFECYCLE_READ',query.strategyId)
    now=now or recording_now(c)
    if now.tzinfo is None or now.utcoffset().total_seconds()!=0:raise ValueError('Worklist evaluation must use UTC.')
    lifecycle_lock(c,tenant)
    subscription=lifecycle_subscription_view(c,tenant)
    result=dict(items=[],total=0,offset=query.offset,limit=query.limit,evaluatedAt=now,fromDate=query.fromDate,toDate=query.toDate,statusCounts={},subscription=subscription,discoveryEventTypes=['BOND_MATURITY'],unavailableReason=None)
    if subscription['maximumTier']<1:
        result['unavailableReason']='Lifecycle notifications require an active Tier1 or higher subscription. Existing booking/history workspaces retain their own access rules.'
        return result
    chosen=current_selections(c,tenant).where(m.strategy_lifecycle_assistance.c.event_type=='BOND_MATURITY',m.strategy_lifecycle_assistance.c.selected_tier>=1,m.strategy_lifecycle_assistance.c.strategy_id.in_(select(m.strategy.c.strategy_id).where(m.strategy.c.tenant_id==tenant,strategy_predicate(c,tenant,actor,'LIFECYCLE_READ',m.strategy.c.strategy_id))))
    if query.strategyId:chosen=chosen.where(m.strategy_lifecycle_assistance.c.strategy_id==query.strategyId)
    if c.execute(chosen.limit(1)).first() is None:
        result['unavailableReason']=('Bond maturity notifications are not enabled for this strategy.' if query.strategyId else 'Bond maturity notifications are not enabled for any strategy you can read.')+' Choose Tier1 or higher under Strategy → Overview → Lifecycle assistance.'
        return result
    pairs=candidate_pairs(c,tenant,actor,query,now)
    if not pairs:return result
    subjects,terms,identifiers,proposals,postings=source_maps(c,tenant,pairs)
    currencies=dict(c.execute(select(m.currency.c.currency_id,m.currency.c.currency_code)).all())
    native=native_policy_map(c,tenant,[r['strategy_id'] for r in pairs])
    by_strategy=defaultdict(list)
    for row in pairs:by_strategy[row['strategy_id']].append(row)
    events=[]
    for strategy,rows in by_strategy.items():
        request=ProjectionRequest(tenant,strategy,now,now)
        relevant={r['instrument_id'] for r in rows};selected_subjects=[subject for subject,parent in subjects.items() if parent in relevant]
        try:
            facts=tuple(iter_ledger_facts(c,request,subject_ids=selected_subjects))
            allocation=load_allocation_policy(c,tenant,strategy)
            annotations=load_trade_annotations(c,tenant,[f.trade_id for f in facts],allocation)
            grouped=defaultdict(list)
            parents={f.trade_id:subjects.get(f.booking.subject_id) for f in facts if f.booking}
            for fact in facts:
                if parents.get(fact.trade_id):grouped[parents[fact.trade_id]].append(fact)
            ledger_error=None
        except (ValueError,LookupError) as exc:
            grouped={};allocation=None;annotations={};ledger_error=str(exc)
        for row in rows:
            identity=row['instrument_id'];day=row['maturity_date'];key=(strategy,identity)
            reasons=[];buckets=[];known=ledger_error is None;event_facts=tuple(grouped.get(identity,[]))
            if ledger_error:reasons.append('Position could not be assessed: '+ledger_error)
            elif event_facts:
                try:buckets=[b for b in reconstruct_allocations(event_facts,request,allocation,annotations).buckets if b.closing_quantity]
                except (ValueError,LookupError) as exc:known=False;reasons.append('Position could not be assessed: '+str(exc))
            history=[p for p in postings.get((strategy,str(identity)),[]) if p['evidence'].get('valueDate')==(day.isoformat() if day else None)]
            posted=next((row for row in history if row['_postingActive']),None)
            pending=[p for p in proposals.get(key,[]) if p['inputs'].get('valueDate')==(day.isoformat() if day else None) and not any(h['proposal_id']==p['proposal_id'] for h in history)]
            proposal=pending[0] if pending else None
            if known and not buckets and not posted:continue
            if day is not None and day<query.fromDate and (not buckets or not query.includeEarlierOverdue):continue
            blocked=False;stale=False;mode=native.get((strategy,'BOND_MATURITY'),dict(mode='REVIEW',revision=0))
            if row['reference_status']!='ACTIVE':blocked=True;reasons.append('The held reference is inactive or retired; review it before processing maturity.')
            if row['selected_tier']>subscription['maximumTier']:blocked=True;reasons.append('Selected assistance exceeds the current subscription; review strategy settings.')
            source=terms.get(identity,[])
            if day is None:blocked=True;reasons.append('An approved maturity date is missing; no date has been assumed.')
            if len(source)!=1:blocked=True;reasons.append('A single current approved bond term set is required.')
            else:
                source=source[0]
                if source['coupon_type'] not in ('FIXED','ZERO') or source['quotation_basis']!='PCT_OF_PAR' or source['redemption_amount_per_par'] is None or source['redemption_amount_per_par']<=0:
                    blocked=True;reasons.append('Automatic principal closure supports plain fixed/zero-coupon percentage-of-par bonds with sourced redemption terms.')
                if day and (source['effective_from']>day or source['effective_to'] and source['effective_to']<day):blocked=True;reasons.append('Current bond terms do not cover contractual maturity.')
            if known and buckets and day:
                for bucket in buckets:
                    for trade_id in bucket.trade_ids:
                        booking=next((f.booking for f in event_facts if f.trade_id==trade_id and f.booking),None)
                        if booking and (booking.product_evidence or {}).get('maturityDate')!=day.isoformat():blocked=True;reasons.append('Booked and current reference maturity differ; reconcile the terms before closing.')
            if proposal:
                proof=proposal['inputs'].get('lifecycleAssistance',{})
                stale=(proposal['policy_revision']!=mode['revision'] or proof.get('subscriptionRevision')!=subscription['revision'] or proof.get('assistanceRevision')!=row['assistance_revision'] or proof.get('entitlementFingerprint')!=subscription['entitlementFingerprint'])
                if len(terms.get(identity,[]))==1 and str(proposal['inputs'].get('termId'))!=str(terms[identity][0]['bond_terms_id']):stale=True
                if set(map(str,proposal['inputs'].get('ledgerEvents',[])))!=set(str(f.event_id) for f in event_facts if day and f.effective_at.date()<=day):stale=True
                if not stale and not blocked and known and buckets and day and day<=now.date() and row['selected_tier']>=2:
                    # Pending work needs the full native fingerprint, not a
                    # hand-maintained subset of economic/profile dependencies.
                    from .bond_service import candidate
                    try:
                        _,fingerprint,_,_=candidate(c,tenant,strategy,identity)
                        stale=fingerprint!=proposal['input_hash']
                    except (ValueError,LookupError) as exc:
                        stale=True;reasons.append('Prepared input reassessment: '+str(exc))
                if stale:reasons.append('Prepared policy, assistance or source evidence changed; prepare and review again.')
                else:reasons.append('Retained preparation exists. The native workflow revalidates current sources before confirmation or approval.')
            if history and not posted:reasons.append('Earlier generated closure is no longer active; any remaining exposure needs fresh handling.')
            if posted and buckets:reasons.append('Closure history exists but exposure remains; reconcile later trades, classifications or corrections.')
            state,attention=event_state(day,now.date(),len(buckets),known=known,posted=bool(posted),prepared=bool(proposal),stale=stale,blocked=blocked)
            if state=='BOOKED':reasons=['Retained maturity closure evidence and no remaining exposure. Payment is not asserted.']
            if not reasons:reasons.append('Sourced maturity event; authoritative pricing, allocation and source checks run in the booking workspace.')
            label='View closure evidence' if state=='BOOKED' else 'Review blocked event' if state in {'BLOCKED','REASSESSMENT'} else 'Handle manually' if row['selected_tier']==1 else 'Review prepared entry' if proposal else 'Open one-click workflow' if row['selected_tier']==3 and mode['mode']=='DIRECT' else 'Prepare for approval' if mode['mode']=='REVIEW' else 'Prepare closing entry'
            href=f'/trades/lifecycle?strategyId={strategy}&instrumentId={identity}' if row['selected_tier']>=2 or state=='BOOKED' else f'/strategies/{strategy}?view=positions'
            events.append(dict(eventKey=evidence_hash(dict(tenantId=tenant,strategyId=strategy,instrumentId=identity,eventType='BOND_MATURITY',maturityDate=day)),strategyId=strategy,strategyName=row['strategy_name'],instrumentId=identity,instrumentName=row['instrument_name'],identifier=next(iter(identifiers.get(identity,[])),None),maturityDate=day,status=state,attention=attention,quantities=_quantities(buckets,currencies) if known else [],remainingEntries=len(buckets) if known else None,selectedTier=row['selected_tier'],maximumTier=subscription['maximumTier'],processingMode=mode['mode'],reasons=list(dict.fromkeys(reasons)),actionLabel=label,actionHref=href,proposalId=proposal['proposal_id'] if proposal else None,postingId=posted['posting_id'] if posted else None,positionAssessed=known))
    if query.attention!='ALL':events=[r for r in events if r['attention']==query.attention]
    counts=defaultdict(int)
    for row in events:counts[row['status']]+=1
    if query.status!='ALL':events=[r for r in events if r['status']==query.status]
    events.sort(key=lambda r:(r['maturityDate'] is not None,r['maturityDate'] or now.date(),r['strategyName'].casefold(),r['instrumentName'].casefold(),r['eventKey']))
    result.update(items=events[query.offset:query.offset+query.limit],total=len(events),statusCounts=dict(counts))
    return result
