"""Information-cutoff-aware assigned fund/strategy calendar decisions."""
from sqlalchemy import select, or_
from security_master_schema import models as m
from .calendar_store import visible_calendar,calendar_days

def decision_for_target(c,tenant,kind,target,purpose,day,asof):
    a=m.calendar_assignment
    row=c.execute(select(a).where(a.c.tenant_id==tenant,a.c.target_kind==kind,a.c.target_id==target,a.c.purpose==purpose,
        a.c.valid_from<=day,a.c.valid_to>=day,a.c.created_at_utc<=asof).order_by(a.c.created_at_utc.desc(),a.c.calendar_assignment_id.desc()).limit(1)).mappings().one_or_none()
    if not row: return None
    calendar=visible_calendar(c,tenant,row['market_calendar_id'])
    evidence=dict(assignmentId=str(row['calendar_assignment_id']),calendarId=str(row['market_calendar_id']),
        targetKind=kind,targetId=str(target),purpose=purpose,date=day.isoformat(),assignmentRecordedAtUtc=row['created_at_utc'].isoformat())
    if not calendar or not calendar['sealed'] or calendar['created_at_utc']>asof:
        return dict(**evidence,status='UNKNOWN',reason='CALENDAR_VERSION_NOT_AVAILABLE_AT_CUTOFF')
    item=calendar_days(c,calendar,day,day)[0]
    return dict(**evidence,status=item['status'],versionNo=calendar['version_no'],reason=item['evidence'].get('reason'),
        dayEvidence=item['evidence'],calendarRecordedAtUtc=calendar['created_at_utc'].isoformat())

def request_calendar_decisions(c,request,series_type):
    result=[]
    if request.strategy_id:
        decision=decision_for_target(c,request.tenant_id,'STRATEGY',request.strategy_id,'VALUATION',request.valuation_date,request.market_data_as_of_utc)
        if decision: result.append(decision)
    if series_type not in ('OFFICIAL_NAV','NAV','INDICATIVE_NAV'): return result
    subject=request.subject_reference_node_id
    canonical=c.scalar(select(m.listing.c.instrument_node_id).where(m.listing.c.listing_node_id==subject)) or subject
    targets=[canonical]
    fund=c.scalar(select(m.fund_share_class_terms.c.fund_reference_node_id).where(m.fund_share_class_terms.c.instrument_node_id==canonical,
        m.fund_share_class_terms.c.effective_from<=request.valuation_date,or_(m.fund_share_class_terms.c.effective_to.is_(None),m.fund_share_class_terms.c.effective_to>=request.valuation_date)).order_by(m.fund_share_class_terms.c.sequence_no.desc()).limit(1))
    if fund: targets.append(fund)
    for target in targets:
        decision=decision_for_target(c,request.tenant_id,'FUND_REFERENCE',target,'VALUATION',request.valuation_date,request.market_data_as_of_utc)
        if decision:
            result.append(decision); break
    return result
