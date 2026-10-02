"""Tenant lookup boundaries for enriched booking."""
import asyncio
from httpx import ASGITransport, AsyncClient
from security_master_schema.demo_data import DEMO_IDS
from apps.reference_api.main import create_app

def test_booking_context_exposes_tenant_catalogue_and_actor():
    async def run():
        async with AsyncClient(transport=ASGITransport(app=create_app()), base_url="http://test") as client:
            return await client.get("/v1/trades/booking-context", headers={"X-Tenant-Id":str(DEMO_IDS["tenant"]), "X-User-Account-Id":str(DEMO_IDS["demo_user_account"])})
    result = asyncio.run(run())
    assert result.status_code == 200
    assert result.json()["data"]["tenantId"] == str(DEMO_IDS["tenant"])
    assert result.json()["data"]["bookedByUserAccountId"] == str(DEMO_IDS["demo_user_account"])
    assert isinstance(result.json()["data"]["properties"], list)

def test_trader_lookup_requires_actor_and_rejects_unbounded_limit():
    async def run():
        async with AsyncClient(transport=ASGITransport(app=create_app()), base_url="http://test") as client:
            missing = await client.get("/v1/trades/traders")
            invalid = await client.get("/v1/trades/traders?limit=101", headers={"X-Tenant-Id":str(DEMO_IDS["tenant"]), "X-User-Account-Id":str(DEMO_IDS["demo_user_account"])})
            return missing, invalid
    missing, invalid = asyncio.run(run())
    assert missing.status_code == 401
    assert invalid.status_code == 422
