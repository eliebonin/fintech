"""Round-trip only this additive revision, in a database owned by this test."""
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4
from sqlalchemy import create_engine,text
from sqlalchemy.engine import make_url


def test_valuation_revision_round_trip_preserves_source_tables():
    base=make_url(os.environ['DATABASE_URL'])
    assert base.database.startswith('fortem_isolated_tests_')
    name='fortem_valuation_migration_'+uuid4().hex
    admin=create_engine(base.set(database='postgres'),isolation_level='AUTOCOMMIT')
    with admin.connect() as c: c.execute(text(f'CREATE DATABASE "{name}"'))
    target=base.set(database=name)
    environment=dict(os.environ,DATABASE_URL=target.render_as_string(hide_password=False))
    root=Path(__file__).resolve().parents[1]
    try:
        # This is the revision-69/70 round trip, not permission to downgrade
        # newer retained evidence (e.g. access history in revision 82).
        for command in [('upgrade','20261008_70'),('downgrade','20261007_68'),('upgrade','20261008_70')]:
            subprocess.run([sys.executable,'-m','alembic',*command],cwd=root,env=environment,check=True,capture_output=True)
        engine=create_engine(target)
        try:
            with engine.connect() as c:
                assert c.scalar(text('SELECT version_num FROM alembic_version'))=='20261008_70'
                assert c.scalar(text("SELECT to_regclass('trd.trade')"))=='trd.trade'
                assert c.scalar(text("SELECT column_default FROM information_schema.columns WHERE table_schema='nav' AND table_name='valuation_run_event' AND column_name='recorded_at'"))=='clock_timestamp()'
        finally: engine.dispose()
    finally:
        # Exact generated target, never an app or parent-suite database.
        assert name.startswith('fortem_valuation_migration_') and len(name.rsplit('_',1)[1])==32
        with admin.connect() as c: c.execute(text(f'DROP DATABASE "{name}"'))
        admin.dispose()
