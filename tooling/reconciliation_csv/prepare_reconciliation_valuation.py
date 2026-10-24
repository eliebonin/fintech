"""Guarded local operator. Default is a full transaction rolled back, not activation."""
import argparse
import json
import os
from pathlib import Path
import sys
from uuid import UUID
from sqlalchemy import create_engine

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from security_master_schema.database_config import local_workspace_database
from tooling.reconciliation_csv.reconciliation_eligibility import prepare


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('tenant','actor','platform-actor','strategy','source','prices-dataset','fx-dataset'):
        parser.add_argument('--'+name,required=True,type=UUID)
    parser.add_argument('--declaration',required=True,help='Attributable owner instruction, personal use only; not provider permission.')
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args();engine=create_engine(os.environ['DATABASE_URL'])
    if (os.environ.get('APP_ENV','local')!='local' or engine.url.host not in ('localhost','127.0.0.1')
        or engine.url.port!=54329 or engine.url.database!=local_workspace_database()):
        raise PermissionError('Explicit local workspace database required')
    try:
        with engine.connect() as c:
            tx=c.begin()
            try:
                result=prepare(c,args.tenant,args.actor,args.platform_actor,args.strategy,args.source,args.prices_dataset,args.fx_dataset,args.declaration)
                if args.apply:tx.commit()
                else:tx.rollback()
                print(json.dumps(dict(status='APPLIED' if args.apply else 'REHEARSED_ROLLED_BACK',**result),default=str))
            except BaseException:
                tx.rollback();raise
    finally:engine.dispose()


if __name__=='__main__':main()
