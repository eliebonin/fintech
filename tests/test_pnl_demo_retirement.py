"""The retired demo must never return a plausible partial financial result."""
import asyncio
import pytest
from httpx import ASGITransport, AsyncClient
from apps.reference_api.main import create_app
from security_master_schema.demo_data import DEMO_IDS


async def request(path, headers):
    async with AsyncClient(transport=ASGITransport(app=create_app()), base_url="http://test") as client:
        return await client.get(path, headers=headers)


@pytest.mark.parametrize("code", ["MVP_US_PORTFOLIO", "MVP_UK_PORTFOLIO", "unknown-strategy"])
def test_retired_pnl_returns_gone_without_financial_results(code):
    response = asyncio.run(request(f"/v1/portfolios/{code}/pnl?asOfDate=2026-08-28", {
        "X-Tenant-Id": str(DEMO_IDS["tenant"]),
        "X-User-Account-Id": str(DEMO_IDS["demo_user_account"]),
    }))
    assert response.status_code == 410, response.text
    assert response.json()["code"] == "valuation.demo_retired"
    assert "data" not in response.json()


def test_retired_pnl_still_requires_tenant_authority():
    response = asyncio.run(request("/v1/portfolios/MVP_US_PORTFOLIO/pnl?asOfDate=2026-08-28", {}))
    assert response.status_code in {401, 403}
    assert "data" not in response.json()


def test_openapi_does_not_advertise_a_successful_demo_calculation():
    operation = create_app().openapi()["paths"]["/v1/portfolios/{portfolio_code}/pnl"]["get"]
    assert operation["deprecated"] is True
    assert "410" in operation["responses"]
    assert "200" not in operation["responses"]
    assert operation["responses"]["410"]["content"]["application/problem+json"]["schema"]["$ref"] == "#/components/schemas/ProblemDetails"
