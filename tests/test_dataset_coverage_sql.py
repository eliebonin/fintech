"""Execute the shared eligibility SQL without a network/database service."""
from datetime import date
from uuid import UUID
import pytest
from sqlalchemy import create_engine, literal, select
from market_data.entitlements import tenant_series_entitlement_clause

TENANT = UUID(int=1)
DATASET = UUID(int=2)
SERIES = UUID(int=3)


@pytest.fixture
def scope_db():
    engine = create_engine('sqlite+pysqlite:///:memory:')
    with engine.begin() as c:
        for schema in ('md', 'ten'):
            c.exec_driver_sql(f"ATTACH DATABASE ':memory:' AS {schema}")
        for statement in (
            'CREATE TABLE md.data_provider (data_provider_id text, owner_tenant_id text, status text)',
            'CREATE TABLE md.provider_product (provider_product_id text, data_provider_id text, status text)',
            'CREATE TABLE md.dataset (dataset_id text, provider_product_id text, status text, valid_from date, valid_to date)',
            'CREATE TABLE ten.tenant_dataset_entitlement (tenant_dataset_entitlement_id text, tenant_id text, dataset_id text, use_purpose text, coverage_mode text, status text, valid_from date, valid_to date)',
            'CREATE TABLE md.dataset_coverage_package (coverage_package_id text, dataset_id text, status text, valid_from date, valid_to date)',
            'CREATE TABLE md.market_data_series_coverage (market_data_series_id text, dataset_id text, coverage_package_id text)',
            'CREATE TABLE ten.tenant_dataset_coverage (tenant_dataset_entitlement_id text, dataset_id text, coverage_package_id text)',
        ):
            c.exec_driver_sql(statement)
        c.exec_driver_sql('INSERT INTO md.data_provider VALUES (?,NULL,\'ACTIVE\')', (UUID(int=4).hex,))
        c.exec_driver_sql('INSERT INTO md.provider_product VALUES (?,?,\'ACTIVE\')', (UUID(int=5).hex, UUID(int=4).hex))
        c.exec_driver_sql("INSERT INTO md.dataset VALUES (?,?,'ACTIVE','2026-10-01',NULL)", (DATASET.hex, UUID(int=5).hex))
        c.exec_driver_sql("INSERT INTO ten.tenant_dataset_entitlement VALUES (?,?,?,'VALUATION','SCOPED','ACTIVE','2026-10-01',NULL)", (UUID(int=6).hex, TENANT.hex, DATASET.hex))
        c.exec_driver_sql("INSERT INTO md.dataset_coverage_package VALUES (?,?,'ACTIVE','2026-10-01',NULL)", (UUID(int=7).hex, DATASET.hex))
        c.exec_driver_sql('INSERT INTO md.market_data_series_coverage VALUES (?,?,?)', (SERIES.hex, DATASET.hex, UUID(int=7).hex))
        c.exec_driver_sql('INSERT INTO ten.tenant_dataset_coverage VALUES (?,?,?)', (UUID(int=6).hex, DATASET.hex, UUID(int=7).hex))
        yield c
    engine.dispose()


def permitted(c, *, series=SERIES, tenant=TENANT, purpose='VALUATION', day=date(2026, 10, 8)):
    return bool(c.scalar(select(literal(True)).where(tenant_series_entitlement_clause(DATASET, series, tenant, purpose, day))))


def test_scoped_permission_requires_exact_series_dataset_tenant_and_purpose(scope_db):
    assert permitted(scope_db)
    assert not permitted(scope_db, series=UUID(int=30))
    assert not permitted(scope_db, series=None)
    assert not permitted(scope_db, tenant=UUID(int=10))
    assert not permitted(scope_db, purpose='INTERNAL_REPORTING')
    scope_db.exec_driver_sql('UPDATE md.market_data_series_coverage SET dataset_id=?', (UUID(int=20).hex,))
    assert not permitted(scope_db)


@pytest.mark.parametrize('change', ['grant', 'package', 'expired', 'future', 'dataset', 'provider', 'foreign_source'])
def test_inactive_or_out_of_scope_records_deny(scope_db, change):
    sql = {
        'grant': "UPDATE ten.tenant_dataset_entitlement SET status='SUSPENDED'",
        'package': "UPDATE md.dataset_coverage_package SET status='SUSPENDED'",
        'expired': "UPDATE md.dataset_coverage_package SET valid_to='2026-10-07'",
        'future': "UPDATE md.dataset_coverage_package SET valid_from='2026-10-09'",
        'dataset': "UPDATE md.dataset SET status='SUSPENDED'",
        'provider': "UPDATE md.data_provider SET status='SUSPENDED'",
        'foreign_source': f"UPDATE md.data_provider SET owner_tenant_id='{UUID(int=99).hex}'",
    }[change]
    scope_db.exec_driver_sql(sql)
    assert not permitted(scope_db)


def test_existing_dataset_wide_grants_and_inclusive_end_dates(scope_db):
    scope_db.exec_driver_sql("UPDATE md.dataset_coverage_package SET valid_to='2026-10-08'")
    assert permitted(scope_db)
    scope_db.exec_driver_sql("UPDATE ten.tenant_dataset_entitlement SET coverage_mode='DATASET'")
    assert permitted(scope_db, series=None)
    assert permitted(scope_db, series=UUID(int=30))
    scope_db.exec_driver_sql('UPDATE md.data_provider SET owner_tenant_id=?', (TENANT.hex,))
    assert permitted(scope_db)
