"""Shared policy workflows on owned PostgreSQL fixtures, without an HTTP request."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from apps.reference_api.db import get_engine
from market_data.pricing_policy_contracts import PolicyCreate
from market_data.pricing_policies import create_policy, policy_definition
from security_master_schema import access_management as am, models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from security_master_schema.errors import IdempotencyKeyConflict
from security_master_schema.tenant_workspace import TenantActionForbidden


def command(**changes):
    values=dict(policyCode='EXTRACT_'+uuid4().hex,displayName='Shared command test',
        valuationCutId=ids['valuation_cut'],validFrom=date(2026,8,1),
        rules=[dict(ruleSequence=1,seriesType='OFFICIAL_CLOSE',pricingConvention='SESSION_CLOSE',
                    subjectReferenceNodeId=ids['hsbc_xlon_listing_node'])])
    return PolicyCreate.model_validate(values | changes)


def count_code(c, payload):
    return c.scalar(select(func.count()).select_from(m.valuation_policy).where(
        m.valuation_policy.c.policy_code==payload.policy_code))


def test_command_and_http_replay_have_identical_wire_result_and_audit():
    from apps.reference_api.valuation_policies import _policy_view
    from tests.test_composite_policy_api import call
    payload=command(); key=str(uuid4())
    with get_engine().begin() as c:
        definition=create_policy(c,ids['tenant'],ids['demo_user_account'],payload,key)
        expected=_policy_view(definition).model_dump(mode='json',by_alias=True)
        assert asdict(policy_definition(c,ids['tenant'],definition.policy_id))==asdict(definition)
    response=call('POST','/v1/market-data/valuation-policies',payload.model_dump(mode='json',by_alias=True),key)
    assert response.status_code==201,response.text
    assert response.json()==expected
    assert response.headers['Location'].endswith(str(definition.policy_id))
    with get_engine().connect() as c:
        audit=c.execute(select(m.access_audit_event).where(m.access_audit_event.c.action=='TENANT_REQUEST',
            m.access_audit_event.c.details['resourceIds'].contains([str(definition.policy_id)]))).mappings().one()
        assert audit['details']['permission']=='MARKET_DATA_MANAGE'
        assert audit['details']['requestId']==response.headers['X-Request-ID']
        assert count_code(c,payload)==1


def test_command_does_not_commit_callers_transaction_and_rejects_conflicting_retry():
    engine=get_engine(); payload=command(); key=str(uuid4())
    with engine.connect() as c:
        tx=c.begin()
        try:
            first=create_policy(c,ids['tenant'],ids['demo_user_account'],payload,key)
            assert create_policy(c,ids['tenant'],ids['demo_user_account'],payload,key)==first
            changed=payload.model_copy(update={'display_name':'Changed request'})
            with pytest.raises(IdempotencyKeyConflict,match='Policy key reused'):
                create_policy(c,ids['tenant'],ids['demo_user_account'],changed,key)
            assert c.in_transaction() and count_code(c,payload)==1
        finally:
            tx.rollback()
    with engine.connect() as c:
        assert count_code(c,payload)==0


def test_revoked_module_prevents_direct_replay():
    with get_engine().connect() as c:
        tx=c.begin()
        try:
            payload=command(); key=str(uuid4())
            create_policy(c,ids['tenant'],ids['demo_user_account'],payload,key)
            c.execute(m.tenant_module_entitlement.update().where(
                m.tenant_module_entitlement.c.tenant_id==ids['tenant'],
                m.tenant_module_entitlement.c.platform_module_id.in_(select(m.platform_module.c.platform_module_id).where(
                    m.platform_module.c.module_code=='MARKET_DATA'))).values(entitlement_state='SUSPENDED'))
            with pytest.raises(PermissionError):
                create_policy(c,ids['tenant'],ids['demo_user_account'],payload,key)
        finally: tx.rollback()


def test_direct_strategy_command_checks_current_action_scope_before_replay():
    with get_engine().connect() as c:
        tx=c.begin()
        try:
            user=am.add_user(c,ids['tenant'],ids['demo_user_account'],name='Scoped policy writer')
            group=am.save_group(c,ids['tenant'],ids['demo_user_account'],code='POLICY_'+uuid4().hex,
                name='Policy commands',actions=['MARKET_DATA_MANAGE','STRATEGY_WRITE'],
                scope_mode='SELECTED',strategy_ids=[ids['strategy']])
            am.set_user_groups(c,ids['tenant'],ids['demo_user_account'],user,[group])
            strategy_start=c.scalar(select(m.strategy.c.effective_from).where(m.strategy.c.strategy_id==ids['strategy']))
            payload=command(strategyId=ids['strategy'],validFrom=strategy_start);key=str(uuid4())
            result=create_policy(c,ids['tenant'],user,payload,key)
            assert result.strategy_id==ids['strategy']
            # Current scope, not an old administrative role or retry key, governs replay.
            c.execute(m.access_group_strategy.delete().where(m.access_group_strategy.c.group_id==group))
            with pytest.raises(TenantActionForbidden):
                create_policy(c,ids['tenant'],user,payload,key)
        finally: tx.rollback()


@pytest.mark.parametrize('field,message', [
    ('subjectReferenceNodeId','Subject is not available'),
    ('marketDataSeriesId','Series is not available'),
    ('datasetId','Dataset is not available'),
    ('marketVenueId','Inactive or unknown'),
])
def test_direct_command_retains_reference_validation(field,message):
    with get_engine().connect() as c:
        tx=c.begin()
        try:
            payload=command(); payload.rules[0]=payload.rules[0].model_copy(update={
                {'subjectReferenceNodeId':'subject_reference_node_id','marketDataSeriesId':'market_data_series_id',
                 'datasetId':'dataset_id','marketVenueId':'market_venue_id'}[field]:uuid4()})
            with pytest.raises(ValueError,match=message):
                create_policy(c,ids['tenant'],ids['demo_user_account'],payload,str(uuid4()))
            assert count_code(c,payload)==0
        finally: tx.rollback()


@pytest.mark.parametrize('same_key',[False,True])
def test_concurrent_commands_serialize_versions_and_retry_identity(same_key):
    engine=get_engine();payload=command();shared_key=str(uuid4())
    def execute(index):
        with engine.begin() as c:
            return create_policy(c,ids['tenant'],ids['demo_user_account'],payload,
                shared_key if same_key else f'{shared_key}:{index}')
    with ThreadPoolExecutor(max_workers=3) as pool:
        results=list(pool.map(execute,range(3)))
    assert len({r.policy_id for r in results})==(1 if same_key else 3)
    assert sorted({r.version_no for r in results})==([1] if same_key else [1,2,3])


def test_policy_request_audit_failure_rolls_back_released_domain_savepoint(monkeypatch):
    from tests.api_client import FixtureTestClient as TestClient
    from apps.reference_api.main import create_app
    payload=command(); original=am.audit
    def fail(c,actor,tenant,action,details,subject=None):
        if action=='TENANT_REQUEST': raise RuntimeError('synthetic-policy-audit-failure')
        return original(c,actor,tenant,action,details,subject)
    monkeypatch.setattr(am,'audit',fail)
    with TestClient(create_app(engine=get_engine()),raise_server_exceptions=False) as client:
        response=client.post('/v1/market-data/valuation-policies',
            headers={'X-Tenant-Id':str(ids['tenant']),'X-User-Account-Id':str(ids['demo_user_account']),
                'Idempotency-Key':str(uuid4())},json=payload.model_dump(mode='json',by_alias=True))
    assert response.status_code==500
    assert 'synthetic-policy' not in response.text
    with get_engine().connect() as c:
        assert count_code(c,payload)==0
