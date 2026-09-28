import asyncio
from uuid import uuid4

from httpx import ASGITransport, AsyncClient

from apps.reference_api.main import create_app
from security_master_schema.demo_data import DEMO_IDS


TENANT = str(DEMO_IDS["tenant"])
ACTOR = str(DEMO_IDS["demo_user_account"])
HEADERS = {"X-Tenant-Id": TENANT, "X-User-Account-Id": ACTOR}


async def _request(method: str, path: str, headers=None, **kwargs):
    async with AsyncClient(transport=ASGITransport(app=create_app()), base_url="http://test") as client:
        return await client.request(method, path, headers=headers or HEADERS, **kwargs)


def _proposal_body():
    return {
        "namespace": "BANK_A_STATIC_PROD",
        "externalObjectType": "LISTING",
        "externalId": f"API_TEST_{uuid4().hex[:12]}",
        "targetObjectType": "LISTING",
        "targetObjectId": str(DEMO_IDS["hsbc_xlon_listing_node"]),
        "contextMarketVenueId": str(DEMO_IDS["xlon_venue"]),
        "validFrom": "2026-08-28",
        "reason": "Reference API integration test mapping",
    }


def test_mapping_proposal_can_be_approved_once_and_cannot_be_decided_twice():
    proposed = asyncio.run(_request("POST", "/v1/reference-mapping-proposals", json=_proposal_body()))
    proposal_id = proposed.json()["proposalId"]

    approved = asyncio.run(_request("POST", f"/v1/reference-mapping-proposals/{proposal_id}/decision", json={"decision": "APPROVED", "reason": "Verified against source fixture"}))
    duplicate = asyncio.run(_request("POST", f"/v1/reference-mapping-proposals/{proposal_id}/decision", json={"decision": "REJECTED", "reason": "Must be rejected as duplicate"}))

    assert proposed.status_code == 201
    assert proposed.json()["status"] == "PENDING"
    assert approved.status_code == 200
    assert approved.json()["status"] == "APPROVED"
    assert duplicate.status_code == 409


def test_mapping_proposal_rejection_does_not_create_verified_mapping():
    proposed = asyncio.run(_request("POST", "/v1/reference-mapping-proposals", json=_proposal_body()))
    proposal_id = proposed.json()["proposalId"]

    rejected = asyncio.run(_request("POST", f"/v1/reference-mapping-proposals/{proposal_id}/decision", json={"decision": "REJECTED", "reason": "Fixture rejection path"}))

    assert proposed.status_code == 201
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "REJECTED"


def test_mapping_mutation_requires_an_active_actor_account():
    response = asyncio.run(_request("POST", "/v1/reference-mapping-proposals", headers={"X-Tenant-Id": TENANT, "X-User-Account-Id": str(uuid4())}, json=_proposal_body()))

    assert response.status_code == 403
    assert response.json()["detail"] == "User account is not active"
