"""End-to-end contracts for canonical cryptoasset onboarding."""

import asyncio
from uuid import uuid4

from httpx import ASGITransport, AsyncClient

from apps.reference_api.main import create_app
from security_master_schema.demo_data import DEMO_IDS


TENANT = str(DEMO_IDS["tenant"])
ACTOR = str(DEMO_IDS["demo_user_account"])


def _post(path: str, payload: dict[str, object]):
    async def request():
        async with AsyncClient(transport=ASGITransport(app=create_app()), base_url="http://test") as client:
            return await client.post(path, json=payload, headers={"X-Tenant-Id": TENANT, "X-User-Account-Id": ACTOR})

    return asyncio.run(request())


def _get(path: str):
    async def request():
        async with AsyncClient(transport=ASGITransport(app=create_app()), base_url="http://test") as client:
            return await client.get(path, headers={"X-Tenant-Id": TENANT, "X-User-Account-Id": ACTOR})

    return asyncio.run(request())


def test_manual_cryptoasset_proposal_is_pending_then_materializes_instrument_and_currency_role():
    suffix = uuid4().hex[:8].upper()
    response = _post("/v1/crypto-asset-proposals", {
        "canonicalName": f"Synthetic token {suffix}",
        "internalCode": f"SYNTH_TOKEN_{suffix}",
        "effectiveFrom": "2026-09-07",
        "assetSubtype": "TOKEN",
        "nativeSymbol": f"SYN{suffix[:4]}",
        "protocolName": "Synthetic Protocol",
        "issuerOrganisationId": str(DEMO_IDS["hsbc_organisation"]),
        "decimals": 18,
        "submissionMode": "MANUAL",
    })
    assert response.status_code == 201, response.text
    proposal = response.json()["data"]
    assert proposal["status"] == "PENDING"
    assert proposal["instrumentId"] is None
    assert proposal["currencyId"] is None

    approved = _post(
        f"/v1/crypto-asset-proposals/{proposal['proposalId']}/decision",
        {"decision": "APPROVED", "reason": "Operations validated the digital asset identity."},
    )
    assert approved.status_code == 200, approved.text
    approved_data = approved.json()["data"]
    assert approved_data["status"] == "APPROVED"
    assert approved_data["instrumentId"]
    assert approved_data["currencyId"]


def test_cryptoasset_requires_unique_internal_code_and_native_symbol():
    suffix = uuid4().hex[:8].upper()
    payload = {
        "canonicalName": f"Synthetic token duplicate check {suffix}",
        "internalCode": f"SYNTH_DUP_{suffix}",
        "effectiveFrom": "2026-09-07",
        "assetSubtype": "NATIVE",
        "nativeSymbol": f"DUP{suffix[:4]}",
        "submissionMode": "MANUAL",
    }
    first = _post("/v1/crypto-asset-proposals", payload)
    assert first.status_code == 201, first.text
    first_proposal = first.json()["data"]["proposalId"]
    approved = _post(
        f"/v1/crypto-asset-proposals/{first_proposal}/decision",
        {"decision": "APPROVED", "reason": "Operations validated the native symbol."},
    )
    assert approved.status_code == 200, approved.text
    second = _post("/v1/crypto-asset-proposals", {**payload, "canonicalName": f"Another token {suffix}"})
    assert second.status_code == 409, second.text

    symbol_collision = _post("/v1/crypto-asset-proposals", {
        **payload,
        "canonicalName": f"Third token {suffix}",
        "internalCode": f"SYNTH_OTHER_{suffix}",
    })
    assert symbol_collision.status_code == 409, symbol_collision.text


def test_pending_cryptoasset_is_reviewable_and_is_a_reference_data_queue_item():
    suffix = uuid4().hex[:8].upper()
    response = _post("/v1/crypto-asset-proposals", {
        "canonicalName": f"Review token {suffix}",
        "internalCode": f"REVIEW_TOKEN_{suffix}",
        "effectiveFrom": "2026-09-07",
        "assetSubtype": "TOKEN",
        "nativeSymbol": f"RVW{suffix[:4]}",
        "protocolName": "Review Protocol",
        "decimals": 18,
        "submissionMode": "MANUAL",
    })
    assert response.status_code == 201, response.text
    proposal_id = response.json()["data"]["proposalId"]

    review = _get(f"/v1/crypto-asset-proposals/{proposal_id}")
    assert review.status_code == 200, review.text
    review_data = review.json()["data"]
    assert review_data["canonicalName"] == f"Review token {suffix}"
    assert review_data["nativeSymbol"] == f"RVW{suffix[:4]}"
    assert review_data["status"] == "PENDING"

    queue = _get("/v1/work-queue")
    assert queue.status_code == 200, queue.text
    item = next(item for item in queue.json()["items"] if item.get("referenceId") == proposal_id)
    assert item["category"] == "REFERENCE_DATA_REVIEW"
    assert item["reviewPath"] == f"/reference-data/review/{proposal_id}"


def test_cryptoasset_rejects_nonexistent_issuer():
    response = _post("/v1/crypto-asset-proposals", {
        "canonicalName": f"Synthetic invalid issuer {uuid4().hex[:8]}",
        "effectiveFrom": "2026-09-07",
        "assetSubtype": "NATIVE",
        "nativeSymbol": f"BAD{uuid4().hex[:4].upper()}",
        "issuerOrganisationId": str(uuid4()),
        "submissionMode": "MANUAL",
    })
    assert response.status_code == 404, response.text
