"""Contract tests for the generic reference-data proposal review workflow."""

import asyncio
from uuid import UUID, uuid4

from httpx import ASGITransport, AsyncClient

from apps.reference_api.main import create_app
from security_master_schema.demo_data import DEMO_IDS


TENANT = str(DEMO_IDS["tenant"])
ACTOR = str(DEMO_IDS["demo_user_account"])


async def _request(method: str, path: str, *, payload: dict[str, object] | None = None):
    async with AsyncClient(transport=ASGITransport(app=create_app()), base_url="http://test") as client:
        return await client.request(
            method,
            path,
            json=payload,
            headers={"X-Tenant-Id": TENANT, "X-User-Account-Id": ACTOR},
        )


def test_generic_proposal_review_can_read_and_decide_a_bond_proposal():
    suffix = uuid4().hex[:8].upper()
    created = asyncio.run(
        _request(
            "POST",
            "/v1/bond-proposals",
            payload={
                "canonicalName": f"Generic review bond {suffix}",
                "internalCode": f"GENERIC_REVIEW_{suffix}",
                "effectiveFrom": "2026-09-08",
                "couponType": "ZERO",
                "baseCurrencyId": str(DEMO_IDS["gbp_currency"]),
                "maturityDate": "2031-09-08",
                "submissionMode": "MANUAL",
            },
        )
    )
    assert created.status_code == 201, created.text
    proposal_id = created.json()["data"]["proposalId"]

    review = asyncio.run(_request("GET", f"/v1/reference-data-proposals/{proposal_id}"))
    assert review.status_code == 200, review.text
    review_data = review.json()["data"]
    assert review_data["proposalId"] == proposal_id
    assert review_data["proposalType"] == "CREATE_BOND"
    assert review_data["status"] == "PENDING"
    assert review_data["proposedPayload"]["canonicalName"] == f"Generic review bond {suffix}"
    assert review_data["decision"] is None

    queue = asyncio.run(_request("GET", "/v1/work-queue"))
    assert queue.status_code == 200, queue.text
    queue_item = next(item for item in queue.json()["items"] if item.get("referenceId") == proposal_id)
    assert queue_item["reviewPath"] == f"/reference-data/review/{proposal_id}"

    decided = asyncio.run(
        _request(
            "POST",
            f"/v1/reference-data-proposals/{proposal_id}/decision",
            payload={"decision": "APPROVED", "reason": "Generic review workflow validated the bond."},
        )
    )
    assert decided.status_code == 200, decided.text
    decided_data = decided.json()["data"]
    assert decided_data["status"] == "APPROVED"
    assert decided_data["decision"] == "APPROVED"
    assert decided_data["decisionEvidence"]["manualDecision"] is True

    repeated = asyncio.run(
        _request(
            "POST",
            f"/v1/reference-data-proposals/{proposal_id}/decision",
            payload={"decision": "REJECTED", "reason": "A second decision is not permitted."},
        )
    )
    assert repeated.status_code == 409, repeated.text


def test_generic_proposal_review_is_tenant_scoped_and_returns_not_found():
    missing = asyncio.run(_request("GET", f"/v1/reference-data-proposals/{uuid4()}"))
    assert missing.status_code == 404, missing.text

    malformed = asyncio.run(_request("GET", f"/v1/reference-data-proposals/{UUID(int=0)}"))
    assert malformed.status_code == 404, malformed.text
