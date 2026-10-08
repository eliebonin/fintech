"""API contracts for the MVP market-data catalogue and portfolio views."""

import asyncio
from uuid import uuid5

from httpx import ASGITransport, AsyncClient

from apps.reference_api.main import create_app
from security_master_schema.demo_data import DEMO_IDS
from security_master_schema.mvp_demo_data import MVP_NAMESPACE


DEMO_TENANT = str(DEMO_IDS["tenant"])
DEMO_ACTOR = str(DEMO_IDS["demo_user_account"])


async def _request(path: str):
    async with AsyncClient(transport=ASGITransport(app=create_app()), base_url="http://test") as client:
        return await client.get(path, headers={"X-Tenant-Id": DEMO_TENANT, "X-User-Account-Id": DEMO_ACTOR})


def test_market_data_series_returns_provenance_and_cut_metadata():
    response = asyncio.run(_request("/v1/market-data/series?fromDate=2026-08-20&toDate=2026-08-28&limit=5"))

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]
    first = payload["data"][0]
    assert first["seriesId"]
    assert first["providerId"]
    assert first["datasetId"]
    assert first["licenceId"]
    assert first["expectedFrequency"] == "BUSINESS_DAILY"
    assert first["expectedCalendarId"]
    assert first["coverageStartDate"] == "2024-09-02"
    assert first["coverageEndDate"] == "2026-08-28"
    assert first["observations"]
    assert first["observations"][0]["datasetId"]
    assert first["observations"][0]["licenceId"]
    assert first["observations"][0]["vintageId"]
    assert payload["meta"]["source"] == "live-reference-api"


def test_market_data_series_can_drill_into_one_reference_node():
    reference_node_id = str(DEMO_IDS["mvp_us_equity_listing"])
    response = asyncio.run(_request(f"/v1/market-data/series?referenceNodeId={reference_node_id}&fromDate=2024-09-02&toDate=2026-08-28&limit=50"))

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["data"]) == 1
    assert payload["data"][0]["referenceNodeId"] == reference_node_id
    assert payload["data"][0]["referenceNodeName"] == "MUST listed"
    assert len(payload["data"][0]["observations"]) >= 500
    assert payload["data"][0]["observations"][0]["marketDate"] == "2024-09-02"
    assert payload["data"][0]["observations"][-1]["marketDate"] == "2026-08-28"




def test_booked_trades_returns_seeded_executions_and_supports_portfolio_filter():
    response = asyncio.run(_request("/v1/trades?limit=50"))

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["data"]) >= 6
    # Real/custom bookings can precede the seeded MVP executions.
    # Check the known fixture instead of assuming the newest trade's strategy.
    first = next(item for item in payload["data"] if item["tradeId"] == str(uuid5(MVP_NAMESPACE, "trade:us_equity")))
    assert first["tradeId"]
    assert first["strategyCode"] in {"MVP_US_PORTFOLIO", "MVP_UK_PORTFOLIO"}
    assert first["subjectName"]
    assert first["instrumentName"]
    assert first["tradeType"] == "INVESTMENT"
    assert first["lifecycleStatus"] == "BOOKED"
    assert first["executionChannel"] == "MANUAL_UI"

    filtered = asyncio.run(_request("/v1/trades?portfolioCode=MVP_US_PORTFOLIO&limit=50"))
    assert filtered.status_code == 200
    assert filtered.json()["data"]
    assert all(item["strategyCode"] == "MVP_US_PORTFOLIO" for item in filtered.json()["data"])


def test_trade_detail_returns_normalized_parties_fees_and_lifecycle():
    trade_id = uuid5(MVP_NAMESPACE, "trade:us_equity")
    response = asyncio.run(_request(f"/v1/trades/{trade_id}"))

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["trade"]["tradeId"] == str(trade_id)
    assert {item["role"] for item in payload["parties"]} >= {"CLIENT", "COUNTERPARTY", "CUSTODIAN", "EXECUTING_BROKER"}
    assert payload["trade"]["traderPersonId"]
    assert payload["parties"][0]["partyName"]
    assert payload["fees"]
    assert payload["fees"][0]["feeCurrency"]
    assert payload["externalReferences"]
    assert payload["lifecycleEvents"]
    assert payload["lifecycleEvents"][0]["eventType"] == "BOOKED"
