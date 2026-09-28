"""Focused contracts for manual index onboarding and catalogue references."""

import asyncio
from uuid import uuid4

from httpx import ASGITransport, AsyncClient

from apps.reference_api.main import create_app
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


def test_index_submission_is_manual_and_pending():
    response = _post("/v1/index-proposals", {
        "canonicalName": f"Provider enriched index {uuid4().hex[:8]}",
        "internalCode": f"INDEX_ENRICH_{uuid4().hex[:8]}",
        "effectiveFrom": "2026-09-07",
        "indexKind": "PROPRIETARY",
        "submissionMode": "MANUAL",
    })

    assert response.status_code == 201, response.text
    data = response.json()["data"]
    assert data["status"] == "PENDING"
    assert data["proposalType"] == "CREATE_INDEX"
    assert data["indexKind"] == "PROPRIETARY"
    assert data["indexId"] is None


def test_index_submission_rejects_unknown_index_kind():
    response = _post("/v1/index-proposals", {
        "canonicalName": "Invalid index",
        "effectiveFrom": "2026-09-07",
        "indexKind": "MYSTERY",
    })

    assert response.status_code == 422, response.text


def test_approved_index_materializes_family_terms_and_methodology():
    profiles = _request("GET", "/v1/return-profiles")
    assert profiles.status_code == 200, profiles.text
    price_profile_id = next(
        row["returnProfileId"]
        for row in profiles.json()["data"]
        if row["profileCode"] == "PRICE_RETURN"
    )
    response = _post("/v1/index-proposals", {
        "canonicalName": f"Demo public price index {uuid4().hex[:8]}",
        "internalCode": f"INDEX_PUBLIC_{uuid4().hex[:8]}",
        "effectiveFrom": "2026-09-07",
        "indexKind": "PUBLIC",
        "indexFamilyName": f"Demo public family {uuid4().hex[:8]}",
        "returnProfileId": price_profile_id,
        "baseCurrencyId": str(DEMO_IDS["usd_currency"]),
        "administratorOrganisationId": str(DEMO_IDS["mvp_bloomberg_organisation"]),
        "calculationAgentOrganisationId": str(DEMO_IDS["mvp_bloomberg_organisation"]),
        "baseDate": "2020-01-01",
        "baseLevel": "1000",
        "methodologyReference": "synthetic://demo/index/methodology/v1",
        "weightingMethod": "FLOAT_ADJUSTED_MARKET_CAP",
        "rebalanceFrequency": "QUARTERLY",
        "calculationFrequency": "BUSINESS_DAILY",
        "dividendTreatment": "PRICE_RETURN",
        "launchDate": "2020-01-01",
        "submissionMode": "MANUAL",
    })
    assert response.status_code == 201, response.text
    proposal_id = response.json()["data"]["proposalId"]

    decision = _post(f"/v1/index-proposals/{proposal_id}/decision", {
        "decision": "APPROVED",
        "reason": "Operations validated the index identity, return semantics, and methodology evidence.",
    })

    assert decision.status_code == 200, decision.text
    data = decision.json()["data"]
    assert data["status"] == "APPROVED"
    assert data["indexId"]


def test_catalogues_return_active_index_options():
    currencies = _request("GET", "/v1/currencies?groups=REGULAR,CRYPTO")
    profiles = _request("GET", "/v1/return-profiles")
    organisations = _request("GET", "/v1/organisations?q=Bloomberg")
    families = _request("GET", "/v1/index-families")

    assert currencies.status_code == 200, currencies.text
    currency_groups = currencies.json()["data"]
    assert [group["groupCode"] for group in currency_groups] == ["REGULAR", "CRYPTO"]
    assert any(row["currencyCode"] == "USD" for row in currency_groups[0]["items"])
    assert any(row["currencyCode"] == "BTC" for row in currency_groups[1]["items"])
    assert profiles.status_code == 200, profiles.text
    assert any(row["profileCode"] == "PRICE_RETURN" for row in profiles.json()["data"])
    assert organisations.status_code == 200, organisations.text
    assert any("Bloomberg" in row["displayName"] for row in organisations.json()["data"])
    assert families.status_code == 200, families.text
    assert isinstance(families.json()["data"], list)


