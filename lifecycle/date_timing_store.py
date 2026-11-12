"""Bulk calendar context for already-authorised, paginated Lifecycle rows.

These are proximity hints, not contractual business-day adjustment decisions.
No source-calendar absence is disguised as assessed holiday coverage.
"""
from collections import defaultdict
from datetime import timedelta
from sqlalchemy import select,or_
from security_master_schema import models as m
from security_master_schema.reference_visibility import visible_clause
from market_data.calendar_composition import reference_day
from . import coupon_tables as ct
from .date_timing import timing_for_event,HORIZON_DAYS


def _chunks(values):
    values=sorted(set(values),key=str)
    for n in range(0,len(values),500):yield values[n:n+500]


def add_date_timing(c,tenant,events,now):
    if not events:return
    instruments={r['instrumentId'] for r in events};strategies={r['strategyId'] for r in events}
    periods={r['couponPeriodId'] for r in events if r.get('couponPeriodId')}
    explicit={};venues=defaultdict(set);assignments=defaultdict(list)
    for batch in _chunks(periods):
        for row in c.execute(select(ct.cashflow.c.cashflow_id,ct.schedule.c.calendar_id).join(ct.schedule,ct.schedule.c.schedule_id==ct.cashflow.c.schedule_id).where(ct.cashflow.c.cashflow_id.in_(batch),ct.schedule.c.tenant_id==tenant,ct.schedule.c.recorded_at<=now)).mappings():
            if row['calendar_id']:explicit[row['cashflow_id']]=row['calendar_id']
    for batch in _chunks(instruments):
        for row in c.execute(select(m.listing.c.instrument_node_id,m.market_venue.c.market_calendar_id).join(m.market_venue,m.market_venue.c.market_venue_id==m.listing.c.market_venue_id).where(m.listing.c.instrument_node_id.in_(batch),visible_clause(m.listing.c.listing_node_id,tenant))).mappings():
            venues[row['instrument_node_id']].add(row['market_calendar_id'])
    a=m.calendar_assignment
    # Source selection is at the current evaluated date. Dated validity below is
    # still enforced for every counted day; future reassignments aren't guessed.
    for batch in _chunks(strategies):
        for row in c.execute(select(a).where(a.c.tenant_id==tenant,a.c.target_kind=='STRATEGY',a.c.target_id.in_(batch),a.c.purpose=='SETTLEMENT',a.c.valid_from<=now.date(),a.c.valid_to>=now.date(),a.c.created_at_utc<=now).order_by(a.c.created_at_utc.desc(),a.c.calendar_assignment_id.desc())).mappings():assignments[row['target_id']].append(row)
    selections=[]
    for event in events:
        calendar=None;reason=None;limits=None
        if event.get('couponPeriodId') in explicit:calendar=explicit[event['couponPeriodId']];reason='Coupon schedule calendar'
        elif venues[event['instrumentId']]:
            available=venues[event['instrumentId']]
            if len(available)!=1:
                selections.append(dict(basis='UNKNOWN',timezone='UTC',name=None,reason='Visible listings have conflicting business calendars.',days={}));continue
            calendar=next(iter(available));reason='Listing venue calendar'
        if calendar is None and assignments[event['strategyId']]:
            assignment=assignments[event['strategyId']][0];calendar=assignment['market_calendar_id'];reason='Strategy settlement calendar (display only)';limits=(assignment['valid_from'],assignment['valid_to'])
        selections.append((calendar,reason,limits) if calendar else None)
    wanted={s[0] for s in selections if isinstance(s,tuple)};calendars={}
    start=now.date()-timedelta(days=1);end=now.date()+timedelta(days=HORIZON_DAYS+1)
    for batch in _chunks(wanted):
        for row in c.execute(select(m.market_calendar).where(m.market_calendar.c.market_calendar_id.in_(batch),or_(m.market_calendar.c.tenant_id.is_(None),m.market_calendar.c.tenant_id==tenant),m.market_calendar.c.status=='ACTIVE',m.market_calendar.c.sealed,m.market_calendar.c.created_at_utc<=now)).mappings():calendars[row['market_calendar_id']]=row
    public={identity for identity,row in calendars.items() if row['tenant_id'] is None};sessions={};holidays={}
    for batch in _chunks(public):
        for row in c.execute(select(m.market_calendar_session).where(m.market_calendar_session.c.market_calendar_id.in_(batch),m.market_calendar_session.c.session_date.between(start,end))).mappings():sessions[(row['market_calendar_id'],row['session_date'])]=row['session_status']
        for row in c.execute(select(m.market_calendar_holiday).where(m.market_calendar_holiday.c.market_calendar_id.in_(batch),m.market_calendar_holiday.c.holiday_date.between(start,end))).mappings():holidays[(row['market_calendar_id'],row['holiday_date'])]=row['holiday_name']
    sources={}
    for identity,row in calendars.items():
        days={};cursor=start
        frozen=(row['definition_json'] or {}).get('days',{})
        while cursor<=end:
            covered=row['coverage_from'] is not None and row['coverage_to'] is not None and row['coverage_from']<=cursor<=row['coverage_to']
            days[cursor]=(frozen.get(cursor.isoformat(),{}).get('status','UNKNOWN') if row['tenant_id'] else reference_day(sessions.get((identity,cursor)),holidays.get((identity,cursor)))) if covered else 'UNKNOWN'
            cursor+=timedelta(days=1)
        sources[identity]=dict(basis='CALENDAR',name=row['display_name'],timezone=row['timezone_name'],days=days)
    for event,selection in zip(events,selections):
        source=None
        if isinstance(selection,dict):source=selection
        elif selection:
            identity,reason,limits=selection
            if identity in sources:
                source=sources[identity]|dict(reason=reason+': '+sources[identity]['name']+'. Holidays and explicit closures are included.')
                if limits:source=source|dict(days={d:s for d,s in source['days'].items() if limits[0]<=d<=limits[1]})
            else:source=dict(basis='UNKNOWN',name=None,timezone='UTC',days={},reason='Configured calendar is unavailable or not a visible sealed version; holidays are not assumed.')
        event['dateTiming']=timing_for_event(event,now,source)
