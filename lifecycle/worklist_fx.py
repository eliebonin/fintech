"""Read-only forward maturity assessment using the native FX closure ledger.

No rate selection or financial command runs on ordinary discovery. Only retained
preparations need the full native candidate fingerprint, with their frozen inputs.
"""
from datetime import datetime,time,timezone
from decimal import Decimal,localcontext
from sqlalchemy import select
from security_master_schema import models as m
from security_master_schema.evidence import evidence_hash
from trading.allocation_policy import load_allocation_policy
from trading.annotation_snapshots import TradeAnnotationBatch
from .allocations import retained_annotation_inputs
from .assistance import native_policy_map
from .fx_service import _exposure,_allocation_groups,candidate
from .worklist_repository import source_maps
from .fx_read_sources import FxMaturityReadSources
from collections import defaultdict


def _assess_sources(c,tenant,pairs,now):
    sources=FxMaturityReadSources(c,tenant,pairs,now);assessments={};by_strategy=defaultdict(list)
    for row in pairs:
        strategy,instrument,day=row['strategy_id'],row['instrument_id'],row['maturity_date'];key=(strategy,instrument)
        item={'terms':None};assessments[key]=item
        try:
            if day is None:raise ValueError('An approved maturity date is missing; no date has been assumed.')
            item['terms']=sources.terms.get(c,tenant,instrument,as_of=day)
            item['cutoff']=min(datetime.combine(day,time.max,timezone.utc),now)
            _,_,_,item['amounts']=_exposure(c,tenant,strategy,instrument,item['terms'],item['cutoff'],now,with_rows=True,read_sources=sources)
            by_strategy[strategy].append(key)
        except (ValueError,LookupError) as exc:item['error']=exc
    for strategy,keys in by_strategy.items():
        try:
            allocation=load_allocation_policy(c,tenant,strategy)
            annotations=TradeAnnotationBatch(c,tenant,{trade for key in keys for trade in assessments[key]['amounts']},allocation)
        except (ValueError,LookupError) as exc:
            for key in keys:assessments[key]['error']=exc
            continue
        for key in keys:
            item=assessments[key]
            try:
                values=annotations.for_trades(c,tenant,item['amounts'])
                item['groups']=_allocation_groups(item['amounts'],allocation,values)
                item['late']=sources.late(c,tenant,*key,item['cutoff'],now)
            except (ValueError,LookupError) as exc:item['error']=exc
    return assessments


