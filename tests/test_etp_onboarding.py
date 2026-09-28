"""End-to-end contract tests for exchange-traded-product onboarding."""

import asyncio
from uuid import uuid4

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from apps.reference_api.main import create_app
from security_master_schema import models as m
from apps.reference_api.db import get_engine
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


def test_etf_proposal_approval_materializes_terms_and_authoritative_index_relationship():
    suffix = uuid4().hex[:8].upper()
    response = _post("/v1/etp-proposals", {
        "canonicalName": f"Synthetic World Equity UCITS ETF {suffix}",
        "internalCode": f"SYN_ETF_{suffix}",
        "effectiveFrom": "2026-09-08",
        "etpKind": "ETF",
        "legalForm": "UCITS_FUND",
        "replicationMethod": "PHYSICAL",
        "collateralisationType": "NOT_APPLICABLE",
        "redemptionModel": "OPEN_ENDED",
        "distributionPolicy": "ACCUMULATING",
        "issuerOrganisationId": str(DEMO_IDS["hsbc_organisation"]),
        "baseCurrencyId": str(DEMO_IDS["usd_currency"]),
        "referenceNodeId": str(DEMO_IDS["mvp_sp500_price_index_node"]),
        "submissionMode": "MANUAL",
    })
    assert response.status_code == 201, response.text
    proposal = response.json()["data"]
    assert proposal["status"] == "PENDING"
    assert proposal["etpKind"] == "ETF"
    queue = _get("/v1/work-queue")
    queue_item = next(item for item in queue.json()["items"] if item.get("referenceId") == proposal["proposalId"])
    assert queue_item["category"] == "REFERENCE_DATA_REVIEW"
    assert queue_item["reviewPath"] == f"/reference-data/review/{proposal['proposalId']}"

    approved = _post(
        f"/v1/reference-data-proposals/{proposal['proposalId']}/decision",
        {"decision": "APPROVED", "reason": "Operations confirmed wrapper terms and tracked index."},
    )
    assert approved.status_code == 200, approved.text
    instrument_id = approved.json()["data"]["referenceNodeId"]
    assert instrument_id

    with get_engine().connect() as connection:
        terms = connection.execute(
            select(m.etp_terms).where(m.etp_terms.c.instrument_node_id == instrument_id)
        ).mappings().one()
        relationship = connection.execute(
            select(m.instrument_relationship).where(
                m.instrument_relationship.c.from_reference_node_id == instrument_id,
                m.instrument_relationship.c.to_reference_node_id == DEMO_IDS["mvp_sp500_price_index_node"],
            )
        ).mappings().one()
    assert terms["etp_kind"] == "ETF"
    assert terms["reference_node_id"] == DEMO_IDS["mvp_sp500_price_index_node"]
    assert relationship["relationship_type"] == "TRACKS_INDEX"

    listing = _post("/v1/listing-proposals", {
        "instrumentId": instrument_id,
        "listing": {
            "marketVenueId": str(DEMO_IDS["mvp_xetr_venue"]),
            "tradingSymbol": f"SYN{suffix[:4]}",
            "tradingCurrencyId": str(DEMO_IDS["usd_currency"]),
            "quoteFactor": 1,
            "unitMultiplier": 1,
            "isPrimaryListing": True,
            "effectiveFrom": "2026-09-08",
        },
        "submissionMode": "MANUAL",
    })
    assert listing.status_code == 201, listing.text


def test_etp_proposal_rejects_a_reference_node_that_is_not_visible_to_the_tenant():
    response = _post("/v1/etp-proposals", {
        "canonicalName": f"Invalid reference ETP {uuid4().hex[:8]}",
        "effectiveFrom": "2026-09-08",
        "etpKind": "ETN",
        "legalForm": "DEBT_NOTE",
        "redemptionModel": "FIXED_MATURITY",
        "referenceNodeId": str(uuid4()),
        "submissionMode": "MANUAL",
    })
    assert response.status_code == 404, response.text
