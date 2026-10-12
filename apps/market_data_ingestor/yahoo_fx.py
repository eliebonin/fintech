"""Serial GBP FX backfill, with bounded requests and separately committed jobs."""
import argparse
from datetime import date,datetime,timedelta,timezone
import json
import time
from uuid import UUID
import httpx
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from security_master_schema.demo_data import DEMO_IDS
from market_data.providers.yahoo.adapter import fetch_chart
from market_data.providers.yahoo.fx_storage import configure_fx,ingest_fx,SYMBOLS
from market_data.jobs import start_job,start_attempt,finish_attempt,finish_job
from market_data.outcomes import delivery_outcome
from .config import IngestorSettings

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply',action='store_true')
    parser.add_argument('--acknowledge-personal-access',action='store_true')
    parser.add_argument('--tenant',type=UUID,default=DEMO_IDS['tenant'])
    parser.add_argument('--actor',type=UUID,default=DEMO_IDS['demo_user_account'])
    parser.add_argument('--start',type=date.fromisoformat,default=date(2021,10,8))
    parser.add_argument('--through',type=date.fromisoformat,default=date.today()-timedelta(days=1))
    parser.add_argument('--request-spacing-seconds',type=float,default=5)
    parser.add_argument('--cutoff-interval',choices=['5m','1h'],default='5m',help='Hourly history supports a 730-day lookback; five-minute supports 60 days. Definitions remain separate.')
    parser.add_argument('--cutoff-only',action='store_true',help='Skip daily history already stored')
    args=parser.parse_args();settings=IngestorSettings.from_environment();url=make_url(settings.database_url)
    if settings.environment!='local' or url.host not in {'localhost','127.0.0.1'} or url.port!=54329 or url.database!='fortem_secm':parser.error('FX research import is restricted to local fortem_secm:54329')
    if args.start>args.through or args.through>=date.today() or (args.through-args.start).days+1>1830 or not 1<=args.request_spacing_seconds<=60:parser.error('Use completed prior dates, at most 1830 days and 1..60 second request spacing')
    if args.apply and not args.acknowledge_personal_access:parser.error('Acquisition requires --acknowledge-personal-access; personal scope is not legal clearance')
    engine=create_engine(settings.database_url,pool_pre_ping=True)
    with engine.connect() as c:
        tx=c.begin()
        try:
            config=configure_fx(c,args.tenant,args.actor)
            if args.apply:tx.commit()
            else:tx.rollback()
        except Exception:tx.rollback();raise
    print(json.dumps({'mode':'APPLY' if args.apply else 'ROLLED_BACK_PREVIEW','datasetId':str(config['datasetId']),'symbols':SYMBOLS,'dailyStart':str(args.start),'through':str(args.through),'cutoffMethod':f'Exact completed {args.cutoff_interval} bar at 16:00 local; not an official benchmark'},default=str),flush=True)
    if not args.apply:engine.dispose();return 0
    results=[]
    try:
        with httpx.Client() as client:
            windows=[] if args.cutoff_only else [('1d',args.start)]
            windows.append((args.cutoff_interval,max(args.start,date.today()-timedelta(days=729 if args.cutoff_interval=='1h' else 59))))
            for interval,start in windows:
                if start>args.through:continue
                with engine.begin() as c:job=start_job(c,config['datasetId'],config['namespaceId'],args.tenant,args.actor,list(SYMBOLS),start,args.through)
                for symbol in SYMBOLS:
                    with engine.begin() as c:attempt=start_attempt(c,job,symbol,start,args.through)
                    try:
                        raw=fetch_chart(client,symbol,start,args.through,interval=interval,max_window_days={'1d':1830,'5m':60,'1h':730}[interval],
                            on_retry=lambda n,delay:print(json.dumps({'event':'RETRY','symbol':symbol,'retry':n,'delaySeconds':delay}),flush=True))
                        with engine.begin() as c:
                            report=ingest_fx(c,config=config,symbol=symbol,raw_payload=raw,start=start,end=args.through,received_at=datetime.now(timezone.utc),interval=interval)
                        status=delivery_outcome(report)
                        with engine.begin() as c:finish_attempt(c,attempt,status,report,UUID(report['runId']))
                        result={'symbol':symbol,'interval':interval,'status':status,'accepted':report['accepted'],'duplicates':report['duplicates'],'rejected':report['rejected'],'runId':report['runId']}
                    except Exception as exc:
                        result={'symbol':symbol,'interval':interval,'status':'FAILED','reason':str(exc)[:500]}
                        with engine.begin() as c:finish_attempt(c,attempt,'FAILED',result)
                    results.append(result);print(json.dumps(result),flush=True)
                    time.sleep(args.request_spacing_seconds)
                with engine.begin() as c:status=finish_job(c,job,{'interval':interval})
                print(json.dumps({'jobId':str(job),'status':status,'interval':interval}),flush=True)
        return 0 if all(r['status']=='COMPLETE' for r in results) else 3
    finally:engine.dispose()

if __name__=='__main__':raise SystemExit(main())
