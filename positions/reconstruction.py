"""Reference projection: signed holdings and period effects, not cost accounting."""
from collections import defaultdict
from dataclasses import asdict
from datetime import datetime, timedelta
from decimal import Decimal, localcontext, Inexact
from hashlib import sha256
import json
from uuid import UUID
from .contracts import (ProjectionRequest, PositionProjection, PositionBucket, ExecutionEffect,
                        ExposureInterval, PositionError)
from .equity import booking_key

def utc(value):
    if not isinstance(value,datetime) or value.tzinfo is None or value.utcoffset()!=timedelta(0):
        raise PositionError('Aware UTC timestamps required')

def canonical(value):
    """Stable exact identity; equivalent Decimal scales have identical hashes."""
    if isinstance(value,Decimal):
        if not value.is_finite(): raise PositionError('Nonfinite financial evidence')
        if value == 0: return '0'
        text=format(value,'f')
        return text.rstrip('0').rstrip('.') if '.' in text else text
    if isinstance(value,UUID): return str(value)
    if isinstance(value,datetime): utc(value); return value.isoformat()
    if isinstance(value,dict): return {k:canonical(v) for k,v in value.items()}
    if isinstance(value,(tuple,list)): return [canonical(x) for x in value]
    if isinstance(value,float): raise PositionError('Binary float is not economic evidence')
    return value

def digest(value):
    return sha256(json.dumps(canonical(value),sort_keys=True,separators=(',',':')).encode()).hexdigest()

def key_identity(key):
    return digest(asdict(key))

def reconstruct(facts, request: ProjectionRequest) -> PositionProjection:
    utc(request.closing_cutoff); utc(request.information_cutoff)
    if request.mode not in {'PERIOD','AS_OF'}: raise PositionError('Unknown projection mode')
    if request.mode=='PERIOD':
        utc(request.opening_cutoff)
        if request.opening_cutoff>=request.closing_cutoff: raise PositionError('Opening cutoff must precede close')
    elif request.opening_cutoff is not None: raise PositionError('AS_OF has no opening cutoff')
    eligible=[]; count=0
    for fact in facts:
        count+=1; utc(fact.effective_at); utc(fact.recorded_at)
        if (fact.tenant_id,fact.strategy_id)!=(request.tenant_id,request.strategy_id):
            raise PositionError('Ledger scope mismatch')
        if fact.recorded_at<=request.information_cutoff and fact.effective_at<=request.closing_cutoff:
            eligible.append(fact)
    eligible.sort(key=lambda f:(str(f.trade_id),f.sequence,str(f.event_id)))
    chains=defaultdict(list)
    for f in eligible: chains[f.trade_id].append(f)
    active=[]
    for trade,chain in chains.items():
        if [f.sequence for f in chain]!=list(range(1,len(chain)+1)):
            raise PositionError('Missing or duplicate lifecycle sequence evidence')
        original=chain[0]
        if original.kind!='BOOKED' or original.booking is None: raise PositionError('Missing original BOOKED economics')
        if original.booking.trade_id!=trade: raise PositionError('BOOKED identity mismatch')
        key=booking_key(original.booking,request.tenant_id,request.strategy_id)
        removed=False; last_time=original.effective_at
        for f in chain[1:]:
            if f.effective_at<last_time: raise PositionError('Lifecycle effective ordering is inconsistent')
            last_time=f.effective_at
            if f.kind in {'CANCELLED','SUPERSEDED'}:
                if removed: raise PositionError('Booking already removed')
                if request.mode=='PERIOD' and f.effective_at>request.opening_cutoff:
                    raise PositionError('Unsupported in-period removal requires economic lifecycle treatment')
                removed=True
            elif f.kind=='CORRECTED':
                if removed: raise PositionError('Correction cannot resurrect removed booking')
            else: raise PositionError(f'Unsupported lifecycle effect: {f.kind}')
        if not removed: active.append((key,original))
    active.sort(key=lambda item:(item[1].effective_at,str(item[1].trade_id)))
    grouped=defaultdict(list)
    for key,f in active: grouped[key].append(f)
    buckets=[]; executions=[]; exposures=[]
    with localcontext() as context:
        context.prec=512; context.traps[Inexact]=True
        for key,bookings in sorted(grouped.items(),key=lambda item:key_identity(item[0])):
            opening=Decimal(0); closing=Decimal(0); movements=[]
            for f in bookings:
                closing+=f.booking.quantity
                if request.mode=='PERIOD':
                    if f.effective_at<=request.opening_cutoff: opening+=f.booking.quantity
                    else: movements.append(ExecutionEffect(key,f.booking,f.event_id,f.effective_at,f.recorded_at))
            by_time=defaultdict(list)
            for f in bookings: by_time[f.effective_at].append(f)
            # Only the unclosed opening episode and ALL period executions own
            # financial lineage. Earlier flat history still establishes state
            # in the projection audit, but is not copied into every new result.
            history_cut=request.opening_cutoff if request.mode=='PERIOD' else request.closing_cutoff
            history=[]; history_quantity=Decimal(0)
            for when,rows in sorted(by_time.items()):
                if when>history_cut: break
                history.extend(rows)
                history_quantity+=sum((f.booking.quantity for f in rows),Decimal(0))
                if history_quantity==0: history=[]
            relevant=history+[f for f in bookings if f.effective_at>history_cut]
            if opening!=0 or closing!=0 or movements:
                buckets.append(PositionBucket(key,opening,closing,
                    tuple(sorted({f.trade_id for f in relevant},key=str)),
                    tuple(sorted({f.booking.definition_id for f in relevant},key=str))))
                executions.extend(movements)
            quantity=Decimal(0); start=None; ids=[]
            for when,rows in sorted(by_time.items()):
                before=quantity
                quantity+=sum((f.booking.quantity for f in rows),Decimal(0))
                if before==0: start=when; ids=[]
                ids.extend(f.trade_id for f in rows)
                if quantity==0 or before*quantity<0:
                    # Validate all historical raw exposure intervals before
                    # trusting a flat boundary. An unreplayed split can make
                    # equal raw buy/sell quantities falsely appear closed.
                    if start is not None:
                        exposures.append(ExposureInterval(key,start,when,tuple(sorted(set(ids),key=str))))
                    start=when if quantity!=0 else None
                    ids=[f.trade_id for f in rows] if quantity!=0 else []
            if quantity!=0 and start is not None:
                exposures.append(ExposureInterval(key,start,request.closing_cutoff,tuple(sorted(set(ids),key=str))))
    executions.sort(key=lambda x:(x.effective_at,str(x.booking.trade_id)))
    payload=dict(request=asdict(request),facts=[asdict(f) for f in eligible],engine='position-reconstruction-v1')
    return PositionProjection(request,tuple(buckets),tuple(executions),tuple(exposures),tuple(eligible),count,
        request.information_cutoff>=request.closing_cutoff,digest(payload))
