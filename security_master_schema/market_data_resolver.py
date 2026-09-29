"""Database-backed, tenant-entitled market-data resolution.

This module is intentionally a narrow selection boundary.  It does not calculate
NAV or mutate observations: it selects an immutable observation under one frozen
tenant policy and can persist the resulting evidence in a resolution snapshot.
"""

from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Connection, and_, case, exists, insert, or_, select

from . import models as m
from .valuation_resolver import (
    MissingDataAction,
    ObservationCandidate,
    PricingDateRule,
    ResolutionStatus,
    resolve_price,
)


RESOLVER_VERSION = "market-data-resolver-v1"


class ValuationPolicyScopeError(PermissionError):
    """Raised when a policy is inactive, expired, or belongs to another tenant."""


@dataclass(frozen=True)
class ResolutionRequest:
    """All context necessary to reproduce selection of one market-data input."""

    tenant_id: UUID
    subject_reference_node_id: UUID
    valuation_policy_id: UUID
    valuation_date: date
    valuation_cut_id: UUID
    market_data_as_of_utc: datetime
    use_purpose: str


@dataclass(frozen=True)
class ResolvedMarketData:
    """Selection result, including explicit evidence when no value is available."""

    status: str
    subject_reference_node_id: UUID
    policy_rule_id: UUID | None
    market_data_series_id: UUID | None
    market_data_observation_id: UUID | None
    market_data_vintage_id: UUID | None
    dataset_id: UUID | None
    acquisition_licence_id: UUID | None
    source_published_at_utc: datetime | None
    received_at_utc: datetime | None
    currency_id: UUID | None
    selected_value: Decimal | None
    pricing_date_requested: date | None
    pricing_date_used: date | None
    staleness_business_days: int | None
    staleness_status: str
    selection_reason: str
    entitlement_decision: str
    exception_code: str | None


def _subject_context(connection: Connection, subject_id: UUID) -> tuple[str, UUID | None]:
    """Return structural node type and the instrument type behind a subject."""

    subject_type = connection.scalar(
        select(m.reference_node_type.c.type_code)
        .select_from(
            m.financial_reference_node.join(
                m.reference_node_type,
                m.financial_reference_node.c.reference_node_type_id
                == m.reference_node_type.c.reference_node_type_id,
            )
        )
        .where(m.financial_reference_node.c.reference_node_id == subject_id)
    )
    if subject_type is None:
        raise ValueError("Unknown subject_reference_node_id")

    instrument_type_id = connection.scalar(
        select(m.instrument.c.instrument_type_id).where(
            m.instrument.c.instrument_node_id == subject_id
        )
    )
    if instrument_type_id is None:
        instrument_type_id = connection.scalar(
            select(m.instrument.c.instrument_type_id)
            .select_from(
                m.listing.join(
                    m.instrument,
                    m.listing.c.instrument_node_id == m.instrument.c.instrument_node_id,
                )
            )
            .where(m.listing.c.listing_node_id == subject_id)
        )
    return subject_type, instrument_type_id


def _assert_policy_scope(connection: Connection, request: ResolutionRequest) -> None:
    """Ensure the caller cannot select with a cross-tenant or inactive policy."""

    active_policy = connection.scalar(
        select(m.valuation_policy.c.valuation_policy_id).where(
            m.valuation_policy.c.valuation_policy_id == request.valuation_policy_id,
            m.valuation_policy.c.tenant_id == request.tenant_id,
            m.valuation_policy.c.valuation_cut_id == request.valuation_cut_id,
            m.valuation_policy.c.status == "ACTIVE",
            m.valuation_policy.c.valid_from <= request.valuation_date,
            or_(
                m.valuation_policy.c.valid_to.is_(None),
                m.valuation_policy.c.valid_to >= request.valuation_date,
            ),
        )
    )
    if active_policy is None:
        raise ValuationPolicyScopeError("Valuation policy is outside the requesting tenant scope")


