"""Local personal-research backfill from retained Yahoo equity payloads; no HTTP."""
import argparse,json
from uuid import UUID
from sqlalchemy import create_engine,select
from security_master_schema import models as m
from .config import IngestorSettings
from market_data.providers.yahoo.corporate_actions import backfill_retained_actions


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tenant',type=UUID,required=True)
    parser.add_argument('--actor',type=UUID,required=True)
    parser.add_argument('--symbols',nargs='+')
    parser.add_argument('--apply',action='store_true',help='Commit events and their assessment job; default rolls back')
    args=parser.parse_args();settings=IngestorSettings.from_environment()
    if settings.environment not in ('local','test'): parser.error('Local/test personal project only')
    engine=create_engine(settings.database_url)
    try:
        with engine.connect() as c:
            tx=c.begin()
            try:
                dataset=c.scalar(select(m.dataset.c.dataset_id).where(m.dataset.c.dataset_code=='YAHOO_PERSONAL_EQUITY_DAILY'))
                if not dataset: raise ValueError('Personal Yahoo equity dataset not configured')
                report=backfill_retained_actions(c,dataset,args.tenant,args.actor,symbols=args.symbols)
                if args.apply: tx.commit()
                else: tx.rollback()
            except Exception:
                tx.rollback();raise
        assessments=report.pop('assessments')
        print(json.dumps(dict(applied=args.apply,**report,tteAssessments=[a for a in assessments if a['symbol']=='TTE.PA']),default=str))
        return 0 if report['status']=='COMPLETE' else 3
    finally: engine.dispose()


if __name__=='__main__': raise SystemExit(main())
