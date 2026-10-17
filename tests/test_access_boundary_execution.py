"""Sync authority units are offloaded and budgeted; body waits own no connection."""
import asyncio
from contextlib import contextmanager
from types import SimpleNamespace
from threading import get_ident
from uuid import uuid4
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from apps.reference_api import access_boundary as boundary


class Engine:
    def __init__(self):self.threads=[];self.budgets=[];self.active=False
    @contextmanager
    def begin(self):
        self.threads.append(get_ident());self.active=True
        try:yield self
        finally:self.active=False
    def execute(self,statement):self.budgets.append(statement.compile().params)


def app(monkeypatch,engine):
    monkeypatch.setattr(boundary,'resolve_tenant_workspace',lambda *_:SimpleNamespace(permission_codes={'STRATEGY_READ','STRATEGY_CREATE'}))
    monkeypatch.setattr(boundary,'require_tenant_action',lambda *_:None)
    application=FastAPI()
    boundary.install_access_boundary(application,lambda:engine,'test')
    @application.get('/v1/strategies')
    def read():return {'ok':True}
    @application.post('/v1/strategies')
    def write():return {'ok':True}
    return application


def test_authorization_is_off_event_loop_and_has_transaction_budgets(monkeypatch):
    engine=Engine();application=app(monkeypatch,engine)
    async def run():
        event_loop_thread=get_ident()
        async with AsyncClient(transport=ASGITransport(app=application),base_url='http://test') as client:
            result=await client.get('/v1/strategies',headers={'X-Tenant-Id':str(uuid4()),'X-User-Account-Id':str(uuid4())})
        assert result.status_code==200
        assert engine.threads and all(thread!=event_loop_thread for thread in engine.threads)
        assert len(engine.budgets)==2
    asyncio.run(run())


def test_slow_request_body_does_not_hold_authorization_connection(monkeypatch):
    engine=Engine();application=app(monkeypatch,engine)
    # The write audit is covered independently; isolate the body/connection order.
    monkeypatch.setattr(boundary.access_management,'audit',lambda *_:None)
    async def run():
        async def body():
            yield b'{'
            await asyncio.sleep(0)
            assert not engine.active, 'No authorization transaction may span await request.json()'
            yield b'}'
        async with AsyncClient(transport=ASGITransport(app=application),base_url='http://test') as client:
            result=await client.post('/v1/strategies',content=body(),headers={
                'Content-Type':'application/json','X-Tenant-Id':str(uuid4()),'X-User-Account-Id':str(uuid4())})
        assert result.status_code==200
    asyncio.run(run())
