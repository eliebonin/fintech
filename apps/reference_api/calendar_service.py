"""Tenant calendar governance. No reference-calendar or financial mutation."""
import hashlib
import json
from datetime import time
from uuid import uuid4
from sqlalchemy import select, func, or_
from security_master_schema import models as m
from security_master_schema.market_data_visibility import visible_subject_clause
from market_data.calendar_composition import compose_day
from market_data.calendar_store import visible_calendar, calendar_days
from market_data.pricing_conventions import local_target
from .calendar_contracts import CalendarView,CalendarOptions,CalendarAssignmentView
from security_master_schema.tenant_workspace import resolve_tenant_workspace, require_tenant_action
from .resource_limits import governance_date
from .repository import RepositoryNotFound,IdempotencyKeyConflict

def authority(c,tenant,actor,write=False):
    workspace=resolve_tenant_workspace(c,tenant,actor,governance_date())
    require_tenant_action(workspace,'CALENDAR_MANAGE' if write else 'CALENDAR_READ')
    return 'CALENDAR_MANAGE' in workspace.permission_codes

def lock(c,value):
    c.execute(select(func.pg_advisory_xact_lock(int.from_bytes(hashlib.sha256(value.encode()).digest()[:8],'big',signed=True))))

def fingerprint(payload):
    return hashlib.sha256(json.dumps(payload.model_dump(mode='json',by_alias=True),sort_keys=True,separators=(',',':')).encode()).hexdigest()

def get_calendar(c,tenant,calendar_id):
    row=visible_calendar(c,tenant,calendar_id)
    if not row: raise RepositoryNotFound('Calendar not available')
    return row

def calendar_view(c,tenant,calendar_id,include_configuration=True):
    row=get_calendar(c,tenant,calendar_id)
    return CalendarView(calendarId=calendar_id,calendarCode=row['logical_code'] or row['calendar_code'],displayName=row['display_name'],
        purpose=row['calendar_kind'],timezoneName=row['timezone_name'],versionNo=row['version_no'],coverageFrom=row['coverage_from'],
        coverageTo=row['coverage_to'],tenantOwned=bool(row['tenant_id']),createdByUserAccountId=row['created_by_user_account_id'],
        createdAtUtc=row['created_at_utc'] if row['tenant_id'] else None,
        configuration=row['definition_json']['configuration'] if include_configuration and row['definition_json'] else None)

def assignment_view(row):
    return CalendarAssignmentView(assignmentId=row['calendar_assignment_id'],calendarId=row['market_calendar_id'],targetKind=row['target_kind'],
        targetId=row['target_id'],purpose=row['purpose'],validFrom=row['valid_from'],validTo=row['valid_to'],reason=row['reason'],
        createdByUserAccountId=row['created_by_user_account_id'],createdAtUtc=row['created_at_utc'])

def options(c,tenant,actor):
    manage=authority(c,tenant,actor)
    ids=c.scalars(select(m.market_calendar.c.market_calendar_id).where(m.market_calendar.c.status=='ACTIVE',
        or_(m.market_calendar.c.tenant_id.is_(None),m.market_calendar.c.tenant_id==tenant)).order_by(m.market_calendar.c.display_name,m.market_calendar.c.version_no.desc()).limit(500)).all()
    return CalendarOptions(canManage=manage,calendars=[calendar_view(c,tenant,cid,False) for cid in ids],
        strategies=[dict(id=sid,label=name) for sid,name in c.execute(select(m.strategy.c.strategy_id,m.strategy.c.display_name).where(m.strategy.c.tenant_id==tenant,m.strategy.c.status=='ACTIVE').limit(500))],
        assignments=[assignment_view(row) for row in c.execute(select(m.calendar_assignment).where(m.calendar_assignment.c.tenant_id==tenant).order_by(
            m.calendar_assignment.c.created_at_utc.desc(),m.calendar_assignment.c.calendar_assignment_id.desc()).limit(500)).mappings()])