def test_currency_catalogue_filters_by_requested_group_without_instrument_assumptions():
    regular = _request("GET", "/v1/currencies?groups=REGULAR")
    crypto = _request("GET", "/v1/currencies?groups=CRYPTO")
    invalid = _request("GET", "/v1/currencies?groups=NOT_A_GROUP")

    assert regular.status_code == 200, regular.text
    assert [group["groupCode"] for group in regular.json()["data"]] == ["REGULAR"]
    assert all(item["currencyKind"] == "FIAT" for item in regular.json()["data"][0]["items"])

    assert crypto.status_code == 200, crypto.text
    assert [group["groupCode"] for group in crypto.json()["data"]] == ["CRYPTO"]
    assert {item["currencyKind"] for item in crypto.json()["data"][0]["items"]} <= {"CRYPTOASSET", "STABLECOIN"}

    assert invalid.status_code == 422, invalid.text


def test_index_kind_catalogue_exposes_governed_metadata():
    response = _request("GET", "/v1/index-kind-catalogue")

    assert response.status_code == 200, response.text
    kinds = {row["indexKindCode"]: row for row in response.json()["data"]}
    assert {"PUBLIC", "QIS", "PROPRIETARY", "CUSTOM_BASKET"}.issubset(kinds)
    assert kinds["PUBLIC"]["disseminationClass"] == "PUBLIC"
    assert kinds["PUBLIC"]["methodologyOwnership"] == "PROVIDER_OWNED"
    assert "S&P 500" in kinds["PUBLIC"]["exampleText"]


def test_index_family_submission_is_manual_and_pending():
    response = _post("/v1/index-family-proposals", {
        "canonicalName": f"Demo family proposal {uuid4().hex[:8]}",
        "internalCode": f"FAMILY_{uuid4().hex[:8]}",
        "providerOrganisationId": str(DEMO_IDS["mvp_bloomberg_organisation"]),
        "submissionMode": "MANUAL",
    })

    assert response.status_code == 201, response.text
    data = response.json()["data"]
    assert data["status"] == "PENDING"
    assert data["proposalType"] == "CREATE_INDEX_FAMILY"
    assert data["submissionMode"] == "MANUAL"
    assert data["familyId"] is None
    assert data["familyNodeId"] is None


def test_approved_index_family_materializes_non_tradable_family():
    family_name = f"Approved family {uuid4().hex[:8]}"
    response = _post("/v1/index-family-proposals", {
        "canonicalName": family_name,
        "providerOrganisationId": str(DEMO_IDS["mvp_bloomberg_organisation"]),
        "submissionMode": "MANUAL",
    })
    assert response.status_code == 201, response.text
    proposal_id = response.json()["data"]["proposalId"]

    decision = _post(f"/v1/index-family-proposals/{proposal_id}/decision", {
        "decision": "APPROVED",
        "reason": "Operations validated the family identity and provider reference.",
    })

    assert decision.status_code == 200, decision.text
    data = decision.json()["data"]
    assert data["status"] == "APPROVED"
    assert data["familyId"]
    assert data["familyNodeId"]

    families = _request("GET", "/v1/index-families")
    assert families.status_code == 200, families.text
    assert any(row["indexFamilyId"] == data["familyId"] and row["familyName"] == family_name for row in families.json()["data"])


def test_index_family_requires_an_active_provider_organisation_when_supplied():
    response = _post("/v1/index-family-proposals", {
        "canonicalName": f"Invalid provider family {uuid4().hex[:8]}",
        "providerOrganisationId": str(uuid4()),
        "submissionMode": "MANUAL",
    })

    assert response.status_code == 404, response.text


def test_work_queue_contains_pending_index_and_index_family_proposals():
    family_response = _post("/v1/index-family-proposals", {
        "canonicalName": f"Queue family {uuid4().hex[:8]}",
        "submissionMode": "MANUAL",
    })
    index_response = _post("/v1/index-proposals", {
        "canonicalName": f"Queue index {uuid4().hex[:8]}",
        "effectiveFrom": "2026-09-07",
        "indexKind": "PUBLIC",
        "submissionMode": "MANUAL",
    })
    assert family_response.status_code == 201, family_response.text
    assert index_response.status_code == 201, index_response.text

    queue = _request("GET", "/v1/work-queue")
    assert queue.status_code == 200, queue.text
    items_by_id = {item["referenceId"]: item for item in queue.json()["items"]}
    family_item = items_by_id[family_response.json()["data"]["proposalId"]]
    index_item = items_by_id[index_response.json()["data"]["proposalId"]]
    assert family_item["category"] == "REFERENCE_DATA_REVIEW"
    assert "family" in family_item["title"].lower()
    assert index_item["category"] == "REFERENCE_DATA_REVIEW"
    assert "index" in index_item["title"].lower()
