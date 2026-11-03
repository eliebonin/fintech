"""Chronological same-security ratio replay; no rounding or income recognition."""
from datetime import datetime, time, timezone
from decimal import Decimal
from collections import defaultdict
from .contracts import PositionError, SplitAdjustment, ExposureInterval, ExecutionEffect
from security_master_schema.cash_products import RATIO_SECURITIES


def visible_splits(events, request):
    from .reconstruction import utc, digest
    by_id={}; by_boundary={}
    for event in events:
        utc(event.effective_at); utc(event.recorded_at)
        if event.recorded_at>request.information_cutoff or event.effective_at>request.closing_cutoff:
            continue
        if not isinstance(event.ratio,Decimal) or not event.ratio.is_finite() or event.ratio<=0:
            raise PositionError('Positive exact split ratio required')
        if not isinstance(event.whole_shares_only,bool) or not event.evidence:
            raise PositionError('Reviewed split entitlement evidence required')
        identity=(event.subject_id,event.action_id)
        if identity in by_id:
            if digest(by_id[identity].__dict__)!=digest(event.__dict__):
                raise PositionError('Conflicting split review evidence')
            continue
        boundary=(event.subject_id,event.effective_date)
        if boundary in by_boundary:
            raise PositionError('Conflicting share-ratio events on the same economic date')
        by_id[identity]=event; by_boundary[boundary]=event
    return tuple(sorted(by_id.values(),key=lambda e:(e.effective_at,str(e.subject_id),str(e.action_id))))


def replay_bucket(key, bookings, actual, events, request):
    """Replay actual exposure and independently timed reporting recognition.

    Execution notionals retain original signed quantity and price. Deferred
    recognition carries intervening ratios, never adds old units after a split.
    """
    if key.product_basis not in RATIO_SECURITIES or key.quantity_unit not in {'SHARES','UNITS'}:
        raise PositionError('Unit-ratio replay requires equity/ETF or quoted-wrapper units')
    actual_rows=defaultdict(list)
    for f in bookings: actual_rows[actual[f.event_id].effective_at].append(f)
    for event in events:
        if event.effective_at in actual_rows:
            raise PositionError('Execution/action ordering at the same instant is ambiguous')
    quantity=Decimal(0); start=None; ids=[]; exposures=[]; adjustments=[]
    for when in sorted(set(actual_rows)|{e.effective_at for e in events}):
        for event in (e for e in events if e.effective_at==when):
            before=quantity; quantity*=event.ratio
            if before and event.whole_shares_only and quantity!=quantity.to_integral_value():
                raise PositionError('Share-ratio fractional entitlement requires cash-in-lieu or explicit fractional holding evidence')
            if before:
                adjustments.append(SplitAdjustment(key,event,before,quantity,tuple(sorted(set(ids),key=str))))
        rows=actual_rows.get(when,[])
        if not rows: continue
        before=quantity; quantity+=sum((f.booking.quantity for f in rows),Decimal(0))
        if before==0: start=when; ids=[]
        ids.extend(f.trade_id for f in rows)
        if quantity==0 or before*quantity<0:
            if start is not None:
                exposures.append(ExposureInterval(key,start,when,tuple(sorted(set(ids),key=str))))
            start=when if quantity else None
            ids=[f.trade_id for f in rows] if quantity else []
    if quantity and start is not None:
        exposures.append(ExposureInterval(key,start,request.closing_cutoff,tuple(sorted(set(ids),key=str))))

    def reporting_time(event):
        return datetime.combine(event.effective_date,time.min,timezone.utc) if request.daily else event.effective_at
    schedule=defaultdict(list)
    for event in events: schedule[reporting_time(event)].append(('SPLIT',event))
    for f in bookings: schedule[f.effective_at].append(('BOOKING',f))
    quantity=Decimal(0); opening=Decimal(0); history=[]; period=[]; movements=[]
    history_cut=request.opening_cutoff if request.mode=='PERIOD' else request.closing_cutoff
    for when, items in sorted(schedule.items()):
        if when>request.closing_cutoff: break
        for kind,item in sorted(items,key=lambda row:0 if row[0]=='SPLIT' else 1):
            if kind=='SPLIT': quantity*=item.ratio
            else:
                added=item.booking.quantity
                for event in events:
                    if actual[item.event_id].effective_at<event.effective_at and reporting_time(event)<=when:
                        added*=event.ratio
                quantity+=added
                if when<=history_cut: history.append(item)
                else:
                    period.append(item)
                    movements.append(ExecutionEffect(key,item.booking,item.event_id,item.effective_at,item.recorded_at))
        if when<=history_cut:
            opening=quantity
            if quantity==0: history=[]
    return (opening if request.mode=='PERIOD' else Decimal(0),quantity,
            history+period,movements,exposures,adjustments)
