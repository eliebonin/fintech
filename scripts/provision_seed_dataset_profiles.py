"""Explicit local backfill for exact loader-owned invented datasets only."""
import argparse
from pathlib import Path
import sys
from uuid import UUID
from dotenv import dotenv_values
from sqlalchemy import create_engine,text
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.local_database_config import migration_url
from security_master_schema.synthetic_market_data import provision_seed_profiles,ORIGIN
from security_master_schema.access_management import require_platform,audit


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true',required=True);parser.parse_args()
    config=dotenv_values(ROOT/'.env.local-access')
    if config.get('APP_ENV') not in {'local','test','development'}:raise RuntimeError('Local seed governance requires explicit local configuration')
    actor=UUID(config['LOCAL_PLATFORM_OPERATOR_ID'])
    engine=create_engine(migration_url(),hide_parameters=True)
    try:
        with engine.begin() as c:
            require_platform(c,actor)
            c.execute(text('SELECT pg_advisory_xact_lock(20261030106)'))
            changed=provision_seed_profiles(c)
            if changed:audit(c,actor,None,'SYNTHETIC_DATASET_PROFILES',{'datasetIds':[str(v) for v in changed],'origin':ORIGIN})
        print('Invented seed datasets explicitly governed:',len(changed),'; existing profiles were preserved.')
    finally:engine.dispose()


if __name__=='__main__':main()
