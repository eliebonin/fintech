"""Read-only futures milestones; no assumed expiry, notice, settlement or cash."""
from datetime import date,datetime,timezone

from collections import defaultdict
from sqlalchemy import select
from security_master_schema import models as m
from security_master_schema.reference_visibility import visible_clause
from security_master_schema.strategy_access import require_strategy_action
from security_master_schema.tenant_workspace import require_tenant_action,resolve_tenant_workspace
from security_master_schema.governance_clock import governance_date
from security_master_schema.booking_conventions import FutureConvention
from security_master_schema.evidence import evidence_hash
from positions.contracts import ProjectionRequest
from positions.repository import iter_ledger_facts
from positions.allocations import reconstruct_allocations
from trading.allocation_policy import load_allocation_policy
from trading.annotation_snapshots import load_trade_annotations
from .entitlements import lifecycle_subscription_view,lifecycle_lock
from .recording_clock import recording_now
from .worklist_contracts import WorklistQuery
from .worklist_holdings import held_candidates,milestone_state


def contract_milestones(convention,expiry_date):
    result=[]
    if convention.get('lastTradingAtUtc'):
        stamp=datetime.fromisoformat(convention['lastTradingAtUtc'].replace('Z','+00:00')).astimezone(timezone.utc)
        result.append(dict(kind='LAST_TRADE',date=stamp.date(),atUtc=stamp))
    if expiry_date:result.append(dict(kind='EXPIRY',date=expiry_date,atUtc=None))
    for kind,key in [('FINAL_SETTLEMENT','finalSettlementDate'),('DELIVERY_START','deliveryStartDate'),('DELIVERY_END','deliveryEndDate')]:
        if kind.startswith('DELIVERY') and convention.get('settlementMethod')!='PHYSICAL':continue
        if convention.get(key):result.append(dict(kind=kind,date=date.fromisoformat(convention[key]),atUtc=None))
    return result






def candidate_futures(c,tenant,actor,query,now):
    return held_candidates(c,tenant,actor,query,now,instrument_type='FUTURE',event_type='FUTURE_EXPIRY')

