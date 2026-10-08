"""A curated universe seed must reject bad identities and preserve operating data."""
from copy import deepcopy

import pytest
from sqlalchemy import select, func

from apps.reference_api.db import get_engine
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS


def test_manifest_has_verified_share_classes_and_primary_venues():
    from security_master_schema.index_universe_seed import load_manifest
    bundle = load_manifest()
    rows = bundle['securities']
    assert len(rows) == 543
    assert sum(r['universe'] == 'SP500' for r in rows) == 503
    assert sum(r['universe'] == 'CAC40' for r in rows) == 40
    by_symbol = {r['symbol']: r for r in rows}
    assert by_symbol['BRK.B']['isin'] == 'US0846707026'
    assert by_symbol['CBOE']['mic'] == 'BATS'
    assert by_symbol['MT']['mic'] == 'XAMS'
    assert by_symbol['GOOG']['isin'] != by_symbol['GOOGL']['isin']
    assert 'CTVA' not in by_symbol and 'WBD' not in by_symbol


@pytest.mark.parametrize('mutation', ['checksum', 'duplicate', 'venue', 'currency', 'missing'])
def test_manifest_rejects_incomplete_or_ambiguous_reference_data(mutation):
    from security_master_schema.index_universe_seed import load_manifest, validate_manifest
    bundle = deepcopy(load_manifest())
    if mutation == 'checksum': bundle['securities'][0]['isin'] = 'US0846707027'
    if mutation == 'duplicate': bundle['securities'][1] = deepcopy(bundle['securities'][0])
    if mutation == 'venue': bundle['securities'][0]['mic'] = 'XXXX'
    if mutation == 'currency': bundle['securities'][0]['currency'] = 'EUR'
    if mutation == 'missing': bundle['securities'].pop()
    with pytest.raises(ValueError): validate_manifest(bundle)


def test_seed_reuses_approved_shared_identities_without_financial_writes():
    from security_master_schema.index_universe_seed import seed
    from apps.reference_api.repository import search_instruments
    with get_engine().connect() as connection:
        tx = connection.begin()
        try:
            financial_tables = (m.trade, m.trade_lifecycle_event, m.market_data_observation, m.cash_balance)
            before = tuple(connection.scalar(select(func.count()).select_from(t)) for t in financial_tables)
            first = seed(connection, DEMO_IDS['demo_user_account'])
            assert first['createdInstruments'] == 543
            assert first['createdListings'] == 543
            second = seed(connection, DEMO_IDS['demo_user_account'])
            assert second['createdInstruments'] == second['createdListings'] == 0
            assert second['reusedInstruments'] == second['reusedListings'] == 543
            assert second['snapshots'] == first['snapshots']
            assert tuple(connection.scalar(select(func.count()).select_from(t)) for t in financial_tables) == before
            payload_id = first['sourcePayloadId']
            for table in (m.instrument_definition_version, m.listing_definition_version):
                assert connection.scalar(select(func.count()).select_from(table).where(
                    table.c.source_payload_id == payload_id, table.c.status == 'APPROVED',
                    table.c.approved_by_user_account_id == DEMO_IDS['demo_user_account'])) == 543
            for tenant in (DEMO_IDS['tenant'], DEMO_IDS['second_tenant']):
                result = search_instruments(connection, tenant, 'US0846707026', 10, 0, 'v1', 'seed-test')
                assert len(result.data) == 1
            listing = connection.execute(select(m.listing).where(m.listing.c.trading_symbol == 'BRK.B')).mappings().one()
            assert listing.unit_multiplier == listing.quote_factor == 1
            definition = connection.execute(select(m.listing_definition_version).where(
                m.listing_definition_version.c.listing_node_id == listing.listing_node_id)).mappings().one()
            assert definition.status == 'APPROVED' and definition.source_payload_id is not None
            from datetime import datetime
            from zoneinfo import ZoneInfo
            bzx = connection.scalar(select(m.market_venue.c.timezone_name).join(m.market_venue_identifier).where(
                m.market_venue_identifier.c.identifier_value == 'BATS'))
            # BZX session times are Eastern, even though the ISO location is Chicago.
            opening = datetime.fromisoformat('2026-10-06T13:30:00+00:00').astimezone(ZoneInfo(bzx))
            assert (opening.hour, opening.minute) == (9, 30)
            connection.execute(m.listing.update().where(m.listing.c.listing_node_id == listing.listing_node_id).values(unit_multiplier=99))
            with pytest.raises(ValueError, match='refusing overwrite'):
                seed(connection, DEMO_IDS['demo_user_account'])
        finally:
            tx.rollback()


