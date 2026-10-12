"""Audited local operator command; dry-run unless --apply is explicit."""
import argparse
import json
import sys
from pathlib import Path
from uuid import UUID
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sqlalchemy import create_engine
from apps.market_data_ingestor.config import IngestorSettings
from market_data.providers.yahoo.valuation_permissions import enable_personal_valuation


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tenant-id',type=UUID,required=True)
    parser.add_argument('--actor-id',type=UUID,required=True)
    parser.add_argument('--dataset-id',type=UUID,action='append',required=True)
    parser.add_argument('--authorization-reference',required=True)
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    settings=IngestorSettings.from_environment()
    if settings.environment not in {'local','test'}:
        parser.error('Personal valuation activation is restricted to local/test environments')
    engine=create_engine(settings.database_url)
    try:
        with engine.connect() as c:
            tx=c.begin()
            try:
                results=[enable_personal_valuation(c,args.tenant_id,args.actor_id,dataset,args.authorization_reference) for dataset in args.dataset_id]
                if args.apply:tx.commit()
                else:tx.rollback()
            except Exception:
                tx.rollback()
                raise
        print(json.dumps(dict(applied=args.apply,datasets=results)))
    finally:
        engine.dispose()


if __name__=='__main__':main()