def publish_calendar(c,tenant,actor,payload,key):
    authority(c,tenant,actor,True)
    if not key.strip(): raise ValueError('Submission key cannot be blank')
    digest=fingerprint(payload); lock(c,f'calendar-key:{tenant}:{key}')
    old=c.execute(select(m.market_calendar).where(m.market_calendar.c.tenant_id==tenant,m.market_calendar.c.submission_key==key)).mappings().one_or_none()
    if old:
        if old['submission_fingerprint']!=digest: raise IdempotencyKeyConflict('Calendar key reused')
        return calendar_view(c,tenant,old['market_calendar_id'])
    components={}
    for cid in payload.base_calendar_ids:
        reference=get_calendar(c,tenant,cid)
        if reference['tenant_id'] and reference['calendar_kind']!=payload.purpose: raise ValueError('Tenant component purpose must match')
        components[str(cid)]={d['date']:d for d in calendar_days(c,reference,payload.coverage_from,payload.coverage_to)}
    exceptions={e.date:e.model_dump(mode='json',by_alias=True,exclude={'date'}) for e in payload.exceptions}
    from datetime import timedelta
    days={}
    for n in range((payload.coverage_to-payload.coverage_from).days+1):
        day=payload.coverage_from+timedelta(days=n)
        result=compose_day(day,payload.mode,payload.weekdays,{cid:rows[day]['status'] for cid,rows in components.items()},exceptions.get(day))
        result['componentEvidence']={cid:rows[day]['evidence'] for cid,rows in components.items()}
        if result['status']=='OPEN': local_target(day,payload.decision_time,payload.timezone_name)
        days[day.isoformat()]=result
    lock(c,f'calendar-code:{tenant}:{payload.calendar_code}')
    version=(c.scalar(select(func.max(m.market_calendar.c.version_no)).where(m.market_calendar.c.tenant_id==tenant,m.market_calendar.c.logical_code==payload.calendar_code)) or 0)+1
    cid=c.execute(m.market_calendar.insert().values(calendar_code='TENANT_'+uuid4().hex,display_name=payload.display_name,
        timezone_name=payload.timezone_name,calendar_kind=payload.purpose,tenant_id=tenant,logical_code=payload.calendar_code,
        version_no=version,coverage_from=payload.coverage_from,coverage_to=payload.coverage_to,
        definition_json=dict(configuration=payload.model_dump(mode='json',by_alias=True),days=days),created_by_user_account_id=actor,
        submission_key=key,submission_fingerprint=digest).returning(m.market_calendar.c.market_calendar_id)).scalar_one()
    sessions=[dict(market_calendar_id=cid,session_date=day,session_status=item['status'],
        open_local_time=time(0) if item['status']=='OPEN' else None,close_local_time=payload.decision_time if item['status']=='OPEN' else None,
        source_reference=payload.source_reference) for day,item in ((payload.coverage_from+timedelta(days=n),days[(payload.coverage_from+timedelta(days=n)).isoformat()]) for n in range(len(days))) if item['status']!='UNKNOWN']
    if sessions: c.execute(m.market_calendar_session.insert(),sessions)
    c.execute(m.market_calendar.update().where(m.market_calendar.c.market_calendar_id==cid).values(sealed=True))
    return calendar_view(c,tenant,cid)

def assign_calendar(c,tenant,actor,payload,key):
    authority(c,tenant,actor,True)
    if not key.strip(): raise ValueError('Submission key cannot be blank')
    digest=fingerprint(payload); lock(c,f'calendar-assignment-key:{tenant}:{key}')
    old=c.execute(select(m.calendar_assignment).where(m.calendar_assignment.c.tenant_id==tenant,m.calendar_assignment.c.submission_key==key)).mappings().one_or_none()
    if old:
        if old['submission_fingerprint']!=digest: raise IdempotencyKeyConflict('Assignment key reused')
        return assignment_view(old)
    calendar=get_calendar(c,tenant,payload.calendar_id)
    if not calendar['tenant_id'] or not calendar['sealed']: raise ValueError('Assign a published tenant calendar version')
    if not calendar['coverage_from']<=payload.valid_from<=payload.valid_to<=calendar['coverage_to']: raise ValueError('Assignment must be within version coverage')
    if payload.target_kind=='STRATEGY':
        from security_master_schema.market_data_resolver import assert_strategy_scope
        assert_strategy_scope(c,tenant,payload.target_id,payload.valid_from)
        assert_strategy_scope(c,tenant,payload.target_id,payload.valid_to)
    else:
        fund=c.scalar(select(m.fund.c.fund_reference_node_id).where(m.fund.c.fund_reference_node_id==payload.target_id,m.fund.c.status=='ACTIVE'))
        share=c.scalar(select(m.instrument.c.instrument_node_id).select_from(m.instrument.join(m.instrument_type)).where(
            m.instrument.c.instrument_node_id==payload.target_id,m.instrument_type.c.type_code.in_(['FUND_SHARE_CLASS','ETP'])))
        visible=c.scalar(select(m.financial_reference_node.c.reference_node_id).where(m.financial_reference_node.c.reference_node_id==payload.target_id,
            m.financial_reference_node.c.status=='ACTIVE',visible_subject_clause(payload.target_id,tenant)))
        if not visible or not (fund or share):
            raise ValueError('Target must be a visible active fund, fund share class or ETP canonical reference')
    purpose=calendar['calendar_kind']; lock(c,f'calendar-target:{tenant}:{payload.target_kind}:{payload.target_id}:{purpose}')
    overlaps=c.execute(select(m.calendar_assignment).where(m.calendar_assignment.c.tenant_id==tenant,
        m.calendar_assignment.c.target_kind==payload.target_kind,m.calendar_assignment.c.target_id==payload.target_id,
        m.calendar_assignment.c.purpose==purpose,m.calendar_assignment.c.valid_from<=payload.valid_to,
        m.calendar_assignment.c.valid_to>=payload.valid_from)).mappings().all()
    if any(row['valid_from']!=payload.valid_from or row['valid_to']!=payload.valid_to for row in overlaps):
        raise ValueError('Overlapping assignments must retain the same effective interval; revise the pinned version instead')
    row=c.execute(m.calendar_assignment.insert().values(tenant_id=tenant,market_calendar_id=payload.calendar_id,
        target_kind=payload.target_kind,target_id=payload.target_id,purpose=purpose,valid_from=payload.valid_from,valid_to=payload.valid_to,
        reason=payload.reason,created_by_user_account_id=actor,submission_key=key,submission_fingerprint=digest).returning(m.calendar_assignment)).mappings().one()
    return assignment_view(row)
