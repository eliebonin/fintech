"""Run pytest against a disposable database, never the operator's app data.

Usage: .venv/Scripts/python.exe scripts/run_isolated_python_tests.py tests/... -q
The legacy suite contains hard-coded local app URLs. Redirect those engines only
inside this test process, before importing test modules; do not alter app settings.
"""
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

import sqlalchemy
from sqlalchemy import text
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.local_database_config import migration_url
APP_URL = make_url(migration_url(test_admin=True)).set(database="platform_secm")


def main():
    name = "platform_isolated_tests_" + uuid4().hex
    isolated = APP_URL.set(database=name)
    print('Owned disposable test database:',name,flush=True)
    original = sqlalchemy.create_engine
    admin = original(APP_URL.set(database="postgres"), isolation_level="AUTOCOMMIT")
    engines = []
    previous = os.environ.get("DATABASE_URL")
    with admin.connect() as connection:
        connection.execute(text(f'CREATE DATABASE "{name}"'))
    try:
        os.environ["DATABASE_URL"] = isolated.render_as_string(hide_password=False)
        subprocess.run([sys.executable,"-m","alembic","upgrade","head"],cwd=ROOT,check=True)

        def test_engine(url, *args, **kwargs):
            parsed = make_url(url)
            local={'localhost','127.0.0.1','::1'}
            same_host=parsed.host==APP_URL.host or (parsed.host in local and APP_URL.host in local)
            if same_host and (parsed.port,parsed.database)==(APP_URL.port,APP_URL.database):
                url = isolated
            engine = original(url, *args, **kwargs)
            engines.append(engine)
            return engine

        sqlalchemy.create_engine = test_engine
        # A fresh migrated database is not an operating fixture. Seed synthetic
        # state before collection so HTTP tests do not depend on another test
        # module running its loader first.
        from security_master_schema.demo_data import load_demo_data,DEMO_IDS
        fixture_engine = test_engine(isolated)
        load_demo_data(fixture_engine)
        # Fresh fixtures explicitly materialize the same profile foundation as
        # local cutover. This is setup, never a resolver/runtime fallback.
        from trading.profiles.migration import backfill_profiles
        with fixture_engine.begin() as seed_connection:
            backfill_profiles(seed_connection,DEMO_IDS['demo_user_account'])
        import pytest
        return pytest.main(sys.argv[1:] or ["-q"])
    finally:
        sqlalchemy.create_engine = original
        if previous is None: os.environ.pop("DATABASE_URL", None)
        else: os.environ["DATABASE_URL"] = previous
        for engine in engines: engine.dispose()
        assert name.startswith("platform_isolated_tests_") and len(name.rsplit("_",1)[1]) == 32
        with admin.connect() as connection:
            connection.execute(text(f'DROP DATABASE "{name}"'))
        admin.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
