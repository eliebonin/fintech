"""Seed the reviewed October 6 universe. Default preview rolls back all writes."""
import argparse
import json
from pathlib import Path
import sys
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy.engine import make_url
from apps.reference_api.config import Settings
from apps.reference_api.db import get_engine
from security_master_schema.demo_data import DEMO_IDS
from security_master_schema.index_universe_seed import seed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='Commit the entire reference-only seed atomically')
    parser.add_argument('--actor', type=UUID, default=DEMO_IDS['demo_user_account'])
    args = parser.parse_args()
    settings = Settings.from_environment()
    url = make_url(settings.database_url)
    if settings.environment != 'local' or url.host not in {'localhost', '127.0.0.1'} or url.port != 54329 or url.database != 'fortem_secm':
        parser.error('This operator seed is restricted to local fortem_secm on port 54329.')
    with get_engine(settings).connect() as connection:
        tx = connection.begin()
        try:
            report = seed(connection, args.actor)
            if args.apply: tx.commit()
            else: tx.rollback()
        except Exception:
            tx.rollback()
            raise
    print(json.dumps(dict(database=url.database, mode='APPLIED' if args.apply else 'ROLLED_BACK_PREVIEW', **report), indent=2))


if __name__ == '__main__':
    main()
