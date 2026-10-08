"""Isolated real HTTP policy lifecycle and preview acceptance."""
import asyncio
import hashlib
import json
from uuid import uuid4, UUID
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, func
from apps.reference_api.db import get_engine
from apps.reference_api.main import create_app
from apps.reference_api.contracts import MarketDataResolutionSnapshotCreate
from apps.reference_api.repository import _market_data_snapshot_fingerprint
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS


def call(method, path, payload=None, key=None):
    async def request():
        async with AsyncClient(transport=ASGITransport(app=create_app(engine=get_engine())), base_url='http://test') as client:
            return await client.request(method, path, json=payload, headers={
                'X-Tenant-Id':str(DEMO_IDS['tenant']), 'X-User-Account-Id':str(DEMO_IDS['demo_user_account']),
                'Idempotency-Key':key or str(uuid4())})
    return asyncio.run(request())


def policy_payload():
    return dict(policyCode='COMPOSITE_'+uuid4().hex[:12],displayName='Composite test',
        valuationCutId=str(DEMO_IDS['valuation_cut']),validFrom='2026-08-01',
        rules=[dict(ruleSequence=1,seriesType='OFFICIAL_CLOSE',pricingConvention='SESSION_CLOSE',
                    subjectReferenceNodeId=str(DEMO_IDS['hsbc_xlon_listing_node']),maxStalenessBusinessDays=0)])


def test_policy_create_replay_conflict_and_versioned_read():
    payload=policy_payload(); key=str(uuid4())
    created=call('POST','/v1/market-data/valuation-policies',payload,key)
    assert created.status_code==201,created.text
    first=created.json()
    assert first['versionNo']==1 and first['createdByUserAccountId']==str(DEMO_IDS['demo_user_account'])
    assert call('POST','/v1/market-data/valuation-policies',payload,key).json()==first
    payload['displayName']='New version'
    assert call('POST','/v1/market-data/valuation-policies',payload,key).status_code==409
    second=call('POST','/v1/market-data/valuation-policies',payload).json()
    assert second['versionNo']==2 and second['valuationPolicyId']!=first['valuationPolicyId']
    assert call('GET','/v1/market-data/valuation-policies/'+first['valuationPolicyId']).json()==first


def test_preview_never_persists_snapshot():
    engine=get_engine()
    with engine.connect() as c:
        before=c.scalar(select(func.count()).select_from(m.market_data_resolution_snapshot))
    payload=dict(subjectReferenceNodeIds=[str(DEMO_IDS['hsbc_xlon_listing_node'])],
        valuationPolicyId=str(DEMO_IDS['valuation_policy']),valuationDate='2026-08-28',
        valuationCutId=str(DEMO_IDS['valuation_cut']),marketDataAsOfUtc='2026-10-07T22:00:00Z',usePurpose='VALUATION')
    result=call('POST','/v1/market-data/resolution-preview',payload)
    assert result.status_code==200,result.text
    assert result.json()['items'][0]['subjectReferenceNodeId']==payload['subjectReferenceNodeIds'][0]
    with engine.connect() as c:
        assert c.scalar(select(func.count()).select_from(m.market_data_resolution_snapshot))==before


def test_legacy_snapshot_fingerprint_is_unchanged_without_strategy():
    original=dict(subjectReferenceNodeIds=[str(DEMO_IDS['hsbc_xlon_listing_node'])],
        valuationPolicyId=str(DEMO_IDS['valuation_policy']),valuationDate='2026-08-28',
        valuationCutId=str(DEMO_IDS['valuation_cut']),marketDataAsOfUtc='2026-10-07T22:00:00Z',usePurpose='VALUATION')
    payload=MarketDataResolutionSnapshotCreate.model_validate(original)
    dumped=payload.model_dump(mode='json',by_alias=True)
    dumped.pop('strategyId',None)
    expected=hashlib.sha256(json.dumps(dumped,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    assert _market_data_snapshot_fingerprint(payload)==expected


def test_policy_options_expose_configuration_permission():
    result=call('GET','/v1/market-data/valuation-policy-options')
    assert result.status_code==200,result.text
    assert result.json()['canManage'] is True and result.json()['cuts']


def test_new_policy_version_cannot_be_changed_in_database():
    import pytest
    from sqlalchemy.exc import DBAPIError
    first=call('POST','/v1/market-data/valuation-policies',policy_payload()).json()
    with get_engine().begin() as c:
        with pytest.raises(DBAPIError), c.begin_nested():
            c.execute(m.valuation_policy.update().where(m.valuation_policy.c.valuation_policy_id==UUID(first['valuationPolicyId'])).values(display_name='Changed'))


def test_new_policy_rejects_foreign_strategy_and_incomplete_fixing():
    payload=policy_payload(); payload['strategyId']=str(uuid4())
    assert call('POST','/v1/market-data/valuation-policies',payload).status_code==422
    payload.pop('strategyId'); payload['rules'][0]['pricingConvention']='NAMED_FIXING'
    assert call('POST','/v1/market-data/valuation-policies',payload).status_code==422


def test_read_only_member_can_inspect_but_not_create():
    membership=m.tenant_user_account
    where=(membership.c.tenant_id==DEMO_IDS['tenant']) & (membership.c.user_account_id==DEMO_IDS['demo_user_account'])
    engine=get_engine()
    with engine.begin() as c:
        originals=c.execute(select(membership.c.tenant_user_account_id,membership.c.membership_role).where(where)).all()
        c.execute(membership.update().where(where).values(membership_role='READ_ONLY'))
    try:
        assert call('GET','/v1/market-data/valuation-policy-options').json()['canManage'] is False
        assert call('POST','/v1/market-data/valuation-policies',policy_payload()).status_code==403
    finally:
        with engine.begin() as c:
            for record_id,role in originals:
                c.execute(membership.update().where(membership.c.tenant_user_account_id==record_id).values(membership_role=role))


def test_missing_module_is_forbidden_and_unknown_policy_is_not_disclosed():
    assert call('GET','/v1/market-data/valuation-policies/'+str(uuid4())).status_code==404
    entitlement=m.tenant_module_entitlement
    where=(entitlement.c.tenant_id==DEMO_IDS['tenant']) & entitlement.c.platform_module_id.in_(select(m.platform_module.c.platform_module_id).where(m.platform_module.c.module_code=='MARKET_DATA'))
    engine=get_engine()
    with engine.begin() as c:
        originals=c.execute(select(entitlement.c.tenant_module_entitlement_id,entitlement.c.entitlement_state).where(where)).all()
        c.execute(entitlement.update().where(where).values(entitlement_state='SUSPENDED'))
    try:
        assert call('GET','/v1/market-data/valuation-policy-options').status_code==403
        assert call('GET','/v1/market-data/valuation-policies?valuationDate=2026-08-28').status_code==403
        assert call('GET','/v1/market-data-resolution-snapshots/'+str(DEMO_IDS['resolution_snapshot'])).status_code==403
    finally:
        with engine.begin() as c:
            for record_id,state in originals:
                c.execute(entitlement.update().where(entitlement.c.tenant_module_entitlement_id==record_id).values(entitlement_state=state))


def test_managed_legacy_rule_cannot_silently_ignore_composite_time_or_basis():
    payload=policy_payload(); payload['rules'][0].update(pricingConvention='LEGACY',valueBasis='RAW')
    assert call('POST','/v1/market-data/valuation-policies',payload).status_code==422
