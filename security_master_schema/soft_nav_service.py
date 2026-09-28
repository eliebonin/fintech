"""Constrained, reproducible V1 orchestration for indicative Soft NAV."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from hashlib import sha256
from uuid import UUID

from sqlalchemy import Connection, insert, select

from . import models as m
from .market_data_resolver import (
    ResolutionRequest,
    persist_resolution_snapshot,
    resolve_market_data,
)
from .tenancy import assert_tenant_owns_strategy


class SoftNavResolutionError(ValueError):
    """Raised when a required input cannot be safely valued under the policy."""


class FxConversionRequired(SoftNavResolutionError):
    """Raised rather than silently using an absent reporting-currency FX rate."""


@dataclass(frozen=True)
class SoftNavRequest:
    """Complete operating context for one reproducible indicative Soft-NAV run."""

    tenant_id: UUID
    strategy_id: UUID
    position_snapshot_id: UUID
    valuation_policy_id: UUID
    valuation_date: date
    valuation_cut_id: UUID
    market_data_as_of_utc: datetime
    reporting_currency_id: UUID
    calculation_version: str
    use_purpose: str = "VALUATION"


def _snapshot_lines(connection: Connection, request: SoftNavRequest) -> list[dict]:
    """Validate and return only the tenant's full position snapshot lines."""

    snapshot = connection.execute(
        select(
            m.position_snapshot.c.tenant_id,
            m.position_snapshot.c.strategy_id,
            m.position_snapshot.c.status,
        ).where(m.position_snapshot.c.position_snapshot_id == request.position_snapshot_id)
    ).mappings().one_or_none()
    if snapshot is None or snapshot["tenant_id"] != request.tenant_id or snapshot["strategy_id"] != request.strategy_id:
        raise SoftNavResolutionError("Position snapshot is outside tenant or strategy scope")
    if snapshot["status"] != "ACTIVE":
        raise SoftNavResolutionError("Position snapshot is not active")
    return [
        dict(row)
        for row in connection.execute(
            select(m.position_snapshot_line).where(
                m.position_snapshot_line.c.position_snapshot_id == request.position_snapshot_id
            )
        ).mappings()
    ]


def _listing_conventions(connection: Connection, reference_node_id: UUID) -> tuple[Decimal, Decimal]:
    """Return quote factor and unit multiplier, defaulting only for non-listings."""

    conventions = connection.execute(
        select(m.listing.c.quote_factor, m.listing.c.unit_multiplier).where(
            m.listing.c.listing_node_id == reference_node_id
        )
    ).one_or_none()
    if conventions is None:
        return Decimal("1"), Decimal("1")
    return Decimal(conventions.quote_factor), Decimal(conventions.unit_multiplier)


