"""Mixed-dataset coverage must restrict actual series, not provider names."""
from datetime import date

import pytest
from sqlalchemy import select

from apps.reference_api.db import get_engine
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS
from tests.test_market_data_ingestion import setup_dataset, ingest


def setup_coverage(c):
    dataset, namespace, listing = setup_dataset(c)
    ingest(c, dataset, namespace)
    provider = c.scalar(select(m.data_provider.c.data_provider_id).limit(1))
    packages = {}
    for code in ('COMEX', 'NYMEX'):
        packages[code] = c.scalar(m.dataset_coverage_package.insert().values(
            dataset_id=dataset, package_code=code, display_name=f'Synthetic {code} EoD',
            content_owner_provider_id=provider, information_timing='END_OF_DAY',
            evidence_reference='Synthetic test only', valid_from=date(2026, 10, 1))
            .returning(m.dataset_coverage_package.c.coverage_package_id))
    series = c.execute(select(m.market_data_series).where(
        m.market_data_series.c.default_dataset_id == dataset).order_by(m.market_data_series.c.series_type)).mappings().all()
    for row, code in zip(series, ('COMEX', 'NYMEX')):
        c.execute(m.market_data_series_coverage.insert().values(dataset_id=dataset,
            market_data_series_id=row['market_data_series_id'], coverage_package_id=packages[code]))
    entitlements = {}
    for purpose in ('VALUATION', 'INTERNAL_REPORTING'):
        eid = c.scalar(m.tenant_dataset_entitlement.insert().values(
            tenant_id=DEMO_IDS['tenant'], dataset_id=dataset, use_purpose=purpose,
            coverage_mode='SCOPED', valid_from=date(2026, 10, 1)).returning(
                m.tenant_dataset_entitlement.c.tenant_dataset_entitlement_id))
        entitlements[purpose] = eid
        c.execute(m.tenant_dataset_coverage.insert().values(
            tenant_dataset_entitlement_id=eid, dataset_id=dataset,
            coverage_package_id=packages['COMEX']))
    return dataset, listing, series, packages, entitlements


def test_scoped_grant_selects_only_its_package_and_whole_dataset_remains_compatible():
    from market_data.entitlements import tenant_series_entitlement_clause
    with get_engine().connect() as c:
        tx = c.begin()
        try:
            dataset, _, series, _, entitlements = setup_coverage(c)
            table = m.market_data_series
            def visible(tenant=DEMO_IDS['tenant']):
                return list(c.scalars(select(table.c.market_data_series_id).where(
                    table.c.default_dataset_id == dataset,
                    tenant_series_entitlement_clause(table.c.default_dataset_id,
                        table.c.market_data_series_id, tenant, 'VALUATION', date(2026, 10, 8)))))
            assert visible() == [series[0]['market_data_series_id']]
            assert visible(DEMO_IDS['second_tenant']) == []
            c.execute(m.market_data_series_coverage.delete().where(
                m.market_data_series_coverage.c.market_data_series_id == series[0]['market_data_series_id']))
            assert visible() == []
            c.execute(m.tenant_dataset_entitlement.update().where(
                m.tenant_dataset_entitlement.c.tenant_dataset_entitlement_id == entitlements['VALUATION']
            ).values(coverage_mode='DATASET'))
            assert set(visible()) == {row['market_data_series_id'] for row in series}
        finally:
            tx.rollback()


def test_resolution_filters_the_actual_source_series_before_selecting_a_price():
    from datetime import datetime, timezone
    from security_master_schema.market_data_resolver import ResolutionRequest, _entitled_observations
    with get_engine().connect() as c:
        tx = c.begin()
        try:
            dataset, listing, series, _, _ = setup_coverage(c)
            assignment = c.scalar(select(m.dataset_licence_assignment.c.dataset_licence_assignment_id).where(
                m.dataset_licence_assignment.c.dataset_id == dataset))
            c.execute(m.dataset_right_requirement.insert().values(dataset_id=dataset, activity='NON_DISPLAY',
                requirement_code='SOURCE_TERMS', dataset_licence_assignment_id=assignment))
            c.execute(m.licence_activity_grant.insert().values(dataset_licence_assignment_id=assignment,
                activity='NON_DISPLAY', usage_scope='PERSONAL', evidence_basis='PERSONAL_DECLARATION',
                evidence_reference='Synthetic calculation test only', valid_from=date(2026, 10, 1)))
            request = ResolutionRequest(DEMO_IDS['tenant'], listing, DEMO_IDS['valuation_policy'],
                date(2026, 10, 6), DEMO_IDS['valuation_cut'], datetime(2026, 10, 8, tzinfo=timezone.utc), 'VALUATION')
            def candidates(row):
                return _entitled_observations(c, request, dict(series_type=row['series_type'],
                    market_data_series_id=row['market_data_series_id'], dataset_id=dataset, pricing_convention='LEGACY'))
            assert len(candidates(series[0])) == 2
            assert candidates(series[1]) == []
            c.execute(m.market_data_series_coverage.delete().where(m.market_data_series_coverage.c.dataset_id == dataset))
            assert candidates(series[0]) == []
        finally:
            tx.rollback()


