"""Regression tests for the UI-driven schema hardening pass."""

import asyncio
import os
from uuid import uuid4

from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, text

from apps.reference_api.main import create_app
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS


def test_hardening_tables_and_audit_columns_are_modelled() -> None:
    assert "ten.tenant_user_account" in m.metadata.tables
    assert "md.market_data_series_dimension" in m.metadata.tables
    assert "tenant_id" in m.external_object_mapping.c
    assert "source_observation_key" in m.market_data_observation.c
    assert "locked_ytm" in m.trade.c
    assert "price_input_snapshot_item_id" in m.nav_valuation_line.c
    assert "fx_input_snapshot_item_id" in m.nav_valuation_line.c


def test_hardening_indexes_and_period_checks_are_declared() -> None:
    indexes = {
        index.name
        for table in m.metadata.tables.values()
        for index in table.indexes
    }
    assert "ix_market_data_series_dimension_lookup" in indexes
    assert "uq_market_data_observation_source_key" in indexes
    assert "uq_trade_external_reference_source_value" in indexes
    assert "uq_cash_balance_snapshot_source" in indexes
    assert any(constraint.name == "ck_instrument_definition_version_valid_period" for constraint in m.instrument_definition_version.constraints)
    assert any(constraint.name == "ck_listing_definition_version_valid_period" for constraint in m.listing_definition_version.constraints)


async def _get(path: str, headers: dict[str, str]):
    async with AsyncClient(transport=ASGITransport(app=create_app()), base_url="http://test") as client:
        return await client.get(path, headers=headers)


def test_tenant_api_requires_an_active_membership() -> None:
    response = asyncio.run(
        _get(
            "/v1/instruments/search?q=HSBC",
            {
                "X-Tenant-Id": str(uuid4()),
                "X-User-Account-Id": str(DEMO_IDS["demo_user_account"]),
            },
        )
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "User account is not an active member of this tenant"


def test_instrument_detail_hides_market_data_without_dataset_entitlement() -> None:
    engine = create_engine(
        os.environ.get(
            "DATABASE_URL",
            "postgresql+psycopg://fortem:fortem_local_only@localhost:54329/fortem_secm",
        )
    )
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                UPDATE ten.tenant_dataset_entitlement
                SET status = 'SUSPENDED'
                WHERE tenant_id = :tenant_id AND dataset_id = :dataset_id
                """
            ),
            {"tenant_id": DEMO_IDS["tenant"], "dataset_id": DEMO_IDS["multi_asset_dataset"]},
        )
    try:
        response = asyncio.run(
            _get(
                f"/v1/instruments/{DEMO_IDS['bond_instrument_node']}",
                {
                    "X-Tenant-Id": str(DEMO_IDS["tenant"]),
                    "X-User-Account-Id": str(DEMO_IDS["demo_user_account"]),
                },
            )
        )
        assert response.status_code == 200
        assert response.json()["data"]["instrumentMarketData"] == []
    finally:
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    UPDATE ten.tenant_dataset_entitlement
                    SET status = 'ACTIVE'
                    WHERE tenant_id = :tenant_id AND dataset_id = :dataset_id
                    """
                ),
                {"tenant_id": DEMO_IDS["tenant"], "dataset_id": DEMO_IDS["multi_asset_dataset"]},
            )


def test_instrument_reads_use_approved_definition_version_not_projection() -> None:
    engine = create_engine(
        os.environ.get(
            "DATABASE_URL",
            "postgresql+psycopg://fortem:fortem_local_only@localhost:54329/fortem_secm",
        )
    )
    with engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE secm.instrument SET asset_class = 'MUTATED_PROJECTION' WHERE instrument_node_id = :instrument_id"
            ),
            {"instrument_id": DEMO_IDS["hsbc_instrument_node"]},
        )
    try:
        response = asyncio.run(
            _get(
                "/v1/instruments/search?q=HSBC",
                {
                    "X-Tenant-Id": str(DEMO_IDS["tenant"]),
                    "X-User-Account-Id": str(DEMO_IDS["demo_user_account"]),
                },
            )
        )
        assert response.status_code == 200
        hsbc = next(item for item in response.json()["data"] if item["instrumentId"] == str(DEMO_IDS["hsbc_instrument_node"]))
        assert hsbc["assetClass"] == "EQUITY"
    finally:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE secm.instrument SET asset_class = 'EQUITY' WHERE instrument_node_id = :instrument_id"
                ),
                {"instrument_id": DEMO_IDS["hsbc_instrument_node"]},
            )
