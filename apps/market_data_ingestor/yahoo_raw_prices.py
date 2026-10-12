"""Local operator: append derived Yahoo RAW closes and their assessed split lineage."""
import argparse
from datetime import date,datetime,timezone
import json
import time
from uuid import UUID
import httpx
from sqlalchemy import create_engine,select
from security_master_schema import models as m
from market_data.providers.yahoo.raw_prices import normalize_dataset,assess_basis,retain_event_coverage
from market_data.providers.yahoo.adapter import fetch_chart
from market_data.contracts import ListingContext
from market_data import storage
from market_data.history import require_admin
from market_data.rights import load_rights
from market_data.jobs import start_job,start_attempt,finish_attempt,finish_job
from .config import IngestorSettings


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tenant',type=UUID,required=True)
    parser.add_argument('--actor',type=UUID,required=True)
    parser.add_argument('--symbols',nargs='+')
    parser.add_argument('--apply',action='store_true')
    parser.add_argument('--fill-gaps',action='store_true',help='Fetch only missing split-coverage dates; requires --apply')
    parser.add_argument('--request-spacing-seconds',type=float,default=2)
    args=parser.parse_args();settings=IngestorSettings.from_environment()
    if settings.environment not in ('local','test'): parser.error('Local/test only')
    if args.fill_gaps and not args.apply: parser.error('--fill-gaps requires --apply')
    if not 1<=args.request_spacing_seconds<=60: parser.error('Spacing must be 1..60 seconds')
    engine=create_engine(settings.database_url)
    try:
        with engine.connect() as c:
            require_admin(c,args.tenant,args.actor)
            dataset=c.scalar(select(m.dataset.c.dataset_id).where(m.dataset.c.dataset_code=='YAHOO_PERSONAL_EQUITY_DAILY'))
            if not dataset: raise ValueError('Yahoo equity dataset is not configured')
            profile=c.execute(select(m.dataset_access_profile).where(m.dataset_access_profile.c.dataset_id==dataset)).mappings().one()
            if profile['permitted_tenant_id']!=args.tenant: raise PermissionError('Dataset owner required')
            namespace=profile['external_id_namespace_id']
            runs=c.execute(select(m.market_data_ingestion_run).join(m.source_payload).where(
                m.market_data_ingestion_run.c.dataset_id==dataset,m.source_payload.c.processing_status=='VALIDATED')).mappings().all()
            runs=[r for r in runs if not args.symbols or r['report']['request']['symbol'] in args.symbols]
            gaps={}
            for run in runs:
                if run['report'].get('eventCoverageOnly'): continue
                symbol=run['report']['request']['symbol']
                _,listing=storage.resolve_listing(c,namespace_id=namespace,symbol=symbol,received_at=run['received_at_utc'],permitted_tenant_id=args.tenant)
                try:
                    assess_basis(run,[r for r in runs if r['report']['request']['symbol']==symbol],
                        ListingContext(listing['currency_code'],listing['mic'],listing['timezone_name']))
                except ValueError as exc:
                    if str(exc).startswith('SPLIT_COVERAGE_GAP: '):
                        gaps.setdefault(symbol,set()).update(str(exc).split(': ',1)[1].split(','))
                    else: print(json.dumps(dict(symbol=symbol,assessmentError=str(exc))),flush=True)
        print(json.dumps(dict(status='COVERAGE_ASSESSED',gapSymbols=len(gaps),gaps={s:sorted(days) for s,days in gaps.items()})),flush=True)
        if args.fill_gaps and gaps:
            all_days=[day for days in gaps.values() for day in days]
            with engine.begin() as c:
                coverage_job=start_job(c,dataset,namespace,args.tenant,args.actor,sorted(gaps),
                    date.fromisoformat(min(all_days)),date.fromisoformat(max(all_days)))
            with httpx.Client() as client:
                for symbol,days in sorted(gaps.items()):
                    begin=date.fromisoformat(min(days));end=date.fromisoformat(max(days))
                    with engine.begin() as c:
                        attempt=start_attempt(c,coverage_job,symbol,begin,end)
                    backoffs=[]
                    def on_retry(number,delay):
                        backoffs.append(dict(retry=number,delaySeconds=delay))
                        with engine.begin() as c:
                            c.execute(m.market_data_ingestion_attempt.update().where(
                                m.market_data_ingestion_attempt.c.attempt_id==attempt).values(report={'backoffs':list(backoffs)}))
                        print(json.dumps(dict(symbol=symbol,retry=number,delaySeconds=delay)),flush=True)
                    # The range is event-only; even today's incomplete bar is not
                    # published. Existing bounded retry/access rules still apply.
                    try:
                        with engine.connect() as c:
                            for activity in ('ACQUIRE','STORE'):
                                rights=load_rights(c,dataset,activity,date.today(),'PERSONAL')
                                if not rights.allowed: raise PermissionError(activity+': '+rights.reason)
                        raw=fetch_chart(client,symbol,begin,end,max_window_days=1830,on_retry=on_retry)
                        with engine.begin() as c:
                            retained=retain_event_coverage(c,dataset_id=dataset,namespace_id=namespace,symbol=symbol,
                                raw_payload=raw,start=begin,end=end,received_at=datetime.now(timezone.utc))
                            finish_attempt(c,attempt,'COMPLETE',dict(retained,backoffs=backoffs),retained['runId'])
                    except (PermissionError,ValueError,httpx.HTTPError) as exc:
                        blocked=isinstance(exc,PermissionError) or isinstance(exc,httpx.HTTPStatusError) and exc.response.status_code in (401,403,429)
                        with engine.begin() as c:
                            finish_attempt(c,attempt,'BLOCKED' if blocked else 'FAILED',dict(errorType=type(exc).__name__,backoffs=backoffs))
                            finish_job(c,coverage_job,dict(eventCoverageOnly=True))
                        raise
                    print(json.dumps(dict(status='EVENT_COVERAGE_RETAINED',symbol=symbol,runId=retained['runId'])),flush=True)
                    time.sleep(args.request_spacing_seconds)
            with engine.begin() as c:
                finish_job(c,coverage_job,dict(eventCoverageOnly=True,symbols=len(gaps)))
        with engine.connect() as c:
            tx=c.begin()
            try:
                report=normalize_dataset(c,dataset,args.tenant,args.actor,symbols=args.symbols,
                    on_symbol=lambda result:print(json.dumps(dict(status='NORMALIZED',**result)),flush=True))
                if args.apply: tx.commit()
                else: tx.rollback()
            except Exception: tx.rollback();raise
        print(json.dumps(dict(applied=args.apply,**report)),flush=True)
        return 0 if report['status']=='COMPLETE' else 3
    finally: engine.dispose()


if __name__=='__main__': raise SystemExit(main())
