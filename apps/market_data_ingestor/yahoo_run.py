"""Serial operator execution with independently committed attempt evidence."""
from datetime import datetime,timezone,date
from hashlib import sha256
import json
import httpx
from sqlalchemy.exc import SQLAlchemyError
from market_data.jobs import start_job,start_attempt,finish_attempt,finish_job
from market_data.outcomes import delivery_outcome,exit_code,gap_windows
from market_data.ingestion import ingest_delivery
from market_data.rights import load_rights


def emit(value):
    print(json.dumps(value,default=str),flush=True)


def execute(engine,*,dataset_id,namespace_id,tenant_id,actor_id,selected,start,end,
            provider,parser,fetch,lookup_previous,history,retry_gaps,sleep,request_spacing_seconds=5):
    if not 1 <= request_spacing_seconds <= 60:
        raise ValueError('Request spacing must be 1..60 seconds.')
    with engine.begin() as c:
        job=start_job(c,dataset_id,namespace_id,tenant_id,actor_id,[r['symbol'] for r in selected],start,end)
    emit({'status':'JOB_STARTED','jobId':str(job),'selected':len(selected),
          'requestSpacingSeconds':request_spacing_seconds})
    downloaded=resumed=0
    stop=False
    with httpx.Client() as client:
        for index,row in enumerate(selected,1):
            symbol=row['symbol']
            with engine.connect() as c:
                denied=None
                for activity in ('ACQUIRE','STORE'):
                    rights=load_rights(c,dataset_id,activity,date.today(),'PERSONAL')
                    if not rights.allowed:
                        denied=f'{activity}: {rights.reason}'
                        break
            if denied:
                with engine.begin() as c:
                    attempt=start_attempt(c,job,symbol,start,end)
                    finish_attempt(c,attempt,'BLOCKED',{'reason':denied})
                emit({'symbol':symbol,'status':'BLOCKED','reason':denied})
                break
            with engine.connect() as c:
                previous=lookup_previous(c,dataset_id,namespace_id,symbol,start,end) if history else None
            windows=gap_windows(previous,start,end) if previous and retry_gaps else []
            if previous and not windows:
                with engine.begin() as c:
                    attempt=start_attempt(c,job,symbol,start,end)
                    finish_attempt(c,attempt,delivery_outcome(previous),dict(previous,resumed=True),previous.get('runId'))
                resumed+=1
                emit(dict(symbol=symbol,index=index,total=len(selected),status='RESUMED',outcome=delivery_outcome(previous),
                    accepted=previous['accepted'],rejected=previous['rejected']))
                continue
            windows=windows or [(start,end)]
            for window_start,window_end in windows:
                with engine.begin() as c:
                    attempt=start_attempt(c,job,symbol,window_start,window_end)
                retries=[]
                try:
                    with engine.connect() as c:
                        for activity in ('ACQUIRE','STORE'):
                            rights=load_rights(c,dataset_id,activity,date.today(),'PERSONAL')
                            if not rights.allowed:
                                raise PermissionError(f'{activity}: {rights.reason}')
                    def on_retry(retry,delay):
                        event={'retry':retry,'delaySeconds':delay}
                        retries.append(event)
                        # Persist backoff evidence before waiting, not only in stdout.
                        from security_master_schema import models as m
                        with engine.begin() as c:
                            c.execute(m.market_data_ingestion_attempt.update().where(
                                m.market_data_ingestion_attempt.c.attempt_id==attempt).values(report={'backoffs':list(retries)}))
                        emit(dict(symbol=symbol,status='RATE_LIMIT_BACKOFF',**event))
                    downloaded+=1
                    raw=fetch(client,symbol,window_start,window_end,on_retry=on_retry,max_window_days=provider.max_window_days)
                    received=datetime.now(timezone.utc)
                    key=f'{symbol}:{window_start}:{window_end}:{sha256(raw.encode()).hexdigest()}'
                    with engine.begin() as c:
                        report=ingest_delivery(c,provider=provider,parser=parser,dataset_id=dataset_id,
                            namespace_id=namespace_id,symbol=symbol,raw_payload=raw,delivery_key=key,
                            received_at=received,start=window_start,end=window_end)
                        finish_attempt(c,attempt,delivery_outcome(report),dict(report,backoffs=retries),report['runId'])
                    emit(dict(symbol=symbol,index=index,total=len(selected),outcome=delivery_outcome(report),**report))
                except (PermissionError,httpx.HTTPError,ValueError,SQLAlchemyError) as exc:
                    blocked=isinstance(exc,PermissionError) or isinstance(exc,httpx.HTTPStatusError) and exc.response.status_code in {401,403,429}
                    state='BLOCKED' if blocked else 'FAILED'
                    # SQL error strings can contain SQL parameters/credentials. Retain a safe category only.
                    error=str(exc) if isinstance(exc,(PermissionError,ValueError)) else type(exc).__name__
                    failure={'errorType':type(exc).__name__,'error':error,'backoffs':retries}
                    with engine.begin() as c:
                        finish_attempt(c,attempt,state,failure)
                    emit(dict(symbol=symbol,status=state,**failure))
                    if blocked:
                        stop=True
                        break
                except KeyboardInterrupt:
                    with engine.begin() as c:
                        finish_attempt(c,attempt,'ABORTED',{'reason':'Operator interrupted execution'})
                    stop=True
                    break
                if index<len(selected) or (window_start,window_end)!=windows[-1]:
                    sleep(request_spacing_seconds)
            if stop:
                break
            if previous and retry_gaps:
                # Re-assess original rejected dates, not merely the last retry span.
                with engine.begin() as c:
                    assessed=lookup_previous(c,dataset_id,namespace_id,symbol,start,end)
                    attempt=start_attempt(c,job,symbol,start,end)
                    finish_attempt(c,attempt,delivery_outcome(assessed),dict(assessed,gapAssessment=True),assessed.get('runId'))
    summary={'selected':len(selected),'attempted':downloaded,'resumed':resumed,'start':start.isoformat(),'end':end.isoformat(),
             'requestSpacingSeconds':request_spacing_seconds}
    with engine.begin() as c:
        status=finish_job(c,job,summary)
    emit(dict(status='RUN_FINISHED',outcome=status,jobId=str(job),**summary))
    return exit_code(status)
