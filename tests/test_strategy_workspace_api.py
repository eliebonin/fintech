"""Focused HTTP contracts for the tenant workspace and strategy alpha."""

import asyncio
from uuid import uuid4

from httpx import ASGITransport, AsyncClient
import os
from sqlalchemy import create_engine

from apps.reference_api.main import create_app
from security_master_schema.demo_data import DEMO_IDS, load_demo_data


DATABASE_URL = os.environ["DATABASE_URL"]


async def _request(app, method: str, path: str, *, headers: dict[str, str], payload: dict[str, object] | None = None):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.request(method, path, headers=headers, json=payload)


def _app_and_headers():
    engine = create_engine(DATABASE_URL)
    load_demo_data(engine)
    return create_app(engine=engine), {
        "X-Tenant-Id": str(DEMO_IDS["tenant"]),
        "X-User-Account-Id": str(DEMO_IDS["demo_user_account"]),
        "Idempotency-Key": f"strategy-test-{uuid4()}",
    }


def test_memberships_are_available_before_a_tenant_is_selected() -> None:
    app, headers = _app_and_headers()
    headers.pop("X-Tenant-Id")

    response = asyncio.run(_request(app, "GET", "/v1/session/memberships", headers=headers))

    assert response.status_code == 200
    assert [item["tenantCode"] for item in response.json()["data"]] == [
        "FORTEM_DEMO_TENANT",
        "FORTEM_SECOND_TENANT",
    ]


def test_tenant_workspace_returns_the_active_membership_and_modules() -> None:
    app, headers = _app_and_headers()

    response = asyncio.run(_request(app, "GET", "/v1/tenant-workspace", headers=headers))

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["tenantId"] == str(DEMO_IDS["tenant"])
    assert "TRADING" in payload["moduleCodes"]


def test_tenant_admin_can_create_a_fund_strategy() -> None:
    app, headers = _app_and_headers()
    payload = {"strategyCode": f"ALPHA_FUND_{uuid4().hex[:8]}", "displayName": "Alpha Fund", "strategyType": "FUND", "baseCurrencyCode": "GBP"}

    response = asyncio.run(_request(app, "POST", "/v1/strategies", headers=headers, payload=payload))

    assert response.status_code == 201
    assert response.json()["data"]["tenantId"] == str(DEMO_IDS["tenant"])


def test_other_strategy_requires_an_operating_model_label() -> None:
    app, headers = _app_and_headers()
    payload = {"strategyCode": f"OTHER_{uuid4().hex[:8]}", "displayName": "Other", "strategyType": "OTHER"}

    response = asyncio.run(_request(app, "POST", "/v1/strategies", headers=headers, payload=payload))

    assert response.status_code == 422


def test_strategy_list_is_scoped_to_the_active_tenant() -> None:
    app, headers = _app_and_headers()

    response = asyncio.run(_request(app, "GET", "/v1/strategies", headers=headers))

    assert response.status_code == 200
    assert all(item["tenantId"] == str(DEMO_IDS["tenant"]) for item in response.json()["data"])


def test_strategy_detail_is_scoped_to_the_active_tenant() -> None:
    app, headers = _app_and_headers()
    created = asyncio.run(_request(app, "POST", "/v1/strategies", headers=headers, payload={"strategyCode": f"DETAIL_{uuid4().hex[:8]}", "displayName": "Detail Strategy", "strategyType": "FUND"}))

    response = asyncio.run(_request(app, "GET", f"/v1/strategies/{created.json()['data']['strategyId']}", headers=headers))

    assert response.status_code == 200
    assert response.json()["data"]["strategyCode"].startswith("DETAIL_")


def test_tenant_admin_can_archive_a_strategy() -> None:
    app, headers = _app_and_headers()
    created = asyncio.run(_request(app, "POST", "/v1/strategies", headers=headers, payload={"strategyCode": f"ARCHIVE_{uuid4().hex[:8]}", "displayName": "Archive Strategy", "strategyType": "FUND"}))

    response = asyncio.run(_request(app, "POST", f"/v1/strategies/{created.json()['data']['strategyId']}/status", headers=headers, payload={"status": "ARCHIVED"}))

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "ARCHIVED"
