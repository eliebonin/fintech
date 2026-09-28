import asyncio
from uuid import UUID

from httpx import ASGITransport, AsyncClient

from apps.reference_api.main import create_app


async def _get(path: str):
    async with AsyncClient(transport=ASGITransport(app=create_app()), base_url="http://test") as client:
        return await client.get(path)


def test_health_reports_reference_api_service():
    response = asyncio.run(_get("/health"))

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "reference-api"}


def test_api_rejects_requests_without_trusted_tenant_context():
    response = asyncio.run(_get("/v1/instruments/search"))

    assert response.status_code == 401
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == "authentication.required"
    assert UUID(response.headers["x-request-id"])