def calculate_soft_nav(connection: Connection, request: SoftNavRequest) -> UUID:
    """Calculate V1 Soft NAV and persist its immutable selection and output trail.

    V1 values a complete position snapshot only.  It supports positions whose
    selected market-data currency equals the reporting currency.  Cash, accrual
    and FX conversion are deliberately refused until their own frozen-input
    rules are implemented; no fake rate or source-price fallback is permitted.
    The caller owns the database transaction, so an error rolls back the whole
    run and leaves no partial audit artefact.
    """

    if request.market_data_as_of_utc.tzinfo is None:
        raise ValueError("market_data_as_of_utc must be timezone-aware")
    assert_tenant_owns_strategy(connection, request.tenant_id, request.strategy_id)
    lines = _snapshot_lines(connection, request)
    if not lines:
        raise SoftNavResolutionError("Position snapshot contains no lines")

    resolution_request_base = {
        "tenant_id": request.tenant_id,
        "valuation_policy_id": request.valuation_policy_id,
        "valuation_date": request.valuation_date,
        "valuation_cut_id": request.valuation_cut_id,
        "market_data_as_of_utc": request.market_data_as_of_utc,
        "use_purpose": request.use_purpose,
    }
    resolutions = []
    for line in lines:
        resolution = resolve_market_data(
            connection,
            ResolutionRequest(
                subject_reference_node_id=line["reference_node_id"],
                **resolution_request_base,
            ),
        )
        if resolution.status != "SELECTED":
            raise SoftNavResolutionError(
                f"No usable valuation input for {line['reference_node_id']}: {resolution.exception_code}"
            )
        if resolution.currency_id != request.reporting_currency_id:
            raise FxConversionRequired(
                f"No frozen FX conversion is implemented for {resolution.currency_id} to {request.reporting_currency_id}"
            )
        resolutions.append((line, resolution))

    resolution_snapshot_id = persist_resolution_snapshot(
        connection, ResolutionRequest(subject_reference_node_id=lines[0]["reference_node_id"], **resolution_request_base), tuple(result for _, result in resolutions)
    )
    run_id = connection.execute(
        insert(m.nav_calculation_run)
        .values(
            tenant_id=request.tenant_id,
            strategy_id=request.strategy_id,
            position_snapshot_id=request.position_snapshot_id,
            valuation_date=request.valuation_date,
            valuation_cut_id=request.valuation_cut_id,
            valuation_policy_id=request.valuation_policy_id,
            market_data_resolution_snapshot_id=resolution_snapshot_id,
            calculation_version=request.calculation_version,
            status="DRAFT",
        )
        .returning(m.nav_calculation_run.c.nav_calculation_run_id)
    ).scalar_one()

    input_hash = sha256(
        "|".join(
            f"{line['position_snapshot_line_id']}:{result.market_data_observation_id}:{result.selected_value}"
            for line, result in resolutions
        ).encode()
    ).hexdigest()
    nav_input_snapshot_id = connection.execute(
        insert(m.nav_input_snapshot)
        .values(nav_calculation_run_id=run_id, input_hash=input_hash, status="FROZEN")
        .returning(m.nav_input_snapshot.c.nav_input_snapshot_id)
    ).scalar_one()

    gross_assets = Decimal("0")
    for line, result in resolutions:
        quote_factor, unit_multiplier = _listing_conventions(connection, line["reference_node_id"])
        local_value = Decimal(line["quantity"]) * result.selected_value * unit_multiplier / quote_factor
        gross_assets += local_value
        resolution_item_id = connection.scalar(
            select(m.market_data_resolution_snapshot_item.c.market_data_resolution_snapshot_item_id).where(
                m.market_data_resolution_snapshot_item.c.market_data_resolution_snapshot_id == resolution_snapshot_id,
                m.market_data_resolution_snapshot_item.c.subject_reference_node_id == line["reference_node_id"],
            )
        )
        connection.execute(
            insert(m.nav_input_snapshot_item).values(
                nav_input_snapshot_id=nav_input_snapshot_id,
                subject_reference_node_id=line["reference_node_id"],
                market_data_series_id=result.market_data_series_id,
                market_data_observation_id=result.market_data_observation_id,
                market_data_resolution_snapshot_item_id=resolution_item_id,
                policy_rule_id=result.policy_rule_id,
                dataset_id=result.dataset_id,
                selected_value=result.selected_value,
                currency_id=result.currency_id,
                pricing_date_requested=result.pricing_date_requested,
                pricing_date_used=result.pricing_date_used,
                staleness_business_days=result.staleness_business_days,
                staleness_status=result.staleness_status,
                selection_reason=result.selection_reason,
                entitlement_decision=result.entitlement_decision,
            )
        )
        connection.execute(
            insert(m.nav_valuation_line).values(
                nav_calculation_run_id=run_id,
                reference_node_id=line["reference_node_id"],
                quantity=line["quantity"],
                local_value=local_value,
                local_currency_id=result.currency_id,
                fx_rate=Decimal("1"),
                reporting_value=local_value,
                exception_status="NONE",
            )
        )
    connection.execute(
        insert(m.nav_result).values(
            nav_calculation_run_id=run_id,
            reporting_currency_id=request.reporting_currency_id,
            gross_assets=gross_assets,
            liabilities=Decimal("0"),
            net_asset_value=gross_assets,
            status="DRAFT",
        )
    )
    return run_id
