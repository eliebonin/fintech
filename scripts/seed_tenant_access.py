"""Add the three local tenant personas without reseeding business data.

Usage: .venv/Scripts/python.exe scripts/seed_tenant_access.py
Requires migrated schema and the existing platform/demo tenant foundation.
"""
import os
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sqlalchemy import create_engine, select
from security_master_schema.access_seed import seed_access
from security_master_schema import models as m


def main():
    if os.environ.get('APP_ENV','local') not in {'local','test','development'}:
        raise SystemExit('Access personas are local-development fixtures only')
    engine=create_engine(os.environ.get('DATABASE_URL','postgresql+psycopg://fortem:fortem_local_only@localhost:54329/fortem_secm'))
    with engine.begin() as c:
        # Serialize repeat runs without granting removed permissions again.
        from sqlalchemy import text
        c.execute(text('SELECT pg_advisory_xact_lock(2026100982)'))
        seed_access(c)
        print('Access seed complete. Active tenants:',c.scalar(select(__import__('sqlalchemy').func.count()).select_from(m.tenant).where(m.tenant.c.status=='ACTIVE')))
    engine.dispose()


if __name__=='__main__':main()
