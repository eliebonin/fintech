"""Option deadline notices, never exercise, assignment, closure or payment."""
from datetime import date,datetime,timezone
from collections import defaultdict
from decimal import Decimal
import json
from sqlalchemy import select
from security_master_schema import models as m
from security_master_schema.reference_visibility import visible_clause
from security_master_schema.strategy_access import require_strategy_action
from security_master_schema.tenant_workspace import require_tenant_action,resolve_tenant_workspace
from security_master_schema.governance_clock import governance_date
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



def option_milestones(terms,dates):
    rows=[]
    cutoff=terms.get('last_trading_at_utc')
    if cutoff is not None:
        cutoff=cutoff.astimezone(timezone.utc)
        rows.append(dict(kind='LAST_TRADE',date=cutoff.date(),atUtc=cutoff))
    elif dates.get('last_trading_date'):rows.append(dict(kind='LAST_TRADE',date=dates['last_trading_date'],atUtc=None))
    if dates.get('expiry_date'):rows.append(dict(kind='EXPIRY',date=dates['expiry_date'],atUtc=None))
    else:rows.append(dict(kind='SOURCE_REVIEW',date=None,atUtc=None))
    if dates.get('final_settlement_date'):rows.append(dict(kind='FINAL_SETTLEMENT',date=dates['final_settlement_date'],atUtc=None))
    return rows


def _number(value):
    if value is None:return None
    value=Decimal(value)
    text=format(value,'f')
    if value==0:return '0'
    return text.rstrip('0').rstrip('.') if '.' in text else text


def _original_conflicts(facts,buckets,originals,term,dates,unit,currencies):
    active={identity for bucket in buckets for identity in bucket.trade_ids}
    wanted=dict(optionType=term.get('option_type'),underlyingId=str(term.get('underlying_reference_node_id')),
        exerciseStyle=term.get('exercise_style'),settlementMethod=term.get('settlement_method'),
        strike=term.get('strike_value'),strikeCurrency=currencies.get(term.get('strike_currency_id')),
        premiumCurrency=currencies.get(term.get('premium_currency_id')),premiumMultiplier=term.get('premium_multiplier'),
        deliverableUnits=unit.get('unit_multiplier'),expiryDate=dates.get('expiry_date'),lastTradingAtUtc=term.get('last_trading_at_utc'))
    for fact in facts:
        if not fact.booking or fact.trade_id not in active:continue
        retained=originals.get(fact.trade_id,{}).get('economics',{}).get('terms',{})
        if not retained:return ['Original option contract evidence is unavailable; no exercise terms are assumed.']
        try:
            for field,current in wanted.items():
                old=retained.get(field)
                if field in ('strike','premiumMultiplier','deliverableUnits'):old,current=_number(old),_number(current)
                elif field=='lastTradingAtUtc' and old:old=datetime.fromisoformat(old.replace('Z','+00:00'))
                elif field=='expiryDate' and old:old=date.fromisoformat(old)
                if old!=current:return ['Booked and current option contract terms differ; reconcile the sources before using this notice.']
        except (ValueError,TypeError,ArithmeticError):return ['Original/current option terms could not be compared; no values are assumed.']
    return []


