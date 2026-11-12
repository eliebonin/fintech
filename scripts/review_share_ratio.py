"""Preview/apply a bounded operator-reviewed share ratio on the local research DB."""
import argparse,json,sys
from pathlib import Path
from uuid import UUID
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review',type=Path,required=True)
    parser.add_argument('--actor',type=UUID,required=True)
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    from sqlalchemy import create_engine,select
    from security_master_schema.database_config import local_workspace_database
    from apps.market_data_ingestor.config import IngestorSettings
    from security_master_schema import models as m
    from market_data.split_replay import require_reviewer,source_snapshot,reviewed_payload,publish_split_decision
    settings=IngestorSettings.from_environment(); engine=create_engine(settings.database_url)
    if (settings.environment!='local' or engine.url.host not in ('localhost','127.0.0.1')
        or engine.url.port!=15432 or engine.url.database!=local_workspace_database()):
        parser.error('Restricted to the local personal platform_secm database on port 15432')
    manifest=json.loads(args.review.read_text(encoding='utf-8'))
    identity=UUID(manifest['corporateActionId']); review=manifest['review']
    try:
        with engine.begin() as c:
            require_reviewer(c,args.actor)
            action=c.execute(select(m.corporate_action).where(m.corporate_action.c.corporate_action_id==identity)).mappings().one()
            draft=reviewed_payload(source_snapshot(c,action),review)
            decision=publish_split_decision(c,args.actor,identity,review) if args.apply else None
            print(json.dumps(dict(mode='APPLIED' if args.apply else 'PREVIEW',actionId=str(identity),
                reviewId=str(decision) if decision else None,ratio=draft['ratio'],effectiveAt=draft['effectiveAt'],
                effectiveDate=draft['effectiveDate'],scope=draft['review']['entitlementScope'],
                wholeSharesOnly=draft['wholeSharesOnly'],sourceSnapshotHash=draft['sourceSnapshotHash']),default=str))
    finally: engine.dispose()


if __name__=='__main__': main()