def test_seed_rejects_retired_projections_and_invalid_snapshot_owner():
    from security_master_schema.index_universe_seed import seed
    with get_engine().connect() as connection:
        tx = connection.begin()
        try:
            seed(connection, DEMO_IDS['demo_user_account'])
            node = connection.scalar(select(m.financial_reference_node.c.reference_node_id).where(
                m.financial_reference_node.c.internal_code == 'PUBLIC_EQ_US0846707026'))
            savepoint = connection.begin_nested()
            connection.execute(m.instrument.update().where(m.instrument.c.instrument_node_id == node).values(is_current=False))
            with pytest.raises(ValueError, match='refusing overwrite'):
                seed(connection, DEMO_IDS['demo_user_account'])
            savepoint.rollback()
            owner = connection.scalar(select(m.financial_reference_node.c.reference_node_id).where(
                m.financial_reference_node.c.internal_code == 'PUBLIC_INDEX_CAC40'))
            connection.execute(m.index_terms.update().where(m.index_terms.c.index_node_id == owner).values(status='INACTIVE'))
            with pytest.raises(ValueError, match='refusing overwrite'):
                seed(connection, DEMO_IDS['demo_user_account'])
        finally:
            tx.rollback()


@pytest.mark.parametrize('database,environment_name', [('not_the_operating_database', 'local'), ('fortem_secm', 'production')])
def test_cli_refuses_non_operating_local_database_before_connecting(database, environment_name):
    import os
    from pathlib import Path
    import subprocess
    import sys
    environment = dict(os.environ, DATABASE_URL=f'postgresql+psycopg://unused:unused@localhost:54329/{database}', APP_ENV=environment_name)
    result = subprocess.run([sys.executable, 'scripts/seed_index_universe.py', '--apply'],
        cwd=Path(__file__).resolve().parents[1], env=environment, capture_output=True, text=True)
    assert result.returncode == 2
    assert 'restricted to local fortem_secm' in result.stderr


def test_seed_rejects_missing_operator_without_creating_reference_rows():
    from uuid import uuid4
    from security_master_schema.index_universe_seed import seed
    with get_engine().begin() as connection:
        before = connection.scalar(select(func.count()).select_from(m.financial_reference_node))
        with pytest.raises(ValueError, match='active recorded'):
            seed(connection, uuid4())
        assert connection.scalar(select(func.count()).select_from(m.financial_reference_node)) == before


@pytest.mark.parametrize('conflict', ['future_identifier', 'private_scope', 'snapshot_cash', 'payload_hash'])
def test_seed_conflicts_rollback_without_rewriting_identity_or_membership(conflict):
    from datetime import date
    from security_master_schema.index_universe_seed import seed
    with get_engine().connect() as connection:
        tx = connection.begin()
        try:
            report = seed(connection, DEMO_IDS['demo_user_account'])
            node = connection.scalar(select(m.financial_reference_node.c.reference_node_id).where(
                m.financial_reference_node.c.internal_code == 'PUBLIC_EQ_US0846707026'))
            if conflict == 'future_identifier':
                connection.execute(m.financial_reference_identifier.update().where(
                    m.financial_reference_identifier.c.reference_node_id == node).values(valid_from=date(2027, 1, 1)))
            if conflict == 'private_scope':
                connection.execute(m.reference_node_scope.update().where(m.reference_node_scope.c.reference_node_id == node).values(
                    scope_type='TENANT_PRIVATE', owner_tenant_id=DEMO_IDS['tenant']))
            if conflict == 'snapshot_cash':
                connection.execute(m.reference_constituent_snapshot_item.update().where(
                    m.reference_constituent_snapshot_item.c.reference_constituent_snapshot_id == report['snapshots']['CAC40']).values(cash_component=1))
            if conflict == 'payload_hash':
                connection.execute(m.source_payload.update().where(m.source_payload.c.source_payload_id == report['sourcePayloadId']).values(payload_sha256='0' * 64))
            with pytest.raises(ValueError, match='refusing overwrite'):
                seed(connection, DEMO_IDS['demo_user_account'])
        finally:
            tx.rollback()
