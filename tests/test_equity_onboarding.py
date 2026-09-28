"""End-to-end contracts for policy-mediated equity onboarding."""

import asyncio
from uuid import uuid4

from httpx import ASGITransport, AsyncClient

from apps.reference_api.main import create_app
from security_master_schema.demo_data import DEMO_IDS


TENANT = str(DEMO_IDS["tenant"])
ACTOR = str(DEMO_IDS["demo_user_account"])


def _payload(*, submission_mode: str = "AUTOMATED", suffix: str | None = None) -> dict[str, object]:
    suffix = suffix or uuid4().hex[:8].upper()
    result: dict[str, object] = {
        "canonicalName": f"Synthetic onboarding equity {suffix}",
        "internalCode": f"ONBOARD_EQUITY_{suffix}",
        "issuerOrganisationId": str(DEMO_IDS["hsbc_organisation"]),
        "baseCurrencyId": str(DEMO_IDS["usd_currency"]),
        "effectiveFrom": "2026-09-01",
        "isin": f"GB00ONBOARD{suffix[:4]}",
        "figi": f"BBG00ONBOARD{suffix[:4]}",
        "sedol": f"ONB{suffix[:4]}",
        "listings": [{
            "marketVenueId": str(DEMO_IDS["xlon_venue"]),
            "tradingSymbol": f"ONB{suffix[:4]}",
            "tradingCurrencyId": str(DEMO_IDS["gbp_currency"]),
            "quoteFactor": "100",
            "unitMultiplier": "1",
            "isPrimaryListing": True,
            "effectiveFrom": "2026-09-01",
        }],
        "submissionMode": submission_mode,
    }
    if submission_mode == "AUTOMATED":
        result.update({
            "sourceSystemId": str(DEMO_IDS["source_system"]),
            "sourceNamespace": "BANK_A_STATIC_PROD",
            "sourceExternalId": f"BANK-{suffix}",
            "sourceObjectType": "LISTING",
            "automationPolicyCode": "BANK_A_EQUITY_CREATE",
            "idempotencyKey": f"bank-equity-{suffix}",
            "confidenceScore": "0.99",
        })
    return result


async def _post(path: str, payload: dict[str, object]):
    async with AsyncClient(transport=ASGITransport(app=create_app()), base_url="http://test") as client:
        return await client.post(path, json=payload, headers={"X-Tenant-Id": TENANT, "X-User-Account-Id": ACTOR})


async def _get(path: str):
    async with AsyncClient(transport=ASGITransport(app=create_app()), base_url="http://test") as client:
        return await client.get(path, headers={"X-Tenant-Id": TENANT, "X-User-Account-Id": ACTOR})


def test_trusted_equity_source_is_auto_approved_and_idempotent():
    payload = _payload()
    first = asyncio.run(_post("/v1/equity-proposals", payload))
    assert first.status_code == 201, first.text
    first_data = first.json()["data"]
    assert first_data["status"] == "APPROVED"
    assert first_data["submissionMode"] == "AUTOMATED"
    assert first_data["decisionMethod"] == "AUTOMATED"
    assert first_data["instrumentId"]
    assert first_data["listingIds"]

    retry = asyncio.run(_post("/v1/equity-proposals", payload))
    assert retry.status_code == 201, retry.text
    assert retry.json()["data"]["proposalId"] == first_data["proposalId"]
    assert retry.json()["data"]["instrumentId"] == first_data["instrumentId"]


def test_manual_equity_proposal_remains_pending_until_decision():
    payload = _payload(submission_mode="MANUAL")
    payload.update({
        "sourceSystemId": str(DEMO_IDS["source_system"]),
        "sourceNamespace": "BANK_A_STATIC_PROD",
        "sourceExternalId": f"MANUAL-BANK-{uuid4().hex[:8].upper()}",
        "sourceObjectType": "LISTING",
    })
    response = asyncio.run(_post("/v1/equity-proposals", payload))
    assert response.status_code == 201, response.text
    data = response.json()["data"]
    assert data["status"] == "PENDING"
    assert data["decisionMethod"] is None

    decided = asyncio.run(_post(
        f"/v1/equity-proposals/{data['proposalId']}/decision",
        {"decision": "APPROVED", "reason": "Operations validated the issuer and venue listing."},
    ))
    assert decided.status_code == 200, decided.text
    decided_data = decided.json()["data"]
    assert decided_data["status"] == "APPROVED"
    assert decided_data["decisionMethod"] == "MANUAL"
    assert decided_data["instrumentId"]


def test_automated_equity_below_policy_threshold_requires_review():
    payload = _payload()
    payload["confidenceScore"] = "0.90"
    response = asyncio.run(_post("/v1/equity-proposals", payload))
    assert response.status_code == 201, response.text
    data = response.json()["data"]
    assert data["status"] == "PENDING"
    assert data["matchStatus"] == "POSSIBLE_MATCH"
    assert data["instrumentId"] is None


