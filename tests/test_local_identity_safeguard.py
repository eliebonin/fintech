"""Contain header impersonation without pretending to provide production login."""
import asyncio
from contextlib import asynccontextmanager, contextmanager
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from apps.reference_api import access_boundary as boundary
from apps.reference_api.config import Settings
from apps.reference_api.tenant_context import get_tenant_context

TENANT=UUID('10000000-0000-4000-8000-000000000001')
USER=UUID('10000000-0000-4000-8000-000000000002')
OPERATOR=UUID('10000000-0000-4000-8000-000000000003')
KEY='synthetic-local-operator-key-for-tests-only'


class Engine:
    def __init__(self): self.calls=0
    @contextmanager
    def begin(self):
        self.calls+=1
        yield self
    def execute(self, statement): pass


def app(monkeypatch):
    engine=Engine()
    monkeypatch.setenv('APP_ENV','test')
    monkeypatch.setenv('LOCAL_ACCESS_OPERATOR_KEY',KEY)
    monkeypatch.setenv('LOCAL_PLATFORM_OPERATOR_ID',str(OPERATOR))
    application=FastAPI()
    boundary.install_access_boundary(application,lambda:engine,'test')
    def resolve(c,token,*,environment):
        if token!='valid-session': raise PermissionError('Session is invalid')
        return {'actorId':str(OPERATOR),'userId':str(USER),'tenantId':str(TENANT)}
    monkeypatch.setattr(boundary.access_sessions,'resolve',resolve)
    monkeypatch.setattr(boundary,'resolve_tenant_workspace',lambda *_:SimpleNamespace(permission_codes={'STRATEGY_READ'}))
    monkeypatch.setattr(boundary,'require_tenant_action',lambda *_:None)
    @application.get('/v1/strategies')
    def read(context=Depends(get_tenant_context)):
        return {'tenant':str(context.tenant_id),'user':str(context.user_account_id),'source':context.source}
    # Probe the boundary independently from the session router's own validation.
    @application.post('/v1/local-session')
    def bootstrap(): return {'created':True}
    from apps.reference_api.problem_details import configure_problem_details
    configure_problem_details(application)
    return application,engine


def send(application,path='/v1/strategies',headers=None,method='GET'):
    async def run():
        async with AsyncClient(transport=ASGITransport(app=application),base_url='http://test') as client:
            return await client.request(method,path,headers=headers or {})
    return asyncio.run(run())


def test_actor_headers_without_session_are_not_authentication(monkeypatch):
    application,engine=app(monkeypatch)
    response=send(application,headers={'X-Tenant-Id':str(TENANT),'X-User-Account-Id':str(USER)})
    assert response.status_code==401
    assert engine.calls==0


def test_session_is_authoritative_without_identity_headers(monkeypatch):
    application,_=app(monkeypatch)
    response=send(application,headers={'X-Local-Access-Token':'valid-session'})
    assert response.status_code==200,response.text
    assert response.json()=={'tenant':str(TENANT),'user':str(USER),'source':'local-session'}


@pytest.mark.parametrize('field,value',[
    ('X-User-Account-Id',str(OPERATOR)),('X-Tenant-Id',str(OPERATOR)),
])
def test_identity_headers_cannot_override_the_session(monkeypatch,field,value):
    application,_=app(monkeypatch)
    assert send(application,headers={'X-Local-Access-Token':'valid-session',field:value}).status_code==403


def test_invalid_session_never_falls_back_to_headers(monkeypatch):
    application,_=app(monkeypatch)
    response=send(application,headers={'X-Local-Access-Token':'invalid','X-Tenant-Id':str(TENANT),'X-User-Account-Id':str(USER)})
    assert response.status_code==401


def test_denial_logs_verified_operator_and_subject_without_trusting_forged_headers(monkeypatch,caplog):
    import json,logging
    application,_=app(monkeypatch)
    with caplog.at_level(logging.WARNING,logger='apps.reference_api.security'):
        response=send(application,headers={'X-Local-Access-Token':'valid-session','X-User-Account-Id':str(OPERATOR)})
    assert response.status_code==403
    events=[json.loads(r.getMessage()) for r in caplog.records if r.name=='apps.reference_api.security']
    assert len(events)==1
    assert events[0]['actorId']==str(OPERATOR) and events[0]['subjectId']==str(USER)
    assert events[0]['tenantId']==str(TENANT) and 'valid-session' not in caplog.text


def test_optional_headers_are_compared_as_uuid_identities(monkeypatch):
    application,_=app(monkeypatch)
    response=send(application,headers={'X-Local-Access-Token':'valid-session',
        'X-User-Account-Id':'{'+str(USER)+'}','X-Tenant-Id':'urn:uuid:'+str(TENANT)})
    assert response.status_code==200,response.text


@pytest.mark.parametrize('supplied',[None,'incorrect'])
def test_bootstrap_requires_the_server_only_operator_key(monkeypatch,supplied):
    application,engine=app(monkeypatch)
    headers={'X-User-Account-Id':str(OPERATOR)}
    if supplied: headers['X-Local-Operator-Key']=supplied
    assert send(application,'/v1/local-session',headers,'POST').status_code==401
    assert engine.calls==0


def test_bootstrap_key_cannot_be_used_for_ordinary_requests(monkeypatch):
    application,engine=app(monkeypatch)
    assert send(application,headers={'X-Local-Operator-Key':KEY,'X-User-Account-Id':str(USER),'X-Tenant-Id':str(TENANT)}).status_code==401
    assert engine.calls==0


@pytest.mark.parametrize('environment',['production','staging','', 'LOCAL','prod'])
def test_non_local_or_implicit_modes_refuse_server_startup(monkeypatch,environment):
    monkeypatch.setenv('APP_ENV',environment)
    monkeypatch.setenv('LOCAL_ACCESS_OPERATOR_KEY',KEY)
    from apps.reference_api.main import create_app
    application=create_app()
    async def start():
        async with application.router.lifespan_context(application): pass
    with pytest.raises(RuntimeError,match='authentication|local|APP_ENV'):
        asyncio.run(start())


def test_missing_bootstrap_secret_refuses_startup(monkeypatch):
    monkeypatch.setenv('APP_ENV','local')
    monkeypatch.delenv('LOCAL_ACCESS_OPERATOR_KEY',raising=False)
    from apps.reference_api.main import create_app
    application=create_app()
    async def start():
        async with application.router.lifespan_context(application): pass
    with pytest.raises(RuntimeError,match='LOCAL_ACCESS_OPERATOR_KEY'):
        asyncio.run(start())
