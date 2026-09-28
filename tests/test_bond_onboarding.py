"""Focused contracts for sparse, provider-enrichable bond onboarding."""

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


def test_bond_submission_requires_coupon_structure_but_accepts_sparse_terms():
    response = _post("/v1/bond-proposals", {
        "canonicalName": f"Provider enriched bond {uuid4().hex[:8]}",
        "internalCode": f"BOND_ENRICH_{uuid4().hex[:8]}",
        "effectiveFrom": "2026-09-03",
        "couponType": "FLOATING",
        "submissionMode": "MANUAL",
    })

    assert response.status_code == 201, response.text
    data = response.json()["data"]
    assert data["status"] == "PENDING"
    assert data["couponType"] == "FLOATING"
    assert data["enrichmentStatus"] == "PENDING_ENRICHMENT"


def test_bond_submission_rejects_unknown_coupon_structure():
    response = _post("/v1/bond-proposals", {
        "canonicalName": "Invalid bond",
        "effectiveFrom": "2026-09-03",
        "couponType": "MYSTERY",
    })

    assert response.status_code == 422, response.text


def test_complete_zero_coupon_bond_can_be_approved():
    response = _post("/v1/bond-proposals", {
        "canonicalName": f"Complete zero coupon bond {uuid4().hex[:8]}",
        "internalCode": f"BOND_ZERO_{uuid4().hex[:8]}",
        "baseCurrencyId": str(DEMO_IDS["usd_currency"]),
        "effectiveFrom": "2026-09-03",
        "maturityDate": "2031-09-03",
        "couponType": "ZERO",
        "redemptionAmountPerPar": "100",
        "submissionMode": "MANUAL",
    })
    assert response.status_code == 201, response.text
    proposal_id = response.json()["data"]["proposalId"]
    assert response.json()["data"]["enrichmentStatus"] == "READY_FOR_APPROVAL"

    decision = _post(f"/v1/bond-proposals/{proposal_id}/decision", {
        "decision": "APPROVED",
        "reason": "Operations validated the zero-coupon bond identity and redemption terms.",
    })
    assert decision.status_code == 200, decision.text
    assert decision.json()["data"]["status"] == "APPROVED"
    assert decision.json()["data"]["instrumentId"]
