"""Display-only business-day proximity; never adjusts an event or its authority."""
from datetime import timedelta
from zoneinfo import ZoneInfo,ZoneInfoNotFoundError

HORIZON_DAYS=40


def timing_for_event(event,now,source=None):
    basis=source['basis'] if source else 'WEEKDAYS'
    zone=source.get('timezone','UTC') if source else 'UTC'
    name=source.get('name') if source else None
    explanation=(source.get('reason','Configured business calendar') if source else 'Monday–Friday estimate; holidays not configured.')
    result=dict(tone='NEUTRAL',label='',businessDays=None,basis=basis,calendarName=name,timezoneName=zone,evaluatedOn=now.date(),explanation=explanation)
    try:today=now.astimezone(ZoneInfo(zone)).date()
    except (ZoneInfoNotFoundError,ValueError):
        return result|dict(basis='UNKNOWN',label='Calendar unavailable',calendarName=None)
    result['evaluatedOn']=today
    day=event.get('eventDate') or event.get('maturityDate')
    if day is None:return result|dict(label='Date missing')
    if event['status'] in ('BOOKED','CONFIRMATION_RECORDED'):return result|dict(label='Completed')
    cutoff=event.get('eventAtUtc')
    if event['attention']=='ACTIONABLE' and (day<today or cutoff is not None and cutoff<now):
        return result|dict(tone='OVERDUE',label='Deadline passed' if day==today else 'Overdue')
    if day<today:return result|dict(label='Date passed')
    if basis=='UNKNOWN':return result|dict(label='Calendar unavailable')
    if day==today:return result|dict(tone='TODAY',label='Today',businessDays=0)
    count=0;last=min(day,today+timedelta(days=HORIZON_DAYS))
    cursor=today
    while cursor<last:
        cursor+=timedelta(days=1)
        state=source['days'].get(cursor,'UNKNOWN') if source else ('OPEN' if cursor.weekday()<5 else 'CLOSED')
        if state not in ('OPEN','HALF_DAY','CLOSED'):
            return result|dict(basis='UNKNOWN',label='Calendar coverage missing',explanation=explanation+' Explicit day coverage is missing or conflicting; no business day is assumed.')
        if state in ('OPEN','HALF_DAY'):count+=1
        if count>5:return result|dict(tone='LATER',label='More than 5 business days' if source else 'Est. >5 weekdays')
    if cursor<day:return result|dict(basis='UNKNOWN',label='Calendar coverage missing')
    label=('Before next business day' if source else 'Est. before next weekday') if count==0 else ('In '+str(count)+' business day'+('s' if count!=1 else '') if source else 'Est. '+str(count)+' weekday'+('s' if count!=1 else ''))
    return result|dict(tone='SOON' if count<=2 else 'WEEK',label=label,businessDays=count)
