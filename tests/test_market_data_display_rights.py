"""Catalogue and instrument detail must enforce actual dataset and node scope."""
from datetime import date

from sqlalchemy import select

from apps.reference_api.db import get_engine
from apps.reference_api.repository import list_market_data_series, _load_market_data
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS
from tests.test_market_data_ingestion import setup_dataset, ingest


def catalogue(c, tenant, listing):
    return list_market_data_series(c, tenant, date(2026, 10, 5), date(2026, 10, 6), listing,
                                  None, 50, 0, 'v1', 'rights-test')


def test_profiled_data_requires_display_rights_even_with_tenant_entitlement():
    with get_engine().connect() as c:
        tx = c.begin()
        try:
            dataset, namespace, listing = setup_dataset(c)
            ingest(c, dataset, namespace)
            for tenant in (DEMO_IDS['tenant'], DEMO_IDS['second_tenant']):
                c.execute(m.tenant_dataset_entitlement.insert().values(tenant_id=tenant, dataset_id=dataset,
                    use_purpose='INTERNAL_REPORTING', valid_from=date(2026, 10, 1)))
            first = catalogue(c, DEMO_IDS['tenant'], listing)
            assert sum(len(s.observations) for s in first.data if str(s.dataset_id) == str(dataset)) == 4
            other = catalogue(c, DEMO_IDS['second_tenant'], listing)
            assert not any(str(s.dataset_id) == str(dataset) for s in other.data)
            c.execute(m.licence_activity_grant.update().where(m.licence_activity_grant.c.activity == 'DISPLAY').values(status='SUSPENDED'))
            denied = catalogue(c, DEMO_IDS['tenant'], listing)
            assert not any(str(s.dataset_id) == str(dataset) for s in denied.data)
            points = _load_market_data(c, DEMO_IDS['tenant'], [listing])
            assert not any(p.dataset == 'Synthetic Yahoo-shaped test' for p in points)
        finally:
            tx.rollback()


def test_catalogue_hides_private_node_and_does_not_double_count_corrections():
    import json
    from tests.test_market_data_ingestion import fixture_payload
    with get_engine().connect() as c:
        tx = c.begin()
        try:
            dataset, namespace, listing = setup_dataset(c)
            ingest(c, dataset, namespace)
            c.execute(m.tenant_dataset_entitlement.insert().values(tenant_id=DEMO_IDS['tenant'], dataset_id=dataset,
                use_purpose='INTERNAL_REPORTING', valid_from=date(2026, 10, 1)))
            raw = json.loads(fixture_payload())
            raw['chart']['result'][0]['indicators']['quote'][0]['close'][0] = 251.5
            ingest(c, dataset, namespace, 'corrected', json.dumps(raw))
            current = catalogue(c, DEMO_IDS['tenant'], listing)
            assert sum(len(s.observations) for s in current.data if str(s.dataset_id) == str(dataset)) == 4
            if not c.scalar(select(m.reference_node_scope.c.reference_node_id).where(m.reference_node_scope.c.reference_node_id == listing)):
                c.execute(m.reference_node_scope.insert().values(reference_node_id=listing,
                    scope_type='TENANT_PRIVATE', owner_tenant_id=DEMO_IDS['second_tenant']))
            else:
                c.execute(m.reference_node_scope.update().where(m.reference_node_scope.c.reference_node_id == listing).values(
                    scope_type='TENANT_PRIVATE', owner_tenant_id=DEMO_IDS['second_tenant']))
            assert not catalogue(c, DEMO_IDS['tenant'], listing).data
        finally:
            tx.rollback()