def _option_views(c,tenant,actor,query,now,subscription):
    from .worklist import _quantities
    pairs=held_candidates(c,tenant,actor,query,now,instrument_type='OPTION',event_type='OPTION_EXPIRY')
    if not pairs:return []
    ids={row['instrument_id'] for row in pairs};subjects={i:i for i in ids}
    subjects.update(dict(c.execute(select(m.listing.c.listing_node_id,m.listing.c.instrument_node_id).where(m.listing.c.instrument_node_id.in_(ids),visible_clause(m.listing.c.listing_node_id,tenant))).all()))
    dates={r['instrument_node_id']:dict(r) for r in c.execute(select(m.instrument_dates).where(m.instrument_dates.c.instrument_node_id.in_(ids))).mappings()}
    terms=defaultdict(list);definitions=defaultdict(list);units=defaultdict(list)
    for r in c.execute(select(m.option_terms).where(m.option_terms.c.instrument_node_id.in_(ids),m.option_terms.c.is_current)).mappings():terms[r['instrument_node_id']].append(dict(r))
    for r in c.execute(select(m.instrument_definition_version).where(m.instrument_definition_version.c.instrument_node_id.in_(ids),m.instrument_definition_version.c.is_current,m.instrument_definition_version.c.status=='APPROVED',m.instrument_definition_version.c.approved_at_utc<=now)).mappings():definitions[r['instrument_node_id']].append(dict(r))
    u=m.instrument_contract_unit_terms
    for r in c.execute(select(u).where(u.c.instrument_node_id.in_(ids))).mappings():
        reference_day=min(now.date(),dates.get(r['instrument_node_id'],{}).get('expiry_date') or now.date())
        if r['valid_from']<=reference_day and (r['valid_to'] is None or r['valid_to']>=reference_day):units[r['instrument_node_id']].append(dict(r))
    currencies=dict(c.execute(select(m.currency.c.currency_id,m.currency.c.currency_code)).all())
    underlying_ids={r['underlying_reference_node_id'] for group in terms.values() for r in group if r['underlying_reference_node_id']}
    underlying_names=dict(c.execute(select(m.financial_reference_node.c.reference_node_id,m.financial_reference_node.c.canonical_name).where(m.financial_reference_node.c.reference_node_id.in_(underlying_ids),visible_clause(m.financial_reference_node.c.reference_node_id,tenant))).all())
    by_strategy=defaultdict(list)
    for row in pairs:by_strategy[row['strategy_id']].append(row)
    result=[]
    for strategy,rows in by_strategy.items():
        request=ProjectionRequest(tenant,strategy,now,now);relevant={r['instrument_id'] for r in rows}
        grouped=defaultdict(list);originals={};ledger_error=None
        try:
            facts=tuple(iter_ledger_facts(c,request,subject_ids=[s for s,i in subjects.items() if i in relevant]))
            allocation=load_allocation_policy(c,tenant,strategy)
            annotations=load_trade_annotations(c,tenant,[f.trade_id for f in facts],allocation)
            parents={f.trade_id:subjects[f.booking.subject_id] for f in facts if f.booking and f.booking.subject_id in subjects}
            for fact in facts:
                if fact.trade_id in parents:grouped[parents[fact.trade_id]].append(fact)
            for identity,payload in c.execute(select(m.trade_lifecycle_event.c.trade_id,m.trade_lifecycle_event.c.event_payload).where(m.trade_lifecycle_event.c.trade_id.in_(parents),m.trade_lifecycle_event.c.event_type=='BOOKED',m.trade_lifecycle_event.c.recorded_at_utc<=now)):
                originals[identity]=json.loads(payload)
        except (ValueError,LookupError) as exc:ledger_error=str(exc)
        for row in rows:
            identity=row['instrument_id'];common=dates.get(identity,{})
            term=terms[identity][0] if len(terms[identity])==1 else {}
            definition=definitions[identity][0] if len(definitions[identity])==1 else {}
            unit=units[identity][0] if len(units[identity])==1 else {}
            reasons=[];buckets=[];known=ledger_error is None;blocked=False
            event_facts=tuple(grouped.get(identity,[]))
            if ledger_error:reasons.append('Position could not be assessed: '+ledger_error)
            else:
                try:buckets=[b for b in reconstruct_allocations(event_facts,request,allocation,annotations).buckets if b.closing_quantity]
                except (ValueError,LookupError) as exc:known=False;reasons.append('Position could not be assessed: '+str(exc))
            if known and not buckets:continue
            if not term or term.get('status')!='ACTIVE' or not definition:
                blocked=True;reasons.append('A single current approved option definition and active term set are required.')
            if not unit or not unit.get('unit_multiplier') or unit['unit_multiplier']<=0:
                blocked=True;reasons.append('A single sourced positive deliverable-unit definition is required; no multiplier is assumed.')
            if row['reference_status']!='ACTIVE':blocked=True;reasons.append('The held option is inactive or retired; review its source.')
            if row['selected_tier']>subscription['maximumTier']:blocked=True;reasons.append('Selected notifications exceed the current subscription.')
            underlying=term.get('underlying_reference_node_id')
            if underlying not in underlying_names:blocked=True;reasons.append('The underlying reference is unavailable in this tenant context.')
            if not common.get('expiry_date'):blocked=True;reasons.append('An explicit expiry date is missing; last trading is not substituted for expiry.')
            if term.get('strike_mode')!='FIXED':blocked=True;reasons.append('Non-fixed/resetting strike terms require separate governed evidence; no strike is resolved here.')
            if known and term and unit:
                conflicts=_original_conflicts(event_facts,buckets,originals,term,common,unit,currencies)
                if conflicts:blocked=True;reasons.extend(conflicts)
            if term.get('last_trading_at_utc') and common.get('last_trading_date') and term['last_trading_at_utc'].astimezone(timezone.utc).date()!=common['last_trading_date']:
                blocked=True;reasons.append('Last-trading dates disagree between the approved option terms and common dates.')
            if term.get('exercise_style')=='AMERICAN':reasons.append('American-style exercise/assignment can occur before expiry; broker instructions and assignment notices remain separate.')
            reasons.append('Expiry review only. Exercise, assignment, lapse, financial closure, cash and security delivery are not assessed or created.')
            reasons.append('AM/PM fixing designation and broker exercise-instruction deadlines are not stored; no time or outcome has been inferred.')
            milestones=option_milestones(term,common)
            fingerprint=evidence_hash(dict(terms=sorted(terms[identity],key=lambda r:str(r['option_terms_id'])),definition=sorted(definitions[identity],key=lambda r:str(r['instrument_definition_version_id'])),units=sorted(units[identity],key=lambda r:str(r['instrument_contract_unit_terms_id'])),dates=common))
            quantities=_quantities(buckets,currencies) if known else []
            for milestone in milestones:
                day=milestone['date'];status,attention=milestone_state(milestone,now) if day else ('BLOCKED','ACTIONABLE')
                if day is not None and not query.fromDate<=day<=query.toDate and not(query.includeEarlierOverdue and day<query.fromDate and status=='OVERDUE'):continue
                if blocked or not known:status='BLOCKED'
                key='OPTION_EXPIRY:'+str(strategy)+':'+str(identity)+':'+milestone['kind']
                event=dict(eventKey=key,eventType='OPTION_EXPIRY',instrumentType='OPTION',strategyId=strategy,strategyName=row['strategy_name'],instrumentId=identity,instrumentName=row['instrument_name'],identifier=None,eventDate=day,eventAtUtc=milestone['atUtc'],milestoneKind=milestone['kind'],sourceFingerprint=fingerprint,maturityDate=None,status=status,attention=attention,quantities=quantities,remainingEntries=len(buckets) if known else None,selectedTier=row['selected_tier'],maximumTier=subscription['maximumTier'],processingMode='MANUAL',reasons=list(dict.fromkeys(reasons)),actionLabel='Inspect option',actionHref='/instruments/'+str(identity),positionAssessed=known)
                view=dict(eventKey=key,strategyId=strategy,instrumentId=identity,sourceFingerprint=fingerprint,evaluatedAt=now,milestoneKind=milestone['kind'],milestones=milestones,optionTermsId=term.get('option_terms_id'),termsVersion=term.get('version_no'),definitionId=definition.get('instrument_definition_version_id'),sourceApprovedAt=definition.get('approved_at_utc'),underlyingId=underlying if underlying in underlying_names else None,underlyingName=underlying_names.get(underlying),optionType=term.get('option_type'),strike=_number(term.get('strike_value')) if term.get('strike_mode')=='FIXED' else None,strikeCurrency=currencies.get(term.get('strike_currency_id')),exerciseStyle=term.get('exercise_style'),settlementMethod=term.get('settlement_method'),settlementCurrency=currencies.get(term.get('settlement_currency_id')),premiumCurrency=currencies.get(term.get('premium_currency_id')),premiumMultiplier=_number(term.get('premium_multiplier')),deliverableUnits=_number(unit.get('unit_multiplier')),positionAssessed=known,quantities=quantities,reasons=event['reasons'])
                result.append((event,view))
    return result


def option_events(c,tenant,actor,query,now,subscription):
    return [event for event,view in _option_views(c,tenant,actor,query,now,subscription)]


def inspect_option(c,tenant,actor,strategy,instrument,milestone):
    require_tenant_action(resolve_tenant_workspace(c,tenant,actor,governance_date()),'LIFECYCLE_READ')
    require_strategy_action(c,tenant,actor,'LIFECYCLE_READ',strategy)
    lifecycle_lock(c,tenant);subscription=lifecycle_subscription_view(c,tenant)
    if subscription['maximumTier']<1:raise LookupError('Option notifications are not available.')
    query=WorklistQuery(fromDate=date.min,toDate=date.max,strategyId=strategy,instrumentId=instrument,eventType='OPTION_EXPIRY')
    for event,view in _option_views(c,tenant,actor,query,recording_now(c),subscription):
        if event['milestoneKind']==milestone:return view
    raise LookupError('Option event is unavailable or changed; refresh Lifecycle.')
