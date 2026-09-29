"""HTTP contract checks for replay-safe Market Data evidence snapshots."""

import asyncio
from datetime import datetime, timezone
from uuid import uuid4

from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine

from apps.reference_api.main import create_app
from security_master_schema.demo_data import DEMO_IDS, load_demo_data


DATABASE_URL = "postgresql+psycopg://fortem:fortem_local_only@localhost:54329/fortem_secm"


def _headers() -> dict[str, str]:
    return {
        "X-Tenant-Id": str(DEMO_IDS["tenant"]),
        "X-User-Account-Id": str(DEMO_IDS["demo_user_account"]),
        "Idempotency-Key": f"http-test-{uuid4()}",
    }


def _payload() -> dict[str, object]:
    return {
        "subjectReferenceNodeIds": [str(DEMO_IDS["hsbc_xlon_listing_node"])],
        "valuationPolicyId": str(DEMO_IDS["valuation_policy"]),
        "valuationDate": "2026-08-28",
        "valuationCutId": str(DEMO_IDS["valuation_cut"]),
        "marketDataAsOfUtc": datetime.now(timezone.utc).isoformat(),
        "usePurpose": "VALUATION",
    }


async def _request(method: str, path: str, *, headers=None, json=None, app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.request(method, path, headers=headers, json=json)


def test_snapshot_post_replays_and_get_returns_frozen_resource() -> None:
    engine = create_engine(DATABASE_URL)
    load_demo_data(engine)
    app = create_app(engine=engine)
    headers, payload = _headers(), _payload()
    created = asyncio.run(_request("POST", "/v1/market-data-resolution-snapshots", headers=headers, json=payload, app=app))

    assert created.status_code == 201
    assert created.headers["location"].endswith(created.json()["marketDataResolutionSnapshotId"])
    assert created.headers["x-request-id"]
    replay = asyncio.run(_request("POST", "/v1/market-data-resolution-snapshots", headers=headers, json=payload, app=app))
    assert replay.status_code == 201
    assert replay.json() == created.json()
    fetched = asyncio.run(_request("GET", created.headers["location"], headers=headers, app=app))
    assert fetched.status_code == 200
    assert fetched.json() == created.json()


def test_snapshot_post_requires_key_and_rejects_conflicting_reuse() -> None:
    engine = create_engine(DATABASE_URL)
    load_demo_data(engine)
    app = create_app(engine=engine)
    headers, payload = _headers(), _payload()
    no_key = asyncio.run(_request("POST", "/v1/market-data-resolution-snapshots", headers={key: value for key, value in headers.items() if key != "Idempotency-Key"}, json=payload, app=app))
    assert no_key.status_code == 422
    assert asyncio.run(_request("POST", "/v1/market-data-resolution-snapshots", headers=headers, json=payload, app=app)).status_code == 201
    payload["subjectReferenceNodeIds"] = [str(DEMO_IDS["demo_share_class_instrument_node"])]
    conflict = asyncio.run(_request("POST", "/v1/market-data-resolution-snapshots", headers=headers, json=payload, app=app))
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "idempotency.key_reused"


def test_snapshot_rejects_invalid_policy_context_and_does_not_disclose_to_other_tenant() -> None:
    engine = create_engine(DATABASE_URL)
    load_demo_data(engine)
    app = create_app(engine=engine)
    headers, payload = _headers(), _payload()
    payload["valuationCutId"] = str(DEMO_IDS["uk_fx_cut"])
    invalid = asyncio.run(_request("POST", "/v1/market-data-resolution-snapshots", headers=headers, json=payload, app=app))
    assert invalid.status_code == 422
    assert invalid.json()["code"] == "market_data.invalid_context"

    created = asyncio.run(_request("POST", "/v1/market-data-resolution-snapshots", headers=_headers(), json=_payload(), app=app))
    other_headers = {**_headers(), "X-Tenant-Id": str(uuid4())}
    hidden = asyncio.run(_request("GET", created.headers["location"], headers=other_headers, app=app))
    assert hidden.status_code in {403, 404}
    assert "items" not in hidden.json()
    assert "marketDataResolutionSnapshotId" not in hidden.json()


def test_active_policy_endpoint_returns_only_effective_tenant_policies() -> None:
    engine = create_engine(DATABASE_URL)
    load_demo_data(engine)
    app = create_app(engine=engine)
    response = asyncio.run(_request("GET", "/v1/market-data/valuation-policies?valuationDate=2026-08-28", headers=_headers(), app=app))

    assert response.status_code == 200
    assert any(item["valuationPolicyId"] == str(DEMO_IDS["valuation_policy"]) for item in response.json())
