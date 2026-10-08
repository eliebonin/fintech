"""Oversized JSON never reaches a domain transaction, including chunked bodies."""
import asyncio
from httpx import ASGITransport, AsyncClient
from apps.reference_api.main import create_app


class ForbiddenEngine:
    def begin(self): raise AssertionError('Oversized request reached the database')


def test_chunked_body_is_bounded_before_database_access():
    async def run():
        async def chunks():
            for _ in range(20): yield b'x' * 65536
        async with AsyncClient(transport=ASGITransport(app=create_app(engine=ForbiddenEngine()),raise_app_exceptions=False),base_url='http://test') as client:
            return await client.post('/v1/strategies',content=chunks(),headers={'Content-Type':'application/json'})
    response=asyncio.run(run())
    assert response.status_code == 413, response.text
    assert response.json()['requestId'] == response.headers['X-Request-ID']
    assert response.json()['code'] == 'request.too_large'


def test_exact_body_budget_is_allowed_and_false_content_length_is_not_trusted():
    async def run():
        async with AsyncClient(transport=ASGITransport(app=create_app(engine=ForbiddenEngine()),raise_app_exceptions=False),base_url='http://test') as client:
            allowed=await client.request('GET','/health',content=b'x'*1048576)
            denied=await client.post('/v1/strategies',content=b'x'*1048577,headers={'Content-Length':'1'})
            return allowed,denied
    allowed,denied=asyncio.run(run())
    assert allowed.status_code==200
    assert denied.status_code==413