def _matching_rules(
    connection: Connection,
    request: ResolutionRequest,
    subject_type: str,
    instrument_type_id: UUID | None,
) -> list[dict]:
    """Return matching policy rules in documented specificity then sequence order."""

    specificity = case(
        (m.valuation_policy_rule.c.market_data_series_id.is_not(None), 3),
        (m.valuation_policy_rule.c.subject_reference_node_id.is_not(None), 2),
        (m.valuation_policy_rule.c.instrument_type_id.is_not(None), 1),
        else_=0,
    )
    statement = (
        select(m.valuation_policy_rule)
        .where(
            m.valuation_policy_rule.c.valuation_policy_id == request.valuation_policy_id,
            m.valuation_policy_rule.c.status == "ACTIVE",
            or_(
                m.valuation_policy_rule.c.subject_type.is_(None),
                m.valuation_policy_rule.c.subject_type == subject_type,
            ),
            or_(
                m.valuation_policy_rule.c.subject_reference_node_id.is_(None),
                m.valuation_policy_rule.c.subject_reference_node_id
                == request.subject_reference_node_id,
            ),
            or_(
                m.valuation_policy_rule.c.instrument_type_id.is_(None),
                m.valuation_policy_rule.c.instrument_type_id == instrument_type_id,
            ),
        )
        .order_by(specificity.desc(), m.valuation_policy_rule.c.rule_sequence.asc())
    )
    return [dict(row) for row in connection.execute(statement).mappings()]


def _entitled_observations(
    connection: Connection,
    request: ResolutionRequest,
    rule: dict,
) -> list[tuple[ObservationCandidate, dict]]:
    """Fetch accepted, uncorrected, entitled candidates before the information cut."""

    vintage = m.market_data_vintage.alias("vintage")
    correction = m.market_data_observation.alias("correction")
    correction_vintage = m.market_data_vintage.alias("correction_vintage")
    has_newer_correction = exists(
        select(1).select_from(
            correction.outerjoin(
                correction_vintage,
                correction.c.market_data_vintage_id
                == correction_vintage.c.market_data_vintage_id,
            )
        ).where(
            correction.c.supersedes_observation_id
            == m.market_data_observation.c.market_data_observation_id,
            correction.c.quality_status == "ACCEPTED",
            correction.c.received_at_utc <= request.market_data_as_of_utc,
            or_(
                correction.c.source_published_at_utc.is_(None),
                correction.c.source_published_at_utc <= request.market_data_as_of_utc,
            ),
            or_(
                correction.c.market_data_vintage_id.is_(None),
                and_(
                    correction_vintage.c.received_at_utc <= request.market_data_as_of_utc,
                    or_(
                        correction_vintage.c.source_published_at_utc.is_(None),
                        correction_vintage.c.source_published_at_utc
                        <= request.market_data_as_of_utc,
                    ),
                ),
            ),
        )
    )
    conditions = [
        m.market_data_series.c.reference_node_id == request.subject_reference_node_id,
        m.market_data_series.c.status == "ACTIVE",
        m.market_data_series.c.series_type == rule["series_type"],
        m.market_data_observation.c.quality_status == "ACCEPTED",
        m.market_data_observation.c.market_date.is_not(None),
        m.market_data_observation.c.received_at_utc <= request.market_data_as_of_utc,
        or_(
            m.market_data_observation.c.source_published_at_utc.is_(None),
            m.market_data_observation.c.source_published_at_utc <= request.market_data_as_of_utc,
        ),
        or_(
            m.market_data_observation.c.market_data_vintage_id.is_(None),
            and_(
                vintage.c.received_at_utc <= request.market_data_as_of_utc,
                or_(
                    vintage.c.source_published_at_utc.is_(None),
                    vintage.c.source_published_at_utc <= request.market_data_as_of_utc,
                ),
            ),
        ),
        ~has_newer_correction,
        m.tenant_dataset_entitlement.c.tenant_id == request.tenant_id,
        m.tenant_dataset_entitlement.c.use_purpose == request.use_purpose,
        m.tenant_dataset_entitlement.c.status == "ACTIVE",
        m.tenant_dataset_entitlement.c.valid_from <= request.valuation_date,
        or_(
            m.tenant_dataset_entitlement.c.valid_to.is_(None),
            m.tenant_dataset_entitlement.c.valid_to >= request.valuation_date,
        ),
    ]
    if rule["market_data_series_id"] is not None:
        conditions.append(m.market_data_series.c.market_data_series_id == rule["market_data_series_id"])
    if rule["dataset_id"] is not None:
        conditions.append(m.market_data_observation.c.dataset_id == rule["dataset_id"])

    statement = (
        select(
            m.market_data_observation.c.market_data_observation_id,
            m.market_data_observation.c.market_date,
            m.market_data_observation.c.received_at_utc,
            m.market_data_observation.c.value,
            m.market_data_observation.c.dataset_id,
            m.market_data_observation.c.market_data_vintage_id,
            m.market_data_observation.c.acquisition_licence_id,
            m.market_data_series.c.market_data_series_id,
            m.market_data_series.c.currency_id,
            case(
                (m.market_data_observation.c.market_data_vintage_id.is_not(None), vintage.c.source_published_at_utc),
                else_=m.market_data_observation.c.source_published_at_utc,
            ).label("source_published_at_utc"),
            case(
                (m.market_data_observation.c.market_data_vintage_id.is_not(None), vintage.c.received_at_utc),
                else_=m.market_data_observation.c.received_at_utc,
            ).label("evidence_received_at_utc"),
        )
        .select_from(
            m.market_data_observation.join(
                m.market_data_series,
                m.market_data_observation.c.market_data_series_id
                == m.market_data_series.c.market_data_series_id,
            ).join(
                m.tenant_dataset_entitlement,
                m.tenant_dataset_entitlement.c.dataset_id
                == m.market_data_observation.c.dataset_id,
            ).outerjoin(
                vintage,
                m.market_data_observation.c.market_data_vintage_id
                == vintage.c.market_data_vintage_id,
            )
        )
        .where(and_(*conditions))
    )
    rows = [dict(row) for row in connection.execute(statement).mappings()]
    return [
        (
            ObservationCandidate(
                observation_id=row["market_data_observation_id"],
                market_date=row["market_date"],
                received_at_utc=row["received_at_utc"],
                value=float(row["value"]),
            ),
            row,
        )
        for row in rows
    ]


