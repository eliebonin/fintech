"""Operational transactions are short; callers never hold them across HTTP."""
from datetime import datetime,timezone
from sqlalchemy import select
from security_master_schema import models as m
from .storage import insert_returning
from .history import require_admin
from .outcomes import TERMINAL,job_outcome


def start_job(c,dataset_id,namespace_id,tenant_id,actor_id,symbols,start,end):
    require_admin(c,tenant_id,actor_id)
    profile=c.execute(select(m.dataset_access_profile).where(m.dataset_access_profile.c.dataset_id==dataset_id,
        m.dataset_access_profile.c.external_id_namespace_id==namespace_id,
        m.dataset_access_profile.c.permitted_tenant_id==tenant_id)).mappings().one_or_none()
    if not profile or not symbols or end<start or len(set(symbols))!=len(symbols):
        raise ValueError('Invalid job scope, selection or ordered dates')
    return insert_returning(c,m.market_data_ingestion_job,'job_id',dataset_id=dataset_id,namespace_id=namespace_id,
        tenant_id=tenant_id,actor_id=actor_id,selection=symbols,request={'start':start.isoformat(),'end':end.isoformat()})


def start_attempt(c,job_id,symbol,start,end):
    job=c.execute(select(m.market_data_ingestion_job).where(m.market_data_ingestion_job.c.job_id==job_id).with_for_update()).mappings().one()
    if job['status']!='RUNNING':
        raise ValueError('Job is terminal')
    if symbol not in job['selection'] or start>end or start.isoformat()<job['request']['start'] or end.isoformat()>job['request']['end']:
        raise ValueError('Attempt is outside the exact job scope')
    return insert_returning(c,m.market_data_ingestion_attempt,'attempt_id',job_id=job_id,symbol=symbol,
        request={'start':start.isoformat(),'end':end.isoformat()})


def finish_attempt(c,attempt_id,status,report,delivery_run_id=None):
    if status not in TERMINAL:
        raise ValueError('Unknown terminal outcome')
    attempt=m.market_data_ingestion_attempt
    row=c.execute(select(attempt).where(attempt.c.attempt_id==attempt_id).with_for_update()).mappings().one()
    if row['status']!='RUNNING':
        raise ValueError('Attempt is terminal')
    if delivery_run_id is not None:
        delivery=c.execute(select(m.market_data_ingestion_run).where(
            m.market_data_ingestion_run.c.run_id==delivery_run_id)).mappings().one_or_none()
        job=c.execute(select(m.market_data_ingestion_job).where(
            m.market_data_ingestion_job.c.job_id==row['job_id'])).mappings().one()
        expected=dict(row['request'],namespaceId=str(job['namespace_id']),symbol=row['symbol'])
        if not delivery or delivery['dataset_id']!=job['dataset_id'] or delivery['report'].get('request')!=expected:
            raise ValueError('Attempt delivery does not match its dataset/namespace/symbol/window')
    c.execute(attempt.update().where(attempt.c.attempt_id==attempt_id).values(status=status,
        report=report,delivery_run_id=delivery_run_id,finished_at_utc=datetime.now(timezone.utc)))


def finish_job(c,job_id,summary=None):
    job=m.market_data_ingestion_job
    row=c.execute(select(job).where(job.c.job_id==job_id).with_for_update()).mappings().one()
    if row['status']!='RUNNING':
        raise ValueError('Job is terminal')
    attempts=c.execute(select(m.market_data_ingestion_attempt).where(
        m.market_data_ingestion_attempt.c.job_id==job_id).order_by(m.market_data_ingestion_attempt.c.attempt_id.desc())).mappings().all()
    if any(a['status']=='RUNNING' for a in attempts):
        raise ValueError('Job still has running attempts')
    latest={}
    for attempt in attempts:
        latest.setdefault(attempt['symbol'],attempt['status'])
    states=[latest.get(symbol,'FAILED') for symbol in row['selection']]
    status=job_outcome(states)
    c.execute(job.update().where(job.c.job_id==job_id).values(status=status,
        summary=summary or {},finished_at_utc=datetime.now(timezone.utc)))
    return status


def abort_job(c,job_id,tenant_id,actor_id,reason):
    require_admin(c,tenant_id,actor_id)
    if not reason.strip():
        raise ValueError('Explicit interruption evidence required')
    job=m.market_data_ingestion_job
    row=c.execute(select(job).where(job.c.job_id==job_id).with_for_update()).mappings().one()
    if row['tenant_id']!=tenant_id:
        raise PermissionError('Job belongs to another tenant')
    if row['status']!='RUNNING':
        raise ValueError('Job is terminal')
    evidence={'interruption':reason.strip(),'actorId':str(actor_id)}
    ids=c.execute(select(m.market_data_ingestion_attempt.c.attempt_id).where(
        m.market_data_ingestion_attempt.c.job_id==job_id,m.market_data_ingestion_attempt.c.status=='RUNNING')).scalars().all()
    for attempt in ids:
        finish_attempt(c,attempt,'ABORTED',evidence)
    c.execute(job.update().where(job.c.job_id==job_id).values(status='ABORTED',summary=evidence,
        finished_at_utc=datetime.now(timezone.utc)))
