"""Platform/tenant API boundaries and direct HTTP permission enforcement."""
import os
from uuid import uuid4
import pytest
from sqlalchemy import create_engine
from fastapi.testclient import TestClient
from security_master_schema.demo_data import DEMO_IDS
from apps.reference_api.main import create_app
from apps.reference_api.config import Settings


@pytest.fixture
def client():
    engine=create_engine(os.environ['DATABASE_URL'])
    client=TestClient(create_app(engine=engine,settings=Settings(os.environ['DATABASE_URL'],'test','test',DEMO_IDS['tenant'])))
    yield client
    engine.dispose()


def headers(user='demo_user_account',tenant='tenant'):
    return {'X-User-Account-Id':str(DEMO_IDS[user]),'X-Tenant-Id':str(DEMO_IDS[tenant])}


def test_platform_registry_is_independent_of_tenant_membership(client):
    r=client.get('/v1/platform/tenants',headers={'X-User-Account-Id':str(DEMO_IDS['platform_admin_user_account'])})
    assert r.status_code==200
    assert len(r.json()['tenants'])>=2
    assert client.get('/v1/platform/tenants',headers=headers()).status_code==403


def test_local_selected_user_cannot_inherit_platform_or_cross_tenant_access(client):
    root={'X-User-Account-Id':str(DEMO_IDS['platform_admin_user_account'])}
    r=client.post('/v1/local-session',headers=root,json={'tenantId':str(DEMO_IDS['tenant']),'userId':str(DEMO_IDS['demo_user_account'])})
    assert r.status_code==201
    token=r.json()['token']
    h=headers()|{'X-Local-Access-Token':token}
    assert client.get('/v1/tenant-workspace',headers=h).status_code==200
    workspace=client.get('/v1/tenant-workspace',headers=h).json()['data']
    assert 'TRADE_WRITE' in workspace['permissionCodes']
    assert 'TRADING' in workspace['tenantModuleCodes']
    assert client.get('/v1/platform/tenants',headers=h).status_code==403
    assert client.get('/v1/tenant-workspace',headers=h|{'X-Tenant-Id':str(DEMO_IDS['second_tenant'])}).status_code==403
    assert client.get('/v1/tenant-workspace',headers=h|{'X-User-Account-Id':str(DEMO_IDS['platform_admin_user_account'])}).status_code==403


def test_member_can_read_but_cannot_book_or_manage_access(client):
    admin=headers()
    r=client.post('/v1/access/users',headers=admin,json={'name':'Read only '+uuid4().hex,'role':'MEMBER'})
    assert r.status_code==201
    user=r.json()['userId']
    group=client.post('/v1/access/groups',headers=admin,json={'code':'READ_'+uuid4().hex,'name':'Read only','actions':['TRADE_READ']})
    assert group.status_code==201
    r=client.put(f'/v1/access/users/{user}/groups',headers=admin,json={'groupIds':[group.json()['groupId']]})
    assert r.status_code==200
    h=admin|{'X-User-Account-Id':user}
    assert client.get('/v1/trades',headers=h).status_code==200
    assert client.post('/v1/trades',headers=h,json={}).status_code==403
    assert client.get('/v1/access',headers=h).status_code==403
    assert client.get('/v1/strategies',headers=h).status_code==403


def test_selected_operator_and_subject_are_both_retained_in_write_evidence(client):
    from sqlalchemy import select
    from security_master_schema import models as m
    root={'X-User-Account-Id':str(DEMO_IDS['platform_admin_user_account'])}
    r=client.post('/v1/local-session',headers=root,json={'tenantId':str(DEMO_IDS['tenant']),'userId':str(DEMO_IDS['demo_user_account'])})
    h=headers()|{'X-Local-Access-Token':r.json()['token']}
    result=client.post('/v1/strategies',headers=h,json={'strategyCode':'AUDIT_'+uuid4().hex,'displayName':'Audit test','strategyType':'FUND','baseCurrencyCode':'GBP'})
    assert result.status_code==201
    engine=create_engine(os.environ['DATABASE_URL'])
    with engine.connect() as c:
        row=c.execute(select(m.access_audit_event).where(m.access_audit_event.c.action=='TENANT_REQUEST',
            m.access_audit_event.c.details['resourceIds'].contains([result.json()['data']['strategyId']]))).mappings().one()
        assert row['actor_id']==DEMO_IDS['platform_admin_user_account']
        assert row['subject_id']==DEMO_IDS['demo_user_account']
    engine.dispose()


