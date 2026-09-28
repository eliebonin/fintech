import asyncio

from httpx import ASGITransport, AsyncClient

from apps.reference_api.main import create_app
from security_master_schema.demo_data import DEMO_IDS


async def _queue():
    async with AsyncClient(transport=ASGITransport(app=create_app()), base_url="http://test") as client:
        return await client.get(
            "/v1/work-queue",
            headers={"X-Tenant-Id": str(DEMO_IDS["tenant"]), "X-User-Account-Id": str(DEMO_IDS["demo_user_account"])},
        )


def test_work_queue_groups_pending_mapping_reviews():
    response = asyncio.run(_queue())

    assert response.status_code == 200
    payload = response.json()
    assert payload["counts"]["MAPPING_REVIEW"] >= 1
    assert any(item["category"] == "MAPPING_REVIEW" and item["status"] == "PENDING" for item in payload["items"])
