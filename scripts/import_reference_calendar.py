"""Preview or publish a reviewed local exchange calendar; optional explicit activation."""
import argparse,json,sys
from pathlib import Path
from uuid import UUID
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    source=parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--review',type=Path)
    source.add_argument('--registry',type=Path)
    parser.add_argument('--actor',type=UUID,required=True)
    parser.add_argument('--apply',action='store_true')
    parser.add_argument('--activate-venue',action='store_true')
    args=parser.parse_args()
    if args.activate_venue and not args.apply: parser.error('Activation requires --apply')
    from sqlalchemy import create_engine,select
    from sqlalchemy.engine import make_url
    from security_master_schema.database_config import local_workspace_database
    from apps.market_data_ingestor.config import IngestorSettings
    from market_data.reference_calendar_import import build_reviewed_schedule,publish_reviewed_schedule,activate_calendar
    from security_master_schema import models as m
    settings=IngestorSettings.from_environment();url=make_url(settings.database_url)
    if settings.environment!='local' or url.host not in ('localhost','127.0.0.1') or url.port!=15432 or url.database!=local_workspace_database():
        parser.error('Operator command restricted to local platform_secm on port 15432')
    if args.registry:
        registry=json.loads(args.registry.read_text(encoding='utf-8'))
        reviews=registry['calendars']+registry.get('additionalVenues',[])
    else: reviews=[json.loads(args.review.read_text(encoding='utf-8'))]
    if len(reviews)>30 or len({r['mic'] for r in reviews})!=len(reviews):
        parser.error('Use at most 30 unique MIC schedules')
    drafts=[build_reviewed_schedule(review) for review in reviews]
    if not args.apply:
        print(json.dumps(dict(mode='PREVIEW',calendars=[dict(mic=r['mic'],status=r.get('publicationStatus','ACTIVE'),
            days=len(d['sessions']),provenance=d['provenance']) for r,d in zip(reviews,drafts)]),default=str));return
    engine=create_engine(settings.database_url)
    try:
        for review,draft in zip(reviews,drafts):
            with engine.begin() as c:
                calendar=publish_reviewed_schedule(c,args.actor,review)
                status=review.get('publicationStatus','ACTIVE');venue=None
                if args.activate_venue and status=='ACTIVE':
                    venue=activate_calendar(c,args.actor,calendar,review['mic'])
            print(json.dumps(dict(mode='APPLIED',mic=review['mic'],calendarId=str(calendar),status=status,
                days=len(draft['sessions']),activatedVenueIds=[str(venue)] if venue else [],
                activation='REVIEW_REQUIRED' if status!='ACTIVE' else 'CONNECTED' if venue else 'NO_VENUE_CHANGE')),flush=True)
    finally: engine.dispose()

if __name__=='__main__': main()
