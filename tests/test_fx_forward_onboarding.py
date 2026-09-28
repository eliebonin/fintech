"""Focused contract tests for FX-forward onboarding."""

import asyncio
from uuid import uuid4

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from apps.reference_api.db import get_engine
from apps.reference_api.main import create_app
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS


TENANT = str(DEMO_IDS["tenant"])
ACTOR = str(DEMO_IDS["demo_user_account"])


def _request(method: str, path: str, payload: dict[str, object] | None = None):
    async def request():
        async with AsyncClient(transport=ASGITransport(app=create_app()), base_url="http://test") as client:
            return await client.request(
                method,
                path,
                json=payload,
                headers={"X-Tenant-Id": TENANT, "X-User-Account-Id": ACTOR},
            )

    return asyncio.run(request())


def _post(path: str, payload: dict[str, object]):
    return _request("POST", path, payload)


def test_fx_forward_proposal_approval_materializes_canonical_terms_and_dates():
    suffix = uuid4().hex[:8].upper()
    response = _post("/v1/fx-forward-proposals", {
        "canonicalName": f"GBP/USD 3M OTC forward {suffix}",
        "internalCode": f"FXFWD_GBPUSD_3M_{suffix}",
        "effectiveFrom": "2026-09-08",
        "baseCurrencyId": str(DEMO_IDS["gbp_currency"]),
        "quoteCurrencyId": str(DEMO_IDS["usd_currency"]),
        "quoteConvention": "USD_PER_GBP",
        "agreedForwardRate": "1.3425",
        "settlementType": "DELIVERABLE",
        "maturityDate": "2026-12-08",
        "settlementDate": "2026-12-10",
        "submissionMode": "MANUAL",
    })
    assert response.status_code == 201, response.text
    proposal = response.json()["data"]
    assert proposal["status"] == "PENDING"
    assert proposal["proposalType"] == "CREATE_FX_FORWARD"
    assert proposal["baseCurrencyId"] == str(DEMO_IDS["gbp_currency"])
    assert proposal["quoteCurrencyId"] == str(DEMO_IDS["usd_currency"])

    proposal_id = proposal["proposalId"]
    queue = _request("GET", "/v1/work-queue")
    assert queue.status_code == 200, queue.text
    queue_item = next(item for item in queue.json()["items"] if item.get("referenceId") == proposal_id)
    assert queue_item["category"] == "REFERENCE_DATA_REVIEW"
    assert queue_item["reviewPath"] == f"/reference-data/review/{proposal_id}"

    approved = _post(f"/v1/reference-data-proposals/{proposal_id}/decision", {
        "decision": "APPROVED",
        "reason": "Operations validated the bilateral currencies, rate convention, and maturity.",
    })
    assert approved.status_code == 200, approved.text
    instrument_id = approved.json()["data"]["referenceNodeId"]
    assert instrument_id

    with get_engine().connect() as connection:
        instrument = connection.execute(
            select(m.instrument).where(m.instrument.c.instrument_node_id == instrument_id)
        ).mappings().one()
        terms = connection.execute(
            select(m.fx_forward_terms).where(m.fx_forward_terms.c.instrument_node_id == instrument_id)
        ).mappings().one()
        dates = connection.execute(
            select(m.instrument_dates).where(m.instrument_dates.c.instrument_node_id == instrument_id)
        ).mappings().one()

    assert instrument["asset_class"] == "FX"
    assert instrument["base_currency_id"] == DEMO_IDS["gbp_currency"]
    assert terms["quote_currency_id"] == DEMO_IDS["usd_currency"]
    assert terms["quote_convention"] == "USD_PER_GBP"
    assert str(terms["agreed_forward_rate"]) == "1.342500000000"
    assert terms["settlement_type"] == "DELIVERABLE"
    assert str(dates["maturity_date"]) == "2026-12-08"
    assert str(dates["settlement_date"]) == "2026-12-10"


def test_fx_forward_rejects_same_base_and_quote_currency():
    response = _post("/v1/fx-forward-proposals", {
        "canonicalName": f"Invalid same-currency forward {uuid4().hex[:8]}",
        "baseCurrencyId": str(DEMO_IDS["gbp_currency"]),
        "quoteCurrencyId": str(DEMO_IDS["gbp_currency"]),
        "quoteConvention": "GBP_PER_GBP",
        "agreedForwardRate": "1",
        "settlementType": "DELIVERABLE",
        "effectiveFrom": "2026-09-08",
        "maturityDate": "2026-12-08",
        "submissionMode": "MANUAL",
    })
    assert response.status_code == 409, response.text
