"""Calendar visibility and frozen dated evidence, shared by API and resolver."""
from datetime import timedelta
from sqlalchemy import select, or_
from security_master_schema import models as m
from .calendar_composition import reference_day
from datetime import datetime, timezone
from uuid import uuid4


def publish_reference_calendar(c, source_id, actor, reason):
    """Publish a sealed reference copy now; caller authorizes and owns the transaction.

    Existing policies/venue defaults are NOT reassigned. Publication cannot be
    backdated. Database triggers protect the new parent and all its dated rows.
    """
    if not isinstance(reason,str) or not reason.strip() or len(reason)>500:
        raise ValueError('A publication reason of 1–500 characters is required')
    from security_master_schema.tenant_workspace import resolve_platform_role
    if (resolve_platform_role(c,actor,datetime.now(timezone.utc).date())!='PLATFORM_ADMIN'
            or c.scalar(select(m.user_account.c.status).where(m.user_account.c.user_account_id==actor))!='ACTIVE'):
        raise PermissionError('Active platform administrator authority required')
    source=c.execute(select(m.market_calendar).where(m.market_calendar.c.market_calendar_id==source_id,
        m.market_calendar.c.tenant_id.is_(None),m.market_calendar.c.status=='ACTIVE').with_for_update()).mappings().one_or_none()
    if not source: raise ValueError('Active platform reference calendar required')
    children=[]; days=[]
    for table, key, date_key in ((m.market_calendar_session,'market_calendar_session_id','session_date'),
                                 (m.market_calendar_holiday,'market_calendar_holiday_id','holiday_date')):
        rows=c.execute(select(table).where(table.c.market_calendar_id==source_id)).mappings().all()
        children.append((table,key,rows)); days.extend(r[date_key] for r in rows)
    if not days: raise ValueError('Explicit dated reference evidence required')
    published=uuid4(); now=datetime.now(timezone.utc)
    code=source['logical_code'] or source['calendar_code']
    from hashlib import sha256
    from sqlalchemy import func
    lock=int.from_bytes(sha256(('reference-calendar:'+code).encode()).digest()[:8],'big',signed=True)
    c.execute(select(func.pg_advisory_xact_lock(lock)))
    last=c.scalar(select(func.max(m.market_calendar.c.version_no)).where(
        m.market_calendar.c.tenant_id.is_(None),m.market_calendar.c.logical_code==code)) or 0
    parent=dict(source)|dict(market_calendar_id=published,calendar_code='PUB_'+published.hex,
        logical_code=code,version_no=last+1,coverage_from=min(days),coverage_to=max(days),sealed=False,
        definition_json={'sourceCalendarId':str(source_id),'publicationReason':reason.strip()},
        created_by_user_account_id=actor,created_at_utc=now,submission_key=None,submission_fingerprint=None)
    c.execute(m.market_calendar.insert().values(**parent))
    for table,key,rows in children:
        if rows:
            c.execute(table.insert(),[dict(r)|{key:uuid4(),'market_calendar_id':published,'created_at_utc':now} for r in rows])
    c.execute(m.market_calendar.update().where(m.market_calendar.c.market_calendar_id==published).values(sealed=True))
    return published

def visible_calendar(c, tenant, calendar_id):
    return c.execute(select(m.market_calendar).where(m.market_calendar.c.market_calendar_id==calendar_id,
        m.market_calendar.c.status=='ACTIVE',or_(m.market_calendar.c.tenant_id.is_(None),m.market_calendar.c.tenant_id==tenant))).mappings().one_or_none()

def calendar_days(c, row, start, end):
    if not 0 <= (end-start).days < 1100: raise ValueError('Request 1–1100 dates')
    if row['tenant_id']:
        frozen=(row['definition_json'] or {}).get('days',{})
        return [dict(date=(day:=start+timedelta(days=n)),status=frozen.get(day.isoformat(),{}).get('status','UNKNOWN'),
            evidence=frozen.get(day.isoformat(),{'reason':'OUTSIDE_COVERAGE'})) for n in range((end-start).days+1)]
    sessions={r['session_date']:dict(r) for r in c.execute(select(m.market_calendar_session).where(
        m.market_calendar_session.c.market_calendar_id==row['market_calendar_id'],
        m.market_calendar_session.c.session_date.between(start,end))).mappings()}
    holidays={r['holiday_date']:dict(r) for r in c.execute(select(m.market_calendar_holiday).where(
        m.market_calendar_holiday.c.market_calendar_id==row['market_calendar_id'],
        m.market_calendar_holiday.c.holiday_date.between(start,end))).mappings()}
    result=[]
    for n in range((end-start).days+1):
        day=start+timedelta(days=n); session=sessions.get(day); holiday=holidays.get(day)
        state=reference_day(session['session_status'] if session else None,holiday['holiday_name'] if holiday else None)
        result.append(dict(date=day,status=state,evidence=dict(reason='REFERENCE_SESSION_HOLIDAY_CONFLICT' if state=='UNKNOWN' and session and holiday else
            'REFERENCE_HOLIDAY' if holiday else 'REFERENCE_SESSION' if session else 'NO_REFERENCE_COVERAGE',
            calendarId=str(row['market_calendar_id']),holidayName=holiday['holiday_name'] if holiday else None,
            sessionSource=session['source_reference'] if session else None,holidaySource=holiday['source_reference'] if holiday else None)))
    return result