def _matching_observation_exists(connection: Connection, request: ResolutionRequest, rule: dict) -> bool:
    """Return whether matching data exists before tenant entitlement is applied."""

    vintage = m.market_data_vintage.alias("vintage")
    correction = m.market_data_observation.alias("correction")
    correction_vintage = m.market_data_vintage.alias("correction_vintage")
    has_newer_correction = exists(
        select(1).select_from(
            correction.outerjoin(
                correction_vintage,
                correction.c.market_data_vintage_id
                == correction_vintage.c.market_data_vintage_id,
            )
        ).where(
            correction.c.supersedes_observation_id
            == m.market_data_observation.c.market_data_observation_id,
            correction.c.quality_status == "ACCEPTED",
            correction.c.received_at_utc <= request.market_data_as_of_utc,
            or_(
                correction.c.source_published_at_utc.is_(None),
                correction.c.source_published_at_utc <= request.market_data_as_of_utc,
            ),
            or_(
                correction.c.market_data_vintage_id.is_(None),
                and_(
                    correction_vintage.c.received_at_utc <= request.market_data_as_of_utc,
                    or_(
                        correction_vintage.c.source_published_at_utc.is_(None),
                        correction_vintage.c.source_published_at_utc
                        <= request.market_data_as_of_utc,
                    ),
                ),
            ),
        )
    )
    conditions = [
        m.market_data_series.c.reference_node_id == request.subject_reference_node_id,
        m.market_data_series.c.status == "ACTIVE",
        m.market_data_series.c.series_type == rule["series_type"],
        m.market_data_observation.c.quality_status == "ACCEPTED",
        m.market_data_observation.c.market_date.is_not(None),
        m.market_data_observation.c.received_at_utc <= request.market_data_as_of_utc,
        or_(
            m.market_data_observation.c.source_published_at_utc.is_(None),
            m.market_data_observation.c.source_published_at_utc <= request.market_data_as_of_utc,
        ),
        or_(
            m.market_data_observation.c.market_data_vintage_id.is_(None),
            and_(
                vintage.c.received_at_utc <= request.market_data_as_of_utc,
                or_(
                    vintage.c.source_published_at_utc.is_(None),
                    vintage.c.source_published_at_utc <= request.market_data_as_of_utc,
                ),
            ),
        ),
        ~has_newer_correction,
    ]
    if rule["market_data_series_id"] is not None:
        conditions.append(m.market_data_series.c.market_data_series_id == rule["market_data_series_id"])
    if rule["dataset_id"] is not None:
        conditions.append(m.market_data_observation.c.dataset_id == rule["dataset_id"])
    return connection.scalar(
        select(m.market_data_observation.c.market_data_observation_id)
        .select_from(
            m.market_data_observation.join(
                m.market_data_series,
                m.market_data_observation.c.market_data_series_id
                == m.market_data_series.c.market_data_series_id,
            ).outerjoin(
                vintage,
                m.market_data_observation.c.market_data_vintage_id
                == vintage.c.market_data_vintage_id,
            )
        )
        .where(and_(*conditions))
        .limit(1)
    ) is not None


