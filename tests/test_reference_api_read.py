import asyncio
from uuid import UUID

from httpx import ASGITransport, AsyncClient

from apps.reference_api.main import create_app
from security_master_schema.demo_data import DEMO_IDS


DEMO_TENANT = str(DEMO_IDS["tenant"])
DEMO_ACTOR = str(DEMO_IDS["demo_user_account"])


async def _request(method: str, path: str):
    async with AsyncClient(transport=ASGITransport(app=create_app()), base_url="http://test") as client:
        return await client.request(method, path, headers={"X-Tenant-Id": DEMO_TENANT, "X-User-Account-Id": DEMO_ACTOR})


def test_search_returns_view_oriented_canonical_instrument_with_listing_and_mapping():
    response = asyncio.run(_request("GET", "/v1/instruments/search?q=HSBC"))

    assert response.status_code == 200
    payload = response.json()
    assert payload["meta"]["source"] == "live-reference-api"
    hsbc = next(item for item in payload["data"] if item["instrumentId"] == str(DEMO_IDS["hsbc_instrument_node"]))
    assert hsbc["canonicalName"] == "HSBC Demo ordinary shares"
    assert hsbc["listings"][0]["marketVenueMic"] == "XLON"
    assert any(mapping["externalId"] == "ABC" for mapping in hsbc["mappings"])


def test_search_supports_pagination_and_otc_instrument_codes():
    response = asyncio.run(_request("GET", "/v1/instruments/search?q=BOND_DEMO_2031&limit=1&offset=0"))

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["data"]) == 1
    assert payload["meta"]["limit"] == 1
    assert payload["data"][0]["listings"] == []


def test_reference_node_search_returns_non_instrument_underlyings_and_filters_instruments():
    index_response = asyncio.run(_request("GET", "/v1/reference-nodes/search?node_type=INDEX&limit=100"))
    crypto_response = asyncio.run(_request("GET", "/v1/reference-nodes/search?instrument_type=DIGITAL_ASSET&limit=100"))

    assert index_response.status_code == 200
    index_payload = index_response.json()
    assert index_payload["data"]
    assert all(item["nodeType"] == "INDEX" for item in index_payload["data"])
    assert any("S&P 500" in item["canonicalName"] for item in index_payload["data"])

    assert crypto_response.status_code == 200
    crypto_payload = crypto_response.json()
    assert crypto_payload["data"]
    assert all(item["instrumentType"] == "DIGITAL_ASSET" for item in crypto_payload["data"])
    assert {item["canonicalName"] for item in crypto_payload["data"]} >= {"Bitcoin", "Ethereum"}


def test_reference_node_search_can_scope_equity_choices_to_venue_listings():
    response = asyncio.run(_request(
        "GET",
        "/v1/reference-nodes/search?reference_level=LISTING&instrument_type=EQUITY&limit=100",
    ))

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]
    assert all(item["nodeType"] == "LISTING" for item in payload["data"])
    assert all(item["instrumentType"] == "EQUITY" for item in payload["data"])
    hsbc = next(item for item in payload["data"] if item["referenceNodeId"] == str(DEMO_IDS["hsbc_xlon_listing_node"]))
    assert hsbc["parentReferenceNodeId"] == str(DEMO_IDS["hsbc_instrument_node"])
    assert hsbc["marketVenueMic"] == "XLON"
    assert hsbc["tradingSymbol"]


def test_reference_node_search_can_exclude_listings_for_economic_choices():
    response = asyncio.run(_request(
        "GET",
        "/v1/reference-nodes/search?reference_level=ECONOMIC&instrument_type=EQUITY&limit=100",
    ))

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]
    assert all(item["nodeType"] != "LISTING" for item in payload["data"])


def test_detail_returns_instrument_level_market_data_and_unknown_is_404():
    detail = asyncio.run(_request("GET", f"/v1/instruments/{DEMO_IDS['bond_instrument_node']}"))
    missing = asyncio.run(_request("GET", f"/v1/instruments/{UUID('00000000-0000-7000-8000-000000009999')}"))

    assert detail.status_code == 200
    assert detail.json()["data"]["instrumentMarketData"][0]["series"] == "EVALUATED_PRICE"
    assert missing.status_code == 404


def test_market_venues_are_loaded_from_the_canonical_venue_catalogue():
    response = asyncio.run(_request("GET", "/v1/market-venues"))

    assert response.status_code == 200
    payload = response.json()
    codes = [item["venueCode"] for item in payload["data"]]
    assert len(codes) == len(set(codes))
    venues = {item["venueCode"]: item for item in payload["data"]}
    assert {"XLON", "XPAR", "XNYS", "XETR", "XNAS", "KRAKEN"}.issubset(venues)
    assert venues["XPAR"]["displayName"] == "Euronext Paris"
    assert venues["XPAR"]["venueIdentifierScheme"] == "ISO_10383_MIC"
    assert venues["KRAKEN"]["venueType"] == "CEX"


def test_day_count_conventions_are_loaded_from_the_governed_catalogue():
    response = asyncio.run(_request("GET", "/v1/day-count-conventions"))

    assert response.status_code == 200
    payload = response.json()
    conventions = {item["code"]: item for item in payload["data"]}
    assert "ACT_ACT_ICMA" in conventions
    assert conventions["ACT_ACT_ICMA"]["displayName"] == "Actual/Actual ICMA"
    assert conventions["ACT_ACT_ICMA"]["description"]
