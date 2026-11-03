"""Explicit local login for product integration fixtures, using real API checks.

These clients select a fixture user through guarded session bootstrap before a
header-only product request. They never replace a verifier or bypass permissions.
Identity/security tests deliberately use the original httpx/Starlette clients.
Supplied tokens are never replaced, so tampering/revocation remains observable.
"""
import os
from contextlib import contextmanager
from uuid import UUID
from urllib.parse import urlsplit
from httpx import ASGITransport, Headers, Request as HttpRequest
from fastapi.testclient import TestClient
from fastapi import Request


class ConnectionEngine:
    """Keep authentication and domain work in the caller's rollback fixture."""
    def __init__(self,connection):self.connection=connection
    @contextmanager
    def begin(self):yield self.connection


def router_fixture_identity(app):
    """Router/DTO unit tests assume verified context; they do not test middleware."""
    from apps.reference_api.tenant_context import get_tenant_context,TenantContext
    def context(request:Request):
        return TenantContext(UUID(request.headers['X-Tenant-Id']),UUID(request.headers['X-User-Account-Id']),'router-unit-fixture')
    app.dependency_overrides[get_tenant_context]=context


def selection(method, url, headers):
    path=urlsplit(str(url)).path
    if not path.startswith('/v1/') or path.startswith('/v1/local-session') or headers.get('X-Local-Access-Token'):
        return None
    user=headers.get('X-User-Account-Id')
    if not user: return None
    tenant=headers.get('X-Tenant-Id')
    return {'tenantId':tenant,'userId':user} if tenant else {}


def operator_headers():
    return {'X-Local-Operator-Key':os.environ['LOCAL_ACCESS_OPERATOR_KEY'],
        'X-User-Account-Id':os.environ.get('LOCAL_PLATFORM_OPERATOR_ID','00000000-0000-7000-8000-000000000304')}


class FixtureASGITransport(ASGITransport):
    async def aclose(self):
        # HTTPX ASGITransport deliberately does not run the app lifespan. Match
        # its resource teardown explicitly, without changing authorization.
        controller=getattr(getattr(self.app,'state',None),'workload_controller',None)
        if controller:
            from starlette.concurrency import run_in_threadpool
            await run_in_threadpool(controller.close)
        await super().aclose()

    async def handle_async_request(self, request):
        payload=selection(request.method,request.url,request.headers)
        if payload is not None:
            login=HttpRequest('POST',request.url.copy_with(path='/v1/local-session',query=None),
                headers=operator_headers(),json=payload)
            response=await super().handle_async_request(login)
            await response.aread()
            if response.status_code!=201: return response
            token=response.json()['token']
            await response.aclose()
            request.headers['X-Local-Access-Token']=token
        return await super().handle_async_request(request)


class FixtureTestClient(TestClient):
    __test__=False
    def request(self,method,url,*args,**kwargs):
        headers=Headers(self.headers)
        headers.update(kwargs.get('headers') or {})
        payload=selection(method,url,headers)
        if payload is not None:
            response=super().request('POST','/v1/local-session',headers=operator_headers(),json=payload)
            if response.status_code!=201: return response
            headers['X-Local-Access-Token']=response.json()['token']
            kwargs['headers']=headers
        return super().request(method,url,*args,**kwargs)