def forward_events(c,tenant,query,now,subscription,pairs):
    from .worklist import event_state
    _,_,identifiers,proposals,postings=source_maps(c,tenant,pairs,event_type='FX_FORWARD_MATURITY')
    native=native_policy_map(c,tenant,{r['strategy_id'] for r in pairs})
    assessments=_assess_sources(c,tenant,pairs,now)
    events=[]
    for row in pairs:
        strategy,identity,day=row['strategy_id'],row['instrument_id'],row['maturity_date']
        reasons=[];groups=[];known=True;blocked=False;terms=None
        mode=native.get((strategy,'FX_FORWARD_MATURITY'),dict(mode='REVIEW',revision=0,pricing_policy_id=None,pricing_cut_id=None))
        if row['selected_tier']>subscription['maximumTier']:
            blocked=True;reasons.append('Selected assistance exceeds the current subscription; review strategy settings.')
        try:
            assessment=assessments[(strategy,identity)];terms=assessment['terms']
            if 'error' in assessment:raise assessment['error']
            groups=assessment['groups'];late=assessment['late']
            if late:known=False;blocked=True;reasons.append('An active execution is effective after maturity; reconcile it before closing.')
        except (ValueError,LookupError) as exc:
            known=False;blocked=True;reasons.append('Forward position could not be assessed: '+str(exc))
        history=[p for p in postings.get((strategy,str(identity)),[]) if p['evidence'].get('valueDate')==(day.isoformat() if day else None)]
        posted=next((p for p in history if p['_postingActive']),None)
        pending=[p for p in proposals.get((strategy,identity),[]) if p['inputs'].get('valueDate')==(day.isoformat() if day else None) and not any(h['proposal_id']==p['proposal_id'] for h in history)]
        proposal=pending[0] if pending else None
        if known and not groups and not posted and not blocked:continue
        if day and day<query.fromDate and ((known and not groups) or not query.includeEarlierOverdue):continue
        if row['selected_tier']>=2 and (not mode['pricing_policy_id'] or not mode['pricing_cut_id']):
            blocked=True;reasons.append('Configure a maturity pricing policy and cut in the full workspace before preparing a closure.')
        stale=False
        if proposal:
            proof=proposal['inputs'].get('lifecycleAssistance',{})
            stale=(proposal['policy_revision']!=mode['revision'] or proof.get('subscriptionRevision')!=subscription['revision'] or proof.get('assistanceRevision')!=row['assistance_revision'] or proof.get('entitlementFingerprint')!=subscription['entitlementFingerprint'])
            if not stale and not blocked and known and groups and day and day<=now.date() and row['selected_tier']>=2:
                inputs=proposal['inputs']
                annotations=retained_annotation_inputs(inputs)
                try:
                    _,fingerprint,_,_=candidate(c,tenant,strategy,identity,rate_override=inputs.get('rateOverride'),annotation_inputs=annotations)
                    stale=fingerprint!=proposal['input_hash']
                except (ValueError,LookupError) as exc:
                    stale=True;reasons.append('Prepared input reassessment: '+str(exc))
            reasons.append('Prepared policy, assistance or source evidence changed; prepare and review again.' if stale else 'Retained preparation exists. Native sources are revalidated before confirmation or approval.')
        if history and not posted:reasons.append('Earlier generated closure is no longer active; remaining exposure needs fresh handling.')
        if posted and groups:reasons.append('Closure history exists but exposure remains; reconcile later trades, allocations or corrections.')
        state,attention=event_state(day,now.date(),len(groups),known=known,posted=bool(posted),prepared=bool(proposal),stale=stale,blocked=blocked)
        if state=='BOOKED':reasons=['Retained maturity closure evidence and no remaining exposure. Currency delivery and cash payment are not asserted.']
        if not reasons:reasons=['Closing rate uses a policy-selected maturity-day FX observation or sourced Ops override in the native preview. Exposure closure does not move cash.']
        quantities=[]
        if known and groups:
            with localcontext() as ctx:
                ctx.prec=512;net=sum((g['quantity'] for _,g in groups),Decimal(0));gross=sum((abs(g['quantity']) for _,g in groups),Decimal(0))
            quantities=[dict(currency=terms.base_currency,unit='CURRENCY_AMOUNT',netQuantity=format(net,'f'),grossQuantity=format(gross,'f'),entries=len(groups))]
        label='View closure evidence' if state=='BOOKED' else 'Review blocked event' if state in {'BLOCKED','REASSESSMENT'} else 'Handle manually' if row['selected_tier']==1 else 'Review prepared entry' if proposal else 'Open one-click workflow' if row['selected_tier']==3 and mode['mode']=='DIRECT' else 'Prepare closing entry'
        href=f'/trades/lifecycle?product=fx-forward&strategyId={strategy}&instrumentId={identity}' if row['selected_tier']>=2 or state=='BOOKED' else f'/strategies/{strategy}?view=positions'
        events.append(dict(eventDate=day,eventType='FX_FORWARD_MATURITY',instrumentType='FX_FORWARD',eventKey=evidence_hash(dict(tenantId=tenant,strategyId=strategy,instrumentId=identity,eventType='FX_FORWARD_MATURITY',maturityDate=day)),strategyId=strategy,strategyName=row['strategy_name'],instrumentId=identity,instrumentName=row['instrument_name'],identifier=next(iter(identifiers.get(identity,[])),None),maturityDate=day,status=state,attention=attention,quantities=quantities,remainingEntries=len(groups) if known else None,selectedTier=row['selected_tier'],maximumTier=subscription['maximumTier'],processingMode=mode['mode'],reasons=list(dict.fromkeys(reasons)),actionLabel=label,actionHref=href,proposalId=proposal['proposal_id'] if proposal else None,postingId=posted['posting_id'] if posted else None,positionAssessed=known))
    return events