def test_observation_history_has_explicit_total_and_pages():
    with get_engine().connect() as c:
        tx = c.begin()
        try:
            dataset, namespace, listing = setup_dataset(c)
            ingest(c, dataset, namespace)
            c.execute(m.tenant_dataset_entitlement.insert().values(tenant_id=DEMO_IDS['tenant'], dataset_id=dataset,
                use_purpose='INTERNAL_REPORTING', valid_from=date(2026, 10, 1)))
            first = list_market_data_series(c, DEMO_IDS['tenant'], date(2026, 10, 5), date(2026, 10, 6),
                listing, 'CLOSE', 50, 0, 'v1', 'pages', observation_limit=1, observation_offset=0)
            second = list_market_data_series(c, DEMO_IDS['tenant'], date(2026, 10, 5), date(2026, 10, 6),
                listing, 'CLOSE', 50, 0, 'v1', 'pages', observation_limit=1, observation_offset=1)
            assert first.data[0].observation_total == second.data[0].observation_total == 2
            assert len(first.data[0].observations) == len(second.data[0].observations) == 1
            assert first.data[0].observations[0].market_date == '2026-10-05'
            assert second.data[0].observations[0].market_date == '2026-10-06'
            assert first.meta.total >= 1
        finally:
            tx.rollback()


def test_resolution_does_not_treat_display_permission_as_non_display_right():
    from datetime import datetime, timezone
    from security_master_schema.market_data_resolver import ResolutionRequest, _entitled_observations
    with get_engine().connect() as c:
        tx = c.begin()
        try:
            dataset, namespace, listing = setup_dataset(c)
            ingest(c, dataset, namespace)
            c.execute(m.tenant_dataset_entitlement.insert().values(tenant_id=DEMO_IDS['tenant'], dataset_id=dataset,
                use_purpose='INTERNAL_REPORTING', valid_from=date(2026, 10, 1)))
            request = ResolutionRequest(DEMO_IDS['tenant'], listing, DEMO_IDS['valuation_policy'],
                date(2026, 10, 6), DEMO_IDS['valuation_cut'], datetime(2026, 10, 8, tzinfo=timezone.utc), 'INTERNAL_REPORTING')
            rule = dict(series_type='CLOSE', market_data_series_id=None, dataset_id=dataset)
            assert not _entitled_observations(c, request, rule)
        finally:
            tx.rollback()


def test_series_api_rejects_invalid_observation_page_bounds():
    import asyncio
    from httpx import ASGITransport, AsyncClient
    from apps.reference_api.main import create_app
    async def run():
        async with AsyncClient(transport=ASGITransport(app=create_app()), base_url='http://test') as client:
            for query in ('observationLimit=0', 'observationLimit=1001', 'observationOffset=-1', 'observationOffset=100001'):
                response = await client.get('/v1/market-data/series?' + query,
                    headers={'X-Tenant-Id':str(DEMO_IDS['tenant']), 'X-User-Account-Id':str(DEMO_IDS['demo_user_account'])})
                assert response.status_code == 422
    asyncio.run(run())


def test_series_api_requires_market_data_module():
    from tests.test_api_reference_authority import request, revoke_module
    with get_engine().connect() as c:
        tx = c.begin()
        try:
            assert request(c, 'GET', '/v1/market-data/series').status_code == 200
            revoke_module(c, 'MARKET_DATA')
            assert request(c, 'GET', '/v1/market-data/series').status_code == 403
        finally:
            tx.rollback()


def test_shared_listing_does_not_expose_private_parent():
    with get_engine().connect() as c:
        tx = c.begin()
        try:
            dataset, namespace, listing = setup_dataset(c)
            ingest(c, dataset, namespace)
            c.execute(m.tenant_dataset_entitlement.insert().values(tenant_id=DEMO_IDS['tenant'], dataset_id=dataset,
                use_purpose='INTERNAL_REPORTING', valid_from=date(2026, 10, 1)))
            parent = c.scalar(select(m.listing.c.instrument_node_id).where(m.listing.c.listing_node_id == listing))
            c.execute(m.reference_node_scope.delete().where(m.reference_node_scope.c.reference_node_id == parent))
            c.execute(m.reference_node_scope.insert().values(reference_node_id=parent, scope_type='TENANT_PRIVATE', owner_tenant_id=DEMO_IDS['second_tenant']))
            assert not catalogue(c, DEMO_IDS['tenant'], listing).data
            assert not _load_market_data(c, DEMO_IDS['tenant'], [listing])
        finally:
            tx.rollback()
