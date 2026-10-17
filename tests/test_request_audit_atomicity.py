"""A mandatory request-audit failure must roll back the command, not lie after commit."""
import os
from uuid import uuid4
from sqlalchemy import create_engine, select
from fastapi.testclient import TestClient
from apps.reference_api.main import create_app
from security_master_schema import access_management as am, models as m
from security_master_schema.demo_data import DEMO_IDS as ids


def test_required_request_audit_failure_rolls_back_strategy_creation(monkeypatch):
    engine=create_engine(os.environ['DATABASE_URL'])
    original=am.audit
    def fail(c,actor,tenant,action,details,subject=None):
        if action=='TENANT_REQUEST':raise RuntimeError('synthetic-audit-failure')
        return original(c,actor,tenant,action,details,subject)
    monkeypatch.setattr(am,'audit',fail)
    code='AUDIT_FAIL_'+uuid4().hex.upper()
    try:
        with TestClient(create_app(engine=engine),raise_server_exceptions=False) as client:
            response=client.post('/v1/strategies',headers={'X-Tenant-Id':str(ids['tenant']),
                'X-User-Account-Id':str(ids['demo_user_account'])},json={
                    'strategyCode':code,'displayName':'Atomicity regression','strategyType':'FUND'})
        assert response.status_code==500
        assert 'synthetic-audit-failure' not in response.text
        with engine.connect() as c:
            assert c.scalar(select(m.strategy.c.strategy_id).where(m.strategy.c.strategy_code==code)) is None
    finally:engine.dispose()


def test_successful_creation_retains_real_operator_subject_request_and_resource():
    engine=create_engine(os.environ['DATABASE_URL'])
    try:
        with TestClient(create_app(engine=engine)) as client:
            context=client.post('/v1/local-session',headers={'X-User-Account-Id':str(ids['platform_admin_user_account'])},
                json={'tenantId':str(ids['tenant']),'userId':str(ids['demo_user_account'])})
            assert context.status_code==201
            response=client.post('/v1/strategies',headers={'X-Tenant-Id':str(ids['tenant']),
                'X-User-Account-Id':str(ids['demo_user_account']),'X-Local-Access-Token':context.json()['token']},
                json={'strategyCode':'AUDIT_OK_'+uuid4().hex,'displayName':'Audited creation','strategyType':'FUND'})
        assert response.status_code==201,response.text
        identity=response.json()['data']['strategyId']
        with engine.connect() as c:
            audit=c.execute(select(m.access_audit_event).where(m.access_audit_event.c.action=='TENANT_REQUEST',
                m.access_audit_event.c.details['resourceIds'].contains([identity]))).mappings().one()
            assert audit['actor_id']==ids['platform_admin_user_account']
            assert audit['subject_id']==ids['demo_user_account']
            assert audit['details']['requestId']==response.headers['X-Request-ID']
            assert audit['details']['permission']=='STRATEGY_CREATE'
    finally:engine.dispose()