def _future_views(c,tenant,actor,query,now,subscription):
    from .worklist import _quantities
    pairs=candidate_futures(c,tenant,actor,query,now)
    if not pairs:return []
    ids={r['instrument_id'] for r in pairs}
    subjects={i:i for i in ids}
    subjects.update(dict(c.execute(select(m.listing.c.listing_node_id,m.listing.c.instrument_node_id).where(m.listing.c.instrument_node_id.in_(ids),visible_clause(m.listing.c.listing_node_id,tenant))).all()))
    dates={r['instrument_node_id']:dict(r) for r in c.execute(select(m.instrument_dates).where(m.instrument_dates.c.instrument_node_id.in_(ids))).mappings()}
    future_terms={r['instrument_node_id']:dict(r) for r in c.execute(select(m.future_terms).where(m.future_terms.c.instrument_node_id.in_(ids))).mappings()}
    conventions={}
    for r in c.execute(select(m.instrument_booking_convention).where(m.instrument_booking_convention.c.instrument_node_id.in_(ids),m.instrument_booking_convention.c.kind=='FUTURE',m.instrument_booking_convention.c.effective_from<=now.date(),m.instrument_booking_convention.c.approved_at_utc<=now).order_by(m.instrument_booking_convention.c.effective_from.desc(),m.instrument_booking_convention.c.version_no.desc())).mappings():conventions.setdefault(r['instrument_node_id'],dict(r))
    currencies=dict(c.execute(select(m.currency.c.currency_id,m.currency.c.currency_code)).all())
    family_node=m.financial_reference_node.alias('future_family_node')
    families={r['future_family_id']:r['canonical_name'] for r in c.execute(select(m.future_family.c.future_family_id,family_node.c.canonical_name).join(family_node,family_node.c.reference_node_id==m.future_family.c.family_node_id).where(m.future_family.c.future_family_id.in_([r['future_family_id'] for r in future_terms.values()]),visible_clause(family_node.c.reference_node_id,tenant))).mappings()}
    by_strategy=defaultdict(list)
    for row in pairs:by_strategy[row['strategy_id']].append(row)
    result=[]
    for strategy,rows in by_strategy.items():
        request=ProjectionRequest(tenant,strategy,now,now)
        relevant={r['instrument_id'] for r in rows};grouped=defaultdict(list);ledger_error=None
        try:
            facts=tuple(iter_ledger_facts(c,request,subject_ids=[s for s,i in subjects.items() if i in relevant]))
            allocation=load_allocation_policy(c,tenant,strategy)
            annotations=load_trade_annotations(c,tenant,[f.trade_id for f in facts],allocation)
            parents={f.trade_id:subjects[f.booking.subject_id] for f in facts if f.booking and f.booking.subject_id in subjects}
            # Cancellation/correction facts carry no booking; retain their
            # original trade's canonical identity without an N-squared scan.
            for fact in facts:
                if fact.trade_id in parents:grouped[parents[fact.trade_id]].append(fact)
        except (ValueError,LookupError) as exc:ledger_error=str(exc)
        for row in rows:
            identity=row['instrument_id'];source=conventions.get(identity);terms=future_terms.get(identity,{});common=dates.get(identity,{})
            reasons=[];cv=None;buckets=[];known=ledger_error is None;blocked=False
            if ledger_error:reasons.append('Position could not be assessed: '+ledger_error)
            else:
                try:buckets=[b for b in reconstruct_allocations(tuple(grouped.get(identity,[])),request,allocation,annotations).buckets if b.closing_quantity]
                except (ValueError,LookupError) as exc:known=False;reasons.append('Position could not be assessed: '+str(exc))
            if known and not buckets:continue
            if source:
                try:cv=FutureConvention.model_validate_json(source['convention_payload'])
                except ValueError:blocked=True;reasons.append('Approved futures conventions are invalid; no contract dates have been assumed.')
            else:blocked=True;reasons.append('Approved futures conventions are missing; no contract dates have been assumed.')
            data=cv.model_dump(mode='json',by_alias=True) if cv else {}
            milestones=contract_milestones(data,common.get('expiry_date'))
            if row['reference_status']!='ACTIVE':blocked=True;reasons.append('The held reference is inactive or retired; review its contract source.')
            if row['selected_tier']>subscription['maximumTier']:blocked=True;reasons.append('Selected notifications exceed the current subscription.')
            if cv:
                for sourced in [common.get('last_trading_date'),terms.get('last_trade_date')]:
                    if sourced is not None and sourced!=cv.last_trading_at_utc.astimezone(timezone.utc).date():blocked=True;reasons.append('Current last-trading dates disagree; reconcile the approved sources.')
                if common.get('final_settlement_date') and common['final_settlement_date']!=cv.final_settlement_date:blocked=True;reasons.append('Current final-settlement dates disagree; reconcile the approved sources.')
                active={trade for bucket in buckets for trade in bucket.trade_ids}
                for fact in grouped.get(identity,[]):
                    if fact.trade_id not in active or not fact.booking:continue
                    frozen=(fact.booking.product_evidence or {}).get('futureConvention')
                    if not frozen:blocked=True;reasons.append('Original frozen futures conventions are unavailable.');continue
                    for field in ['lastTradingAtUtc','finalSettlementDate','settlementMethod','deliveryStartDate','deliveryEndDate','monetaryMultiplier','quoteFactor']:
                        # Parse instants/numbers, since equivalent representations
                        # (Z/+00:00, 5/5.0) do not mean changed contract economics.
                        old=frozen.get(field);new=data.get(field)
                        if field=='lastTradingAtUtc' and old and new:old=datetime.fromisoformat(old.replace('Z','+00:00'));new=datetime.fromisoformat(new.replace('Z','+00:00'))
                        if field in ('monetaryMultiplier','quoteFactor') and old is not None and new is not None:
                            from decimal import Decimal
                            old,new=Decimal(str(old)),Decimal(str(new))
                        if old!=new:blocked=True;reasons.append('Booked and current futures contract terms differ; reconcile the sources.');break
            if not common.get('expiry_date'):reasons.append('An explicit expiry date is not recorded; last trading and settlement are not substituted for expiry.')
            reasons.append('First-notice date is not stored in this contract model; confirm exchange and broker notice deadlines separately.')
            reasons.append('Notifications only. Open ledger contracts do not prove an unpaid settlement or physical delivery; no closure, roll, cash or delivery is created.')
            fingerprint=evidence_hash(dict(convention=source,dates=common,terms=terms))
            quantities=_quantities(buckets,currencies) if known else []
            for milestone in milestones or [dict(kind='SOURCE_REVIEW',date=None,atUtc=None)]:
                day=milestone['date'];status,attention=milestone_state(milestone,now) if day else ('BLOCKED','ACTIONABLE')
                if day is not None and not query.fromDate<=day<=query.toDate and not (query.includeEarlierOverdue and day<query.fromDate and status=='OVERDUE'):continue
                if not known or blocked:status='BLOCKED'
                event_key='FUTURE_EXPIRY:'+str(strategy)+':'+str(identity)+':'+milestone['kind']
                event=dict(eventKey=event_key,eventType='FUTURE_EXPIRY',instrumentType='FUTURE',strategyId=strategy,strategyName=row['strategy_name'],instrumentId=identity,instrumentName=row['instrument_name'],identifier=None,eventDate=day,eventAtUtc=milestone['atUtc'],milestoneKind=milestone['kind'],sourceFingerprint=fingerprint,maturityDate=None,status=status,attention=attention,quantities=quantities,remainingEntries=len(buckets) if known else None,selectedTier=row['selected_tier'],maximumTier=subscription['maximumTier'],processingMode='MANUAL',reasons=list(dict.fromkeys(reasons)),actionLabel='Inspect future',actionHref='/instruments/'+str(identity),positionAssessed=known)
                view=dict(eventKey=event_key,strategyId=strategy,instrumentId=identity,sourceFingerprint=fingerprint,evaluatedAt=now,milestoneKind=milestone['kind'],milestones=milestones,settlementMethod=data.get('settlementMethod'),familyName=families.get(terms.get('future_family_id')),contractMonth=terms.get('contract_month'),conventionId=source['instrument_booking_convention_id'] if source else None,conventionVersion=source['version_no'] if source else None,sourceReference=data.get('sourceReference'),sourceApprovedAt=source['approved_at_utc'] if source else None,monetaryMultiplier=data.get('monetaryMultiplier'),quoteFactor=data.get('quoteFactor'),positionAssessed=known,quantities=quantities,reasons=event['reasons'])
                result.append((event,view))
    return result


def future_events(c,tenant,actor,query,now,subscription):
    return [event for event,view in _future_views(c,tenant,actor,query,now,subscription)]


def inspect_future(c,tenant,actor,strategy,instrument,milestone):
    require_tenant_action(resolve_tenant_workspace(c,tenant,actor,governance_date()),'LIFECYCLE_READ')
    require_strategy_action(c,tenant,actor,'LIFECYCLE_READ',strategy)
    lifecycle_lock(c,tenant);subscription=lifecycle_subscription_view(c,tenant)
    if subscription['maximumTier']<1:raise LookupError('Futures notifications are not available.')
    query=WorklistQuery(fromDate=date.min,toDate=date.max,strategyId=strategy,instrumentId=instrument,eventType='FUTURE_EXPIRY')
    for event,view in _future_views(c,tenant,actor,query,recording_now(c),subscription):
        if event['milestoneKind']==milestone:return view
    raise LookupError('Futures event is unavailable or changed; refresh Lifecycle.')
