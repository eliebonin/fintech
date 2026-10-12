"""Regressions for the live catalogue's historical-observation read path."""
from datetime import date

from sqlalchemy import select, text
from apps.reference_api.db import get_engine
from apps.reference_api.repository import _market_data_display_entitlement_clause, _load_market_data
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS
from tests.test_market_data_ingestion import setup_dataset, ingest


def test_profiled_observations_do_not_change_unrelated_legacy_entitlement():
    with get_engine().connect() as c:
        tx = c.begin()
        try:
            legacy_dataset = DEMO_IDS['multi_asset_dataset']
            c.execute(m.tenant_dataset_entitlement.update().where(
                m.tenant_dataset_entitlement.c.tenant_id == DEMO_IDS['tenant'],
                m.tenant_dataset_entitlement.c.dataset_id == legacy_dataset,
            ).values(use_purpose='VALUATION'))
            before = _load_market_data(c, DEMO_IDS['tenant'], [DEMO_IDS['bond_instrument_node']])
            assert before
            dataset, namespace, listing = setup_dataset(c)
            ingest(c, dataset, namespace)
            legacy_ids = select(m.market_data_observation.c.market_data_observation_id).where(
                m.market_data_observation.c.dataset_id == legacy_dataset,
                _market_data_display_entitlement_clause(m.market_data_observation.c.dataset_id, DEMO_IDS['tenant']),
            )
            assert list(c.scalars(legacy_ids)), 'An unrelated profiled dataset must not suppress legacy observations'
            assert _load_market_data(c, DEMO_IDS['tenant'], [DEMO_IDS['bond_instrument_node']]) == before
            # Profiled datasets still require INTERNAL_REPORTING, independently of legacy datasets.
            c.execute(m.tenant_dataset_entitlement.insert().values(
                tenant_id=DEMO_IDS['tenant'], dataset_id=dataset,
                use_purpose='VALUATION', valid_from=date(2026, 10, 1)))
            assert not list(c.scalars(select(m.market_data_observation.c.market_data_observation_id).where(
                m.market_data_observation.c.dataset_id == dataset,
                _market_data_display_entitlement_clause(m.market_data_observation.c.dataset_id, DEMO_IDS['tenant']),
            )))
        finally:
            tx.rollback()


def test_observation_read_indexes_support_latest_values_and_correction_lookup():
    with get_engine().connect() as c:
        indexes = dict(c.execute(text("SELECT indexname, indexdef FROM pg_indexes WHERE schemaname='md' AND tablename='market_data_observation'")).all())
    latest = indexes.get('ix_md_observation_accepted_latest', '')
    correction = indexes.get('ix_md_observation_accepted_supersedes', '')
    assert 'market_data_series_id, market_date DESC NULLS LAST, observed_at_utc DESC, received_at_utc DESC' in latest
    assert 'supersedes_observation_id' in correction
    assert "ACCEPTED" in latest and "ACCEPTED" in correction
    assert 'supersedes_observation_id IS NOT NULL' in correction


def test_large_history_catalogue_completes_within_read_budget():
    from apps.reference_api.repository import search_instruments
    with get_engine().connect() as c:
        tx = c.begin()
        try:
            # Repeated synthetic observations intentionally have no source key:
            # exercise historical volume without editing the original evidence.
            c.execute(text("""
                INSERT INTO md.market_data_observation
                    (market_data_series_id, dataset_id, observed_at_utc, received_at_utc,
                     value, market_date, quality_status)
                SELECT o.market_data_series_id, o.dataset_id, o.observed_at_utc,
                    o.received_at_utc, o.value, o.market_date, 'ACCEPTED'
                FROM (SELECT * FROM md.market_data_observation WHERE dataset_id=:dataset LIMIT 1) o
                CROSS JOIN generate_series(1, 100000)
            """), {'dataset': DEMO_IDS['multi_asset_dataset']})
            c.execute(text('ANALYZE md.market_data_observation'))
            c.execute(text("SET LOCAL statement_timeout = '2000ms'"))
            page = search_instruments(c, DEMO_IDS['tenant'], '', 25, 0, 'v1', 'large-history')
            assert page.data and page.meta.total >= len(page.data)
        finally:
            tx.rollback()


def test_index_migration_round_trip_preserves_observations():
    # Concurrent index DDL commits independently. Use a database owned by this
    # test, not a downgrade of the parent's current, forward-only schema.
    import importlib.util
    import os
    from pathlib import Path
    from uuid import uuid4
    from sqlalchemy import create_engine
    from sqlalchemy.engine import make_url
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    url=make_url(os.environ['DATABASE_URL'])
    assert url.database.startswith('fortem_isolated_tests_')
    name='fortem_index_migration_'+uuid4().hex
    admin=create_engine(url.set(database='postgres'),isolation_level='AUTOCOMMIT')
    with admin.connect() as c:
        c.execute(text(f'CREATE DATABASE "{name}"'))
    engine=create_engine(url.set(database=name))
    spec=importlib.util.spec_from_file_location('index_migration',
        Path(__file__).resolve().parents[1]/'alembic/versions/20261008_71_catalogue_observation_indexes.py')
    migration=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    try:
        with engine.begin() as c:
            c.execute(text("""CREATE SCHEMA md;
                CREATE TABLE md.market_data_observation (
                    market_data_series_id uuid, market_date date,
                    observed_at_utc timestamptz, received_at_utc timestamptz,
                    quality_status text, supersedes_observation_id uuid, value numeric);
                INSERT INTO md.market_data_observation VALUES
                    ('00000000-0000-7000-8000-000000000001','2026-10-06',
                     '2026-10-06 16:00+00','2026-10-06 17:00+00','ACCEPTED',NULL,123.456789);
            """))
        with engine.connect() as c:
            before=c.execute(text('SELECT * FROM md.market_data_observation')).all()
            c.commit()
            with Operations.context(MigrationContext.configure(c)):
                migration.upgrade()
                migration.downgrade()
                migration.upgrade()
                migration.upgrade()
            assert c.execute(text('SELECT * FROM md.market_data_observation')).all()==before
            indexes=set(c.scalars(text("SELECT indexname FROM pg_indexes WHERE schemaname='md'")))
            assert set(migration.INDEX_DEFINITIONS).issubset(indexes)
    finally:
        engine.dispose()
        assert name.startswith('fortem_index_migration_') and len(name.rsplit('_',1)[1])==32
        with admin.connect() as c:
            c.execute(text(f'DROP DATABASE "{name}"'))
        admin.dispose()
