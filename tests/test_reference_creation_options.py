"""Creation choices must come from scoped, effective configuration."""
from datetime import date
from uuid import uuid4
from sqlalchemy import select
from apps.reference_api.db import get_engine
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids


def test_only_effective_instrument_namespaces_and_visible_sources_are_offered():
    from security_master_schema.creation_options import equity_creation_options
    with get_engine().begin() as c:
        other=c.scalar(select(m.tenant.c.tenant_id).where(m.tenant.c.tenant_id!=ids['tenant']).limit(1))
        assert other is not None
        source=uuid4();private=uuid4();code='SYNTHETIC_'+uuid4().hex
        for identity,tenant in ((source,ids['tenant']),(private,other)):
            c.execute(m.integration_source_system.insert().values(integration_source_system_id=identity,tenant_id=tenant,system_code=code+str(identity),display_name='Sourced provider',source_kind='VENDOR',status='ACTIVE'))
            c.execute(m.reference_data_automation_policy.insert().values(policy_code=code+str(identity),display_name='Reviewed creation',source_system_id=identity,target_object_type='EQUITY',operation_type='CREATE',valid_from=date(2020,1,1),version_no=1,status='ACTIVE'))
            c.execute(m.external_id_namespace.insert().values(integration_source_system_id=identity,namespace_code=code+str(identity),external_object_type='INSTRUMENT',valid_from=date(2020,1,1),status='ACTIVE'))
        rows=equity_creation_options(c,ids['tenant'],date(2026,1,2))
        assert any(r['sourceSystemId']==str(source) for r in rows)
        assert not any(r['sourceSystemId']==str(private) for r in rows)
        import pytest
        from types import SimpleNamespace
        from apps.reference_api.repository import _equity_policy, RepositoryNotFound
        with pytest.raises(RepositoryNotFound):
            _equity_policy(c,ids['tenant'],SimpleNamespace(source_system_id=private,automation_policy_code=code+str(private),effective_from=date(2026,1,2)))
        c.execute(m.external_id_namespace.update().where(m.external_id_namespace.c.integration_source_system_id==source).values(valid_to=date(2025,12,31)))
        assert not any(r['sourceSystemId']==str(source) for r in equity_creation_options(c,ids['tenant'],date(2026,1,2)))


def test_latest_tenant_policy_overrides_shared_policy_and_listing_namespaces_are_not_canonical_choices():
    from security_master_schema.creation_options import equity_creation_options
    with get_engine().begin() as c:
        source=uuid4();code='SYNTHETIC_'+uuid4().hex
        c.execute(m.integration_source_system.insert().values(integration_source_system_id=source,system_code=code,display_name='Provider',source_kind='VENDOR',status='ACTIVE'))
        for tenant,version in ((None,5),(ids['tenant'],1),(ids['tenant'],2)):
            c.execute(m.reference_data_automation_policy.insert().values(policy_code=code,display_name='Reviewed creation',source_system_id=source,target_object_type='EQUITY',operation_type='CREATE',tenant_id=tenant,valid_from=date(2020,1,1),version_no=version,status='ACTIVE'))
        for kind in ('INSTRUMENT','LISTING'):
            c.execute(m.external_id_namespace.insert().values(integration_source_system_id=source,namespace_code=code+kind,external_object_type=kind,valid_from=date(2020,1,1),status='ACTIVE'))
        rows=[r for r in equity_creation_options(c,ids['tenant'],date(2026,1,2)) if r['sourceSystemId']==str(source)]
        assert len(rows)==1
        assert rows[0]['policyVersion']==2
        assert rows[0]['sourceNamespace']==code+'INSTRUMENT'


def test_creation_choices_http_adapter_uses_native_tenant_authority():
    import asyncio
    from httpx import AsyncClient
    from tests.api_client import FixtureASGITransport
    from apps.reference_api.main import create_app

    async def request():
        async with AsyncClient(transport=FixtureASGITransport(app=create_app()),base_url='http://test') as client:
            return await client.get('/v1/equity-creation-options?effectiveDate=2026-11-03',headers={
                'X-Tenant-Id':str(ids['tenant']), 'X-User-Account-Id':str(ids['demo_user_account'])})
    response=asyncio.run(request())
    assert response.status_code==200,response.text
    assert isinstance(response.json()['data'],list)


def test_creation_choices_permission_mapping_is_exact_and_read_only():
    from apps.reference_api.access_boundary import required_action
    assert required_action('/v1/equity-creation-options','GET')=='REFERENCE_PROPOSE'
    assert required_action('/v1/equity-creation-options','HEAD')=='REFERENCE_PROPOSE'
    assert required_action('/v1/equity-creation-options','POST') is None
    assert required_action('/v1/equity-creation-options/unrecognised','GET') is None