def test_expired_session_can_be_ended_without_changing_actor(client):
    from sqlalchemy import update
    from datetime import datetime, timezone, timedelta
    from security_master_schema import models as m
    root={'X-User-Account-Id':str(DEMO_IDS['platform_admin_user_account'])}
    token=client.post('/v1/local-session',headers=root,json={}).json()['token']
    engine=create_engine(os.environ['DATABASE_URL'])
    with engine.begin() as c:
        c.execute(update(m.local_access_session).values(expires_at_utc=datetime.now(timezone.utc)-timedelta(days=1)))
    h=root|{'X-Local-Access-Token':token}
    assert client.get('/v1/local-session',headers=h).status_code==403
    assert client.delete('/v1/local-session',headers=h).status_code==200
    assert client.post('/v1/local-session',headers=root,json={}).status_code==201
    assert client.delete('/v1/local-session',headers=headers()|{'X-Local-Access-Token':token}).status_code==403
    engine.dispose()


def test_group_granted_member_can_book_without_becoming_admin(client):
    from tests.test_cash_booking_integrity import payload
    admin=headers()
    user=client.post('/v1/access/users',headers=admin,json={'name':'Trader '+uuid4().hex,'role':'MEMBER'}).json()['userId']
    group=client.post('/v1/access/groups',headers=admin,json={'code':'BOOK_'+uuid4().hex,'name':'Book','actions':['TRADE_READ','TRADE_WRITE']}).json()['groupId']
    assert client.put(f'/v1/access/users/{user}/groups',headers=admin,json={'groupIds':[group]}).status_code==200
    h=admin|{'X-User-Account-Id':user,'Idempotency-Key':str(uuid4())}
    result=client.post('/v1/trades',headers=h,json=payload().model_dump(mode='json',by_alias=True))
    assert result.status_code==201,result.text
    assert result.json()['data']['trade']['bookedByUserAccountId']==user


@pytest.mark.parametrize('actions,expected',[
    (['TRADE_WRITE','VALUATION_RUN','MARKET_DATA_READ'],403),
    (['TRADE_CORRECT','VALUATION_READ','MARKET_DATA_READ'],200),
])
def test_flow_cancellation_http_uses_correction_not_calculation_or_booking(client,actions,expected):
    admin=headers()
    flow=client.post('/v1/valuation/economic-flows',headers=admin|{'Idempotency-Key':str(uuid4())},json={
        'strategyId':str(DEMO_IDS['strategy']),'instrumentId':str(DEMO_IDS['hsbc_instrument_node']),
        'currencyId':str(DEMO_IDS['gbp_currency']),'amount':'100','component':'DIVIDEND',
        'recognitionRole':'INCOME','economicDate':'2026-10-01','sourceReference':'SYNTHETIC'})
    assert flow.status_code==201,flow.text
    user=client.post('/v1/access/users',headers=admin,json={'name':'Flow operator '+uuid4().hex,'role':'MEMBER'}).json()['userId']
    group=client.post('/v1/access/groups',headers=admin,json={'code':'FLOW_'+uuid4().hex,'name':'Flow operator','actions':actions}).json()['groupId']
    assert client.put(f'/v1/access/users/{user}/groups',headers=admin,json={'groupIds':[group]}).status_code==200
    response=client.post('/v1/valuation/economic-flows/'+flow.json()['tradeId']+'/cancel',
        headers=admin|{'X-User-Account-Id':user,'Idempotency-Key':str(uuid4())},json={'reason':'Incorrect flow'})
    assert response.status_code==expected,response.text