def test_manual_instrument_proposal_has_no_listing_and_can_be_approved():
    payload = _payload(submission_mode="MANUAL")
    payload["listings"] = []
    payload.pop("sourceSystemId", None)
    payload.pop("sourceNamespace", None)
    payload.pop("sourceExternalId", None)
    payload["sourceObjectType"] = "INSTRUMENT"
    response = asyncio.run(_post("/v1/equity-proposals", payload))
    assert response.status_code == 201, response.text
    data = response.json()["data"]
    assert data["status"] == "PENDING"
    assert data["listingIds"] == []

    decided = asyncio.run(_post(
        f"/v1/equity-proposals/{data['proposalId']}/decision",
        {"decision": "APPROVED", "reason": "Operations validated the economic instrument."},
    ))
    assert decided.status_code == 200, decided.text
    assert decided.json()["data"]["instrumentId"]
    assert decided.json()["data"]["listingIds"] == []


def test_listing_proposal_requires_an_existing_instrument_context():
    response = asyncio.run(_post("/v1/equity-listing-proposals", {
        "instrumentId": str(uuid4()),
        "listing": {
            "marketVenueId": str(DEMO_IDS["xlon_venue"]),
            "tradingSymbol": "MISSING",
            "tradingCurrencyId": str(DEMO_IDS["gbp_currency"]),
            "quoteFactor": "100",
            "unitMultiplier": "1",
            "effectiveFrom": "2026-09-01",
        },
    }))
    assert response.status_code == 404, response.text


def test_listing_proposal_is_scoped_to_the_selected_instrument():
    suffix = uuid4().hex[:8].upper()
    response = asyncio.run(_post("/v1/equity-listing-proposals", {
        "instrumentId": str(DEMO_IDS["hsbc_instrument_node"]),
        "listing": {
            "marketVenueId": str(DEMO_IDS["xpar_venue"]),
            "tradingSymbol": f"HSD{suffix[:4]}",
            "tradingCurrencyId": str(DEMO_IDS["eur_currency"]),
            "quoteFactor": "1",
            "unitMultiplier": "1",
            "isPrimaryListing": False,
            "effectiveFrom": "2026-09-01",
        },
    }))
    assert response.status_code == 201, response.text
    data = response.json()["data"]
    assert data["status"] == "PENDING"
    assert data["instrumentId"] == str(DEMO_IDS["hsbc_instrument_node"])
    assert data["listingIds"] == [str(DEMO_IDS["hsbc_xlon_listing_node"])]


def test_listing_proposal_is_visible_as_reference_data_review():
    suffix = uuid4().hex[:8].upper()
    response = asyncio.run(_post("/v1/equity-listing-proposals", {
        "instrumentId": str(DEMO_IDS["hsbc_instrument_node"]),
        "listing": {
            "marketVenueId": str(DEMO_IDS["xpar_venue"]),
            "tradingSymbol": f"QUEUE{suffix[:4]}",
            "tradingCurrencyId": str(DEMO_IDS["eur_currency"]),
            "quoteFactor": "1",
            "unitMultiplier": "1",
            "effectiveFrom": "2026-09-01",
        },
    }))
    assert response.status_code == 201, response.text
    proposal_id = response.json()["data"]["proposalId"]

    queue = asyncio.run(_get("/v1/work-queue"))
    assert queue.status_code == 200, queue.text
    item = next(item for item in queue.json()["items"] if item["referenceId"] == proposal_id)
    assert item["itemId"] == f"reference:{proposal_id}"
    assert item["category"] == "REFERENCE_DATA_REVIEW"
    assert "Review listing" in item["title"]


def test_listing_workflow_accepts_digital_asset_and_preserves_operational_identifiers():
    suffix = uuid4().hex[:8].upper()
    response = asyncio.run(_post("/v1/listing-proposals", {
        "instrumentId": str(DEMO_IDS["mvp_btc_node"]),
        "listing": {
            "marketVenueId": str(DEMO_IDS["coinbase_venue"]),
            "tradingSymbol": f"BTC-USD-{suffix[:4]}",
            "venueProductId": f"BTC-USD-{suffix}",
            "fixSecurityId": f"BTCUSD-{suffix}",
            "tradingCurrencyId": str(DEMO_IDS["usd_currency"]),
            "quoteFactor": "1",
            "unitMultiplier": "1",
            "isPrimaryListing": False,
            "effectiveFrom": "2026-09-01",
        },
    }))
    assert response.status_code == 201, response.text
    proposal_id = response.json()["data"]["proposalId"]

    decided = asyncio.run(_post(
        f"/v1/equity-proposals/{proposal_id}/decision",
        {"decision": "APPROVED", "reason": "Operations validated the crypto venue product identifiers."},
    ))
    assert decided.status_code == 200, decided.text
    detail = asyncio.run(_get(f"/v1/instruments/{DEMO_IDS['mvp_btc_node']}"))
    assert detail.status_code == 200, detail.text
    listing = next(row for row in detail.json()["data"]["listings"] if row["tradingSymbol"] == f"BTC-USD-{suffix[:4]}")
    identifiers = {(row["scheme"], row["value"]) for row in listing["identifiers"]}
    assert ("VENUE_PRODUCT_ID", f"BTC-USD-{suffix}") in identifiers
    assert ("FIX_SECURITY_ID", f"BTCUSD-{suffix}") in identifiers
