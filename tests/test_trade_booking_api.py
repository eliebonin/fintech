"""HTTP contract for tenant-scoped listed-cash trade booking."""

import asyncio

from httpx import ASGITransport, AsyncClient

from apps.reference_api.main import create_app
from security_master_schema.demo_data import DEMO_IDS


def _headers(key: str) -> dict[str, str]:
    return {
        "X-Tenant-Id": str(DEMO_IDS["tenant"]),
        "X-User-Account-Id": str(DEMO_IDS["demo_user_account"]),
        "Idempotency-Key": key,
    }


def _payload() -> dict[str, str]:
    return {
        "listingId": str(DEMO_IDS["hsbc_xlon_listing_node"]),
        "strategyId": str(DEMO_IDS["strategy"]),
        "side": "BUY",
        "quantity": "1250",
        "executionPrice": "10.23",
        "tradeDatetime": "2026-09-30T14:32:00+00:00",
        "settlementDate": "2026-10-02",
    }


def test_tenant_admin_can_book_a_listing_backed_cash_trade() -> None:
    async def request():
        async with AsyncClient(transport=ASGITransport(app=create_app()), base_url="http://test") as client:
            return await client.post("/v1/trades", json=_payload(), headers=_headers("trade-api-booking-1"))

    response = asyncio.run(request())

    assert response.status_code == 201
    assert response.headers["location"].startswith("/v1/trades/")
    assert response.json()["data"]["trade"]["listingId"] == str(DEMO_IDS["hsbc_xlon_listing_node"])


def test_booking_rejects_a_client_supplied_listing_currency() -> None:
    async def request():
        async with AsyncClient(transport=ASGITransport(app=create_app()), base_url="http://test") as client:
            payload = _payload() | {"priceCurrency": "USD"}
            return await client.post("/v1/trades", json=payload, headers=_headers("trade-api-derived-facts"))

    response = asyncio.run(request())

    assert response.status_code == 422
