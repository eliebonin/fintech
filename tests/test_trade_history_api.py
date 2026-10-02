"""Public query contract for tenant-scoped trade history."""

import asyncio
from httpx import ASGITransport, AsyncClient
from apps.reference_api.main import create_app
from security_master_schema.demo_data import DEMO_IDS


def request(path):
    async def run():
        async with AsyncClient(transport=ASGITransport(app=create_app()), base_url="http://test") as client:
            return await client.get(path, headers={
                "X-Tenant-Id": str(DEMO_IDS["tenant"]),
                "X-User-Account-Id": str(DEMO_IDS["demo_user_account"]),
            })
    return asyncio.run(run())


def test_api_search_is_applied_before_pagination():
    response = request("/v1/trades?q=no-such-trade-history-match&limit=1")
    assert response.status_code == 200
    assert response.json()["data"] == []
    assert response.json()["meta"]["total"] == 0


def test_api_rejects_invalid_side():
    assert request("/v1/trades?side=INVALID").status_code == 422


def test_api_rejects_reversed_date_range():
    assert request("/v1/trades?fromDate=2026-10-02&toDate=2026-10-01").status_code == 400