def resolve_market_data(connection: Connection, request: ResolutionRequest) -> ResolvedMarketData:
    """Resolve one subject without assuming availability or silently falling back.

    A rule is chosen by exact series, exact node, instrument type, then default
    rule precedence.  Its `missing_data_action` is authoritative: a missing exact
    rule must not silently select a less specific price.
    """

    if (
        request.market_data_as_of_utc.tzinfo is None
        or request.market_data_as_of_utc.utcoffset() is None
        or request.market_data_as_of_utc.utcoffset() != timedelta(0)
    ):
        raise ValueError("market_data_as_of_utc must be timezone-aware UTC")
    _assert_policy_scope(connection, request)
    subject_type, instrument_type_id = _subject_context(connection, request.subject_reference_node_id)
    rules = _matching_rules(connection, request, subject_type, instrument_type_id)
    if not rules:
        return ResolvedMarketData(
            status="MISSING", subject_reference_node_id=request.subject_reference_node_id,
            policy_rule_id=None, market_data_series_id=None, market_data_observation_id=None,
            market_data_vintage_id=None, dataset_id=None, acquisition_licence_id=None,
            source_published_at_utc=None, received_at_utc=None, currency_id=None, selected_value=None,
            pricing_date_requested=None, pricing_date_used=None, staleness_business_days=None,
            staleness_status="MISSING", selection_reason="MISSING_DATA",
            entitlement_decision="NOT_AVAILABLE", exception_code="NO_MATCHING_POLICY_RULE",
        )

    rule = rules[0]
    candidates_and_rows = _entitled_observations(connection, request, rule)
    matching_observation_exists = _matching_observation_exists(connection, request, rule)
    price_result = resolve_price(
        valuation_date=request.valuation_date,
        information_cutoff_utc=request.market_data_as_of_utc,
        pricing_date_rule=PricingDateRule(rule["pricing_date_rule"]),
        lag_business_days=rule["lag_business_days"],
        max_staleness_business_days=rule["max_staleness_business_days"],
        missing_data_action=MissingDataAction(rule["missing_data_action"]),
        candidates=tuple(candidate for candidate, _ in candidates_and_rows),
    )
    row_by_id = {candidate.observation_id: row for candidate, row in candidates_and_rows}
    selected_row = row_by_id.get(price_result.selected_observation_id)
    selected = price_result.status is ResolutionStatus.SELECTED
    denied = matching_observation_exists and not candidates_and_rows
    return ResolvedMarketData(
        status="DENIED" if denied else str(price_result.status),
        subject_reference_node_id=request.subject_reference_node_id,
        policy_rule_id=rule["valuation_policy_rule_id"],
        market_data_series_id=selected_row["market_data_series_id"] if selected_row else None,
        market_data_observation_id=price_result.selected_observation_id,
        market_data_vintage_id=selected_row["market_data_vintage_id"] if selected_row else None,
        dataset_id=selected_row["dataset_id"] if selected_row else None,
        acquisition_licence_id=selected_row["acquisition_licence_id"] if selected_row else None,
        source_published_at_utc=selected_row["source_published_at_utc"] if selected_row else None,
        received_at_utc=selected_row["evidence_received_at_utc"] if selected_row else None,
        currency_id=selected_row["currency_id"] if selected_row else None,
        selected_value=Decimal(str(price_result.selected_value)) if price_result.selected_value is not None else None,
        pricing_date_requested=price_result.pricing_date_requested,
        pricing_date_used=price_result.pricing_date_used,
        staleness_business_days=price_result.staleness_business_days,
        staleness_status=("CURRENT" if selected and price_result.staleness_business_days == 0 else "WITHIN_TOLERANCE" if selected else str(price_result.status)),
        selection_reason=(
            "ENTITLED_PROVIDER" if selected else "ENTITLEMENT_DENIED" if denied else "MISSING_DATA"
        ),
        entitlement_decision="ALLOWED" if candidates_and_rows else "DENIED" if denied else "NOT_AVAILABLE",
        exception_code=(
            None if selected else "NO_VALID_ENTITLEMENT" if denied else price_result.exception_code
        ),
    )


