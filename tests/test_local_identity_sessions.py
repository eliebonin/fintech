"""Real, unmodified HTTP authentication against an owned disposable database."""
from datetime import datetime,timedelta,timezone
from hashlib import sha256
import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine,select,update

from apps.reference_api.main import create_app
from apps.reference_api.config import Settings
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids


@pytest.fixture
def client():
    engine=create_engine(os.environ['DATABASE_URL'])
    with TestClient(create_app(engine=engine)) as http:
        yield http,engine
    engine.dispose()


def root():
    return {'X-Local-Operator-Key':os.environ['LOCAL_ACCESS_OPERATOR_KEY'],
        'X-User-Account-Id':str(ids['platform_admin_user_account'])}


def select_user(http):
    response=http.post('/v1/local-session',headers=root(),json={
        'tenantId':str(ids['tenant']),'userId':str(ids['demo_user_account'])})
    assert response.status_code==201,response.text
    assert os.environ['LOCAL_ACCESS_OPERATOR_KEY'] not in response.text
    return response.json()['token']


def test_uuid_headers_cannot_bootstrap_or_read_operating_context(client):
    http,_=client
    forged={'X-User-Account-Id':str(ids['platform_admin_user_account'])}
    assert http.post('/v1/local-session',headers=forged,json={}).status_code==401
    assert http.get('/v1/local-session/options',headers=forged).status_code==401
    assert http.get('/v1/platform/tenants',headers=forged).status_code==401
    assert http.get('/v1/local-session-pretend',headers=forged).status_code==401
    assert http.post('/v1/local-session',headers=root()|{'X-User-Account-Id':str(ids['demo_user_account'])},json={}).status_code==403


def test_session_subject_and_tenant_are_authoritative_and_not_platform_admin(client):
    http,_=client;token=select_user(http);headers={'X-Local-Access-Token':token}
    response=http.get('/v1/tenant-workspace',headers=headers)
    assert response.status_code==200,response.text
    assert response.headers['cache-control']=='no-store'
    assert response.json()['data']['tenantId']==str(ids['tenant'])
    assert http.get('/v1/tenant-workspace',headers=headers|{'X-Tenant-Id':str(ids['second_tenant'])}).status_code==403
    assert http.get('/v1/tenant-workspace',headers=headers|{'X-User-Account-Id':str(ids['platform_admin_user_account'])}).status_code==403
    assert http.get('/v1/platform/tenants',headers=headers).status_code==403
    assert http.get('/v1/tenant-workspace',headers={'X-Local-Access-Token':token+'tampered'}).status_code==401


def test_expired_session_can_be_replaced_without_header_fallback(client):
    http,engine=client;token=select_user(http)
    with engine.begin() as c:
        c.execute(update(m.local_access_session).where(m.local_access_session.c.token_hash==sha256(token.encode()).hexdigest())
            .values(expires_at_utc=datetime.now(timezone.utc)-timedelta(seconds=1)))
    assert http.get('/v1/tenant-workspace',headers={'X-Local-Access-Token':token}).status_code==401
    assert http.get('/v1/local-session',headers={'X-Local-Access-Token':token}).status_code==401
    assert http.get('/v1/local-session/options',headers=root()|{'X-Local-Access-Token':token}).status_code==200
    replacement=http.post('/v1/local-session',headers=root()|{'X-Local-Access-Token':token},json={
        'tenantId':str(ids['tenant']),'userId':str(ids['demo_user_account'])})
    assert replacement.status_code==201,replacement.text
    assert http.get('/v1/tenant-workspace',headers={'X-Local-Access-Token':replacement.json()['token']}).status_code==200


def test_revoked_sessions_and_current_membership_are_rechecked(client):
    http,engine=client;token=select_user(http)
    assert http.delete('/v1/local-session',headers=root()|{'X-Local-Access-Token':token}).status_code==200
    assert http.get('/v1/tenant-workspace',headers={'X-Local-Access-Token':token}).status_code==401
    token=select_user(http)
    predicate=(m.tenant_user_account.c.tenant_id==ids['tenant'])&(m.tenant_user_account.c.user_account_id==ids['demo_user_account'])
    with engine.begin() as c:
        original=c.scalar(select(m.tenant_user_account.c.status).where(predicate))
        c.execute(update(m.tenant_user_account).where(predicate).values(status='SUSPENDED'))
    try:
        assert http.get('/v1/tenant-workspace',headers={'X-Local-Access-Token':token}).status_code==401
    finally:
        with engine.begin() as c:c.execute(update(m.tenant_user_account).where(predicate).values(status=original))


def test_verified_real_operator_and_selected_user_are_retained_in_write_audit(client):
    http,engine=client;token=select_user(http)
    response=http.post('/v1/strategies',headers={'X-Local-Access-Token':token},json={
        'strategyCode':'IDENTITY_'+uuid4().hex,'displayName':'Synthetic identity regression','strategyType':'FUND'})
    assert response.status_code==201,response.text
    with engine.connect() as c:
        row=c.execute(select(m.access_audit_event).where(m.access_audit_event.c.action=='TENANT_REQUEST',
            m.access_audit_event.c.details['resourceIds'].contains([response.json()['data']['strategyId']]))).mappings().one()
        assert row['actor_id']==ids['platform_admin_user_account']
        assert row['subject_id']==ids['demo_user_account']
        assert row['details']['requestId']==response.headers['X-Request-ID']
    assert os.environ['LOCAL_ACCESS_OPERATOR_KEY'] not in repr(Settings.from_environment())
