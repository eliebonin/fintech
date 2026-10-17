"""Reviewed library schedules become explicit, immutable reference evidence.

No network access, implicit venue assignment or exchange-certification claim.
The caller owns the transaction. A new source review produces a new version.
"""
from datetime import date,datetime,timedelta,time,timezone
from security_master_schema.governance_clock import governance_date
from hashlib import sha256
from importlib.metadata import version
import json
from uuid import uuid4
from zoneinfo import ZoneInfo
from sqlalchemy import select,func
from security_master_schema import models as m


def build_reviewed_schedule(review):
    import pandas_market_calendars as calendars
    if not review.get('sourceReference') or not review.get('reviewScope'):
        raise ValueError('A source reference and explicit review scope are required')
    reviewed=date.fromisoformat(review['reviewedOn'])
    if reviewed>governance_date(): raise ValueError('Review cannot be future-dated')
    year=review['year']
    if not isinstance(year,int) or isinstance(year,bool) or not 1900<=year<=2200:
        raise ValueError('Supported calendar year required')
    if review.get('mode')=='LIBRARY_SNAPSHOT':
        return build_library_snapshot(review)
    start,end=date(year,1,1),date(year,12,31)
    calendar=calendars.get_calendar(review['calendarName'])
    if str(calendar.tz)!=review['timezone']: raise ValueError('Calendar timezone disagrees with review')
    zone=ZoneInfo(review['timezone'])
    normal_open=time.fromisoformat(review['normalOpen'])
    normal_close=time.fromisoformat(review['normalClose'])
    half_close=time.fromisoformat(review['halfDayClose'])
    schedule=calendar.schedule(start_date=start,end_date=end)
    open_days={day.date():(row.market_open.to_pydatetime().astimezone(zone).time(),
        row.market_close.to_pydatetime().astimezone(zone).time()) for day,row in schedule.iterrows()}
    expected_closed={date.fromisoformat(day) for day in review['closedWeekdays']}
    expected_half={date.fromisoformat(day) for day in review['halfDays']}
    closed=set();half=set();rows=[]
    for offset in range((end-start).days+1):
        day=start+timedelta(days=offset)
        opening,closing=open_days.get(day,(None,None))
        if opening is None:
            state='CLOSED'
            if day.weekday()<5: closed.add(day)
        else:
            if opening!=normal_open or closing not in (normal_close,half_close):
                raise ValueError('Session times disagree with review')
            state='HALF_DAY' if closing==half_close else 'OPEN'
            if state=='HALF_DAY': half.add(day)
        rows.append(dict(session_date=day,session_status=state,open_local_time=opening,
            close_local_time=closing,source_reference=review['sourceReference']))
    if closed!=expected_closed or half!=expected_half:
        raise ValueError('Library schedule disagrees with reviewed holiday/half-day dates')
    digest=sha256(json.dumps(rows,sort_keys=True,default=str).encode()).hexdigest()
    provenance=dict(sourceKind='REVIEWED_LIBRARY_SCHEDULE',exchangeCertified=False,
        package='pandas_market_calendars',packageVersion=version('pandas_market_calendars'),
        calendarName=review['calendarName'],mic=review['mic'],timezone=review['timezone'],
        sourceReference=review['sourceReference'],reviewedOn=review['reviewedOn'],
        reviewScope=review['reviewScope'],coverageFrom=str(start),coverageTo=str(end),
        scheduleSha256=digest,review=review)
    fingerprint=sha256(json.dumps(provenance,sort_keys=True).encode()).hexdigest()
    return dict(sessions=rows,provenance=provenance,fingerprint=fingerprint,start=start,end=end)


def build_library_snapshot(review):
    """Freeze package output honestly; known defects remain REVIEW_REQUIRED."""
    import warnings
    import pandas_market_calendars as calendars
    start=date.fromisoformat(review.get('coverageFrom',f"{review['year']}-01-01"))
    end=date.fromisoformat(review.get('coverageTo',f"{review['year']}-12-31"))
    if not start<=end or start.year!=review['year'] or end.year!=review['year']:
        raise ValueError('Coverage must be ordered within the selected year')
    status=review.get('publicationStatus')
    if status not in ('ACTIVE','REVIEW_REQUIRED'): raise ValueError('Explicit publication status required')
    with warnings.catch_warnings(record=True) as notices:
        warnings.simplefilter('always')
        calendar=calendars.get_calendar(review['calendarName'])
        schedule=calendar.schedule(start_date=start,end_date=end)
        early=set(calendar.early_closes(schedule).index.date)
    zone=ZoneInfo(str(calendar.tz)); opened={day.date():row for day,row in schedule.iterrows()}
    rows=[];breaks={}
    for offset in range((end-start).days+1):
        day=start+timedelta(days=offset); item=opened.get(day)
        opening=closing=None; state='CLOSED'
        if item is not None:
            opening=item.market_open.to_pydatetime().astimezone(zone).time()
            closing=item.market_close.to_pydatetime().astimezone(zone).time()
            if opening>=closing: raise ValueError('Overnight calendars need a product-specific importer')
            state='HALF_DAY' if day in early else 'OPEN'
            if 'break_start' in item and not item['break_start'] is None:
                import pandas as pd
                if pd.notna(item['break_start']):
                    breaks[str(day)]={'startUtc':item['break_start'].isoformat(),'endUtc':item['break_end'].isoformat()}
        rows.append(dict(session_date=day,session_status=state,open_local_time=opening,
            close_local_time=closing,source_reference=review['sourceReference']))
    digest=sha256(json.dumps(rows,sort_keys=True,default=str).encode()).hexdigest()
    provenance=dict(sourceKind='LIBRARY_SNAPSHOT',exchangeCertified=False,
        package='pandas_market_calendars',packageVersion=version('pandas_market_calendars'),
        calendarName=review['calendarName'],mic=review['mic'],timezone=str(calendar.tz),
        sourceReference=review['sourceReference'],verificationReferences=review.get('verificationReferences',[]),
        reviewedOn=review['reviewedOn'],reviewScope=review['reviewScope'],review=review,
        coverageFrom=str(start),coverageTo=str(end),scheduleSha256=digest,
        sessionBreaks=breaks,warnings=[str(n.message) for n in notices])
    fingerprint=sha256(json.dumps(provenance,sort_keys=True).encode()).hexdigest()
    return dict(sessions=rows,provenance=provenance,fingerprint=fingerprint,start=start,end=end)