def test_database_rejects_cross_dataset_package_grants():
    from sqlalchemy.exc import IntegrityError
    with get_engine().connect() as c:
        tx = c.begin()
        try:
            dataset, _, _, packages, entitlements = setup_coverage(c)
            other = c.scalar(m.dataset.insert().values(
                provider_product_id=c.scalar(select(m.provider_product.c.provider_product_id).limit(1)),
                dataset_code='OTHER_COVERAGE_TEST', display_name='Other synthetic dataset',
                data_domain='MARKET_DATA', valid_from=date(2026, 10, 1)).returning(m.dataset.c.dataset_id))
            with pytest.raises(IntegrityError), c.begin_nested():
                c.execute(m.tenant_dataset_coverage.insert().values(
                    tenant_dataset_entitlement_id=entitlements['VALUATION'], dataset_id=other,
                    coverage_package_id=packages['NYMEX']))
        finally:
            tx.rollback()


def test_migration_roundtrip_and_guard_against_discarding_coverage_evidence():
    import importlib.util
    from pathlib import Path
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import inspect
    spec = importlib.util.spec_from_file_location('coverage_migration',
        Path(__file__).resolve().parents[1] / 'alembic/versions/20261008_73_dataset_coverage.py')
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    with get_engine().connect() as c:
        tx = c.begin()
        try:
            context = MigrationContext.configure(c)
            with Operations.context(context):
                migration.downgrade()
                assert 'coverage_mode' not in {column['name'] for column in inspect(c).get_columns('tenant_dataset_entitlement', schema='ten')}
                migration.upgrade()
                assert 'coverage_mode' in {column['name'] for column in inspect(c).get_columns('tenant_dataset_entitlement', schema='ten')}
                setup_coverage(c)
                with pytest.raises(RuntimeError, match='Coverage evidence exists'):
                    migration.downgrade()
        finally:
            tx.rollback()


def test_scoped_catalogue_detail_and_frozen_evidence_do_not_disclose_other_packages():
    from apps.reference_api.repository import list_market_data_series, _load_market_data
    from market_data.display_access import assert_dataset_display, EvidenceDisplayDenied
    with get_engine().connect() as c:
        tx = c.begin()
        try:
            dataset, listing, series, packages, _ = setup_coverage(c)
            result = list_market_data_series(c, DEMO_IDS['tenant'], date(2026, 10, 5), date(2026, 10, 6),
                listing, None, 50, 0, 'v1', 'coverage-test')
            actual = [row for row in result.data if row.dataset_id == dataset]
            assert len(actual) == 1
            assert actual[0].series_id == series[0]['market_data_series_id']
            assert actual[0].observation_total == 2
            points = [row for row in _load_market_data(c, DEMO_IDS['tenant'], [listing])
                if row.dataset == 'Synthetic Yahoo-shaped test']
            assert len(points) == 2
            allowed = [(dataset, series[0]['market_data_series_id'])]
            denied = [(dataset, series[1]['market_data_series_id'])]
            assert_dataset_display(c, DEMO_IDS['tenant'], {dataset}, series_contexts=allowed)
            with pytest.raises(EvidenceDisplayDenied):
                assert_dataset_display(c, DEMO_IDS['tenant'], {dataset}, series_contexts=denied)
            with pytest.raises(EvidenceDisplayDenied):
                assert_dataset_display(c, DEMO_IDS['tenant'], {dataset})
            c.execute(m.dataset_coverage_package.update().where(
                m.dataset_coverage_package.c.coverage_package_id == packages['COMEX']).values(status='SUSPENDED'))
            with pytest.raises(EvidenceDisplayDenied):
                assert_dataset_display(c, DEMO_IDS['tenant'], {dataset}, series_contexts=allowed)
        finally:
            tx.rollback()
