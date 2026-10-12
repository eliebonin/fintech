"""Assess/seed historical booking availability; default preview rolls back."""
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
from apps.market_data_ingestor.index_trading_history import apply_history, export_evidence

DEFAULT = Path(__file__).resolve().parents[1] / 'security_master_schema/data/index_trading_starts_2026_10_08.json'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--export', action='store_true', help='Generate evidence from retained Yahoo history; no database writes')
    parser.add_argument('--manifest', type=Path, default=DEFAULT)
    parser.add_argument('--actor', type=UUID, default=DEMO_IDS['demo_user_account'])
    args = parser.parse_args()
    settings = Settings.from_environment()
    url = make_url(settings.database_url)
    if settings.environment != 'local' or url.host not in {'localhost','127.0.0.1'} or url.port != 54329 or url.database != 'fortem_secm':
        parser.error('This operator seed is restricted to local fortem_secm on port 54329.')
    if args.export and args.apply:
        parser.error('Export is read-only; inspect its evidence before a separate --apply.')
    if args.export:
        if args.manifest.exists():
            parser.error('Refusing to overwrite existing evidence.')
        with get_engine(settings).connect() as c:
            bundle = export_evidence(c)
        args.manifest.write_text(json.dumps(bundle, indent=2)+'\n', encoding='utf-8')
        print(json.dumps(dict(mode='EXPORTED', entries=len(bundle['securities']), manifest=str(args.manifest))))
        return
    with get_engine(settings).connect() as c:
        tx = c.begin()
        try:
            report = apply_history(c, args.actor, args.manifest)
            if args.apply: tx.commit()
            else: tx.rollback()
        except Exception:
            tx.rollback()
            raise
    print(json.dumps(dict(mode='APPLIED' if args.apply else 'ROLLED_BACK_PREVIEW', **report), indent=2))


if __name__ == '__main__':
    main()