def publish_reviewed_schedule(c,actor,review):
    from security_master_schema.tenant_workspace import resolve_platform_role
    from .calendar_store import publish_reference_calendar
    now=datetime.now(timezone.utc)
    if (resolve_platform_role(c,actor,now.date())!='PLATFORM_ADMIN' or
            c.scalar(select(m.user_account.c.status).where(m.user_account.c.user_account_id==actor))!='ACTIVE'):
        raise PermissionError('Active platform administrator required')
    draft=build_reviewed_schedule(review)
    status=review.get('publicationStatus','ACTIVE')
    code=f"{review['mic']}_TRADING_{review['year']}"
    lock=int.from_bytes(sha256(('reference-calendar:'+code).encode()).digest()[:8],'big',signed=True)
    c.execute(select(func.pg_advisory_xact_lock(lock)))
    prior=c.scalar(select(m.market_calendar.c.market_calendar_id).where(
        m.market_calendar.c.tenant_id.is_(None),m.market_calendar.c.logical_code==code,
        m.market_calendar.c.sealed.is_(True),m.market_calendar.c.status==status,
        m.market_calendar.c.definition_json['importFingerprint'].as_string()==draft['fingerprint']))
    if prior: return prior
    source=uuid4()
    c.execute(m.market_calendar.insert().values(market_calendar_id=source,
        calendar_code='IMPORT_'+source.hex,logical_code=code,display_name=f"{review['mic']} reviewed trading schedule {review['year']}",
        timezone_name=draft['provenance']['timezone'],calendar_kind='TRADING',coverage_from=draft['start'],coverage_to=draft['end'],
        created_by_user_account_id=actor,created_at_utc=now,
        definition_json={'provenance':draft['provenance'],'importFingerprint':draft['fingerprint']}))
    c.execute(m.market_calendar_session.insert(),[row|dict(market_calendar_id=source,created_at_utc=now) for row in draft['sessions']])
    return publish_reference_calendar(c,source,actor,'Explicit reference schedule import; source provenance retained',publication_status=status)


def activate_calendar(c,actor,calendar_id,mic):
    """No new venues or implicit MIC aliases; activation is separately audited."""
    from security_master_schema.tenant_workspace import resolve_platform_role
    if (resolve_platform_role(c,actor,governance_date())!='PLATFORM_ADMIN' or
        c.scalar(select(m.user_account.c.status).where(m.user_account.c.user_account_id==actor))!='ACTIVE'):
        raise PermissionError('Active platform administrator required')
    calendar=c.execute(select(m.market_calendar).where(m.market_calendar.c.market_calendar_id==calendar_id,
        m.market_calendar.c.status=='ACTIVE',m.market_calendar.c.sealed.is_(True),m.market_calendar.c.tenant_id.is_(None))).mappings().one_or_none()
    if not calendar: raise ValueError('An active sealed reference calendar is required')
    provenance=(calendar['definition_json'] or {}).get('provenance',{})
    if provenance.get('mic')!=mic: raise ValueError('Calendar MIC differs from venue')
    venues=c.execute(select(m.market_venue).join(m.market_venue_identifier).where(
        m.market_venue_identifier.c.identifier_scheme=='ISO_10383_MIC',
        m.market_venue_identifier.c.identifier_value==mic,m.market_venue_identifier.c.is_primary.is_(True))
        .with_for_update(of=m.market_venue)).mappings().all()
    if not venues: return None
    if len(venues)!=1: raise ValueError('Ambiguous MIC venue')
    venue=venues[0]
    if venue['market_calendar_id']!=calendar_id:
        c.execute(m.market_venue.update().where(m.market_venue.c.market_venue_id==venue['market_venue_id']).values(market_calendar_id=calendar_id))
        c.execute(m.access_audit_event.insert().values(actor_id=actor,action='REFERENCE_CALENDAR_ACTIVATED',
            details=dict(venueId=str(venue['market_venue_id']),previousCalendarId=str(venue['market_calendar_id']),
                calendarId=str(calendar_id),sourceReference=provenance.get('sourceReference'))))
    return venue['market_venue_id']
