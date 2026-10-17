"""Read-only reporting predicates; no new calculation or publication authority.

The same filtered relation drives count and page. A batch is selected once per
attempt, including the recorded reuse path, so amendments do not multiply rows.
"""
from sqlalchemy import select,func,cast,Date,and_,String
from sqlalchemy.dialects.postgresql import UUID
from security_master_schema import models as _models  # registers shared tables
from . import tables as t

def history_queries(tenant,scope,*,strategy_id=None,from_date=None,to_date=None,
                    calculation_status=None,publication_status=None,results_only=False,limit=25,offset=0):
    b=t.batch.alias('history_batch')
    direct=select(t.batch.c.batch_id).where(t.batch.c.tenant_id==tenant,
        t.batch.c.attempt_id==t.attempt.c.attempt_id).order_by(t.batch.c.created_at.desc(),t.batch.c.batch_id.desc()).limit(1).correlate(t.attempt).scalar_subquery()
    reused=select(cast(t.run_event.c.details['batchId'].astext,UUID(as_uuid=True))).where(
        t.run_event.c.attempt_id==t.attempt.c.attempt_id,t.run_event.c.details['batchId'].astext.is_not(None)
    ).order_by(t.run_event.c.recorded_at.desc(),t.run_event.c.event_id.desc()).limit(1).correlate(t.attempt).scalar_subquery()
    relation=t.attempt.outerjoin(b,and_(b.c.batch_id==func.coalesce(direct,reused),
        b.c.tenant_id==tenant,b.c.strategy_id==t.attempt.c.strategy_id))
    day=func.coalesce(b.c.value_date,cast(func.substr(t.attempt.c.request_payload['closing_cutoff'].astext,1,10),Date))
    where=[t.attempt.c.tenant_id==tenant,scope]
    if strategy_id is not None:where.append(t.attempt.c.strategy_id==strategy_id)
    if from_date is not None:where.append(day>=from_date)
    if to_date is not None:where.append(day<=to_date)
    if calculation_status is not None:where.append(t.attempt.c.status==calculation_status)
    if publication_status is not None:where.append(b.c.status==publication_status)
    if results_only:where.append(b.c.batch_id.is_not(None))
    reason=select(t.run_event.c.details['reason'].astext).where(t.run_event.c.attempt_id==t.attempt.c.attempt_id,
        t.run_event.c.event_code=='FAILED').order_by(t.run_event.c.recorded_at.desc(),t.run_event.c.event_id.desc()).limit(1).correlate(t.attempt).scalar_subquery()
    mode=select(t.run_event.c.details['reviewMode'].astext).where(t.run_event.c.attempt_id==b.c.attempt_id,
        t.run_event.c.details['batchId'].astext==cast(b.c.batch_id,String),t.run_event.c.event_code=='PUBLISHED')\
        .order_by(t.run_event.c.recorded_at.desc(),t.run_event.c.event_id.desc()).limit(1).correlate(b).scalar_subquery()
    rows=select(t.attempt,b.c.batch_id,b.c.status.label('batch_status'),day.label('valuation_date'),mode.label('publication_review_mode'),
        reason.label('failure_reason')).select_from(relation).where(*where).order_by(t.attempt.c.started_at.desc(),t.attempt.c.attempt_id.desc()).limit(limit).offset(offset)
    count=select(func.count()).select_from(relation).where(*where)
    return rows,count