def resolve_market_data_batch(
    connection: Connection,
    request: ResolutionRequest,
    subject_reference_node_ids: tuple[UUID, ...],
) -> tuple[ResolvedMarketData, ...]:
    """Resolve a bounded, ordered set of distinct subjects under one request context."""

    if not subject_reference_node_ids or len(subject_reference_node_ids) > 50:
        raise ValueError("subject_reference_node_ids must contain between 1 and 50 items")
    if len(set(subject_reference_node_ids)) != len(subject_reference_node_ids):
        raise ValueError("subject_reference_node_ids must be distinct")
    return tuple(
        resolve_market_data(connection, replace(request, subject_reference_node_id=subject_id))
        for subject_id in subject_reference_node_ids
    )


def persist_resolution_snapshot(
    connection: Connection,
    request: ResolutionRequest,
    items: tuple[ResolvedMarketData, ...],
) -> UUID:
    """Persist a header and immutable result items in the caller's transaction."""

    snapshot_status = "COMPLETED" if all(item.status == "SELECTED" for item in items) else "PARTIAL"
    snapshot_id = connection.execute(
        insert(m.market_data_resolution_snapshot)
        .values(
            tenant_id=request.tenant_id,
            valuation_policy_id=request.valuation_policy_id,
            valuation_date=request.valuation_date,
            valuation_cut_id=request.valuation_cut_id,
            market_data_as_of_utc=request.market_data_as_of_utc,
            use_purpose=request.use_purpose,
            resolver_version=RESOLVER_VERSION,
            status=snapshot_status,
        )
        .returning(m.market_data_resolution_snapshot.c.market_data_resolution_snapshot_id)
    ).scalar_one()
    for request_sequence, item in enumerate(items):
        connection.execute(
            insert(m.market_data_resolution_snapshot_item).values(
                market_data_resolution_snapshot_id=snapshot_id,
                subject_reference_node_id=item.subject_reference_node_id,
                status=item.status,
                request_sequence=request_sequence,
                market_data_series_id=item.market_data_series_id,
                market_data_observation_id=item.market_data_observation_id,
                market_data_vintage_id=item.market_data_vintage_id,
                dataset_id=item.dataset_id,
                acquisition_licence_id=item.acquisition_licence_id,
                source_published_at_utc=item.source_published_at_utc,
                received_at_utc=item.received_at_utc,
                selected_value=item.selected_value,
                currency_id=item.currency_id,
                pricing_date_requested=item.pricing_date_requested,
                pricing_date_used=item.pricing_date_used,
                staleness_business_days=item.staleness_business_days,
                staleness_status=item.staleness_status,
                selection_reason=item.selection_reason,
                entitlement_decision=item.entitlement_decision,
                policy_rule_id=item.policy_rule_id,
                exception_code=item.exception_code,
            )
        )
    return snapshot_id
