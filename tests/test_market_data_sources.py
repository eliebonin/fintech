"""Real configuration API must not manufacture market-data permissions."""
from datetime import date
from uuid import uuid4
from sqlalchemy import select
from apps.reference_api.db import get_engine
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from tests.test_dataset_coverage import setup_coverage


def test_catalogue_exposes_authorised_package_metadata_without_contract_evidence():
    from apps.reference_api.market_data_sources import catalogue
    with get_engine().connect() as c:
        tx=c.begin()
        try:
            dataset, _, _, _, _=setup_coverage(c)
            result=catalogue(c,ids['tenant'],ids['demo_user_account'])
            source=next(row for row in result['sources'] if row['datasetId']==dataset)
            assert source['coverageMode']=='SCOPED'
            assert [p['code'] for p in source['packages']]==['COMEX']
            assert source['nonDisplayAllowed'] is False
            assert 'Synthetic test only' not in str(source)
            import pytest
            with pytest.raises(PermissionError):
                catalogue(c,ids['second_tenant'],ids['demo_user_account'])
        finally:tx.rollback()


def test_http_catalogue_contract_and_platform_write_denial():
    from tests.test_composite_policy_api import call
    result=call('GET','/v1/market-data/sources')
    assert result.status_code==200, result.text
    assert result.json()['canManage'] is True
    assert result.json()['canManagePlatform'] is False
    with get_engine().connect() as c:
        type_id=c.scalar(select(m.instrument_type.c.instrument_type_id).limit(1))
    payload=dict(instrumentTypeId=str(type_id),scope='PLATFORM',mode='CUSTOM',datasetIds=[])
    assert call('POST','/v1/market-data/source-priorities',payload).status_code==403
    payload['scope']='TENANT'
    payload['datasetIds']=[str(uuid4())]
    assert call('POST','/v1/market-data/source-priorities',payload).status_code==422


def test_catalogue_does_not_confuse_reporting_coverage_with_valuation_coverage():
    from apps.reference_api.market_data_sources import catalogue
    with get_engine().connect() as c:
        tx=c.begin()
        try:
            dataset,_,_,_,entitlements=setup_coverage(c)
            c.execute(m.tenant_dataset_entitlement.update().where(
                m.tenant_dataset_entitlement.c.tenant_dataset_entitlement_id==entitlements['INTERNAL_REPORTING']).values(coverage_mode='DATASET'))
            source=next(s for s in catalogue(c,ids['tenant'],ids['demo_user_account'])['sources'] if s['datasetId']==dataset)
            scopes={g['purpose']:g for g in source['entitlementScopes']}
            assert scopes['VALUATION']['coverageMode']=='SCOPED'
            assert scopes['VALUATION']['packageCodes']==['COMEX']
            assert scopes['INTERNAL_REPORTING']['coverageMode']=='DATASET'
        finally:tx.rollback()


def test_priority_save_is_versioned_idempotent_and_checks_concurrent_edits():
    from apps.reference_api.market_data_sources import save_priority
    from apps.reference_api.market_data_source_contracts import SourcePriorityInput
    from apps.reference_api.repository import IdempotencyKeyConflict
    import pytest
    with get_engine().connect() as c:
        tx=c.begin()
        try:
            dataset, _, _, _, _=setup_coverage(c)
            type_id=c.scalar(select(m.instrument_type.c.instrument_type_id).where(m.instrument_type.c.type_code=='EQUITY'))
            payload=SourcePriorityInput(instrumentTypeId=type_id,datasetIds=[dataset],mode='CUSTOM',expectedVersionId=None)
            key=str(uuid4())
            first=save_priority(c,ids['tenant'],ids['demo_user_account'],payload,key)
            assert save_priority(c,ids['tenant'],ids['demo_user_account'],payload,key)['versionId']==first['versionId']
            with pytest.raises(IdempotencyKeyConflict):
                save_priority(c,ids['tenant'],ids['demo_user_account'],payload,str(uuid4()))
            reset=payload.model_copy(update={'mode':'INHERIT','dataset_ids':[], 'expected_version_id':first['versionId']})
            second=save_priority(c,ids['tenant'],ids['demo_user_account'],reset,str(uuid4()))
            assert second['mode']=='INHERIT' and second['versionNo']==first['versionNo']+1
        finally:tx.rollback()


def test_reader_and_foreign_dataset_cannot_set_priorities():
    import pytest
    from apps.reference_api.market_data_sources import save_priority
    from apps.reference_api.market_data_source_contracts import SourcePriorityInput
    with get_engine().connect() as c:
        tx=c.begin()
        try:
            type_id=c.scalar(select(m.instrument_type.c.instrument_type_id).limit(1))
            payload=SourcePriorityInput(instrumentTypeId=type_id,datasetIds=[uuid4()],mode='CUSTOM')
            with pytest.raises(ValueError):save_priority(c,ids['tenant'],ids['demo_user_account'],payload,str(uuid4()))
            c.execute(m.tenant_user_account.update().where(m.tenant_user_account.c.user_account_id==ids['demo_user_account']).values(membership_role='TENANT_READER'))
            with pytest.raises(PermissionError):save_priority(c,ids['tenant'],ids['demo_user_account'],payload,str(uuid4()))
        finally:tx.rollback()


def test_platform_defaults_are_inherited_and_tenant_private_sources_cannot_be_global():
    from datetime import timedelta
    from apps.reference_api.market_data_sources import save_priority
    from apps.reference_api.market_data_source_contracts import SourcePriorityInput
    from market_data.source_priority import effective_priority
    import pytest
    with get_engine().connect() as c:
        tx=c.begin()
        try:
            c.execute(m.platform_user_account.insert().values(user_account_id=ids['demo_user_account'],platform_role='PLATFORM_ADMIN',valid_from=date(2026,1,1)))
            dataset,_,_,_,_=setup_coverage(c)
            type_id=c.scalar(select(m.instrument_type.c.instrument_type_id).limit(1))
            shared=SourcePriorityInput(instrumentTypeId=type_id,scope='PLATFORM',datasetIds=[dataset])
            saved=save_priority(c,ids['tenant'],ids['demo_user_account'],shared,str(uuid4()))
            result=effective_priority(c,ids['tenant'],type_id,saved['createdAt']+timedelta(seconds=1))
            assert result['scope']=='PLATFORM' and result['datasetIds']==[str(dataset)]
            provider=c.scalar(select(m.provider_product.c.data_provider_id).join(m.dataset).where(m.dataset.c.dataset_id==dataset))
            c.execute(m.data_provider.update().where(m.data_provider.c.data_provider_id==provider).values(owner_tenant_id=ids['tenant']))
            private=shared.model_copy(update={'expected_version_id':saved['versionId']})
            with pytest.raises(ValueError):save_priority(c,ids['tenant'],ids['demo_user_account'],private,str(uuid4()))
        finally:tx.rollback()
