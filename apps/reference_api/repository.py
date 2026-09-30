"""PostgreSQL read/write queries behind the reference-data API."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
from uuid import UUID, uuid4

from sqlalchemy import Connection, and_, cast, exists, func, insert, or_, select, String, true

from security_master_schema import models as m
from security_master_schema.market_data_resolver import (
    ResolutionRequest,
    persist_resolution_snapshot,
    resolve_market_data_batch,
)

from .contracts import (
    ApiMeta,
    ActiveValuationPolicyView,
    BondProposalRequest,
    BondProposalView,
    CryptoAssetProposalRequest,
    CryptoAssetProposalView,
    CurrencyResponse,
    CurrencyGroupView,
    CurrencyView,
    DayCountConventionResponse,
    DayCountConventionView,
    EquityListingCreateProposalRequest,
    EquityProposalRequest,
    EquityProposalView,
    EtpProposalRequest,
    EtpProposalView,
    FxForwardProposalRequest,
    FxForwardProposalView,
    ExternalMappingView,
    InstrumentIdentifierView,
    InstrumentListingView,
    InstrumentSearchResponse,
    InstrumentView,
    ReferenceNodeOptionView,
    ReferenceNodeSearchResponse,
    IndexFamilyOptionResponse,
    IndexFamilyOptionView,
    IndexFamilyProposalRequest,
    IndexFamilyProposalView,
    IndexKindResponse,
    IndexKindView,
    IndexProposalRequest,
    IndexProposalView,
    MappingProposalRequest,
    MappingProposalView,
    MarketDataPointView,
    MarketDataResolutionSnapshotCreate,
    MarketDataResolutionSnapshotItemView,
    MarketDataResolutionSnapshotView,
    MarketDataObservationView,
    MarketDataSeriesResponse,
    MarketDataSeriesView,
    MarketVenueResponse,
    MarketVenueView,
    PortfolioPnlLine,
    PortfolioPnlResponse,
    PortfolioPnlView,
    OrganisationOptionResponse,
    OrganisationOptionView,
    ReturnProfileResponse,
    ReturnProfileView,
    ReferenceDataProposalView,
    StructuredProductProposalView,
    TradeDetailResponse,
    TradeDetailView,
    TradeBookingRequest,
    TradeExternalReferenceView,
    TradeFeeView,
    TradeLifecycleEventView,
    TradePartyView,
    TradeResponse,
    TradeView,
    StrategyCreateRequest,
    StrategyView,
    StrategyListResponse,
    StrategyStatusRequest,
    WorkQueueItemView,
    WorkQueueView,
)


def create_strategy(connection: Connection, tenant_id: UUID, actor_id: UUID, request: StrategyCreateRequest) -> StrategyView:
    if request.strategy_type == "OTHER" and not request.operating_model_label:
        raise ValueError("operatingModelLabel is required when strategyType is OTHER")
    currency_id = None
    currency_code = None
    if request.base_currency_code:
        currency_code = request.base_currency_code.upper()
        currency_id = connection.scalar(select(m.currency.c.currency_id).where(m.currency.c.currency_code == currency_code).where(m.currency.c.status == "ACTIVE"))
        if currency_id is None:
            raise ValueError("baseCurrencyCode is not an active currency")
    strategy_id = uuid4()
    connection.execute(insert(m.strategy).values(strategy_id=strategy_id, tenant_id=tenant_id, strategy_code=request.strategy_code.strip().upper(), display_name=request.display_name.strip(), strategy_type=request.strategy_type, operating_model_label=request.operating_model_label, base_currency_id=currency_id, status="ACTIVE", created_by_user_account_id=actor_id))
    return StrategyView(strategyId=strategy_id, tenantId=tenant_id, strategyCode=request.strategy_code.strip().upper(), displayName=request.display_name.strip(), strategyType=request.strategy_type, baseCurrencyCode=currency_code, status="ACTIVE")


def list_strategies(connection: Connection, tenant_id: UUID) -> StrategyListResponse:
    rows = connection.execute(select(m.strategy.c.strategy_id, m.strategy.c.tenant_id, m.strategy.c.strategy_code, m.strategy.c.display_name, m.strategy.c.strategy_type, m.strategy.c.status, m.currency.c.currency_code).outerjoin(m.currency, m.currency.c.currency_id == m.strategy.c.base_currency_id).where(m.strategy.c.tenant_id == tenant_id).order_by(m.strategy.c.strategy_code)).mappings().all()
    return StrategyListResponse(data=[StrategyView(strategyId=row["strategy_id"], tenantId=row["tenant_id"], strategyCode=row["strategy_code"], displayName=row["display_name"], strategyType=row["strategy_type"], baseCurrencyCode=row["currency_code"], status=row["status"]) for row in rows])


def get_strategy(connection: Connection, tenant_id: UUID, strategy_id: UUID) -> StrategyView | None:
    rows = list_strategies(connection, tenant_id).data
    return next((row for row in rows if row.strategy_id == strategy_id), None)


def archive_strategy(connection: Connection, tenant_id: UUID, strategy_id: UUID, request: StrategyStatusRequest) -> StrategyView | None:
    if request.status != "ARCHIVED":
        raise ValueError("Only ARCHIVED is supported")
    strategy = get_strategy(connection, tenant_id, strategy_id)
    if strategy is None:
        return None
    connection.execute(m.strategy.update().where(m.strategy.c.strategy_id == strategy_id).where(m.strategy.c.tenant_id == tenant_id).values(status="ARCHIVED"))
    return strategy.model_copy(update={"status": "ARCHIVED"})
from .structured_product_contracts import (
    AutocallDraftRequest,
    AutocallScheduleRowRequest,
    aggregate_pay_once_for_group,
    logical_operator_for_scope,
    payout_multiplicity_for_group,
    underlying_aggregation_for_scope,
    validate_autocall_draft,
)


class RepositoryNotFound(LookupError):
    """Raised when a requested visible reference object does not exist."""


class InvalidWorkflowState(ValueError):
    """Raised when an append-only workflow transition is not permitted."""


class InvalidCatalogueValue(InvalidWorkflowState):
    """Raised when a request names a missing or inactive governed catalogue value."""


class IdempotencyKeyConflict(InvalidWorkflowState):
    """Raised when one tenant reuses an idempotency key for another payload."""


_CURRENCY_GROUP_KINDS: dict[str, tuple[str, ...]] = {
    "REGULAR": ("FIAT",),
    "CRYPTO": ("CRYPTOASSET", "STABLECOIN"),
}
_CURRENCY_GROUP_LABELS = {
    "REGULAR": "Regular currencies",
    "CRYPTO": "Cryptoassets",
}


def parse_currency_groups(value: str | None) -> tuple[str, ...]:
    """Normalise the caller's currency groups and reject unknown values."""

    raw_groups = [part.strip().upper() for part in (value or "REGULAR").split(",") if part.strip()]
    if not raw_groups:
        raise InvalidCatalogueValue("At least one currency group must be requested")
    if "ALL" in raw_groups:
        raw_groups = list(_CURRENCY_GROUP_KINDS)
    unknown = sorted(set(raw_groups) - set(_CURRENCY_GROUP_KINDS))
    if unknown:
        raise InvalidCatalogueValue(f"Unknown currency group(s): {', '.join(unknown)}")
    # Always return the stable display order, regardless of query-string order.
    return tuple(group for group in _CURRENCY_GROUP_KINDS if group in raw_groups)


def _iso(value: date | datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _decimal(value: Decimal | int | float | None) -> str:
    return str(value if value is not None else 0)


def _visible_node_clause(tenant_id: UUID):
    scope = m.reference_node_scope
    return or_(
        scope.c.reference_node_id.is_(None),
        scope.c.scope_type == "SHARED_CANONICAL",
        and_(scope.c.scope_type == "TENANT_PRIVATE", scope.c.owner_tenant_id == tenant_id),
    )


def _base_instrument_select(tenant_id: UUID):
    as_of = date.today()
    rn = m.financial_reference_node
    inst = m.instrument
    version = m.instrument_definition_version
    typ = m.instrument_type
    issuer = m.organisation.alias("issuer")
    currency = m.currency.alias("base_currency")
    scope = m.reference_node_scope
    from_clause = (
        rn.join(inst, inst.c.instrument_node_id == rn.c.reference_node_id)
        .join(
            version,
            and_(
                version.c.instrument_node_id == inst.c.instrument_node_id,
                version.c.status == "APPROVED",
                version.c.is_current.is_(True),
                version.c.effective_from <= as_of,
                or_(version.c.effective_to.is_(None), version.c.effective_to >= as_of),
            ),
        )
        .join(typ, typ.c.instrument_type_id == version.c.instrument_type_id)
        .outerjoin(issuer, issuer.c.organisation_id == version.c.issuer_organisation_id)
        .outerjoin(currency, currency.c.currency_id == version.c.base_currency_id)
        .outerjoin(scope, scope.c.reference_node_id == rn.c.reference_node_id)
    )
    columns = [
        rn.c.reference_node_id.label("instrument_id"),
        rn.c.canonical_name,
        rn.c.status.label("node_status"),
        typ.c.type_code.label("instrument_type"),
        version.c.asset_class,
        issuer.c.display_name.label("issuer"),
        currency.c.currency_code.label("base_currency"),
        version.c.sequence_no.label("definition_version"),
        version.c.effective_from,
    ]
    return rn, inst, typ, from_clause, columns, select(*columns).select_from(from_clause).where(_visible_node_clause(tenant_id))


def _search_predicate(tenant_id: UUID, query: str, rn, inst, typ):
    normalized = query.strip().lower()
    if not normalized:
        return None
    issuer = m.organisation.alias("search_issuer")
    currency = m.currency.alias("search_currency")
    identifier = m.financial_reference_identifier
    scheme = m.identifier_scheme
    listing = m.listing
    listing_version = m.listing_definition_version
    venue = m.market_venue
    mapping = m.external_object_mapping
    namespace = m.external_id_namespace
    predicates = [
        func.lower(rn.c.canonical_name).contains(normalized),
        func.lower(rn.c.internal_code).contains(normalized),
        func.lower(typ.c.type_code).contains(normalized),
        func.lower(m.instrument_definition_version.c.asset_class).contains(normalized),
        exists(
            select(1)
            .select_from(issuer)
            .where(issuer.c.organisation_id == inst.c.issuer_organisation_id)
            .where(func.lower(issuer.c.display_name).contains(normalized))
        ),
        exists(
            select(1)
            .select_from(identifier.join(scheme, identifier.c.identifier_scheme_id == scheme.c.identifier_scheme_id))
            .where(identifier.c.reference_node_id == rn.c.reference_node_id)
            .where(func.lower(identifier.c.identifier_value).contains(normalized))
        ),
        exists(
            select(1)
            .select_from(
                listing.join(
                    listing_version,
                    and_(
                        listing_version.c.listing_node_id == listing.c.listing_node_id,
                        listing_version.c.status == "APPROVED",
                        listing_version.c.is_current.is_(True),
                        listing_version.c.effective_from <= date.today(),
                        or_(listing_version.c.effective_to.is_(None), listing_version.c.effective_to >= date.today()),
                    ),
                ).join(venue, listing_version.c.market_venue_id == venue.c.market_venue_id)
            )
            .where(listing.c.instrument_node_id == rn.c.reference_node_id)
            .where(
                or_(
                    func.lower(listing_version.c.trading_symbol).contains(normalized),
                    func.lower(venue.c.display_name).contains(normalized),
                )
            )
        ),
        exists(
            select(1)
            .select_from(mapping.join(namespace, mapping.c.external_id_namespace_id == namespace.c.external_id_namespace_id))
            .where(
                or_(
                    mapping.c.target_object_id == rn.c.reference_node_id,
                    exists(
                        select(1)
                        .select_from(listing)
                        .where(listing.c.listing_node_id == mapping.c.target_object_id)
                        .where(listing.c.instrument_node_id == rn.c.reference_node_id)
                    ),
                )
            )
            .where(
                or_(
                    func.lower(mapping.c.external_id_value).contains(normalized),
                    func.lower(namespace.c.namespace_code).contains(normalized),
                )
            )
            .where(or_(mapping.c.tenant_id.is_(None), mapping.c.tenant_id == tenant_id))
            .where(mapping.c.valid_from <= date.today())
            .where(or_(mapping.c.valid_to.is_(None), mapping.c.valid_to >= date.today()))
            .where(namespace.c.status == "ACTIVE")
            .where(namespace.c.valid_from <= date.today())
            .where(or_(namespace.c.valid_to.is_(None), namespace.c.valid_to >= date.today()))
        ),
        func.lower(cast(rn.c.reference_node_id, String)).contains(normalized),
    ]
    return or_(*predicates)


def _load_identifiers(connection: Connection, node_id: UUID) -> list[InstrumentIdentifierView]:
    as_of = date.today()
    rows = connection.execute(
        select(m.identifier_scheme.c.scheme_code, m.identifier_scheme.c.scope, m.financial_reference_identifier.c.identifier_value)
        .select_from(
            m.financial_reference_identifier.join(
                m.identifier_scheme,
                m.financial_reference_identifier.c.identifier_scheme_id == m.identifier_scheme.c.identifier_scheme_id,
            )
        )
        .where(m.financial_reference_identifier.c.reference_node_id == node_id)
        .where(or_(m.financial_reference_identifier.c.valid_from.is_(None), m.financial_reference_identifier.c.valid_from <= as_of))
        .where(or_(m.financial_reference_identifier.c.valid_to.is_(None), m.financial_reference_identifier.c.valid_to >= as_of))
        .order_by(m.financial_reference_identifier.c.is_primary.desc(), m.identifier_scheme.c.scheme_code)
    ).mappings()
    return [InstrumentIdentifierView(scheme=row.scheme_code, value=row.identifier_value, scope=row.scope) for row in rows]


def _load_mappings(connection: Connection, tenant_id: UUID, instrument_id: UUID, listing_ids: list[UUID]) -> list[ExternalMappingView]:
    mapping = m.external_object_mapping
    namespace = m.external_id_namespace
    as_of = date.today()
    targets = [mapping.c.target_object_id == instrument_id]
    if listing_ids:
        targets.append(mapping.c.target_object_id.in_(listing_ids))
    rows = connection.execute(
        select(namespace.c.namespace_code, mapping.c.external_id_value, mapping.c.status, mapping.c.mapping_role)
        .select_from(mapping.join(namespace, mapping.c.external_id_namespace_id == namespace.c.external_id_namespace_id))
        .where(or_(*targets))
        .where(mapping.c.status.not_in(["RETIRED", "SUPERSEDED"]))
        .where(or_(mapping.c.tenant_id.is_(None), mapping.c.tenant_id == tenant_id))
        .where(namespace.c.status == "ACTIVE")
        .where(mapping.c.valid_from <= as_of)
        .where(or_(mapping.c.valid_to.is_(None), mapping.c.valid_to >= as_of))
        .where(namespace.c.valid_from <= as_of)
        .where(or_(namespace.c.valid_to.is_(None), namespace.c.valid_to >= as_of))
        .order_by(namespace.c.namespace_code, mapping.c.external_id_value)
    ).mappings()
    return [
        ExternalMappingView(
            namespace=row.namespace_code,
            externalId=row.external_id_value,
            status=row.status,
            mappingRole=row.mapping_role,
        )
        for row in rows
    ]


def _load_market_data(connection: Connection, tenant_id: UUID, node_ids: list[UUID]) -> list[MarketDataPointView]:
    if not node_ids:
        return []
    series = m.market_data_series
    series_currency = m.currency.alias("series_currency")
    series_rows = connection.execute(
        select(
            series.c.market_data_series_id,
            series.c.reference_node_id,
            series.c.series_type,
            series.c.source_system_id,
            series_currency.c.currency_code.label("series_currency"),
        )
        .select_from(series.outerjoin(series_currency, series.c.currency_id == series_currency.c.currency_id))
        .where(series.c.reference_node_id.in_(node_ids))
        .where(series.c.status == "ACTIVE")
        .order_by(series.c.series_type)
    ).mappings().all()
    points: list[MarketDataPointView] = []
    observation = m.market_data_observation
    dataset = m.dataset
    product = m.provider_product
    provider = m.data_provider
    vintage = m.market_data_vintage
    cut = m.valuation_cut
    entitlement = m.tenant_dataset_entitlement
    as_of = date.today()
    for series_row in series_rows:
        row = connection.execute(
            select(
                observation.c.value,
                observation.c.market_date,
                observation.c.valuation_cut_id,
                observation.c.received_at_utc,
                observation.c.value_basis,
                observation.c.source_sequence,
                observation.c.source_timestamp_utc,
                dataset.c.dataset_code,
                dataset.c.display_name.label("dataset_name"),
                provider.c.display_name.label("provider_name"),
                vintage.c.source_vintage_key,
                cut.c.cut_code,
            )
            .select_from(
                observation.join(dataset, observation.c.dataset_id == dataset.c.dataset_id)
                .outerjoin(product, dataset.c.provider_product_id == product.c.provider_product_id)
                .outerjoin(provider, product.c.data_provider_id == provider.c.data_provider_id)
                .outerjoin(vintage, observation.c.market_data_vintage_id == vintage.c.market_data_vintage_id)
                .outerjoin(cut, observation.c.valuation_cut_id == cut.c.valuation_cut_id)
            )
            .where(observation.c.market_data_series_id == series_row.market_data_series_id)
            .where(observation.c.quality_status == "ACCEPTED")
            .where(
                exists(
                    select(1)
                    .select_from(entitlement)
                    .where(entitlement.c.tenant_id == tenant_id)
                    .where(entitlement.c.dataset_id == observation.c.dataset_id)
                    .where(entitlement.c.status == "ACTIVE")
                    .where(entitlement.c.valid_from <= as_of)
                    .where(or_(entitlement.c.valid_to.is_(None), entitlement.c.valid_to >= as_of))
                )
            )
            .order_by(observation.c.market_date.desc().nullslast(), observation.c.observed_at_utc.desc(), observation.c.received_at_utc.desc())
            .limit(3)
        ).mappings().all()
        for observation_row in row:
            points.append(
                MarketDataPointView(
                    series=series_row.series_type,
                    value=_decimal(observation_row.value),
                    currency=series_row.series_currency,
                    marketDate=_iso(observation_row.market_date),
                    valuationCut=observation_row.cut_code,
                    provider=observation_row.provider_name or series_row.source_system_id,
                    dataset=observation_row.dataset_name or observation_row.dataset_code,
                    vintage=observation_row.source_vintage_key or observation_row.source_sequence or "unversioned",
                    receivedAt=_iso(observation_row.received_at_utc) or "",
                    valueBasis=observation_row.value_basis,
                    referenceNodeId=series_row.reference_node_id,
                )
            )
    return points


def _load_taxonomy(connection: Connection, instrument_id: UUID) -> list[str]:
    rows = connection.execute(
        select(m.taxonomy_value.c.value_code)
        .select_from(
            m.instrument_taxonomy_assignment.join(
                m.taxonomy_value,
                m.instrument_taxonomy_assignment.c.taxonomy_value_id == m.taxonomy_value.c.taxonomy_value_id,
            )
        )
        .where(m.instrument_taxonomy_assignment.c.instrument_node_id == instrument_id)
        .where(m.taxonomy_value.c.status == "ACTIVE")
        .order_by(m.taxonomy_value.c.value_code)
    ).scalars()
    return list(rows)


def list_market_venues(connection: Connection, tenant_id: UUID, limit: int, offset: int, api_version: str, correlation_id: str) -> MarketVenueResponse:
    """Return active canonical venues for listing onboarding.

    Venue options are reference data, not user-entered labels.  The primary
    venue identifier is normally an ISO 10383 MIC; crypto venues can use their
    governed exchange-code namespace instead.
    """

    venue = m.market_venue
    identifier = m.market_venue_identifier
    venue_code = (
        select(identifier.c.identifier_value, identifier.c.identifier_scheme)
        .where(identifier.c.market_venue_id == venue.c.market_venue_id)
        .order_by(identifier.c.is_primary.desc(), identifier.c.identifier_scheme, identifier.c.identifier_value)
        .limit(1)
        .lateral()
    )
    rows = connection.execute(
        select(
            venue.c.market_venue_id,
            venue_code.c.identifier_value.label("venue_code"),
            venue_code.c.identifier_scheme.label("venue_identifier_scheme"),
            venue.c.display_name,
            venue.c.venue_type,
            venue.c.country_code,
            venue.c.timezone_name,
        )
        .select_from(venue.outerjoin(venue_code, true()))
        .where(venue.c.status == "ACTIVE")
        .order_by(venue_code.c.identifier_value, venue.c.display_name)
        .limit(limit)
        .offset(offset)
    ).mappings().all()
    total = connection.execute(
        select(func.count()).select_from(venue).where(venue.c.status == "ACTIVE")
    ).scalar_one()
    return MarketVenueResponse(
        data=[
            MarketVenueView(
                marketVenueId=row.market_venue_id,
                # Keep incomplete legacy venue rows visible without making
                # every unmapped row collide in the onboarding dropdown.  The
                # UUID fragment is a display fallback only; it is never used
                # as the venue identity (the UUID remains the selected value).
                venueCode=row.venue_code
                or f"UNMAPPED-{str(row.market_venue_id).replace('-', '')[-8:].upper()}",
                venueIdentifierScheme=row.venue_identifier_scheme or "UNMAPPED",
                displayName=row.display_name,
                venueType=row.venue_type,
                countryCode=row.country_code,
                timezoneName=row.timezone_name,
            )
            for row in rows
        ],
        meta=ApiMeta(
            tenantContext=str(tenant_id),
            source="live-reference-api",
            apiVersion=api_version,
            correlationId=correlation_id,
            limit=limit,
            offset=offset,
            total=int(total),
        ),
    )


def list_day_count_conventions(connection: Connection, tenant_id: UUID, api_version: str, correlation_id: str) -> DayCountConventionResponse:
    """Return active governed day-count conventions for terms dropdowns."""

    rows = connection.execute(
        select(
            m.day_count_convention.c.day_count_convention_id,
            m.day_count_convention.c.code,
            m.day_count_convention.c.display_name,
            m.day_count_convention.c.description,
            m.day_count_convention.c.standard_source,
        )
        .where(m.day_count_convention.c.status == "ACTIVE")
        .order_by(m.day_count_convention.c.sort_order, m.day_count_convention.c.code)
    ).mappings().all()
    return DayCountConventionResponse(
        data=[
            DayCountConventionView(
                dayCountConventionId=row.day_count_convention_id,
                code=row.code,
                displayName=row.display_name,
                description=row.description,
                standardSource=row.standard_source,
            )
            for row in rows
        ],
        meta=ApiMeta(
            tenantContext=str(tenant_id),
            source="live-reference-api",
            apiVersion=api_version,
            correlationId=correlation_id,
            total=len(rows),
        ),
    )


def list_currencies(
    connection: Connection,
    tenant_id: UUID,
    api_version: str,
    correlation_id: str,
    groups: str | None = None,
) -> CurrencyResponse:
    """Return active currencies in caller-selected, stable display groups."""

    selected_groups = parse_currency_groups(groups)
    selected_kinds = tuple(kind for group in selected_groups for kind in _CURRENCY_GROUP_KINDS[group])

    rows = connection.execute(
        select(
            m.currency.c.currency_id,
            m.currency.c.currency_code,
            m.currency.c.display_name,
            m.currency.c.currency_kind,
        )
        .where(m.currency.c.status == "ACTIVE")
        .where(m.currency.c.currency_kind.in_(selected_kinds))
        .order_by(m.currency.c.currency_code)
    ).mappings().all()

    grouped_items: dict[str, list[CurrencyView]] = {group: [] for group in selected_groups}
    for row in rows:
        item = CurrencyView(
            currencyId=row.currency_id,
            currencyCode=row.currency_code,
            displayName=row.display_name,
            currencyKind=row.currency_kind,
        )
        for group in selected_groups:
            if row.currency_kind in _CURRENCY_GROUP_KINDS[group]:
                grouped_items[group].append(item)
                break

    return CurrencyResponse(
        data=[
            CurrencyGroupView(groupCode=group, label=_CURRENCY_GROUP_LABELS[group], items=grouped_items[group])
            for group in selected_groups
        ],
        meta=ApiMeta(
            tenantContext=str(tenant_id),
            source="live-reference-api",
            apiVersion=api_version,
            correlationId=correlation_id,
            total=len(rows),
        ),
    )


def list_return_profiles(connection: Connection, tenant_id: UUID, api_version: str, correlation_id: str) -> ReturnProfileResponse:
    """Return active governed return semantics for index and swap workflows."""

    rows = connection.execute(
        select(
            m.return_profile.c.return_profile_id,
            m.return_profile.c.profile_code,
            m.return_profile.c.display_name,
            m.return_profile.c.description,
            m.return_profile.c.base_return_basis,
            m.return_profile.c.income_treatment,
        )
        .where(m.return_profile.c.status == "ACTIVE")
        .order_by(m.return_profile.c.sort_order, m.return_profile.c.profile_code)
    ).mappings().all()
    return ReturnProfileResponse(
        data=[
            ReturnProfileView(
                returnProfileId=row.return_profile_id,
                profileCode=row.profile_code,
                displayName=row.display_name,
                description=row.description,
                baseReturnBasis=row.base_return_basis,
                incomeTreatment=row.income_treatment,
            )
            for row in rows
        ],
        meta=ApiMeta(
            tenantContext=str(tenant_id),
            source="live-reference-api",
            apiVersion=api_version,
            correlationId=correlation_id,
            total=len(rows),
        ),
    )


def list_index_kinds(connection: Connection, tenant_id: UUID, api_version: str, correlation_id: str) -> IndexKindResponse:
    """Return active governed index-kind semantics for onboarding forms."""

    rows = connection.execute(
        select(
            m.index_kind_catalogue.c.index_kind_code,
            m.index_kind_catalogue.c.display_name,
            m.index_kind_catalogue.c.description,
            m.index_kind_catalogue.c.dissemination_class,
            m.index_kind_catalogue.c.methodology_ownership,
            m.index_kind_catalogue.c.example_text,
            m.index_kind_catalogue.c.status,
        )
        .where(m.index_kind_catalogue.c.status == "ACTIVE")
        .order_by(m.index_kind_catalogue.c.sort_order, m.index_kind_catalogue.c.index_kind_code)
    ).mappings().all()
    return IndexKindResponse(
        data=[
            IndexKindView(
                indexKindCode=row.index_kind_code,
                displayName=row.display_name,
                description=row.description,
                disseminationClass=row.dissemination_class,
                methodologyOwnership=row.methodology_ownership,
                exampleText=row.example_text,
                status=row.status,
            )
            for row in rows
        ],
        meta=ApiMeta(
            tenantContext=str(tenant_id),
            source="live-reference-api",
            apiVersion=api_version,
            correlationId=correlation_id,
            total=len(rows),
        ),
    )


def list_organisations(
    connection: Connection,
    tenant_id: UUID,
    api_version: str,
    correlation_id: str,
    query: str = "",
    limit: int = 100,
) -> OrganisationOptionResponse:
    """Return active organisation options for administrator and agent roles."""

    organisation = m.organisation
    statement = select(
        organisation.c.organisation_id,
        organisation.c.display_name,
        organisation.c.legal_name,
        organisation.c.status,
    ).where(organisation.c.status == "ACTIVE")
    normalized = query.strip().lower()
    if normalized:
        statement = statement.where(
            or_(
                func.lower(organisation.c.display_name).contains(normalized),
                func.lower(organisation.c.legal_name).contains(normalized),
            )
        )
    rows = connection.execute(
        statement.order_by(organisation.c.display_name).limit(limit)
    ).mappings().all()
    return OrganisationOptionResponse(
        data=[
            OrganisationOptionView(
                organisationId=row.organisation_id,
                displayName=row.display_name,
                legalName=row.legal_name,
                status=row.status,
            )
            for row in rows
        ],
        meta=ApiMeta(
            tenantContext=str(tenant_id),
            source="live-reference-api",
            apiVersion=api_version,
            correlationId=correlation_id,
            limit=limit,
            total=len(rows),
        ),
    )


def list_index_families(connection: Connection, tenant_id: UUID, api_version: str, correlation_id: str) -> IndexFamilyOptionResponse:
    """Return active shared or tenant-private index families for selection."""

    family = m.index_family
    node = m.financial_reference_node
    provider = m.organisation.alias("family_provider")
    scope = m.reference_node_scope
    rows = connection.execute(
        select(
            family.c.index_family_id,
            family.c.family_node_id,
            node.c.canonical_name,
            family.c.provider_organisation_id,
            provider.c.display_name.label("provider_organisation_name"),
        )
        .select_from(
            family.join(node, family.c.family_node_id == node.c.reference_node_id)
            .outerjoin(provider, family.c.provider_organisation_id == provider.c.organisation_id)
            .outerjoin(scope, scope.c.reference_node_id == family.c.family_node_id)
        )
        .where(family.c.status == "ACTIVE")
        .where(node.c.status == "ACTIVE")
        .where(
            or_(
                scope.c.reference_node_id.is_(None),
                scope.c.scope_type == "SHARED_CANONICAL",
                and_(scope.c.scope_type == "TENANT_PRIVATE", scope.c.owner_tenant_id == tenant_id),
            )
        )
        .order_by(node.c.canonical_name)
    ).mappings().all()
    return IndexFamilyOptionResponse(
        data=[
            IndexFamilyOptionView(
                indexFamilyId=row.index_family_id,
                familyNodeId=row.family_node_id,
                familyName=row.canonical_name,
                providerOrganisationId=row.provider_organisation_id,
                providerOrganisationName=row.provider_organisation_name,
            )
            for row in rows
        ],
        meta=ApiMeta(
            tenantContext=str(tenant_id),
            source="live-reference-api",
            apiVersion=api_version,
            correlationId=correlation_id,
            total=len(rows),
        ),
    )


def _load_listing_views(connection: Connection, tenant_id: UUID, instrument_id: UUID) -> tuple[list[InstrumentListingView], list[UUID]]:
    as_of = date.today()
    listing = m.listing
    version = m.listing_definition_version
    venue = m.market_venue
    currency = m.currency
    venue_mic = (
        select(m.market_venue_identifier.c.identifier_value)
        .where(m.market_venue_identifier.c.market_venue_id == venue.c.market_venue_id)
        .order_by(
            m.market_venue_identifier.c.is_primary.desc(),
            (m.market_venue_identifier.c.identifier_scheme == "ISO_10383_MIC").desc(),
            m.market_venue_identifier.c.identifier_value,
        )
        .limit(1)
        .scalar_subquery()
    )
    rows = connection.execute(
        select(
            listing.c.listing_node_id,
            venue_mic.label("market_venue_mic"),
            venue.c.display_name.label("venue_name"),
            version.c.trading_symbol,
            currency.c.currency_code.label("trading_currency"),
            listing.c.status.label("listing_status"),
            version.c.quote_factor,
            version.c.unit_multiplier,
        )
        .select_from(
            listing.join(
                version,
                and_(
                    version.c.listing_node_id == listing.c.listing_node_id,
                    version.c.status == "APPROVED",
                    version.c.is_current.is_(True),
                    version.c.effective_from <= as_of,
                    or_(version.c.effective_to.is_(None), version.c.effective_to >= as_of),
                ),
            )
            .join(venue, version.c.market_venue_id == venue.c.market_venue_id)
            .join(currency, version.c.trading_currency_id == currency.c.currency_id)
        )
        .where(listing.c.instrument_node_id == instrument_id)
        .order_by(listing.c.is_primary_listing.desc(), venue.c.display_name, listing.c.trading_symbol)
    ).mappings().all()
    listing_ids = [row.listing_node_id for row in rows]
    views = [
        InstrumentListingView(
            listingId=row.listing_node_id,
            marketVenueMic=row.market_venue_mic or "UNMAPPED",
            venueName=row.venue_name,
            tradingSymbol=row.trading_symbol,
            tradingCurrency=row.trading_currency,
            status=row.listing_status,
            quoteFactor=_decimal(row.quote_factor),
            unitMultiplier=_decimal(row.unit_multiplier),
            identifiers=_load_identifiers(connection, row.listing_node_id),
            marketData=_load_market_data(connection, tenant_id, [row.listing_node_id]),
        )
        for row in rows
    ]
    return views, listing_ids


def get_instrument(connection: Connection, tenant_id: UUID, instrument_id: UUID) -> InstrumentView | None:
    _, _, _, _, _, stmt = _base_instrument_select(tenant_id)
    row = connection.execute(stmt.where(m.financial_reference_node.c.reference_node_id == instrument_id)).mappings().first()
    if row is None:
        return None
    listings, listing_ids = _load_listing_views(connection, tenant_id, instrument_id)
    return InstrumentView(
        instrumentId=row.instrument_id,
        canonicalName=row.canonical_name,
        instrumentType=row.instrument_type,
        assetClass=row.asset_class,
        status=row.node_status,
        issuer=row.issuer,
        baseCurrency=row.base_currency,
        definitionVersion=row.definition_version,
        effectiveFrom=_iso(row.effective_from),
        identifiers=_load_identifiers(connection, instrument_id),
        mappings=_load_mappings(connection, tenant_id, instrument_id, listing_ids),
        listings=listings,
        instrumentMarketData=_load_market_data(connection, tenant_id, [instrument_id]),
        taxonomy=_load_taxonomy(connection, instrument_id),
        notes="Canonical reference-data view returned by the reference API.",
    )


def search_instruments(connection: Connection, tenant_id: UUID, query: str, limit: int, offset: int, api_version: str, correlation_id: str, instrument_type: str | None = None, asset_class: str | None = None, status: str | None = None) -> InstrumentSearchResponse:
    rn, inst, typ, _, _, stmt = _base_instrument_select(tenant_id)
    predicate = _search_predicate(tenant_id, query, rn, inst, typ)
    if predicate is not None:
        stmt = stmt.where(predicate)
    if instrument_type:
        stmt = stmt.where(typ.c.type_code == instrument_type.upper())
    if asset_class:
        stmt = stmt.where(inst.c.asset_class == asset_class.upper())
    if status:
        stmt = stmt.where(rn.c.status == status.upper())
    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = int(connection.execute(count_stmt).scalar_one())
    rows = connection.execute(stmt.order_by(rn.c.canonical_name).limit(limit).offset(offset)).mappings().all()
    data = []
    for row in rows:
        view = get_instrument(connection, tenant_id, row.instrument_id)
        if view is not None:
            data.append(view)
    from .contracts import ApiMeta

    return InstrumentSearchResponse(
        data=data,
        meta=ApiMeta(
            tenantContext=str(tenant_id),
            source="live-reference-api",
            apiVersion=api_version,
            correlationId=correlation_id,
            limit=limit,
            offset=offset,
            total=total,
        ),
    )


def search_reference_nodes(
    connection: Connection,
    tenant_id: UUID,
    query: str,
    limit: int,
    offset: int,
    api_version: str,
    correlation_id: str,
    node_type: str | None = None,
    instrument_type: str | None = None,
    asset_class: str | None = None,
    reference_level: str = "ANY",
) -> ReferenceNodeSearchResponse:
    """Search visible reference nodes for contract-underlying selection.

    Unlike ``search_instruments``, this endpoint deliberately includes
    non-instrument reference objects such as INDEX, FX_PAIR, COMMODITY, FUND,
    and RATE_INDEX nodes.  If both node and instrument filters are supplied,
    they are alternatives (OR), which lets a caller request a fund vehicle and
    its tradeable share classes in one list.
    """

    def split_filter(value: str | None) -> tuple[str, ...]:
        return tuple(sorted({part.strip().upper() for part in (value or "").split(",") if part.strip()}))

    node_types = split_filter(node_type)
    instrument_types = split_filter(instrument_type)
    reference_level = reference_level.strip().upper()
    if reference_level not in {"ANY", "ECONOMIC", "LISTING"}:
        raise InvalidCatalogueValue("reference_level must be ANY, ECONOMIC, or LISTING")
    as_of = date.today()
    rn = m.financial_reference_node
    node_typ = m.reference_node_type
    inst = m.instrument
    inst_typ = m.instrument_type.alias("reference_instrument_type")
    definition = m.instrument_definition_version.alias("reference_definition")
    definition_typ = m.instrument_type.alias("reference_definition_type")
    listing = m.listing.alias("reference_listing")
    listing_definition = m.listing_definition_version.alias("reference_listing_definition")
    listing_venue = m.market_venue.alias("reference_listing_venue")
    listing_currency = m.currency.alias("reference_listing_currency")
    parent_inst = m.instrument.alias("reference_parent_instrument")
    parent_inst_typ = m.instrument_type.alias("reference_parent_instrument_type")
    parent_definition = m.instrument_definition_version.alias("reference_parent_definition")
    parent_definition_typ = m.instrument_type.alias("reference_parent_definition_type")
    index_term = m.index_terms
    inst_currency = m.currency.alias("reference_instrument_currency")
    index_currency = m.currency.alias("reference_index_currency")
    scope = m.reference_node_scope

    effective_definition = and_(
        definition.c.instrument_node_id == rn.c.reference_node_id,
        definition.c.status == "APPROVED",
        definition.c.is_current.is_(True),
        definition.c.effective_from <= as_of,
        or_(definition.c.effective_to.is_(None), definition.c.effective_to >= as_of),
    )
    effective_parent_definition = and_(
        parent_definition.c.instrument_node_id == listing.c.instrument_node_id,
        parent_definition.c.status == "APPROVED",
        parent_definition.c.is_current.is_(True),
        parent_definition.c.effective_from <= as_of,
        or_(parent_definition.c.effective_to.is_(None), parent_definition.c.effective_to >= as_of),
    )
    effective_listing_definition = and_(
        listing_definition.c.listing_node_id == listing.c.listing_node_id,
        listing_definition.c.status == "APPROVED",
        listing_definition.c.is_current.is_(True),
        listing_definition.c.effective_from <= as_of,
        or_(listing_definition.c.effective_to.is_(None), listing_definition.c.effective_to >= as_of),
    )
    listing_venue_mic = (
        select(m.market_venue_identifier.c.identifier_value)
        .where(m.market_venue_identifier.c.market_venue_id == listing_venue.c.market_venue_id)
        .order_by(
            m.market_venue_identifier.c.is_primary.desc(),
            (m.market_venue_identifier.c.identifier_scheme == "ISO_10383_MIC").desc(),
            m.market_venue_identifier.c.identifier_value,
        )
        .limit(1)
        .scalar_subquery()
    )
    from_clause = (
        rn.join(node_typ, node_typ.c.reference_node_type_id == rn.c.reference_node_type_id)
        .outerjoin(inst, inst.c.instrument_node_id == rn.c.reference_node_id)
        .outerjoin(inst_typ, inst_typ.c.instrument_type_id == inst.c.instrument_type_id)
        .outerjoin(definition, effective_definition)
        .outerjoin(definition_typ, definition_typ.c.instrument_type_id == definition.c.instrument_type_id)
        .outerjoin(listing, listing.c.listing_node_id == rn.c.reference_node_id)
        .outerjoin(listing_definition, effective_listing_definition)
        .outerjoin(listing_venue, listing_venue.c.market_venue_id == func.coalesce(listing_definition.c.market_venue_id, listing.c.market_venue_id))
        .outerjoin(listing_currency, listing_currency.c.currency_id == func.coalesce(listing_definition.c.trading_currency_id, listing.c.trading_currency_id))
        .outerjoin(parent_inst, parent_inst.c.instrument_node_id == listing.c.instrument_node_id)
        .outerjoin(parent_inst_typ, parent_inst_typ.c.instrument_type_id == parent_inst.c.instrument_type_id)
        .outerjoin(parent_definition, effective_parent_definition)
        .outerjoin(parent_definition_typ, parent_definition_typ.c.instrument_type_id == parent_definition.c.instrument_type_id)
        .outerjoin(index_term, index_term.c.index_node_id == rn.c.reference_node_id)
        .outerjoin(inst_currency, inst_currency.c.currency_id == func.coalesce(definition.c.base_currency_id, inst.c.base_currency_id))
        .outerjoin(index_currency, index_currency.c.currency_id == index_term.c.base_currency_id)
        .outerjoin(scope, scope.c.reference_node_id == rn.c.reference_node_id)
    )
    resolved_instrument_type = func.coalesce(
        definition_typ.c.type_code,
        inst_typ.c.type_code,
        parent_definition_typ.c.type_code,
        parent_inst_typ.c.type_code,
    )
    resolved_asset_class = func.coalesce(
        definition.c.asset_class,
        inst.c.asset_class,
        parent_definition.c.asset_class,
        parent_inst.c.asset_class,
    )
    resolved_currency = func.coalesce(inst_currency.c.currency_code, index_currency.c.currency_code)
    node_parent_id = listing.c.instrument_node_id
    resolved_trading_currency = listing_currency.c.currency_code
    stmt = (
        select(
            rn.c.reference_node_id,
            rn.c.canonical_name,
            rn.c.internal_code,
            node_typ.c.type_code.label("node_type"),
            resolved_instrument_type.label("instrument_type"),
            resolved_asset_class.label("asset_class"),
            resolved_currency.label("base_currency"),
            rn.c.status,
            rn.c.is_tradable,
            node_parent_id.label("parent_reference_node_id"),
            listing_venue_mic.label("market_venue_mic"),
            listing_venue.c.display_name.label("venue_name"),
            func.coalesce(listing_definition.c.trading_symbol, listing.c.trading_symbol).label("trading_symbol"),
            resolved_trading_currency.label("trading_currency"),
        )
        .select_from(from_clause)
        .where(rn.c.status == "ACTIVE")
        .where(node_typ.c.status == "ACTIVE")
        .where(_visible_node_clause(tenant_id))
    )
    if reference_level == "LISTING":
        stmt = stmt.where(node_typ.c.type_code == "LISTING")
    elif reference_level == "ECONOMIC":
        stmt = stmt.where(node_typ.c.type_code != "LISTING")
    if node_types and instrument_types:
        stmt = stmt.where(or_(node_typ.c.type_code.in_(node_types), resolved_instrument_type.in_(instrument_types)))
    elif node_types:
        stmt = stmt.where(node_typ.c.type_code.in_(node_types))
    elif instrument_types:
        stmt = stmt.where(resolved_instrument_type.in_(instrument_types))
    if asset_class:
        stmt = stmt.where(resolved_asset_class == asset_class.strip().upper())
    normalized = query.strip().lower()
    if normalized:
        stmt = stmt.where(
            or_(
                func.lower(rn.c.canonical_name).contains(normalized),
                func.lower(rn.c.internal_code).contains(normalized),
                func.lower(node_typ.c.type_code).contains(normalized),
                func.lower(resolved_instrument_type).contains(normalized),
                func.lower(resolved_asset_class).contains(normalized),
            )
        )
    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = int(connection.execute(count_stmt).scalar_one())
    rows = connection.execute(stmt.order_by(rn.c.canonical_name, rn.c.reference_node_id).limit(limit).offset(offset)).mappings().all()
    return ReferenceNodeSearchResponse(
        data=[
            ReferenceNodeOptionView(
                referenceNodeId=row.reference_node_id,
                canonicalName=row.canonical_name,
                internalCode=row.internal_code,
                nodeType=row.node_type,
                instrumentType=row.instrument_type,
                assetClass=row.asset_class,
                baseCurrency=row.base_currency,
                status=row.status,
                isTradable=row.is_tradable,
                parentReferenceNodeId=row.parent_reference_node_id,
                marketVenueMic=row.market_venue_mic,
                venueName=row.venue_name,
                tradingSymbol=row.trading_symbol,
                tradingCurrency=row.trading_currency,
            )
            for row in rows
        ],
        meta=ApiMeta(
            tenantContext=str(tenant_id),
            source="live-reference-api",
            apiVersion=api_version,
            correlationId=correlation_id,
            limit=limit,
            offset=offset,
            total=total,
        ),
    )


def create_mapping_proposal(connection: Connection, tenant_id: UUID, actor_id: UUID, request: MappingProposalRequest) -> MappingProposalView:
    namespace_row = connection.execute(
        select(m.external_id_namespace.c.external_id_namespace_id)
        .where(m.external_id_namespace.c.namespace_code == request.namespace)
        .where(m.external_id_namespace.c.status == "ACTIVE")
    ).first()
    if namespace_row is None:
        raise RepositoryNotFound("External identifier namespace does not exist")
    target = get_instrument(connection, tenant_id, request.target_object_id)
    if request.target_object_type == "INSTRUMENT" and target is None:
        raise RepositoryNotFound("Target instrument is not visible in this tenant context")
    if request.target_object_type == "LISTING":
        parent_instrument_id = connection.execute(
            select(m.listing.c.instrument_node_id).where(m.listing.c.listing_node_id == request.target_object_id)
        ).scalar_one_or_none()
        if parent_instrument_id is None or get_instrument(connection, tenant_id, parent_instrument_id) is None:
            raise RepositoryNotFound("Target listing is not visible in this tenant context")
    if request.target_object_type not in {"INSTRUMENT", "LISTING"}:
        raise InvalidWorkflowState("Only INSTRUMENT and LISTING mappings are supported by this workflow")
    proposal_id = uuid4()
    payload = {
        "namespace": request.namespace,
        "externalObjectType": request.external_object_type,
        "externalId": request.external_id,
        "targetObjectType": request.target_object_type,
        "targetObjectId": str(request.target_object_id),
        "contextMarketVenueId": str(request.context_market_venue_id) if request.context_market_venue_id else None,
        "validFrom": request.valid_from.isoformat(),
        "reason": request.reason,
        "proposedByUserAccountId": str(actor_id),
    }
    proposal_row = connection.execute(
        m.reference_data_proposal.insert()
        .values(
            reference_data_proposal_id=proposal_id,
            reference_node_id=request.target_object_id if request.target_object_type in {"INSTRUMENT", "LISTING"} else None,
            tenant_id=tenant_id,
            proposal_type="IDENTIFIER_MAPPING",
            proposed_payload=json.dumps(payload, sort_keys=True),
            status="PENDING",
        )
        .returning(m.reference_data_proposal.c.proposed_at_utc)
    ).first()
    return MappingProposalView(
        proposalId=proposal_id,
        status="PENDING",
        proposalType="IDENTIFIER_MAPPING",
        proposedAt=_iso(proposal_row.proposed_at_utc) or datetime.now(timezone.utc).isoformat(),
        namespace=request.namespace,
        externalId=request.external_id,
        targetObjectType=request.target_object_type,
        targetObjectId=request.target_object_id,
    )


def decide_mapping_proposal(connection: Connection, tenant_id: UUID, actor_id: UUID, proposal_id: UUID, decision: str, reason: str) -> MappingProposalView:
    proposal = connection.execute(
        select(m.reference_data_proposal)
        .where(m.reference_data_proposal.c.reference_data_proposal_id == proposal_id)
        .where(m.reference_data_proposal.c.tenant_id == tenant_id)
        .with_for_update()
    ).mappings().first()
    if proposal is None:
        raise RepositoryNotFound("Mapping proposal does not exist")
    if proposal.status != "PENDING":
        raise InvalidWorkflowState("Mapping proposal has already received a decision")
    payload = json.loads(proposal.proposed_payload)
    now = datetime.now(timezone.utc)
    connection.execute(
        m.reference_data_approval.insert().values(
            reference_data_approval_id=uuid4(),
            reference_data_proposal_id=proposal_id,
            decision=decision,
            decided_by_user_account_id=actor_id,
            decided_at_utc=now,
            reason=reason,
        )
    )
    connection.execute(
        m.reference_data_proposal.update()
        .where(m.reference_data_proposal.c.reference_data_proposal_id == proposal_id)
        .values(status=decision, proposed_at_utc=proposal.proposed_at_utc)
    )
    if decision == "APPROVED":
        namespace_id = connection.execute(
            select(m.external_id_namespace.c.external_id_namespace_id).where(m.external_id_namespace.c.namespace_code == payload["namespace"])
        ).scalar_one()
        existing = connection.execute(
            select(m.external_object_mapping.c.external_object_mapping_id)
            .where(m.external_object_mapping.c.external_id_namespace_id == namespace_id)
            .where(m.external_object_mapping.c.external_object_type == payload["externalObjectType"])
            .where(m.external_object_mapping.c.external_id_value == payload["externalId"])
            .where(m.external_object_mapping.c.context_market_venue_id == payload.get("contextMarketVenueId"))
            .where(m.external_object_mapping.c.tenant_id == tenant_id)
            .where(m.external_object_mapping.c.valid_from == date.fromisoformat(payload["validFrom"]))
            .where(m.external_object_mapping.c.status.not_in(["RETIRED", "SUPERSEDED"]))
        ).first()
        if existing is not None:
            raise InvalidWorkflowState("An active mapping already exists for this namespace and effective date")
        connection.execute(
            m.external_object_mapping.insert().values(
                external_object_mapping_id=uuid4(),
                external_id_namespace_id=namespace_id,
                external_object_type=payload["externalObjectType"],
                external_id_value=payload["externalId"],
                tenant_id=tenant_id,
                target_object_type=payload["targetObjectType"],
                target_object_id=UUID(payload["targetObjectId"]),
                context_market_venue_id=UUID(payload["contextMarketVenueId"]) if payload.get("contextMarketVenueId") else None,
                mapping_role="ALIAS",
                mapping_method="MANUAL",
                status="VERIFIED",
                verified_by_user_account_id=actor_id,
                verified_at_utc=now,
                valid_from=date.fromisoformat(payload["validFrom"]),
                recorded_at_utc=now,
            )
        )
    return MappingProposalView(
        proposalId=proposal_id,
        status=decision,
        proposalType=proposal.proposal_type,
        proposedAt=_iso(proposal.proposed_at_utc) or now.isoformat(),
        namespace=payload["namespace"],
        externalId=payload["externalId"],
        targetObjectType=payload["targetObjectType"],
        targetObjectId=UUID(payload["targetObjectId"]),
    )


def _proposal_payload(value: object) -> dict[str, object]:
    """Decode a proposal payload without allowing a malformed row to break review."""

    try:
        decoded = json.loads(value) if isinstance(value, str) else value
    except (TypeError, ValueError):
        decoded = None
    if isinstance(decoded, dict):
        return decoded
    return {"_raw": str(value)}


def _proposal_evidence(value: object) -> dict[str, object] | None:
    """Return only object-shaped decision evidence to keep the UI contract stable."""

    return dict(value) if isinstance(value, dict) else None


def get_reference_data_proposal(connection: Connection, tenant_id: UUID, proposal_id: UUID) -> ReferenceDataProposalView:
    """Return one tenant-scoped proposal with its latest decision evidence."""

    proposal = connection.execute(
        select(m.reference_data_proposal)
        .where(m.reference_data_proposal.c.reference_data_proposal_id == proposal_id)
        .where(m.reference_data_proposal.c.tenant_id == tenant_id)
    ).mappings().first()
    if proposal is None:
        raise RepositoryNotFound("Reference-data proposal does not exist")

    approval = connection.execute(
        select(m.reference_data_approval)
        .where(m.reference_data_approval.c.reference_data_proposal_id == proposal_id)
        .order_by(m.reference_data_approval.c.decided_at_utc.desc())
    ).mappings().first()
    return ReferenceDataProposalView(
        proposalId=proposal.reference_data_proposal_id,
        referenceNodeId=proposal.reference_node_id,
        proposalType=proposal.proposal_type,
        status=proposal.status,
        submissionMode=proposal.submission_mode,
        matchStatus=proposal.match_status,
        confidenceScore=_decimal(proposal.confidence_score) if proposal.confidence_score is not None else None,
        payloadSchemaVersion=proposal.payload_schema_version,
        proposedPayload=_proposal_payload(proposal.proposed_payload),
        proposedAt=_iso(proposal.proposed_at_utc) or datetime.now(timezone.utc).isoformat(),
        decision=approval.decision if approval else None,
        decisionMethod=approval.decision_method if approval else None,
        decisionEvidence=_proposal_evidence(approval.decision_evidence_json) if approval else None,
        decisionReason=approval.reason if approval else None,
        decidedAt=_iso(approval.decided_at_utc) if approval else None,
    )


def decide_reference_data_proposal(
    connection: Connection,
    tenant_id: UUID,
    actor_id: UUID,
    proposal_id: UUID,
    decision: str,
    reason: str,
) -> ReferenceDataProposalView:
    """Dispatch one generic steward decision to the owning workflow.

    The generic endpoint is deliberately an orchestration layer.  Each
    instrument-specific workflow still validates its own payload and performs
    materialisation, so adding a new proposal type cannot silently bypass its
    domain rules.
    """

    proposal = connection.execute(
        select(m.reference_data_proposal.c.proposal_type, m.reference_data_proposal.c.status)
        .where(m.reference_data_proposal.c.reference_data_proposal_id == proposal_id)
        .where(m.reference_data_proposal.c.tenant_id == tenant_id)
        .with_for_update()
    ).mappings().first()
    if proposal is None:
        raise RepositoryNotFound("Reference-data proposal does not exist")
    if proposal.status != "PENDING":
        raise InvalidWorkflowState("Reference-data proposal has already received a decision")

    dispatchers = {
        "IDENTIFIER_MAPPING": decide_mapping_proposal,
        "CREATE": decide_equity_proposal,
        "CREATE_LISTING": decide_equity_proposal,
        "CREATE_BOND": decide_bond_proposal,
        "CREATE_ETP": decide_etp_proposal,
        "CREATE_CRYPTO_ASSET": decide_crypto_asset_proposal,
        "CREATE_INDEX": decide_index_proposal,
        "CREATE_INDEX_FAMILY": decide_index_family_proposal,
        "CREATE_FX_FORWARD": decide_fx_forward_proposal,
        "CREATE_STRUCTURED_PRODUCT": decide_structured_product_proposal,
    }
    dispatcher = dispatchers.get(proposal.proposal_type)
    if dispatcher is None:
        raise InvalidWorkflowState(f"Unsupported reference-data proposal type: {proposal.proposal_type}")
    dispatcher(connection, tenant_id, actor_id, proposal_id, decision, reason)
    return get_reference_data_proposal(connection, tenant_id, proposal_id)


def _equity_policy(connection: Connection, tenant_id: UUID, request: EquityProposalRequest):
    """Resolve the most specific active policy for an automated source submission."""

    if request.source_system_id is None:
        raise InvalidWorkflowState("Automated equity proposals require sourceSystemId")
    if not request.automation_policy_code:
        raise InvalidWorkflowState("Automated equity proposals require automationPolicyCode")
    source = connection.execute(
        select(m.integration_source_system.c.integration_source_system_id)
        .where(m.integration_source_system.c.integration_source_system_id == request.source_system_id)
        .where(m.integration_source_system.c.status == "ACTIVE")
    ).scalar_one_or_none()
    if source is None:
        raise RepositoryNotFound("Source system does not exist or is not active")
    policy = m.reference_data_automation_policy
    common = (
        select(policy)
        .where(policy.c.policy_code == request.automation_policy_code)
        .where(policy.c.source_system_id == request.source_system_id)
        .where(policy.c.target_object_type == "EQUITY")
        .where(policy.c.operation_type == "CREATE")
        .where(policy.c.status == "ACTIVE")
        .where(policy.c.valid_from <= request.effective_from)
        .where(or_(policy.c.valid_to.is_(None), policy.c.valid_to >= request.effective_from))
    )
    # A tenant policy overrides a shared policy with the same code/version.
    for scope in (tenant_id, None):
        scoped = common.where(policy.c.tenant_id == scope if scope is not None else policy.c.tenant_id.is_(None)).order_by(policy.c.version_no.desc())
        row = connection.execute(scoped).mappings().first()
        if row is not None:
            return row
    raise RepositoryNotFound("No active automation policy matches this source and effective date")


def _equity_source_namespace(connection: Connection, request: EquityProposalRequest):
    if not request.source_namespace and not request.source_external_id:
        return None
    if not request.source_namespace or not request.source_external_id:
        raise InvalidWorkflowState("sourceNamespace and sourceExternalId must be supplied together")
    if request.source_system_id is None:
        raise InvalidWorkflowState("An external source mapping requires sourceSystemId")
    namespace = connection.execute(
        select(m.external_id_namespace)
        .where(m.external_id_namespace.c.namespace_code == request.source_namespace)
        .where(m.external_id_namespace.c.integration_source_system_id == request.source_system_id)
        .where(m.external_id_namespace.c.status == "ACTIVE")
    ).mappings().first()
    if namespace is None:
        raise RepositoryNotFound("External identifier namespace does not exist for this source system")
    if namespace.external_object_type and namespace.external_object_type != request.source_object_type:
        raise InvalidWorkflowState("External identifier namespace does not allow this source object type")
    return namespace


def _equity_scheme_id(connection: Connection, scheme_code: str) -> UUID:
    scheme_id = connection.execute(
        select(m.identifier_scheme.c.identifier_scheme_id)
        .where(m.identifier_scheme.c.scheme_code == scheme_code)
    ).scalar_one_or_none()
    if scheme_id is None:
        raise RepositoryNotFound(f"Identifier scheme {scheme_code} is not configured")
    return scheme_id


def _insert_reference_identifier(connection: Connection, reference_node_id: UUID, scheme_code: str, value: str, effective_from: date, *, venue_id: UUID | None = None) -> None:
    scheme_id = _equity_scheme_id(connection, scheme_code)
    existing = connection.execute(
        select(m.financial_reference_identifier.c.financial_reference_identifier_id)
        .where(m.financial_reference_identifier.c.identifier_scheme_id == scheme_id)
        .where(m.financial_reference_identifier.c.identifier_value == value)
        .where(m.financial_reference_identifier.c.context_market_venue_id == venue_id if venue_id is not None else m.financial_reference_identifier.c.context_market_venue_id.is_(None))
    ).first()
    if existing is not None:
        raise InvalidWorkflowState(f"Identifier {scheme_code}:{value} is already assigned")
    connection.execute(
        m.financial_reference_identifier.insert().values(
            reference_node_id=reference_node_id,
            identifier_scheme_id=scheme_id,
            identifier_value=value,
            context_market_venue_id=venue_id,
            valid_from=effective_from,
            is_primary=True,
        )
    )


def _materialize_equity(connection: Connection, tenant_id: UUID, actor_id: UUID, request: EquityProposalRequest) -> tuple[UUID, list[UUID]]:
    """Create the private canonical aggregate atomically after approval."""

    node_types = connection.execute(
        select(m.reference_node_type.c.type_code, m.reference_node_type.c.reference_node_type_id)
        .where(m.reference_node_type.c.type_code.in_(["INSTRUMENT", "LISTING"]))
        .where(m.reference_node_type.c.status == "ACTIVE")
    ).all()
    node_type_ids = {row.type_code: row.reference_node_type_id for row in node_types}
    if set(node_type_ids) != {"INSTRUMENT", "LISTING"}:
        raise RepositoryNotFound("Instrument/listing reference-node types are not configured")
    equity_type_id = connection.execute(
        select(m.instrument_type.c.instrument_type_id)
        .where(m.instrument_type.c.type_code == "EQUITY")
        .where(m.instrument_type.c.status == "ACTIVE")
    ).scalar_one_or_none()
    if equity_type_id is None:
        raise RepositoryNotFound("EQUITY instrument type is not configured")
    base_currency = connection.execute(
        select(m.currency.c.currency_id)
        .where(m.currency.c.currency_id == request.base_currency_id)
        .where(m.currency.c.status == "ACTIVE")
    ).scalar_one_or_none()
    if base_currency is None:
        raise RepositoryNotFound("Base currency does not exist or is not active")
    if request.issuer_organisation_id is not None:
        issuer = connection.execute(
            select(m.organisation.c.organisation_id)
            .where(m.organisation.c.organisation_id == request.issuer_organisation_id)
            .where(m.organisation.c.status == "ACTIVE")
        ).scalar_one_or_none()
        if issuer is None:
            raise RepositoryNotFound("Issuer organisation does not exist or is not active")

    node_row = connection.execute(
        m.financial_reference_node.insert().values(
            canonical_name=request.canonical_name,
            internal_code=request.internal_code,
            reference_node_type_id=node_type_ids["INSTRUMENT"],
            status="ACTIVE",
            is_tradable=True,
        ).returning(m.financial_reference_node.c.reference_node_id)
    ).one()
    instrument_id = node_row.reference_node_id
    connection.execute(
        m.instrument.insert().values(
            instrument_node_id=instrument_id,
            instrument_type_id=equity_type_id,
            asset_class="EQUITY",
            issuer_organisation_id=request.issuer_organisation_id,
            base_currency_id=base_currency,
            effective_from=request.effective_from,
            is_current=True,
            sequence_no=1,
        )
    )
    connection.execute(
        m.instrument_definition_version.insert().values(
            instrument_node_id=instrument_id,
            sequence_no=1,
            instrument_type_id=equity_type_id,
            asset_class="EQUITY",
            issuer_organisation_id=request.issuer_organisation_id,
            base_currency_id=base_currency,
            effective_from=request.effective_from,
            is_current=True,
            status="APPROVED",
            source_payload_id=request.source_payload_id,
            approved_by_user_account_id=actor_id,
            approved_at_utc=datetime.now(timezone.utc),
        )
    )
    connection.execute(
        m.reference_node_scope.insert().values(
            reference_node_id=instrument_id,
            scope_type="TENANT_PRIVATE",
            owner_tenant_id=tenant_id,
            status="ACTIVE",
        )
    )
    for scheme_code, value in (("ISIN", request.isin), ("FIGI", request.figi), ("SEDOL", request.sedol), ("CUSIP", request.cusip)):
        if value:
            _insert_reference_identifier(connection, instrument_id, scheme_code, value, request.effective_from)

    listing_ids: list[UUID] = []
    for listing_request in request.listings:
        venue = connection.execute(
            select(m.market_venue.c.market_venue_id)
            .where(m.market_venue.c.market_venue_id == listing_request.market_venue_id)
            .where(m.market_venue.c.status == "ACTIVE")
        ).scalar_one_or_none()
        if venue is None:
            raise RepositoryNotFound("Listing market venue does not exist or is not active")
        trading_currency = connection.execute(
            select(m.currency.c.currency_id)
            .where(m.currency.c.currency_id == listing_request.trading_currency_id)
            .where(m.currency.c.status == "ACTIVE")
        ).scalar_one_or_none()
        if trading_currency is None:
            raise RepositoryNotFound("Listing trading currency does not exist or is not active")
        listing_row = connection.execute(
            m.financial_reference_node.insert().values(
                canonical_name=f"{request.canonical_name} — {listing_request.trading_symbol}",
                reference_node_type_id=node_type_ids["LISTING"],
                status="ACTIVE",
                is_tradable=True,
            ).returning(m.financial_reference_node.c.reference_node_id)
        ).one()
        listing_id = listing_row.reference_node_id
        listing_ids.append(listing_id)
        connection.execute(
            m.listing.insert().values(
                listing_node_id=listing_id,
                instrument_node_id=instrument_id,
                market_venue_id=venue,
                trading_currency_id=trading_currency,
                trading_symbol=listing_request.trading_symbol,
                quote_factor=listing_request.quote_factor,
                unit_multiplier=listing_request.unit_multiplier,
                is_primary_listing=listing_request.is_primary_listing,
                effective_from=listing_request.effective_from,
                status="ACTIVE",
            )
        )
        connection.execute(
            m.listing_definition_version.insert().values(
                listing_node_id=listing_id,
                sequence_no=1,
                market_venue_id=venue,
                trading_currency_id=trading_currency,
                trading_symbol=listing_request.trading_symbol,
                quote_factor=listing_request.quote_factor,
                unit_multiplier=listing_request.unit_multiplier,
                effective_from=listing_request.effective_from,
                is_current=True,
                status="APPROVED",
                source_payload_id=request.source_payload_id,
                approved_by_user_account_id=actor_id,
                approved_at_utc=datetime.now(timezone.utc),
            )
        )
        connection.execute(
            m.reference_node_scope.insert().values(
                reference_node_id=listing_id,
                scope_type="TENANT_PRIVATE",
                owner_tenant_id=tenant_id,
                status="ACTIVE",
            )
        )
        _insert_reference_identifier(connection, listing_id, "TICKER", listing_request.trading_symbol, listing_request.effective_from, venue_id=venue)
        if listing_request.figi:
            _insert_reference_identifier(connection, listing_id, "FIGI", listing_request.figi, listing_request.effective_from, venue_id=venue)
        if listing_request.venue_product_id:
            _insert_reference_identifier(connection, listing_id, "VENUE_PRODUCT_ID", listing_request.venue_product_id, listing_request.effective_from, venue_id=venue)
        if listing_request.fix_security_id:
            _insert_reference_identifier(connection, listing_id, "FIX_SECURITY_ID", listing_request.fix_security_id, listing_request.effective_from, venue_id=venue)
    return instrument_id, listing_ids


def _materialize_equity_listing(
    connection: Connection,
    tenant_id: UUID,
    actor_id: UUID,
    instrument_id: UUID,
    listing_request,
) -> UUID:
    """Create one listing only after its approved economic instrument is selected."""

    instrument = get_instrument(connection, tenant_id, instrument_id)
    if instrument is None or instrument.status != "ACTIVE":
        raise RepositoryNotFound("Parent instrument does not exist, is not approved, or is not visible in this tenant context")
    if instrument.instrument_type not in {"EQUITY", "DIGITAL_ASSET", "ETF", "ETC", "ETN", "ETV", "ETI"}:
        raise InvalidWorkflowState("This listing workflow supports equity, ETP, and digital-asset instruments")
    node_type_id = connection.execute(
        select(m.reference_node_type.c.reference_node_type_id)
        .where(m.reference_node_type.c.type_code == "LISTING")
        .where(m.reference_node_type.c.status == "ACTIVE")
    ).scalar_one_or_none()
    if node_type_id is None:
        raise RepositoryNotFound("LISTING reference-node type is not configured")
    venue = connection.execute(
        select(m.market_venue.c.market_venue_id)
        .where(m.market_venue.c.market_venue_id == listing_request.market_venue_id)
        .where(m.market_venue.c.status == "ACTIVE")
    ).scalar_one_or_none()
    if venue is None:
        raise RepositoryNotFound("Listing market venue does not exist or is not active")
    trading_currency = connection.execute(
        select(m.currency.c.currency_id)
        .where(m.currency.c.currency_id == listing_request.trading_currency_id)
        .where(m.currency.c.status == "ACTIVE")
    ).scalar_one_or_none()
    if trading_currency is None:
        raise RepositoryNotFound("Listing trading currency does not exist or is not active")
    listing_row = connection.execute(
        m.financial_reference_node.insert().values(
            canonical_name=f"{instrument.canonical_name} — {listing_request.trading_symbol}",
            reference_node_type_id=node_type_id,
            status="ACTIVE",
            is_tradable=True,
        ).returning(m.financial_reference_node.c.reference_node_id)
    ).one()
    listing_id = listing_row.reference_node_id
    connection.execute(
        m.listing.insert().values(
            listing_node_id=listing_id,
            instrument_node_id=instrument_id,
            market_venue_id=venue,
            trading_currency_id=trading_currency,
            trading_symbol=listing_request.trading_symbol,
            quote_factor=listing_request.quote_factor,
            unit_multiplier=listing_request.unit_multiplier,
            is_primary_listing=listing_request.is_primary_listing,
            effective_from=listing_request.effective_from,
            status="ACTIVE",
        )
    )
    connection.execute(
        m.listing_definition_version.insert().values(
            listing_node_id=listing_id,
            sequence_no=1,
            market_venue_id=venue,
            trading_currency_id=trading_currency,
            trading_symbol=listing_request.trading_symbol,
            quote_factor=listing_request.quote_factor,
            unit_multiplier=listing_request.unit_multiplier,
            effective_from=listing_request.effective_from,
            is_current=True,
            status="APPROVED",
            approved_by_user_account_id=actor_id,
            approved_at_utc=datetime.now(timezone.utc),
        )
    )
    connection.execute(
        m.reference_node_scope.insert().values(
            reference_node_id=listing_id,
            scope_type="TENANT_PRIVATE",
            owner_tenant_id=tenant_id,
            status="ACTIVE",
        )
    )
    _insert_reference_identifier(connection, listing_id, "TICKER", listing_request.trading_symbol, listing_request.effective_from, venue_id=venue)
    if listing_request.figi:
        _insert_reference_identifier(connection, listing_id, "FIGI", listing_request.figi, listing_request.effective_from, venue_id=venue)
    if listing_request.venue_product_id:
        _insert_reference_identifier(connection, listing_id, "VENUE_PRODUCT_ID", listing_request.venue_product_id, listing_request.effective_from, venue_id=venue)
    if listing_request.fix_security_id:
        _insert_reference_identifier(connection, listing_id, "FIX_SECURITY_ID", listing_request.fix_security_id, listing_request.effective_from, venue_id=venue)
    return listing_id


def _insert_equity_source_mapping(connection: Connection, tenant_id: UUID, actor_id: UUID, request: EquityProposalRequest, instrument_id: UUID, listing_ids: list[UUID], *, automated: bool) -> None:
    """Persist an optional verified source alias after canonical materialisation."""

    namespace = _equity_source_namespace(connection, request)
    if namespace is None:
        return
    target_id = listing_ids[0] if request.source_object_type == "LISTING" and listing_ids else instrument_id
    existing = connection.execute(
        select(m.external_object_mapping.c.external_object_mapping_id)
        .where(m.external_object_mapping.c.external_id_namespace_id == namespace.external_id_namespace_id)
        .where(m.external_object_mapping.c.external_object_type == request.source_object_type)
        .where(m.external_object_mapping.c.external_id_value == request.source_external_id)
        .where(m.external_object_mapping.c.tenant_id == tenant_id)
        .where(m.external_object_mapping.c.valid_from == request.effective_from)
        .where(m.external_object_mapping.c.status.not_in(["RETIRED", "SUPERSEDED"]))
    ).first()
    if existing is not None:
        raise InvalidWorkflowState("An active source mapping already exists for this external identifier and effective date")
    connection.execute(
        m.external_object_mapping.insert().values(
            external_id_namespace_id=namespace.external_id_namespace_id,
            external_object_type=request.source_object_type,
            external_id_value=request.source_external_id,
            tenant_id=tenant_id,
            target_object_type=request.source_object_type,
            target_object_id=target_id,
            mapping_role="PRIMARY",
            mapping_method="PROVIDER_MATCH" if automated else "MANUAL",
            status="VERIFIED",
            confidence=request.confidence_score,
            verified_by_user_account_id=actor_id,
            verified_at_utc=datetime.now(timezone.utc),
            valid_from=request.effective_from,
            source_payload_id=request.source_payload_id,
        )
    )


def _equity_view(connection: Connection, tenant_id: UUID, proposal_id: UUID) -> EquityProposalView:
    proposal = connection.execute(
        select(m.reference_data_proposal)
        .where(m.reference_data_proposal.c.reference_data_proposal_id == proposal_id)
        .where(m.reference_data_proposal.c.tenant_id == tenant_id)
    ).mappings().first()
    if proposal is None:
        raise RepositoryNotFound("Equity proposal does not exist")
    approval = connection.execute(
        select(m.reference_data_approval.c.decision_method, m.reference_data_approval.c.decision_evidence_json)
        .where(m.reference_data_approval.c.reference_data_proposal_id == proposal_id)
        .order_by(m.reference_data_approval.c.decided_at_utc.desc())
    ).mappings().first()
    listing_ids: list[UUID] = []
    if proposal.reference_node_id is not None:
        listing_ids = list(connection.execute(
            select(m.listing.c.listing_node_id)
            .where(m.listing.c.instrument_node_id == proposal.reference_node_id)
            .order_by(m.listing.c.is_primary_listing.desc(), m.listing.c.trading_symbol)
        ).scalars().all())
    return EquityProposalView(
        proposalId=proposal.reference_data_proposal_id,
        status=proposal.status,
        proposalType=proposal.proposal_type,
        submissionMode=proposal.submission_mode,
        matchStatus=proposal.match_status,
        confidenceScore=_decimal(proposal.confidence_score) if proposal.confidence_score is not None else None,
        automationPolicyId=proposal.automation_policy_id,
        instrumentId=proposal.reference_node_id,
        listingIds=listing_ids,
        proposedAt=_iso(proposal.proposed_at_utc) or datetime.now(timezone.utc).isoformat(),
        decisionMethod=approval.decision_method if approval else None,
        decisionEvidence=approval.decision_evidence_json if approval else None,
    )


def submit_equity_proposal(connection: Connection, tenant_id: UUID, actor_id: UUID, request: EquityProposalRequest) -> EquityProposalView:
    """Validate and record an equity proposal, auto-approving only by policy."""

    if request.submission_mode == "AUTOMATED" and request.source_system_id is None:
        raise InvalidWorkflowState("Automated equity proposals require sourceSystemId")
    if request.source_payload_id:
        if request.source_system_id is None:
            raise InvalidWorkflowState("sourcePayloadId requires sourceSystemId")
        payload_source = connection.execute(
            select(m.source_payload.c.source_payload_id)
            .where(m.source_payload.c.source_payload_id == request.source_payload_id)
            .where(m.source_payload.c.integration_source_system_id == request.source_system_id)
            .where(or_(m.source_payload.c.tenant_id == tenant_id, m.source_payload.c.tenant_id.is_(None)))
        ).scalar_one_or_none()
        if payload_source is None:
            raise RepositoryNotFound("Source payload does not exist for this source system and tenant")
    if request.cfi:
        raise InvalidWorkflowState("CFI is a classification code; CFI assignment is deferred until the classification-assignment model is enabled")
    if request.idempotency_key:
        if request.source_system_id is None:
            raise InvalidWorkflowState("idempotencyKey requires sourceSystemId")
        existing = connection.execute(
            select(m.reference_data_proposal.c.reference_data_proposal_id)
            .where(m.reference_data_proposal.c.source_system_id == request.source_system_id)
            .where(m.reference_data_proposal.c.idempotency_key == request.idempotency_key)
            .where(m.reference_data_proposal.c.tenant_id == tenant_id)
        ).scalar_one_or_none()
        if existing is not None:
            return _equity_view(connection, tenant_id, existing)
    listing_keys = [(item.market_venue_id, item.trading_symbol.casefold()) for item in request.listings]
    if len(set(listing_keys)) != len(listing_keys):
        raise InvalidWorkflowState("An equity proposal cannot contain duplicate venue and symbol listings")
    if request.internal_code:
        existing_code = connection.execute(
            select(m.financial_reference_node.c.reference_node_id)
            .where(m.financial_reference_node.c.internal_code == request.internal_code)
        ).scalar_one_or_none()
        if existing_code is not None:
            raise InvalidWorkflowState("An instrument with this internal code already exists")
    if request.isin:
        isin_scheme = _equity_scheme_id(connection, "ISIN")
        existing_isin = connection.execute(
            select(m.financial_reference_identifier.c.reference_node_id)
            .where(m.financial_reference_identifier.c.identifier_scheme_id == isin_scheme)
            .where(m.financial_reference_identifier.c.identifier_value == request.isin)
        ).scalar_one_or_none()
        if existing_isin is not None:
            raise InvalidWorkflowState("An instrument with this ISIN already exists")
    for listing_request in request.listings:
        existing_listing = connection.execute(
            select(m.listing.c.listing_node_id)
            .where(m.listing.c.market_venue_id == listing_request.market_venue_id)
            .where(m.listing.c.trading_symbol == listing_request.trading_symbol)
            .where(m.listing.c.status == "ACTIVE")
        ).first()
        if existing_listing is not None:
            raise InvalidWorkflowState("An active listing already exists for this venue and symbol")
    namespace = _equity_source_namespace(connection, request)
    policy = _equity_policy(connection, tenant_id, request) if request.submission_mode == "AUTOMATED" else None
    required_schemes = list(policy.required_identifier_schemes or []) if policy else []
    supplied_schemes = {code for code, value in (("ISIN", request.isin), ("FIGI", request.figi), ("SEDOL", request.sedol), ("CUSIP", request.cusip)) if value}
    missing_required = [scheme for scheme in required_schemes if scheme not in supplied_schemes]
    criteria = dict(policy.criteria_json or {}) if policy else {}
    criteria_failures: list[str] = []
    if criteria.get("requireIssuer") and request.issuer_organisation_id is None:
        criteria_failures.append("issuerOrganisationId is required")
    if criteria.get("requirePrimaryListing") and not any(item.is_primary_listing for item in request.listings):
        criteria_failures.append("a primary listing is required")
    eligible_for_auto = bool(policy and policy.auto_approve and not missing_required and not criteria_failures and (policy.min_confidence is None or (request.confidence_score is not None and request.confidence_score >= policy.min_confidence)))
    match_status = "NEW" if not policy or eligible_for_auto else "POSSIBLE_MATCH"
    payload = request.model_dump(mode="json", by_alias=True, exclude_none=True)
    payload["proposedByUserAccountId"] = str(actor_id)
    row = connection.execute(
        m.reference_data_proposal.insert().values(
            tenant_id=tenant_id,
            proposal_type="CREATE",
            proposed_payload=json.dumps(payload, sort_keys=True),
            source_payload_id=request.source_payload_id,
            source_system_id=request.source_system_id,
            submission_mode=request.submission_mode,
            automation_policy_id=policy.reference_data_automation_policy_id if policy else None,
            idempotency_key=request.idempotency_key,
            match_status=match_status,
            confidence_score=request.confidence_score,
            payload_schema_version="equity.v1",
            status="PENDING",
        ).returning(m.reference_data_proposal.c.reference_data_proposal_id)
    ).one()
    proposal_id = row.reference_data_proposal_id
    if eligible_for_auto:
        instrument_id, _ = _materialize_equity(connection, tenant_id, actor_id, request)
        evidence = {
            "policyCode": policy.policy_code,
            "policyVersion": policy.version_no,
            "requiredIdentifiers": required_schemes,
            "missingIdentifiers": missing_required,
            "criteriaFailures": criteria_failures,
            "confidenceScore": str(request.confidence_score) if request.confidence_score is not None else None,
            "sourceNamespace": namespace.namespace_code if namespace else None,
        }
        connection.execute(
            m.reference_data_approval.insert().values(
                reference_data_proposal_id=proposal_id,
                decision="APPROVED",
                decided_by_user_account_id=actor_id,
                decision_method="AUTOMATED",
                automation_policy_id=policy.reference_data_automation_policy_id,
                decision_evidence_json=evidence,
                reason="Automatically approved under governed reference-data policy",
            )
        )
        connection.execute(
            m.reference_data_proposal.update()
            .where(m.reference_data_proposal.c.reference_data_proposal_id == proposal_id)
            .values(reference_node_id=instrument_id, status="APPROVED")
        )
        _insert_equity_source_mapping(connection, tenant_id, actor_id, request, instrument_id, _equity_view(connection, tenant_id, proposal_id).listing_ids, automated=True)
    return _equity_view(connection, tenant_id, proposal_id)


def submit_equity_listing_proposal(
    connection: Connection,
    tenant_id: UUID,
    actor_id: UUID,
    request: EquityListingCreateProposalRequest,
) -> EquityProposalView:
    """Record a listing proposal against a selected approved instrument."""

    instrument = get_instrument(connection, tenant_id, request.instrument_id)
    if instrument is None or instrument.status != "ACTIVE":
        raise RepositoryNotFound("Parent instrument does not exist, is not approved, or is not visible in this tenant context")
    if instrument.instrument_type not in {"EQUITY", "DIGITAL_ASSET", "ETF", "ETC", "ETN", "ETV", "ETI"}:
        raise InvalidWorkflowState("This listing workflow supports equity, ETP, and digital-asset instruments")
    if request.idempotency_key:
        if request.source_system_id is None:
            raise InvalidWorkflowState("idempotencyKey requires sourceSystemId")
        existing = connection.execute(
            select(m.reference_data_proposal.c.reference_data_proposal_id)
            .where(m.reference_data_proposal.c.source_system_id == request.source_system_id)
            .where(m.reference_data_proposal.c.idempotency_key == request.idempotency_key)
            .where(m.reference_data_proposal.c.tenant_id == tenant_id)
        ).scalar_one_or_none()
        if existing is not None:
            return _equity_view(connection, tenant_id, existing)
    existing_listing = connection.execute(
        select(m.listing.c.listing_node_id)
        .where(m.listing.c.market_venue_id == request.listing.market_venue_id)
        .where(m.listing.c.trading_symbol == request.listing.trading_symbol)
        .where(m.listing.c.status == "ACTIVE")
    ).first()
    if existing_listing is not None:
        raise InvalidWorkflowState("An active listing already exists for this venue and symbol")
    payload = request.model_dump(mode="json", by_alias=True, exclude_none=True)
    payload["proposedByUserAccountId"] = str(actor_id)
    proposal_id = connection.execute(
        m.reference_data_proposal.insert().values(
            tenant_id=tenant_id,
            reference_node_id=request.instrument_id,
            proposal_type="CREATE_LISTING",
            proposed_payload=json.dumps(payload, sort_keys=True),
            source_payload_id=request.source_payload_id,
            source_system_id=request.source_system_id,
            submission_mode=request.submission_mode,
            idempotency_key=request.idempotency_key,
            match_status="NEW",
            confidence_score=request.confidence_score,
            payload_schema_version="equity-listing.v1",
            status="PENDING",
        ).returning(m.reference_data_proposal.c.reference_data_proposal_id)
    ).scalar_one()
    return _equity_view(connection, tenant_id, proposal_id)


def decide_equity_proposal(connection: Connection, tenant_id: UUID, actor_id: UUID, proposal_id: UUID, decision: str, reason: str) -> EquityProposalView:
    """Record a manual decision and materialize an approved equity proposal."""

    proposal = connection.execute(
        select(m.reference_data_proposal)
        .where(m.reference_data_proposal.c.reference_data_proposal_id == proposal_id)
        .where(m.reference_data_proposal.c.tenant_id == tenant_id)
        .with_for_update()
    ).mappings().first()
    if proposal is None:
        raise RepositoryNotFound("Equity proposal does not exist")
    if proposal.proposal_type not in {"CREATE", "CREATE_LISTING"}:
        raise InvalidWorkflowState("This endpoint only handles equity creation proposals")
    if proposal.status != "PENDING":
        raise InvalidWorkflowState("Equity proposal has already received a decision")
    payload = json.loads(proposal.proposed_payload)
    request = EquityProposalRequest.model_validate(payload) if proposal.proposal_type == "CREATE" else EquityListingCreateProposalRequest.model_validate(payload)
    now = datetime.now(timezone.utc)
    instrument_id = None
    if decision == "APPROVED":
        if proposal.proposal_type == "CREATE":
            instrument_id, listing_ids = _materialize_equity(connection, tenant_id, actor_id, request)
            _insert_equity_source_mapping(connection, tenant_id, actor_id, request, instrument_id, listing_ids, automated=False)
        else:
            instrument_id = request.instrument_id
            _materialize_equity_listing(connection, tenant_id, actor_id, request.instrument_id, request.listing)
    evidence = {"manualDecision": True, "reason": reason}
    connection.execute(
        m.reference_data_approval.insert().values(
            reference_data_proposal_id=proposal_id,
            decision=decision,
            decided_by_user_account_id=actor_id,
            decision_method="MANUAL",
            decision_evidence_json=evidence,
            decided_at_utc=now,
            reason=reason,
        )
    )
    connection.execute(
        m.reference_data_proposal.update()
        .where(m.reference_data_proposal.c.reference_data_proposal_id == proposal_id)
        .values(status=decision, reference_node_id=instrument_id)
    )
    return _equity_view(connection, tenant_id, proposal_id)


def _crypto_asset_view(connection: Connection, tenant_id: UUID, proposal_id: UUID) -> CryptoAssetProposalView:
    proposal = connection.execute(
        select(m.reference_data_proposal)
        .where(m.reference_data_proposal.c.reference_data_proposal_id == proposal_id)
        .where(m.reference_data_proposal.c.tenant_id == tenant_id)
    ).mappings().first()
    if proposal is None:
        raise RepositoryNotFound("Cryptoasset proposal does not exist")
    payload = json.loads(proposal.proposed_payload)
    currency_id = None
    currency_code = None
    if proposal.reference_node_id is not None:
        currency = connection.execute(
            select(m.currency.c.currency_id, m.currency.c.currency_code)
            .where(m.currency.c.reference_node_id == proposal.reference_node_id)
        ).mappings().first()
        if currency is not None:
            currency_id = currency.currency_id
            currency_code = currency.currency_code
    return CryptoAssetProposalView(
        proposalId=proposal.reference_data_proposal_id,
        status=proposal.status,
        proposalType=proposal.proposal_type,
        submissionMode=proposal.submission_mode,
        canonicalName=payload.get("canonicalName", payload.get("nativeSymbol", "")),
        internalCode=payload.get("internalCode"),
        effectiveFrom=payload.get("effectiveFrom"),
        assetSubtype=payload["assetSubtype"],
        nativeSymbol=payload["nativeSymbol"],
        protocolName=payload.get("protocolName"),
        issuerOrganisationId=payload.get("issuerOrganisationId"),
        decimals=payload.get("decimals"),
        instrumentId=proposal.reference_node_id,
        currencyId=currency_id,
        currencyCode=currency_code,
        proposedAt=_iso(proposal.proposed_at_utc) or datetime.now(timezone.utc).isoformat(),
    )


def get_crypto_asset_proposal(connection: Connection, tenant_id: UUID, proposal_id: UUID) -> CryptoAssetProposalView:
    """Return one tenant-scoped cryptoasset proposal for steward review."""

    return _crypto_asset_view(connection, tenant_id, proposal_id)


def _materialize_crypto_asset(
    connection: Connection,
    tenant_id: UUID,
    actor_id: UUID,
    request: CryptoAssetProposalRequest,
) -> tuple[UUID, UUID]:
    """Create a DIGITAL_ASSET instrument and its currency-role record."""

    node_type_id = connection.execute(
        select(m.reference_node_type.c.reference_node_type_id)
        .where(m.reference_node_type.c.type_code == "INSTRUMENT")
        .where(m.reference_node_type.c.status == "ACTIVE")
    ).scalar_one_or_none()
    if node_type_id is None:
        raise RepositoryNotFound("INSTRUMENT reference-node type is not configured")
    digital_asset_type_id = connection.execute(
        select(m.instrument_type.c.instrument_type_id)
        .where(m.instrument_type.c.type_code == "DIGITAL_ASSET")
        .where(m.instrument_type.c.status == "ACTIVE")
    ).scalar_one_or_none()
    if digital_asset_type_id is None:
        raise RepositoryNotFound("DIGITAL_ASSET instrument type is not configured")
    if request.issuer_organisation_id is not None:
        issuer = connection.execute(
            select(m.organisation.c.organisation_id)
            .where(m.organisation.c.organisation_id == request.issuer_organisation_id)
            .where(m.organisation.c.status == "ACTIVE")
        ).scalar_one_or_none()
        if issuer is None:
            raise RepositoryNotFound("Issuer organisation does not exist or is not active")

    node_id = connection.execute(
        m.financial_reference_node.insert().values(
            canonical_name=request.canonical_name.strip(),
            internal_code=request.internal_code.strip() if request.internal_code else None,
            reference_node_type_id=node_type_id,
            status="ACTIVE",
            is_tradable=True,
        ).returning(m.financial_reference_node.c.reference_node_id)
    ).scalar_one()
    connection.execute(m.instrument.insert().values(
        instrument_node_id=node_id,
        instrument_type_id=digital_asset_type_id,
        asset_class="DIGITAL_ASSET",
        issuer_organisation_id=request.issuer_organisation_id,
        base_currency_id=None,
        effective_from=request.effective_from,
        is_current=True,
        sequence_no=1,
    ))
    connection.execute(m.instrument_definition_version.insert().values(
        instrument_node_id=node_id,
        sequence_no=1,
        instrument_type_id=digital_asset_type_id,
        asset_class="DIGITAL_ASSET",
        issuer_organisation_id=request.issuer_organisation_id,
        base_currency_id=None,
        effective_from=request.effective_from,
        is_current=True,
        status="APPROVED",
        source_payload_id=request.source_payload_id,
        approved_by_user_account_id=actor_id,
        approved_at_utc=datetime.now(timezone.utc),
    ))
    connection.execute(m.reference_node_scope.insert().values(
        reference_node_id=node_id,
        scope_type="TENANT_PRIVATE",
        owner_tenant_id=tenant_id,
        status="ACTIVE",
    ))
    symbol = request.native_symbol.strip().upper()
    connection.execute(m.crypto_asset_terms.insert().values(
        instrument_node_id=node_id,
        asset_subtype=request.asset_subtype,
        native_symbol=symbol,
        protocol_name=request.protocol_name.strip() if request.protocol_name else None,
        issuer_organisation_id=request.issuer_organisation_id,
        effective_from=request.effective_from,
        is_current=True,
        sequence_no=1,
        status="ACTIVE",
        source_payload_id=request.source_payload_id,
    ))
    currency_kind = "STABLECOIN" if request.asset_subtype == "STABLECOIN" else "CRYPTOASSET"
    currency_id = connection.execute(m.currency.insert().values(
        reference_node_id=node_id,
        currency_code=symbol,
        display_name=request.canonical_name.strip(),
        minor_unit=request.decimals,
        currency_kind=currency_kind,
        status="ACTIVE",
    ).returning(m.currency.c.currency_id)).scalar_one()
    return node_id, currency_id


def submit_crypto_asset_proposal(
    connection: Connection,
    tenant_id: UUID,
    actor_id: UUID,
    request: CryptoAssetProposalRequest,
) -> CryptoAssetProposalView:
    """Record a manual-first cryptoasset proposal for steward approval."""

    if request.submission_mode == "AUTOMATED" and request.source_system_id is None:
        raise InvalidWorkflowState("Automated cryptoasset proposals require sourceSystemId")
    if request.idempotency_key:
        if request.source_system_id is None:
            raise InvalidWorkflowState("idempotencyKey requires sourceSystemId")
        existing = connection.execute(
            select(m.reference_data_proposal.c.reference_data_proposal_id)
            .where(m.reference_data_proposal.c.source_system_id == request.source_system_id)
            .where(m.reference_data_proposal.c.idempotency_key == request.idempotency_key)
            .where(m.reference_data_proposal.c.tenant_id == tenant_id)
        ).scalar_one_or_none()
        if existing is not None:
            return _crypto_asset_view(connection, tenant_id, existing)
    normalized_symbol = request.native_symbol.strip().upper()
    if not normalized_symbol:
        raise InvalidWorkflowState("Native symbol cannot be empty")
    if request.internal_code:
        existing_code = connection.execute(
            select(m.financial_reference_node.c.reference_node_id)
            .where(m.financial_reference_node.c.internal_code == request.internal_code.strip())
            .where(m.financial_reference_node.c.status == "ACTIVE")
        ).scalar_one_or_none()
        if existing_code is not None:
            raise InvalidWorkflowState("A reference node with this internal code already exists")
    existing_symbol = connection.execute(
        select(m.currency.c.currency_id)
        .where(m.currency.c.currency_code == normalized_symbol)
        .where(m.currency.c.status == "ACTIVE")
    ).scalar_one_or_none()
    if existing_symbol is not None:
        raise InvalidWorkflowState("A currency or cryptoasset with this native symbol already exists")
    if request.issuer_organisation_id is not None:
        issuer = connection.execute(
            select(m.organisation.c.organisation_id)
            .where(m.organisation.c.organisation_id == request.issuer_organisation_id)
            .where(m.organisation.c.status == "ACTIVE")
        ).scalar_one_or_none()
        if issuer is None:
            raise RepositoryNotFound("Issuer organisation does not exist or is not active")
    normalized_request = request.model_copy(update={
        "canonical_name": request.canonical_name.strip(),
        "internal_code": request.internal_code.strip() if request.internal_code else None,
        "native_symbol": normalized_symbol,
        "protocol_name": request.protocol_name.strip() if request.protocol_name else None,
    })
    payload = normalized_request.model_dump(mode="json", by_alias=True, exclude_none=True)
    payload["proposedByUserAccountId"] = str(actor_id)
    proposal_id = connection.execute(
        m.reference_data_proposal.insert().values(
            tenant_id=tenant_id,
            proposal_type="CREATE_CRYPTO_ASSET",
            proposed_payload=json.dumps(payload, sort_keys=True),
            source_payload_id=request.source_payload_id,
            source_system_id=request.source_system_id,
            submission_mode=request.submission_mode,
            idempotency_key=request.idempotency_key,
            match_status="NEW",
            confidence_score=request.confidence_score,
            payload_schema_version="crypto-asset.v1",
            status="PENDING",
        ).returning(m.reference_data_proposal.c.reference_data_proposal_id)
    ).scalar_one()
    return _crypto_asset_view(connection, tenant_id, proposal_id)


def decide_crypto_asset_proposal(
    connection: Connection,
    tenant_id: UUID,
    actor_id: UUID,
    proposal_id: UUID,
    decision: str,
    reason: str,
) -> CryptoAssetProposalView:
    """Record a steward decision and materialize an approved cryptoasset."""

    proposal = connection.execute(
        select(m.reference_data_proposal)
        .where(m.reference_data_proposal.c.reference_data_proposal_id == proposal_id)
        .where(m.reference_data_proposal.c.tenant_id == tenant_id)
        .with_for_update()
    ).mappings().first()
    if proposal is None:
        raise RepositoryNotFound("Cryptoasset proposal does not exist")
    if proposal.proposal_type != "CREATE_CRYPTO_ASSET":
        raise InvalidWorkflowState("This endpoint only handles cryptoasset creation proposals")
    if proposal.status != "PENDING":
        raise InvalidWorkflowState("Cryptoasset proposal has already received a decision")
    request = CryptoAssetProposalRequest.model_validate(json.loads(proposal.proposed_payload))
    instrument_id = None
    if decision == "APPROVED":
        instrument_id, _ = _materialize_crypto_asset(connection, tenant_id, actor_id, request)
    now = datetime.now(timezone.utc)
    connection.execute(m.reference_data_approval.insert().values(
        reference_data_proposal_id=proposal_id,
        decision=decision,
        decided_by_user_account_id=actor_id,
        decision_method="MANUAL",
        decision_evidence_json={"manualDecision": True, "reason": reason},
        decided_at_utc=now,
        reason=reason,
    ))
    connection.execute(
        m.reference_data_proposal.update()
        .where(m.reference_data_proposal.c.reference_data_proposal_id == proposal_id)
        .values(status=decision, reference_node_id=instrument_id)
    )
    return _crypto_asset_view(connection, tenant_id, proposal_id)


def _bond_enrichment_status(request: BondProposalRequest) -> str:
    """Return whether enough provider-independent terms exist for approval."""

    common = bool(request.base_currency_id and request.maturity_date)
    if request.coupon_type == "ZERO":
        return "READY_FOR_APPROVAL" if common else "PENDING_ENRICHMENT"
    if request.coupon_type == "FIXED":
        complete = common and request.coupon_rate is not None and request.coupon_frequency_per_year is not None and bool(request.day_count_convention)
    else:
        complete = common and request.coupon_frequency_per_year is not None and bool(request.day_count_convention) and bool(request.floating_reference_index)
    return "READY_FOR_APPROVAL" if complete else "PENDING_ENRICHMENT"


def _bond_view(connection: Connection, tenant_id: UUID, proposal_id: UUID) -> BondProposalView:
    proposal = connection.execute(
        select(m.reference_data_proposal)
        .where(m.reference_data_proposal.c.reference_data_proposal_id == proposal_id)
        .where(m.reference_data_proposal.c.tenant_id == tenant_id)
    ).mappings().first()
    if proposal is None:
        raise RepositoryNotFound("Bond proposal does not exist")
    payload = json.loads(proposal.proposed_payload)
    return BondProposalView(
        proposalId=proposal.reference_data_proposal_id,
        status=proposal.status,
        proposalType=proposal.proposal_type,
        submissionMode=proposal.submission_mode,
        couponType=payload["couponType"],
        enrichmentStatus=payload.get("enrichmentStatus", "PENDING_ENRICHMENT"),
        instrumentId=proposal.reference_node_id,
        proposedAt=_iso(proposal.proposed_at_utc) or datetime.now(timezone.utc).isoformat(),
    )


def submit_bond_proposal(connection: Connection, tenant_id: UUID, actor_id: UUID, request: BondProposalRequest) -> BondProposalView:
    """Record a sparse bond proposal; external enrichment may complete it before approval."""

    if request.submission_mode == "AUTOMATED" and request.source_system_id is None:
        raise InvalidWorkflowState("Automated bond proposals require sourceSystemId")
    if request.idempotency_key and request.source_system_id:
        existing = connection.execute(
            select(m.reference_data_proposal.c.reference_data_proposal_id)
            .where(m.reference_data_proposal.c.source_system_id == request.source_system_id)
            .where(m.reference_data_proposal.c.idempotency_key == request.idempotency_key)
            .where(m.reference_data_proposal.c.tenant_id == tenant_id)
        ).scalar_one_or_none()
        if existing is not None:
            return _bond_view(connection, tenant_id, existing)
    if request.base_currency_id is not None:
        exists_currency = connection.execute(
            select(m.currency.c.currency_id)
            .where(m.currency.c.currency_id == request.base_currency_id)
            .where(m.currency.c.status == "ACTIVE")
        ).scalar_one_or_none()
        if exists_currency is None:
            raise RepositoryNotFound("Base currency does not exist or is not active")
    if request.issuer_organisation_id is not None:
        exists_issuer = connection.execute(
            select(m.organisation.c.organisation_id)
            .where(m.organisation.c.organisation_id == request.issuer_organisation_id)
            .where(m.organisation.c.status == "ACTIVE")
        ).scalar_one_or_none()
        if exists_issuer is None:
            raise RepositoryNotFound("Issuer organisation does not exist or is not active")
    if request.day_count_convention:
        exists_convention = connection.execute(
            select(m.day_count_convention.c.day_count_convention_id)
            .where(m.day_count_convention.c.code == request.day_count_convention)
            .where(m.day_count_convention.c.status == "ACTIVE")
        ).scalar_one_or_none()
        if exists_convention is None:
            raise RepositoryNotFound("Day-count convention does not exist or is not active")
    payload = request.model_dump(mode="json", by_alias=True, exclude_none=True)
    payload["proposedByUserAccountId"] = str(actor_id)
    payload["enrichmentStatus"] = _bond_enrichment_status(request)
    proposal_id = connection.execute(
        m.reference_data_proposal.insert().values(
            tenant_id=tenant_id,
            proposal_type="CREATE_BOND",
            proposed_payload=json.dumps(payload, sort_keys=True),
            source_payload_id=request.source_payload_id,
            source_system_id=request.source_system_id,
            submission_mode=request.submission_mode,
            idempotency_key=request.idempotency_key,
            match_status="NEW",
            confidence_score=request.confidence_score,
            payload_schema_version="bond.v1",
            status="PENDING",
        ).returning(m.reference_data_proposal.c.reference_data_proposal_id)
    ).scalar_one()
    return _bond_view(connection, tenant_id, proposal_id)


def _materialize_bond(connection: Connection, tenant_id: UUID, actor_id: UUID, request: BondProposalRequest) -> UUID:
    if _bond_enrichment_status(request) != "READY_FOR_APPROVAL":
        raise InvalidWorkflowState("Bond requires provider enrichment before approval")
    node_types = connection.execute(
        select(m.reference_node_type.c.type_code, m.reference_node_type.c.reference_node_type_id)
        .where(m.reference_node_type.c.type_code == "INSTRUMENT")
        .where(m.reference_node_type.c.status == "ACTIVE")
    ).first()
    if node_types is None:
        raise RepositoryNotFound("INSTRUMENT reference-node type is not configured")
    bond_type_id = connection.execute(
        select(m.instrument_type.c.instrument_type_id)
        .where(m.instrument_type.c.type_code == "BOND")
        .where(m.instrument_type.c.status == "ACTIVE")
    ).scalar_one_or_none()
    if bond_type_id is None:
        raise RepositoryNotFound("BOND instrument type is not configured")
    node_id = connection.execute(
        m.financial_reference_node.insert().values(
            canonical_name=request.canonical_name,
            internal_code=request.internal_code,
            reference_node_type_id=node_types.reference_node_type_id,
            status="ACTIVE",
            is_tradable=True,
        ).returning(m.financial_reference_node.c.reference_node_id)
    ).scalar_one()
    connection.execute(m.instrument.insert().values(
        instrument_node_id=node_id,
        instrument_type_id=bond_type_id,
        asset_class="FIXED_INCOME",
        issuer_organisation_id=request.issuer_organisation_id,
        base_currency_id=request.base_currency_id,
        effective_from=request.effective_from,
        is_current=True,
        sequence_no=1,
    ))
    connection.execute(m.instrument_definition_version.insert().values(
        instrument_node_id=node_id,
        sequence_no=1,
        instrument_type_id=bond_type_id,
        asset_class="FIXED_INCOME",
        issuer_organisation_id=request.issuer_organisation_id,
        base_currency_id=request.base_currency_id,
        effective_from=request.effective_from,
        is_current=True,
        status="APPROVED",
        source_payload_id=request.source_payload_id,
        approved_by_user_account_id=actor_id,
        approved_at_utc=datetime.now(timezone.utc),
    ))
    connection.execute(m.reference_node_scope.insert().values(
        reference_node_id=node_id,
        scope_type="TENANT_PRIVATE",
        owner_tenant_id=tenant_id,
        status="ACTIVE",
    ))
    connection.execute(m.instrument_dates.insert().values(
        instrument_node_id=node_id,
        issue_date=request.issue_date,
        maturity_date=request.maturity_date,
        final_settlement_date=request.final_settlement_date,
    ))
    day_count_convention_id = None
    if request.day_count_convention:
        day_count_convention_id = connection.execute(
            select(m.day_count_convention.c.day_count_convention_id)
            .where(m.day_count_convention.c.code == request.day_count_convention)
            .where(m.day_count_convention.c.status == "ACTIVE")
        ).scalar_one_or_none()
        if day_count_convention_id is None:
            raise RepositoryNotFound("Day-count convention does not exist or is not active")
    connection.execute(m.bond_terms.insert().values(
        instrument_node_id=node_id,
        issue_currency_id=request.base_currency_id,
        par_amount=request.par_amount,
        coupon_type=request.coupon_type,
        coupon_rate=request.coupon_rate,
        coupon_frequency_per_year=request.coupon_frequency_per_year,
        day_count_convention_id=day_count_convention_id,
        day_count_convention=request.day_count_convention,
        floating_reference_index=request.floating_reference_index,
        floating_spread=request.floating_spread,
        redemption_amount_per_par=request.redemption_amount_per_par,
        effective_from=request.effective_from,
        is_current=True,
        sequence_no=1,
    ))
    for scheme_code, value in (("ISIN", request.isin), ("FIGI", request.figi), ("SEDOL", request.sedol), ("CUSIP", request.cusip)):
        if value:
            _insert_reference_identifier(connection, node_id, scheme_code, value, request.effective_from)
    return node_id


def decide_bond_proposal(connection: Connection, tenant_id: UUID, actor_id: UUID, proposal_id: UUID, decision: str, reason: str) -> BondProposalView:
    proposal = connection.execute(
        select(m.reference_data_proposal)
        .where(m.reference_data_proposal.c.reference_data_proposal_id == proposal_id)
        .where(m.reference_data_proposal.c.tenant_id == tenant_id)
        .with_for_update()
    ).mappings().first()
    if proposal is None:
        raise RepositoryNotFound("Bond proposal does not exist")
    if proposal.proposal_type != "CREATE_BOND":
        raise InvalidWorkflowState("This endpoint only handles bond creation proposals")
    if proposal.status != "PENDING":
        raise InvalidWorkflowState("Bond proposal has already received a decision")
    payload = json.loads(proposal.proposed_payload)
    request = BondProposalRequest.model_validate(payload)
    instrument_id = None
    if decision == "APPROVED":
        instrument_id = _materialize_bond(connection, tenant_id, actor_id, request)
    now = datetime.now(timezone.utc)
    connection.execute(m.reference_data_approval.insert().values(
        reference_data_proposal_id=proposal_id,
        decision=decision,
        decided_by_user_account_id=actor_id,
        decision_method="MANUAL",
        decision_evidence_json={"manualDecision": True, "reason": reason, "enrichmentStatus": payload.get("enrichmentStatus")},
        decided_at_utc=now,
        reason=reason,
    ))
    connection.execute(m.reference_data_proposal.update().where(m.reference_data_proposal.c.reference_data_proposal_id == proposal_id).values(status=decision, reference_node_id=instrument_id))
    return _bond_view(connection, tenant_id, proposal_id)


def _fx_forward_view(connection: Connection, tenant_id: UUID, proposal_id: UUID) -> FxForwardProposalView:
    """Return the stable, type-specific view used by FX-forward onboarding."""

    proposal = connection.execute(
        select(m.reference_data_proposal)
        .where(m.reference_data_proposal.c.reference_data_proposal_id == proposal_id)
        .where(m.reference_data_proposal.c.tenant_id == tenant_id)
    ).mappings().first()
    if proposal is None:
        raise RepositoryNotFound("FX-forward proposal does not exist")
    payload = json.loads(proposal.proposed_payload)
    request = FxForwardProposalRequest.model_validate(payload)
    return FxForwardProposalView(
        proposalId=proposal.reference_data_proposal_id,
        status=proposal.status,
        proposalType=proposal.proposal_type,
        submissionMode=proposal.submission_mode,
        baseCurrencyId=request.base_currency_id,
        quoteCurrencyId=request.quote_currency_id,
        quoteConvention=request.quote_convention,
        agreedForwardRate=_decimal(request.agreed_forward_rate),
        settlementType=request.settlement_type,
        maturityDate=request.maturity_date,
        instrumentId=proposal.reference_node_id,
        proposedAt=_iso(proposal.proposed_at_utc) or datetime.now(timezone.utc).isoformat(),
    )


def submit_fx_forward_proposal(
    connection: Connection,
    tenant_id: UUID,
    actor_id: UUID,
    request: FxForwardProposalRequest,
) -> FxForwardProposalView:
    """Record one actual OTC FX-forward contract for steward approval.

    The forward is an economic instrument in its own right.  Its rate and
    currency convention live in ``fx_forward_terms`` while maturity and
    settlement dates live in the common ``instrument_dates`` row.  Counterparty
    trade-specific marks are deliberately not materialised here.
    """

    if request.submission_mode == "AUTOMATED" and request.source_system_id is None:
        raise InvalidWorkflowState("Automated FX-forward proposals require sourceSystemId")
    if request.base_currency_id == request.quote_currency_id:
        raise InvalidWorkflowState("Base and quote currencies must be different")
    if request.maturity_date < request.effective_from:
        raise InvalidWorkflowState("Maturity date cannot precede effective date")
    if request.settlement_date is not None and request.settlement_date < request.maturity_date:
        raise InvalidWorkflowState("Settlement date cannot precede maturity date")
    if request.cash_settlement_date is not None and request.cash_settlement_date < request.maturity_date:
        raise InvalidWorkflowState("Cash-settlement date cannot precede maturity date")
    if request.final_settlement_date is not None and request.final_settlement_date < request.maturity_date:
        raise InvalidWorkflowState("Final-settlement date cannot precede maturity date")
    if request.idempotency_key and request.source_system_id:
        existing = connection.execute(
            select(m.reference_data_proposal.c.reference_data_proposal_id)
            .where(m.reference_data_proposal.c.source_system_id == request.source_system_id)
            .where(m.reference_data_proposal.c.idempotency_key == request.idempotency_key)
            .where(m.reference_data_proposal.c.tenant_id == tenant_id)
        ).scalar_one_or_none()
        if existing is not None:
            return _fx_forward_view(connection, tenant_id, existing)
    if request.internal_code:
        duplicate = connection.execute(
            select(m.financial_reference_node.c.reference_node_id)
            .where(m.financial_reference_node.c.internal_code == request.internal_code)
            .where(m.financial_reference_node.c.status == "ACTIVE")
        ).scalar_one_or_none()
        if duplicate is not None:
            raise InvalidWorkflowState("A reference node with this internal code already exists")
    _active_index_catalogue_reference(connection, m.currency, m.currency.c.currency_id, request.base_currency_id, "Base currency")
    _active_index_catalogue_reference(connection, m.currency, m.currency.c.currency_id, request.quote_currency_id, "Quote currency")
    if request.fixing_currency_id is not None:
        _active_index_catalogue_reference(connection, m.currency, m.currency.c.currency_id, request.fixing_currency_id, "Fixing currency")

    payload = request.model_dump(mode="json", by_alias=True, exclude_none=True)
    payload["proposedByUserAccountId"] = str(actor_id)
    proposal_id = connection.execute(
        m.reference_data_proposal.insert().values(
            tenant_id=tenant_id,
            proposal_type="CREATE_FX_FORWARD",
            proposed_payload=json.dumps(payload, sort_keys=True),
            source_payload_id=request.source_payload_id,
            source_system_id=request.source_system_id,
            submission_mode=request.submission_mode,
            idempotency_key=request.idempotency_key,
            match_status="NEW",
            confidence_score=request.confidence_score,
            payload_schema_version="fx-forward.v1",
            status="PENDING",
        ).returning(m.reference_data_proposal.c.reference_data_proposal_id)
    ).scalar_one()
    return _fx_forward_view(connection, tenant_id, proposal_id)


def _materialize_fx_forward(
    connection: Connection,
    tenant_id: UUID,
    actor_id: UUID,
    request: FxForwardProposalRequest,
) -> UUID:
    """Materialise the approved economic FX-forward and its common dates."""

    node_type_id = connection.execute(
        select(m.reference_node_type.c.reference_node_type_id)
        .where(m.reference_node_type.c.type_code == "INSTRUMENT")
        .where(m.reference_node_type.c.status == "ACTIVE")
    ).scalar_one_or_none()
    if node_type_id is None:
        raise RepositoryNotFound("INSTRUMENT reference-node type is not configured")
    instrument_type_id = connection.execute(
        select(m.instrument_type.c.instrument_type_id)
        .where(m.instrument_type.c.type_code == "FX_FORWARD")
        .where(m.instrument_type.c.status == "ACTIVE")
    ).scalar_one_or_none()
    if instrument_type_id is None:
        raise RepositoryNotFound("FX_FORWARD instrument type is not configured")

    node_id = connection.execute(
        m.financial_reference_node.insert().values(
            canonical_name=request.canonical_name,
            internal_code=request.internal_code,
            reference_node_type_id=node_type_id,
            status="ACTIVE",
            is_tradable=True,
        ).returning(m.financial_reference_node.c.reference_node_id)
    ).scalar_one()
    connection.execute(m.instrument.insert().values(
        instrument_node_id=node_id,
        instrument_type_id=instrument_type_id,
        asset_class="FX",
        base_currency_id=request.base_currency_id,
        effective_from=request.effective_from,
        is_current=True,
        sequence_no=1,
    ))
    connection.execute(m.instrument_definition_version.insert().values(
        instrument_node_id=node_id,
        sequence_no=1,
        instrument_type_id=instrument_type_id,
        asset_class="FX",
        base_currency_id=request.base_currency_id,
        effective_from=request.effective_from,
        is_current=True,
        status="APPROVED",
        source_payload_id=request.source_payload_id,
        approved_by_user_account_id=actor_id,
        approved_at_utc=datetime.now(timezone.utc),
    ))
    connection.execute(m.reference_node_scope.insert().values(
        reference_node_id=node_id,
        scope_type="TENANT_PRIVATE",
        owner_tenant_id=tenant_id,
        status="ACTIVE",
    ))
    connection.execute(m.instrument_dates.insert().values(
        instrument_node_id=node_id,
        effective_date=request.effective_from,
        maturity_date=request.maturity_date,
        settlement_date=request.settlement_date,
        cash_settlement_date=request.cash_settlement_date,
        final_settlement_date=request.final_settlement_date or request.cash_settlement_date or request.settlement_date,
    ))
    connection.execute(m.fx_forward_terms.insert().values(
        instrument_node_id=node_id,
        base_currency_id=request.base_currency_id,
        quote_currency_id=request.quote_currency_id,
        quote_convention=request.quote_convention,
        agreed_forward_rate=request.agreed_forward_rate,
        settlement_type=request.settlement_type,
        fixing_currency_id=request.fixing_currency_id,
    ))
    return node_id


def decide_fx_forward_proposal(
    connection: Connection,
    tenant_id: UUID,
    actor_id: UUID,
    proposal_id: UUID,
    decision: str,
    reason: str,
) -> FxForwardProposalView:
    """Record a steward decision and materialise an approved FX forward."""

    proposal = connection.execute(
        select(m.reference_data_proposal)
        .where(m.reference_data_proposal.c.reference_data_proposal_id == proposal_id)
        .where(m.reference_data_proposal.c.tenant_id == tenant_id)
        .with_for_update()
    ).mappings().first()
    if proposal is None:
        raise RepositoryNotFound("FX-forward proposal does not exist")
    if proposal.proposal_type != "CREATE_FX_FORWARD":
        raise InvalidWorkflowState("This endpoint only handles FX-forward creation proposals")
    if proposal.status != "PENDING":
        raise InvalidWorkflowState("FX-forward proposal has already received a decision")
    payload = json.loads(proposal.proposed_payload)
    request = FxForwardProposalRequest.model_validate(payload)
    instrument_id = None
    if decision == "APPROVED":
        instrument_id = _materialize_fx_forward(connection, tenant_id, actor_id, request)
    now = datetime.now(timezone.utc)
    connection.execute(m.reference_data_approval.insert().values(
        reference_data_proposal_id=proposal_id,
        decision=decision,
        decided_by_user_account_id=actor_id,
        decision_method="MANUAL",
        decision_evidence_json={"manualDecision": True, "reason": reason},
        decided_at_utc=now,
        reason=reason,
    ))
    connection.execute(
        m.reference_data_proposal.update()
        .where(m.reference_data_proposal.c.reference_data_proposal_id == proposal_id)
        .values(status=decision, reference_node_id=instrument_id)
    )
    return _fx_forward_view(connection, tenant_id, proposal_id)


def _etp_view(connection: Connection, tenant_id: UUID, proposal_id: UUID) -> EtpProposalView:
    proposal = connection.execute(
        select(m.reference_data_proposal)
        .where(m.reference_data_proposal.c.reference_data_proposal_id == proposal_id)
        .where(m.reference_data_proposal.c.tenant_id == tenant_id)
    ).mappings().first()
    if proposal is None:
        raise RepositoryNotFound("ETP proposal does not exist")
    payload = json.loads(proposal.proposed_payload)
    return EtpProposalView(
        proposalId=proposal.reference_data_proposal_id,
        status=proposal.status,
        proposalType=proposal.proposal_type,
        submissionMode=proposal.submission_mode,
        etpKind=payload["etpKind"],
        instrumentId=proposal.reference_node_id,
        proposedAt=_iso(proposal.proposed_at_utc) or datetime.now(timezone.utc).isoformat(),
    )


def _visible_reference_node(connection: Connection, tenant_id: UUID, reference_node_id: UUID) -> UUID:
    scope = m.reference_node_scope
    visible = connection.execute(
        select(m.financial_reference_node.c.reference_node_id)
        .select_from(
            m.financial_reference_node.outerjoin(
                scope, scope.c.reference_node_id == m.financial_reference_node.c.reference_node_id,
            )
        )
        .where(m.financial_reference_node.c.reference_node_id == reference_node_id)
        .where(m.financial_reference_node.c.status == "ACTIVE")
        .where(_visible_node_clause(tenant_id))
    ).scalar_one_or_none()
    if visible is None:
        raise RepositoryNotFound("Primary reference does not exist, is not active, or is not visible to this tenant")
    return visible


def _etp_relationship_type(etp_kind: str) -> str:
    return {
        "ETF": "TRACKS_INDEX",
        "ETC": "TRACKS_REFERENCE",
        "ETN": "REFERENCES_INDEX",
        "ETV": "REFERENCES_INDEX",
        "ETI": "REFERENCES_INDEX",
    }[etp_kind]


def submit_etp_proposal(connection: Connection, tenant_id: UUID, actor_id: UUID, request: EtpProposalRequest) -> EtpProposalView:
    """Record a sparse ETP proposal; legal and venue data remain separate workflows."""

    if request.submission_mode == "AUTOMATED" and request.source_system_id is None:
        raise InvalidWorkflowState("Automated ETP proposals require sourceSystemId")
    if request.internal_code:
        duplicate = connection.execute(
            select(m.financial_reference_node.c.reference_node_id)
            .where(m.financial_reference_node.c.internal_code == request.internal_code)
            .where(m.financial_reference_node.c.status == "ACTIVE")
        ).scalar_one_or_none()
        if duplicate is not None:
            raise InvalidWorkflowState("A reference node with this internal code already exists")
    if request.issuer_organisation_id is not None:
        _active_index_catalogue_reference(connection, m.organisation, m.organisation.c.organisation_id, request.issuer_organisation_id, "Issuer organisation")
    if request.base_currency_id is not None:
        _active_index_catalogue_reference(connection, m.currency, m.currency.c.currency_id, request.base_currency_id, "Base currency")
    if request.reference_node_id is not None:
        _visible_reference_node(connection, tenant_id, request.reference_node_id)
    payload = request.model_dump(mode="json", by_alias=True, exclude_none=True)
    payload["proposedByUserAccountId"] = str(actor_id)
    proposal_id = connection.execute(
        m.reference_data_proposal.insert().values(
            tenant_id=tenant_id,
            proposal_type="CREATE_ETP",
            proposed_payload=json.dumps(payload, sort_keys=True),
            source_payload_id=request.source_payload_id,
            source_system_id=request.source_system_id,
            submission_mode=request.submission_mode,
            idempotency_key=request.idempotency_key,
            match_status="NEW",
            confidence_score=request.confidence_score,
            payload_schema_version="etp.v1",
            status="PENDING",
        ).returning(m.reference_data_proposal.c.reference_data_proposal_id)
    ).scalar_one()
    return _etp_view(connection, tenant_id, proposal_id)


def _materialize_etp(connection: Connection, tenant_id: UUID, actor_id: UUID, request: EtpProposalRequest) -> UUID:
    node_type_id = connection.execute(
        select(m.reference_node_type.c.reference_node_type_id)
        .where(m.reference_node_type.c.type_code == "INSTRUMENT")
        .where(m.reference_node_type.c.status == "ACTIVE")
    ).scalar_one_or_none()
    instrument_type_id = connection.execute(
        select(m.instrument_type.c.instrument_type_id)
        .where(m.instrument_type.c.type_code == request.etp_kind)
        .where(m.instrument_type.c.status == "ACTIVE")
    ).scalar_one_or_none()
    if node_type_id is None or instrument_type_id is None:
        raise RepositoryNotFound(f"{request.etp_kind} instrument configuration is not active")
    node_id = connection.execute(
        m.financial_reference_node.insert().values(
            canonical_name=request.canonical_name,
            internal_code=request.internal_code,
            reference_node_type_id=node_type_id,
            status="ACTIVE",
            is_tradable=True,
        ).returning(m.financial_reference_node.c.reference_node_id)
    ).scalar_one()
    asset_class = "FUND" if request.etp_kind == "ETF" else "STRUCTURED_PRODUCT"
    instrument_values = dict(
        instrument_node_id=node_id,
        instrument_type_id=instrument_type_id,
        asset_class=asset_class,
        issuer_organisation_id=request.issuer_organisation_id,
        base_currency_id=request.base_currency_id,
        effective_from=request.effective_from,
        is_current=True,
        sequence_no=1,
    )
    connection.execute(m.instrument.insert().values(**instrument_values))
    connection.execute(m.instrument_definition_version.insert().values(
        **instrument_values,
        status="APPROVED",
        source_payload_id=request.source_payload_id,
        approved_by_user_account_id=actor_id,
        approved_at_utc=datetime.now(timezone.utc),
    ))
    connection.execute(m.reference_node_scope.insert().values(
        reference_node_id=node_id, scope_type="TENANT_PRIVATE", owner_tenant_id=tenant_id, status="ACTIVE",
    ))
    connection.execute(m.etp_terms.insert().values(
        instrument_node_id=node_id,
        etp_kind=request.etp_kind,
        legal_form=request.legal_form,
        replication_method=request.replication_method,
        collateralisation_type=request.collateralisation_type,
        redemption_model=request.redemption_model,
        distribution_policy=request.distribution_policy,
        reference_node_id=request.reference_node_id,
        effective_from=request.effective_from,
        is_current=True,
        sequence_no=1,
        status="ACTIVE",
        source_payload_id=request.source_payload_id,
    ))
    if request.reference_node_id is not None:
        connection.execute(m.instrument_relationship.insert().values(
            from_reference_node_id=node_id,
            to_reference_node_id=request.reference_node_id,
            relationship_type=_etp_relationship_type(request.etp_kind),
            effective_from=request.effective_from,
            source_system_id="MANUAL" if request.submission_mode == "MANUAL" else "AUTOMATED",
        ))
    if request.isin:
        _insert_reference_identifier(connection, node_id, "ISIN", request.isin, request.effective_from)
    return node_id


def decide_etp_proposal(connection: Connection, tenant_id: UUID, actor_id: UUID, proposal_id: UUID, decision: str, reason: str) -> EtpProposalView:
    proposal = connection.execute(
        select(m.reference_data_proposal)
        .where(m.reference_data_proposal.c.reference_data_proposal_id == proposal_id)
        .where(m.reference_data_proposal.c.tenant_id == tenant_id)
        .with_for_update()
    ).mappings().first()
    if proposal is None:
        raise RepositoryNotFound("ETP proposal does not exist")
    if proposal.proposal_type != "CREATE_ETP":
        raise InvalidWorkflowState("This endpoint only handles ETP creation proposals")
    if proposal.status != "PENDING":
        raise InvalidWorkflowState("ETP proposal has already received a decision")
    request = EtpProposalRequest.model_validate(json.loads(proposal.proposed_payload))
    instrument_id = _materialize_etp(connection, tenant_id, actor_id, request) if decision == "APPROVED" else None
    now = datetime.now(timezone.utc)
    connection.execute(m.reference_data_approval.insert().values(
        reference_data_proposal_id=proposal_id,
        decision=decision,
        decided_by_user_account_id=actor_id,
        decision_method="MANUAL",
        decision_evidence_json={"manualDecision": True, "reason": reason, "etpKind": request.etp_kind},
        decided_at_utc=now,
        reason=reason,
    ))
    connection.execute(m.reference_data_proposal.update().where(
        m.reference_data_proposal.c.reference_data_proposal_id == proposal_id
    ).values(status=decision, reference_node_id=instrument_id))
    return _etp_view(connection, tenant_id, proposal_id)


def _index_view(connection: Connection, tenant_id: UUID, proposal_id: UUID) -> IndexProposalView:
    proposal = connection.execute(
        select(m.reference_data_proposal)
        .where(m.reference_data_proposal.c.reference_data_proposal_id == proposal_id)
        .where(m.reference_data_proposal.c.tenant_id == tenant_id)
    ).mappings().first()
    if proposal is None:
        raise RepositoryNotFound("Index proposal does not exist")
    payload = json.loads(proposal.proposed_payload)
    return IndexProposalView(
        proposalId=proposal.reference_data_proposal_id,
        status=proposal.status,
        proposalType=proposal.proposal_type,
        submissionMode=proposal.submission_mode,
        indexKind=payload["indexKind"],
        indexId=proposal.reference_node_id,
        proposedAt=_iso(proposal.proposed_at_utc) or datetime.now(timezone.utc).isoformat(),
    )


def _active_index_catalogue_reference(connection: Connection, table, column, value: UUID, label: str) -> None:
    exists_row = connection.execute(
        select(column)
        .select_from(table)
        .where(column == value)
        .where(table.c.status == "ACTIVE")
    ).scalar_one_or_none()
    if exists_row is None:
        raise RepositoryNotFound(f"{label} does not exist or is not active")


def _index_family_view(connection: Connection, tenant_id: UUID, proposal_id: UUID) -> IndexFamilyProposalView:
    proposal = connection.execute(
        select(m.reference_data_proposal)
        .where(m.reference_data_proposal.c.reference_data_proposal_id == proposal_id)
        .where(m.reference_data_proposal.c.tenant_id == tenant_id)
    ).mappings().first()
    if proposal is None:
        raise RepositoryNotFound("Index-family proposal does not exist")
    payload = json.loads(proposal.proposed_payload)
    family_id = None
    if proposal.reference_node_id is not None:
        family_id = connection.execute(
            select(m.index_family.c.index_family_id)
            .where(m.index_family.c.family_node_id == proposal.reference_node_id)
        ).scalar_one_or_none()
    return IndexFamilyProposalView(
        proposalId=proposal.reference_data_proposal_id,
        status=proposal.status,
        proposalType=proposal.proposal_type,
        submissionMode=proposal.submission_mode,
        familyName=payload["canonicalName"],
        familyId=family_id,
        familyNodeId=proposal.reference_node_id,
        proposedAt=_iso(proposal.proposed_at_utc) or datetime.now(timezone.utc).isoformat(),
    )


def _materialize_index_family_record(
    connection: Connection,
    tenant_id: UUID,
    request: IndexFamilyProposalRequest,
) -> tuple[UUID, UUID]:
    family_type_id = connection.execute(
        select(m.reference_node_type.c.reference_node_type_id)
        .where(m.reference_node_type.c.type_code == "INDEX_FAMILY")
        .where(m.reference_node_type.c.status == "ACTIVE")
    ).scalar_one_or_none()
    if family_type_id is None:
        raise RepositoryNotFound("INDEX_FAMILY reference-node type is not configured")
    duplicate = connection.execute(
        select(m.financial_reference_node.c.reference_node_id)
        .where(m.financial_reference_node.c.canonical_name == request.canonical_name)
        .where(m.financial_reference_node.c.reference_node_type_id == family_type_id)
        .where(m.financial_reference_node.c.status == "ACTIVE")
    ).scalar_one_or_none()
    if duplicate is not None:
        raise InvalidWorkflowState("An active index family with this canonical name already exists")
    family_node_id = connection.execute(
        m.financial_reference_node.insert().values(
            reference_node_type_id=family_type_id,
            canonical_name=request.canonical_name,
            internal_code=request.internal_code,
            status="ACTIVE",
            is_tradable=False,
        ).returning(m.financial_reference_node.c.reference_node_id)
    ).scalar_one()
    family_id = connection.execute(
        m.index_family.insert().values(
            family_node_id=family_node_id,
            provider_organisation_id=request.provider_organisation_id,
            status="ACTIVE",
        ).returning(m.index_family.c.index_family_id)
    ).scalar_one()
    connection.execute(
        m.reference_node_scope.insert().values(
            reference_node_id=family_node_id,
            scope_type="TENANT_PRIVATE",
            owner_tenant_id=tenant_id,
            status="ACTIVE",
        )
    )
    return family_id, family_node_id


def submit_index_family_proposal(
    connection: Connection,
    tenant_id: UUID,
    actor_id: UUID,
    request: IndexFamilyProposalRequest,
) -> IndexFamilyProposalView:
    """Record a manual-first proposal for a conceptual index family."""

    if request.submission_mode == "AUTOMATED" and request.source_system_id is None:
        raise InvalidWorkflowState("Automated index-family proposals require sourceSystemId")
    if request.idempotency_key:
        if request.source_system_id is None:
            raise InvalidWorkflowState("idempotencyKey requires sourceSystemId")
        existing = connection.execute(
            select(m.reference_data_proposal.c.reference_data_proposal_id)
            .where(m.reference_data_proposal.c.source_system_id == request.source_system_id)
            .where(m.reference_data_proposal.c.idempotency_key == request.idempotency_key)
            .where(m.reference_data_proposal.c.tenant_id == tenant_id)
        ).scalar_one_or_none()
        if existing is not None:
            return _index_family_view(connection, tenant_id, existing)
    if request.internal_code:
        existing_code = connection.execute(
            select(m.financial_reference_node.c.reference_node_id)
            .where(m.financial_reference_node.c.internal_code == request.internal_code)
            .where(m.financial_reference_node.c.status == "ACTIVE")
        ).scalar_one_or_none()
        if existing_code is not None:
            raise InvalidWorkflowState("A reference node with this internal code already exists")
    if request.provider_organisation_id is not None:
        _active_index_catalogue_reference(
            connection,
            m.organisation,
            m.organisation.c.organisation_id,
            request.provider_organisation_id,
            "Provider organisation",
        )
    payload = request.model_dump(mode="json", by_alias=True, exclude_none=True)
    payload["proposedByUserAccountId"] = str(actor_id)
    proposal_id = connection.execute(
        m.reference_data_proposal.insert().values(
            tenant_id=tenant_id,
            proposal_type="CREATE_INDEX_FAMILY",
            proposed_payload=json.dumps(payload, sort_keys=True),
            source_payload_id=request.source_payload_id,
            source_system_id=request.source_system_id,
            submission_mode=request.submission_mode,
            idempotency_key=request.idempotency_key,
            match_status="NEW",
            confidence_score=request.confidence_score,
            payload_schema_version="index-family.v1",
            status="PENDING",
        ).returning(m.reference_data_proposal.c.reference_data_proposal_id)
    ).scalar_one()
    return _index_family_view(connection, tenant_id, proposal_id)


def decide_index_family_proposal(
    connection: Connection,
    tenant_id: UUID,
    actor_id: UUID,
    proposal_id: UUID,
    decision: str,
    reason: str,
) -> IndexFamilyProposalView:
    """Record a steward decision and materialize an approved index family."""

    proposal = connection.execute(
        select(m.reference_data_proposal)
        .where(m.reference_data_proposal.c.reference_data_proposal_id == proposal_id)
        .where(m.reference_data_proposal.c.tenant_id == tenant_id)
        .with_for_update()
    ).mappings().first()
    if proposal is None:
        raise RepositoryNotFound("Index-family proposal does not exist")
    if proposal.proposal_type != "CREATE_INDEX_FAMILY":
        raise InvalidWorkflowState("This endpoint only handles index-family creation proposals")
    if proposal.status != "PENDING":
        raise InvalidWorkflowState("Index-family proposal has already received a decision")
    payload = json.loads(proposal.proposed_payload)
    request = IndexFamilyProposalRequest.model_validate(payload)
    family_node_id = None
    if decision == "APPROVED":
        _, family_node_id = _materialize_index_family_record(connection, tenant_id, request)
    now = datetime.now(timezone.utc)
    connection.execute(
        m.reference_data_approval.insert().values(
            reference_data_proposal_id=proposal_id,
            decision=decision,
            decided_by_user_account_id=actor_id,
            decision_method="MANUAL",
            decision_evidence_json={"manualDecision": True, "reason": reason},
            decided_at_utc=now,
            reason=reason,
        )
    )
    connection.execute(
        m.reference_data_proposal.update()
        .where(m.reference_data_proposal.c.reference_data_proposal_id == proposal_id)
        .values(status=decision, reference_node_id=family_node_id)
    )
    return _index_family_view(connection, tenant_id, proposal_id)


def _visible_index_family_id(connection: Connection, tenant_id: UUID, family_id: UUID) -> UUID:
    scope = m.reference_node_scope
    row = connection.execute(
        select(m.index_family.c.index_family_id)
        .select_from(
            m.index_family.join(
                m.financial_reference_node,
                m.index_family.c.family_node_id == m.financial_reference_node.c.reference_node_id,
            ).outerjoin(scope, scope.c.reference_node_id == m.index_family.c.family_node_id)
        )
        .where(m.index_family.c.index_family_id == family_id)
        .where(m.index_family.c.status == "ACTIVE")
        .where(m.financial_reference_node.c.status == "ACTIVE")
        .where(
            or_(
                scope.c.reference_node_id.is_(None),
                scope.c.scope_type == "SHARED_CANONICAL",
                and_(scope.c.scope_type == "TENANT_PRIVATE", scope.c.owner_tenant_id == tenant_id),
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise RepositoryNotFound("Index family does not exist, is not active, or is not visible to this tenant")
    return row


def _materialize_index_family(
    connection: Connection,
    tenant_id: UUID,
    request: IndexProposalRequest,
) -> UUID | None:
    if request.index_family_id is not None:
        return _visible_index_family_id(connection, tenant_id, request.index_family_id)
    if not request.index_family_name:
        return None
    family_type_id = connection.execute(
        select(m.reference_node_type.c.reference_node_type_id)
        .where(m.reference_node_type.c.type_code == "INDEX_FAMILY")
        .where(m.reference_node_type.c.status == "ACTIVE")
    ).scalar_one_or_none()
    if family_type_id is None:
        raise RepositoryNotFound("INDEX_FAMILY reference-node type is not configured")
    existing = connection.execute(
        select(m.index_family.c.index_family_id, m.index_family.c.family_node_id)
        .select_from(
            m.index_family.join(
                m.financial_reference_node,
                m.index_family.c.family_node_id == m.financial_reference_node.c.reference_node_id,
            )
        )
        .where(m.index_family.c.status == "ACTIVE")
        .where(m.financial_reference_node.c.status == "ACTIVE")
        .where(m.financial_reference_node.c.canonical_name == request.index_family_name)
    ).mappings().all()
    if len(existing) > 1:
        raise InvalidWorkflowState("More than one active index family matches this family name")
    if existing:
        return existing[0].index_family_id
    family_node_id = connection.execute(
        m.financial_reference_node.insert().values(
            reference_node_type_id=family_type_id,
            canonical_name=request.index_family_name,
            status="ACTIVE",
            is_tradable=False,
        ).returning(m.financial_reference_node.c.reference_node_id)
    ).scalar_one()
    connection.execute(
        m.index_family.insert().values(
            family_node_id=family_node_id,
            provider_organisation_id=request.administrator_organisation_id,
            status="ACTIVE",
        )
    )
    connection.execute(
        m.reference_node_scope.insert().values(
            reference_node_id=family_node_id,
            scope_type="TENANT_PRIVATE",
            owner_tenant_id=tenant_id,
            status="ACTIVE",
        )
    )
    return connection.execute(
        select(m.index_family.c.index_family_id)
        .where(m.index_family.c.family_node_id == family_node_id)
    ).scalar_one()


def _materialize_index(connection: Connection, tenant_id: UUID, actor_id: UUID, request: IndexProposalRequest) -> UUID:
    index_type_id = connection.execute(
        select(m.reference_node_type.c.reference_node_type_id)
        .where(m.reference_node_type.c.type_code == "INDEX")
        .where(m.reference_node_type.c.status == "ACTIVE")
    ).scalar_one_or_none()
    if index_type_id is None:
        raise RepositoryNotFound("INDEX reference-node type is not configured")
    if request.index_family_id is not None:
        _visible_index_family_id(connection, tenant_id, request.index_family_id)
    if request.return_profile_id is not None:
        _active_index_catalogue_reference(connection, m.return_profile, m.return_profile.c.return_profile_id, request.return_profile_id, "Return profile")
    if request.base_currency_id is not None:
        _active_index_catalogue_reference(connection, m.currency, m.currency.c.currency_id, request.base_currency_id, "Base currency")
    for organisation_id, label in (
        (request.administrator_organisation_id, "Administrator organisation"),
        (request.calculation_agent_organisation_id, "Calculation-agent organisation"),
    ):
        if organisation_id is not None:
            _active_index_catalogue_reference(connection, m.organisation, m.organisation.c.organisation_id, organisation_id, label)
    family_id = _materialize_index_family(connection, tenant_id, request)
    node_id = connection.execute(
        m.financial_reference_node.insert().values(
            reference_node_type_id=index_type_id,
            canonical_name=request.canonical_name,
            internal_code=request.internal_code,
            status="ACTIVE",
            is_tradable=False,
        ).returning(m.financial_reference_node.c.reference_node_id)
    ).scalar_one()
    connection.execute(
        m.index_terms.insert().values(
            index_node_id=node_id,
            index_family_id=family_id,
            index_kind=request.index_kind,
            return_profile_id=request.return_profile_id,
            base_currency_id=request.base_currency_id,
            administrator_organisation_id=request.administrator_organisation_id,
            calculation_agent_organisation_id=request.calculation_agent_organisation_id,
            base_date=request.base_date,
            base_level=request.base_level,
            methodology_reference=request.methodology_reference,
            status="ACTIVE",
        )
    )
    methodology_values = {
        "weighting_method": request.weighting_method,
        "rebalance_frequency": request.rebalance_frequency,
        "calculation_frequency": request.calculation_frequency,
        "dividend_treatment": request.dividend_treatment,
        "launch_date": request.launch_date,
        "is_backtested_history": request.is_backtested_history,
        "methodology_document_uri": request.methodology_document_uri,
    }
    if request.methodology_reference or any(value is not None for value in methodology_values.values()):
        connection.execute(
            m.index_methodology_version.insert().values(
                index_node_id=node_id,
                sequence_no=1,
                effective_from=request.effective_from,
                **methodology_values,
                status="APPROVED",
                source_payload_id=request.source_payload_id,
                approved_by_user_account_id=actor_id,
                approved_at_utc=datetime.now(timezone.utc),
            )
        )
    connection.execute(
        m.reference_node_scope.insert().values(
            reference_node_id=node_id,
            scope_type="TENANT_PRIVATE",
            owner_tenant_id=tenant_id,
            status="ACTIVE",
        )
    )
    return node_id


def submit_index_proposal(connection: Connection, tenant_id: UUID, actor_id: UUID, request: IndexProposalRequest) -> IndexProposalView:
    """Record a manual-first index proposal for Operations approval."""

    if request.submission_mode == "AUTOMATED" and request.source_system_id is None:
        raise InvalidWorkflowState("Automated index proposals require sourceSystemId")
    kind_status = connection.execute(
        select(m.index_kind_catalogue.c.status)
        .where(m.index_kind_catalogue.c.index_kind_code == request.index_kind)
    ).scalar_one_or_none()
    if kind_status != "ACTIVE":
        raise InvalidCatalogueValue(f"Index kind {request.index_kind} is not an active governed catalogue value")
    if request.idempotency_key:
        if request.source_system_id is None:
            raise InvalidWorkflowState("idempotencyKey requires sourceSystemId")
        existing = connection.execute(
            select(m.reference_data_proposal.c.reference_data_proposal_id)
            .where(m.reference_data_proposal.c.source_system_id == request.source_system_id)
            .where(m.reference_data_proposal.c.idempotency_key == request.idempotency_key)
            .where(m.reference_data_proposal.c.tenant_id == tenant_id)
        ).scalar_one_or_none()
        if existing is not None:
            return _index_view(connection, tenant_id, existing)
    if request.internal_code:
        existing_code = connection.execute(
            select(m.financial_reference_node.c.reference_node_id)
            .where(m.financial_reference_node.c.internal_code == request.internal_code)
        ).scalar_one_or_none()
        if existing_code is not None:
            raise InvalidWorkflowState("A reference node with this internal code already exists")
    if request.index_family_id is not None:
        _visible_index_family_id(connection, tenant_id, request.index_family_id)
    if request.return_profile_id is not None:
        _active_index_catalogue_reference(connection, m.return_profile, m.return_profile.c.return_profile_id, request.return_profile_id, "Return profile")
    if request.base_currency_id is not None:
        _active_index_catalogue_reference(connection, m.currency, m.currency.c.currency_id, request.base_currency_id, "Base currency")
    for organisation_id, label in (
        (request.administrator_organisation_id, "Administrator organisation"),
        (request.calculation_agent_organisation_id, "Calculation-agent organisation"),
    ):
        if organisation_id is not None:
            _active_index_catalogue_reference(connection, m.organisation, m.organisation.c.organisation_id, organisation_id, label)
    payload = request.model_dump(mode="json", by_alias=True, exclude_none=True)
    payload["proposedByUserAccountId"] = str(actor_id)
    proposal_id = connection.execute(
        m.reference_data_proposal.insert().values(
            tenant_id=tenant_id,
            proposal_type="CREATE_INDEX",
            proposed_payload=json.dumps(payload, sort_keys=True),
            source_payload_id=request.source_payload_id,
            source_system_id=request.source_system_id,
            submission_mode=request.submission_mode,
            idempotency_key=request.idempotency_key,
            match_status="NEW",
            confidence_score=request.confidence_score,
            payload_schema_version="index.v1",
            status="PENDING",
        ).returning(m.reference_data_proposal.c.reference_data_proposal_id)
    ).scalar_one()
    return _index_view(connection, tenant_id, proposal_id)


def decide_index_proposal(connection: Connection, tenant_id: UUID, actor_id: UUID, proposal_id: UUID, decision: str, reason: str) -> IndexProposalView:
    """Record a manual decision and materialize an approved index proposal."""

    proposal = connection.execute(
        select(m.reference_data_proposal)
        .where(m.reference_data_proposal.c.reference_data_proposal_id == proposal_id)
        .where(m.reference_data_proposal.c.tenant_id == tenant_id)
        .with_for_update()
    ).mappings().first()
    if proposal is None:
        raise RepositoryNotFound("Index proposal does not exist")
    if proposal.proposal_type != "CREATE_INDEX":
        raise InvalidWorkflowState("This endpoint only handles index creation proposals")
    if proposal.status != "PENDING":
        raise InvalidWorkflowState("Index proposal has already received a decision")
    payload = json.loads(proposal.proposed_payload)
    request = IndexProposalRequest.model_validate(payload)
    index_id = None
    if decision == "APPROVED":
        index_id = _materialize_index(connection, tenant_id, actor_id, request)
    now = datetime.now(timezone.utc)
    connection.execute(
        m.reference_data_approval.insert().values(
            reference_data_proposal_id=proposal_id,
            decision=decision,
            decided_by_user_account_id=actor_id,
            decision_method="MANUAL",
            decision_evidence_json={"manualDecision": True, "reason": reason},
            decided_at_utc=now,
            reason=reason,
        )
    )
    connection.execute(
        m.reference_data_proposal.update()
        .where(m.reference_data_proposal.c.reference_data_proposal_id == proposal_id)
        .values(status=decision, reference_node_id=index_id)
    )
    return _index_view(connection, tenant_id, proposal_id)


def _structured_product_view(connection: Connection, tenant_id: UUID, proposal_id: UUID) -> StructuredProductProposalView:
    proposal = connection.execute(
        select(m.reference_data_proposal)
        .where(m.reference_data_proposal.c.reference_data_proposal_id == proposal_id)
        .where(m.reference_data_proposal.c.tenant_id == tenant_id)
    ).mappings().first()
    if proposal is None:
        raise RepositoryNotFound("Structured-product proposal does not exist")
    payload = json.loads(proposal.proposed_payload)
    request = AutocallDraftRequest.model_validate(payload)
    approval = connection.execute(
        select(m.reference_data_approval)
        .where(m.reference_data_approval.c.reference_data_proposal_id == proposal_id)
        .order_by(m.reference_data_approval.c.decided_at_utc.desc())
    ).mappings().first()
    evidence = approval.decision_evidence_json if approval else None
    evidence = evidence if isinstance(evidence, dict) else None
    return StructuredProductProposalView(
        proposalId=proposal.reference_data_proposal_id,
        status=proposal.status,
        proposalType=proposal.proposal_type,
        submissionMode=proposal.submission_mode,
        productSubtype=request.product_subtype,
        instrumentId=proposal.reference_node_id,
        termsId=UUID(evidence["termsId"]) if evidence and evidence.get("termsId") else None,
        componentInstrumentIds=[UUID(value) for value in (evidence or {}).get("componentInstrumentIds", [])],
        compositionIds=[UUID(value) for value in (evidence or {}).get("compositionIds", [])],
        conditionGroupIds=[UUID(value) for value in (evidence or {}).get("conditionGroupIds", [])],
        actionIds=[UUID(value) for value in (evidence or {}).get("actionIds", [])],
        initialFixingIds=[UUID(value) for value in (evidence or {}).get("initialFixingIds", [])],
        proposedAt=_iso(proposal.proposed_at_utc) or datetime.now(timezone.utc).isoformat(),
        decisionEvidence=evidence,
    )


def _structured_product_catalogue_reference(connection: Connection, table, column, value: UUID, label: str) -> None:
    """Validate a governed reference used by a structured-product draft."""

    row = connection.execute(
        select(column)
        .select_from(table)
        .where(column == value)
        .where(table.c.status == "ACTIVE")
    ).scalar_one_or_none()
    if row is None:
        raise RepositoryNotFound(f"{label} does not exist or is not active")


def _insert_structured_node(
    connection: Connection,
    node_type_id: UUID,
    canonical_name: str,
    internal_code: str | None,
    *,
    is_tradable: bool,
) -> UUID:
    return connection.execute(
        m.financial_reference_node.insert().values(
            reference_node_type_id=node_type_id,
            canonical_name=canonical_name[:500],
            internal_code=internal_code[:100] if internal_code else None,
            status="ACTIVE",
            is_tradable=is_tradable,
        ).returning(m.financial_reference_node.c.reference_node_id)
    ).scalar_one()


def _materialize_structured_product(
    connection: Connection,
    tenant_id: UUID,
    actor_id: UUID,
    request: AutocallDraftRequest,
) -> dict[str, object]:
    """Materialise one approved draft as a versioned contractual graph.

    The function intentionally creates fresh child option identities for every
    component row.  A parent consolation trigger is represented as a group
    action and does not invent a synthetic underlying or child option.
    """

    node_type_rows = connection.execute(
        select(m.reference_node_type.c.type_code, m.reference_node_type.c.reference_node_type_id)
        .where(m.reference_node_type.c.type_code.in_(["INSTRUMENT"]))
        .where(m.reference_node_type.c.status == "ACTIVE")
    ).all()
    node_type_id = next((row.reference_node_type_id for row in node_type_rows if row.type_code == "INSTRUMENT"), None)
    if node_type_id is None:
        raise RepositoryNotFound("INSTRUMENT reference-node type is not configured")
    instrument_type_rows = connection.execute(
        select(m.instrument_type.c.type_code, m.instrument_type.c.instrument_type_id)
        .where(m.instrument_type.c.type_code.in_(["STRUCTURED_PRODUCT", "OPTION"]))
        .where(m.instrument_type.c.status == "ACTIVE")
    ).all()
    instrument_type_ids = {row.type_code: row.instrument_type_id for row in instrument_type_rows}
    if "STRUCTURED_PRODUCT" not in instrument_type_ids or "OPTION" not in instrument_type_ids:
        raise RepositoryNotFound("STRUCTURED_PRODUCT and OPTION instrument types are required")
    composed_templates = {"VANILLA_SPREAD_KIP", "VANILLA_KIP", "DIGITAL_KIP"}
    maturity_only_templates = composed_templates | {"SUPERTRACKER"}
    coupon_templates = {"AUTOCALL", "AUTOCALL_CONSOLATION", "PHOENIX", "ATHENA", "RANGE_ACCRUAL"}
    is_composed_template = request.product_subtype in composed_templates
    is_maturity_only_template = request.product_subtype in maturity_only_templates
    is_range_accrual = request.product_subtype == "RANGE_ACCRUAL"
    is_supertracker = request.product_subtype == "SUPERTRACKER"

    _structured_product_catalogue_reference(
        connection, m.currency, m.currency.c.currency_id, request.issue_currency_id, "Issue currency"
    )
    _structured_product_catalogue_reference(
        connection, m.market_calendar, m.market_calendar.c.market_calendar_id, request.calendar_id, "Calendar"
    )
    for organisation_id, label in (
        (request.issuer_organisation_id, "Issuer organisation"),
        (request.guarantor_organisation_id, "Guarantor organisation"),
        (request.counterparty_organisation_id, "Counterparty organisation"),
    ):
        if organisation_id is not None:
            _structured_product_catalogue_reference(connection, m.organisation, m.organisation.c.organisation_id, organisation_id, label)
    for underlying in request.underlyings:
        _visible_reference_node(connection, tenant_id, underlying.reference_node_id)

    parent_id = _insert_structured_node(
        connection,
        node_type_id,
        request.canonical_name,
        request.internal_code,
        is_tradable=True,
    )
    connection.execute(
        m.instrument.insert().values(
            instrument_node_id=parent_id,
            instrument_type_id=instrument_type_ids["STRUCTURED_PRODUCT"],
            asset_class="STRUCTURED_PRODUCT",
            issuer_organisation_id=request.issuer_organisation_id,
            base_currency_id=request.issue_currency_id,
            effective_from=request.effective_from,
            is_current=True,
            sequence_no=1,
        )
    )
    connection.execute(
        m.instrument_definition_version.insert().values(
            instrument_node_id=parent_id,
            sequence_no=1,
            instrument_type_id=instrument_type_ids["STRUCTURED_PRODUCT"],
            asset_class="STRUCTURED_PRODUCT",
            issuer_organisation_id=request.issuer_organisation_id,
            base_currency_id=request.issue_currency_id,
            effective_from=request.effective_from,
            is_current=True,
            status="APPROVED",
            source_payload_id=request.source_payload_id,
            approved_by_user_account_id=actor_id,
            approved_at_utc=datetime.now(timezone.utc),
        )
    )
    connection.execute(
        m.reference_node_scope.insert().values(
            reference_node_id=parent_id,
            scope_type="TENANT_PRIVATE",
            owner_tenant_id=tenant_id,
            status="ACTIVE",
        )
    )
    final_payment_date = max(row.payment_date for row in request.rows)
    connection.execute(
        m.instrument_dates.insert().values(
            instrument_node_id=parent_id,
            effective_date=request.effective_from,
            issue_date=request.effective_from,
            maturity_date=request.maturity_date,
            expiry_date=request.maturity_date,
            final_valuation_date=request.maturity_date,
            final_settlement_date=final_payment_date,
        )
    )

    party_roles = (
        (request.issuer_organisation_id, "ISSUER"),
        (request.guarantor_organisation_id, "GUARANTOR"),
        (request.counterparty_organisation_id, "COUNTERPARTY"),
    )
    for organisation_id, role in party_roles:
        if organisation_id is not None:
            connection.execute(
                m.instrument_party_role.insert().values(
                    instrument_node_id=parent_id,
                    organisation_id=organisation_id,
                    role=role,
                    valid_from=request.effective_from,
                    source_payload_id=request.source_payload_id,
                )
            )

    taxonomy_value = connection.execute(
        select(m.taxonomy_value.c.taxonomy_value_id)
        .select_from(m.taxonomy.join(m.taxonomy_value, m.taxonomy_value.c.taxonomy_id == m.taxonomy.c.taxonomy_id))
        .where(m.taxonomy.c.taxonomy_code == "STRUCTURED_PRODUCT_ARCHETYPE")
        .where(m.taxonomy.c.status == "ACTIVE")
        .where(m.taxonomy_value.c.value_code == request.product_subtype)
        .where(m.taxonomy_value.c.status == "ACTIVE")
    ).scalar_one_or_none()
    if taxonomy_value is None:
        raise RepositoryNotFound(f"Structured-product subtype {request.product_subtype} is not configured")
    connection.execute(
        m.instrument_taxonomy_assignment.insert().values(
            instrument_node_id=parent_id,
            taxonomy_value_id=taxonomy_value,
            effective_from=request.effective_from,
            is_primary=True,
            source_system_id=str(request.source_system_id) if request.source_system_id else "STRUCTURED_PRODUCT_WORKFLOW",
        )
    )

    terms_id = connection.execute(
        m.structured_product_terms.insert().values(
            instrument_node_id=parent_id,
            version_no=1,
            effective_from=request.effective_from,
            is_current=True,
            first_autocall_observation_date=None if is_maturity_only_template or is_range_accrual else request.first_autocall_observation_date,
            issue_currency_id=request.issue_currency_id,
            notional_amount=request.notional_amount,
            redemption_currency_id=request.issue_currency_id,
            default_underlying_scope=request.scope,
            status="VALIDATED",
            source_payload_id=request.source_payload_id,
        ).returning(m.structured_product_terms.c.structured_product_terms_id)
    ).scalar_one()

    def create_schedule(
        schedule_type: str,
        schedule_rows: list[AutocallScheduleRowRequest],
    ) -> tuple[UUID, dict[date, UUID]]:
        schedule_id = connection.execute(
            m.schedule.insert().values(
                owner_reference_node_id=parent_id,
                schedule_type=schedule_type,
                calendar_id=request.calendar_id,
                status="ACTIVE",
                source_payload_id=request.source_payload_id,
            ).returning(m.schedule.c.schedule_id)
        ).scalar_one()
        event_ids: dict[date, UUID] = {}
        dates = sorted({row.observation_date for row in schedule_rows})
        for sequence, event_date in enumerate(dates, start=1):
            payment_date = min(
                row.payment_date for row in schedule_rows if row.observation_date == event_date
            )
            event_ids[event_date] = connection.execute(
                m.schedule_event.insert().values(
                    schedule_id=schedule_id,
                    event_sequence=sequence,
                    event_type="OBSERVATION",
                    event_date=event_date,
                    payment_date=payment_date,
                    status="SCHEDULED",
                ).returning(m.schedule_event.c.schedule_event_id)
            ).scalar_one()
        return schedule_id, event_ids

    coupon_rows = [row for row in request.rows if row.condition_role == "COUPON_ELIGIBILITY"] if request.product_subtype in coupon_templates else []
    autocall_rows = [row for row in request.rows if row.condition_role != "COUPON_ELIGIBILITY"]
    # A Phoenix has two explicit contractual cadences. The parent/autocall
    # schedule owns redemption and maturity tests; the coupon schedule owns
    # coupon eligibility/payment periods. The fallback keeps legacy/manual
    # payloads valid when one side has no rows after editing.
    if not autocall_rows:
        autocall_rows = list(request.rows)
    if not coupon_rows and request.product_subtype in coupon_templates:
        coupon_rows = list(request.rows)
    schedule_id, schedule_event_ids = create_schedule("FINAL_VALUATION" if is_maturity_only_template or is_range_accrual else "AUTOCALL_OBSERVATION", autocall_rows)
    if not request.product_subtype in coupon_templates:
        coupon_schedule_id = None
        coupon_schedule_event_ids: dict[date, UUID] = {}
    else:
        coupon_schedule_id, coupon_schedule_event_ids = create_schedule("COUPON_OBSERVATION", coupon_rows)

    if is_range_accrual:
        connection.execute(
            m.structured_product_range_accrual_terms.insert().values(
                structured_product_terms_id=terms_id,
                observation_frequency=request.range_observation_frequency,
                accrual_basis=request.range_accrual_basis,
                non_business_day_rule=request.range_non_business_day_rule,
                lower_level=request.range_lower_level,
                upper_level=request.range_upper_level,
                coupon_rate_per_annum=request.range_coupon_rate_per_annum,
                observation_schedule_id=coupon_schedule_id,
                status="VALIDATED",
                source_payload_id=request.source_payload_id,
            )
        )
    if is_supertracker:
        connection.execute(
            m.structured_product_supertracker_terms.insert().values(
                structured_product_terms_id=terms_id,
                participation_rate=request.supertracker_participation_rate,
                cap_enabled=request.supertracker_include_cap,
                cap_return=request.supertracker_cap_return,
                status="VALIDATED",
                source_payload_id=request.source_payload_id,
            )
        )

    def event_id_for_row(row: AutocallScheduleRowRequest) -> UUID:
        preferred = coupon_schedule_event_ids if row.condition_role == "COUPON_ELIGIBILITY" else schedule_event_ids
        return preferred.get(row.observation_date) or schedule_event_ids.get(row.observation_date) or coupon_schedule_event_ids[row.observation_date]

    composition_ids: list[UUID] = []
    for sequence, underlying in enumerate(request.underlyings, start=1):
        composition_ids.append(
            connection.execute(
                m.instrument_composition.insert().values(
                    parent_instrument_node_id=parent_id,
                    component_reference_node_id=underlying.reference_node_id,
                    composition_role="UNDERLYING",
                    composition_value=1,
                    composition_value_kind="SIGNED_MULTIPLIER",
                    component_sequence=sequence,
                    structured_product_terms_id=terms_id,
                    composition_date=request.effective_from,
                    source_system_id=str(request.source_system_id) if request.source_system_id else "STRUCTURED_PRODUCT_WORKFLOW",
                    source_payload_id=request.source_payload_id,
                ).returning(m.instrument_composition.c.instrument_composition_id)
            ).scalar_one()
        )

    underlying_fixings: dict[UUID, AutocallUnderlyingRequest] = {
        underlying.reference_node_id: underlying for underlying in request.underlyings
    }
    component_instrument_ids: list[UUID] = []
    component_by_row_id: dict[str, tuple[UUID, UUID]] = {}
    option_terms_by_row_id: dict[str, UUID] = {}
    component_rows = [row for row in request.rows if row.row_kind == "COMPONENT"]
    for component_sequence, row in enumerate(component_rows, start=len(composition_ids) + 1):
        underlying = underlying_fixings[row.underlying_reference_node_id]
        child_code = f"{request.internal_code or 'STRUCTURED_PRODUCT'}_COMP_{component_sequence:04d}"
        child_id = _insert_structured_node(
            connection,
            node_type_id,
            f"{request.canonical_name} component {component_sequence}",
            child_code,
            is_tradable=False,
        )
        component_instrument_ids.append(child_id)
        connection.execute(
            m.instrument.insert().values(
                instrument_node_id=child_id,
                instrument_type_id=instrument_type_ids["OPTION"],
                asset_class="EQUITY_DERIVATIVE",
                base_currency_id=request.issue_currency_id,
                effective_from=request.effective_from,
                is_current=True,
                sequence_no=1,
            )
        )
        connection.execute(
            m.instrument_definition_version.insert().values(
                instrument_node_id=child_id,
                sequence_no=1,
                instrument_type_id=instrument_type_ids["OPTION"],
                asset_class="EQUITY_DERIVATIVE",
                base_currency_id=request.issue_currency_id,
                effective_from=request.effective_from,
                is_current=True,
                status="APPROVED",
                source_payload_id=request.source_payload_id,
                approved_by_user_account_id=actor_id,
                approved_at_utc=datetime.now(timezone.utc),
            )
        )
        connection.execute(
            m.reference_node_scope.insert().values(
                reference_node_id=child_id,
                scope_type="TENANT_PRIVATE",
                owner_tenant_id=tenant_id,
                status="ACTIVE",
            )
        )
        option_type = "PUT" if row.option_type == "PUT" or row.condition_role == "CAPITAL_PROTECTION" else (row.option_type if row.option_type in {"CALL", "PUT"} else "CALL")
        strike_percent = row.strike_percent or Decimal("100")
        option_terms_id = connection.execute(
            m.option_terms.insert().values(
                instrument_node_id=child_id,
                version_no=1,
                effective_from=request.effective_from,
                is_current=True,
                status="ACTIVE",
                underlying_reference_node_id=row.underlying_reference_node_id,
                option_type=option_type,
                exercise_style=row.exercise_style or "EUROPEAN",
                strike_value=strike_percent,
                strike_mode="FIXED",
                strike_basis="PERCENT_OF_INITIAL",
                premium_currency_id=request.issue_currency_id,
                settlement_method="CASH",
                settlement_currency_id=request.issue_currency_id,
            ).returning(m.option_terms.c.option_terms_id)
        ).scalar_one()
        option_terms_by_row_id[row.row_id] = option_terms_id
        composition_id = connection.execute(
            m.instrument_composition.insert().values(
                parent_instrument_node_id=parent_id,
                component_reference_node_id=child_id,
                composition_role="PAYOFF_COMPONENT",
                composition_value=row.participation if row.participation is not None else 1,
                composition_value_kind="SIGNED_MULTIPLIER",
                component_sequence=component_sequence,
                structured_product_terms_id=terms_id,
                composition_date=row.observation_date,
                source_system_id=str(request.source_system_id) if request.source_system_id else "STRUCTURED_PRODUCT_WORKFLOW",
                source_payload_id=request.source_payload_id,
            ).returning(m.instrument_composition.c.instrument_composition_id)
        ).scalar_one()
        composition_ids.append(composition_id)
        component_by_row_id[row.row_id] = (child_id, composition_id)
        component_kind = row.component_kind
        payout_rate = row.payout_rate if row.payout_rate is not None else row.coupon_rate
        # A range-accrual row carries eligibility only. The annualised rate is
        # stored in the focused range-terms row and the lifecycle service
        # applies the qualifying-observation fraction. Do not expose that
        # annual rate as a per-event digital payout.
        component_payout_rate = None if is_range_accrual and row.condition_role == "COUPON_ELIGIBILITY" else payout_rate
        is_maturity_component = row.condition_role in {"CAPITAL_PROTECTION", "OPTION_PAYOFF"}
        connection.execute(
            m.structured_product_component_terms.insert().values(
                instrument_composition_id=composition_id,
                component_kind=component_kind,
                payoff_style="OPTION_PAYOFF" if component_kind == "VANILLA_OPTION" else "RATE_OF_NOTIONAL",
                payout_rate=None if component_kind == "VANILLA_OPTION" else component_payout_rate,
                payout_currency_id=None if component_kind == "VANILLA_OPTION" or component_payout_rate is None else request.issue_currency_id,
                payout_basis=None if component_kind == "VANILLA_OPTION" or component_payout_rate is None else "PCT_OF_NOTIONAL",
                payment_timing="ON_MATURITY" if is_maturity_component else "ON_OBSERVATION",
                schedule_id=coupon_schedule_id if row.condition_role == "COUPON_ELIGIBILITY" else schedule_id,
                status="VALIDATED",
                source_payload_id=request.source_payload_id,
            )
        )

    condition_group_ids: list[UUID] = []
    action_ids: list[UUID] = []
    coupon_condition_group_ids: dict[date, UUID] = {}
    grouped_rows: dict[tuple[str, date, str, str], list[AutocallScheduleRowRequest]] = {}
    for row in request.rows:
        grouped_rows.setdefault((row.group_code, row.observation_date, row.condition_role, row.action_code), []).append(row)
    grouped_items = sorted(
        grouped_rows.items(),
        key=lambda item: (
            item[0][1],
            item[0][3] == "FINAL_REDEMPTION",
            item[0][0],
            item[0][2],
            item[0][3],
        ),
    )
    for evaluation_sequence, ((group_code, observation_date, condition_role, action_code), rows) in enumerate(grouped_items, start=1):
        observation_style = rows[0].observation_style or request.observation_style
        condition_group_id = connection.execute(
            m.structured_product_condition_group.insert().values(
                structured_product_terms_id=terms_id,
                group_code=f"{group_code}_{observation_date.isoformat()}_{evaluation_sequence}"[:100],
                observation_style=observation_style,
                schedule_event_id=None if observation_style == "CONTINUOUS" else event_id_for_row(rows[0]),
                # A final redemption is a maturity lifecycle gate, not an
                # underlying predicate.  Its TERMINATE_PARENT action is
                # evaluated only when no earlier parent redemption occurred.
                logical_operator=logical_operator_for_scope(
                    rows[0].condition_scope,
                    has_predicate=not (action_code == "FINAL_REDEMPTION" or condition_role == "OPTION_PAYOFF"),
                ),
                underlying_aggregation=underlying_aggregation_for_scope(
                    rows[0].condition_scope,
                    has_predicate=not (action_code == "FINAL_REDEMPTION" or condition_role == "OPTION_PAYOFF"),
                ),
                underlying_scope=rows[0].condition_scope,
                evaluation_sequence=evaluation_sequence,
                status="VALIDATED",
                source_payload_id=request.source_payload_id,
            ).returning(m.structured_product_condition_group.c.condition_group_id)
        ).scalar_one()
        condition_group_ids.append(condition_group_id)
        if condition_role == "COUPON_ELIGIBILITY":
            coupon_condition_group_ids[observation_date] = condition_group_id
        if action_code != "FINAL_REDEMPTION" and condition_role != "OPTION_PAYOFF":
            rule_sequence = 1
            for row in rows:
                rule_underlyings = [row.underlying_reference_node_id] if row.underlying_reference_node_id else [item.reference_node_id for item in request.underlyings]
                for underlying_id in rule_underlyings:
                    lower = row.condition_lower_level if row.condition_operator in {"BETWEEN", "OUTSIDE"} else row.condition_level
                    upper = row.condition_upper_level if row.condition_operator in {"BETWEEN", "OUTSIDE"} else None
                    connection.execute(
                        m.barrier_rule.insert().values(
                            condition_group_id=condition_group_id,
                            owner_reference_node_id=component_by_row_id[row.row_id][0] if row.row_kind == "COMPONENT" else parent_id,
                            underlying_reference_node_id=underlying_id,
                            condition_sequence=rule_sequence,
                            comparison_operator=row.condition_operator,
                            level_reference_type=row.condition_level_basis,
                            lower_level_value=lower,
                            upper_level_value=upper,
                            lower_bound_inclusive=row.condition_lower_inclusive,
                            upper_bound_inclusive=row.condition_upper_inclusive,
                            underlying_measure="OFFICIAL_CLOSE",
                            status="VALIDATED",
                            source_payload_id=request.source_payload_id,
                        )
                    )
                    rule_sequence += 1
        if action_code == "PAY_COMPONENT":
            # For a best-/worst-of coupon or KIP, the rows are underlying
            # members of one aggregate predicate. Emit one parent-level
            # payment action so the amount is not multiplied by the number of
            # names. Independent option-payoff legs remain component actions.
            aggregate_pay_once = aggregate_pay_once_for_group(
                rows[0].condition_scope,
                rows[0].condition_role,
                action_code,
            )
            action_rows = rows[:1] if aggregate_pay_once else rows
            for row in action_rows:
                child_id, composition_id = component_by_row_id[row.row_id]
                action_ids.append(
                    connection.execute(
                        m.condition_group_action.insert().values(
                            condition_group_id=condition_group_id,
                            action_type="PAY_COMPONENT",
                            target_scope="PARENT" if aggregate_pay_once else "COMPONENT",
                            target_reference_node_id=parent_id if aggregate_pay_once else child_id,
                            target_composition_id=None if aggregate_pay_once else composition_id,
                            payment_rate=None if is_range_accrual and row.condition_role == "COUPON_ELIGIBILITY" else (row.payout_rate if row.payout_rate is not None else row.coupon_rate),
                            payment_currency_id=request.issue_currency_id if not (is_range_accrual and row.condition_role == "COUPON_ELIGIBILITY") and (row.payout_rate is not None or row.coupon_rate is not None) else None,
                            payment_basis="PCT_OF_NOTIONAL" if not (is_range_accrual and row.condition_role == "COUPON_ELIGIBILITY") and (row.payout_rate is not None or row.coupon_rate is not None) else None,
                            payment_timing="ON_MATURITY" if row.condition_role in {"CAPITAL_PROTECTION", "OPTION_PAYOFF"} else "ON_OBSERVATION",
                            payment_schedule_id=coupon_schedule_id if row.condition_role == "COUPON_ELIGIBILITY" else schedule_id,
                            payment_date=row.payment_date,
                            payout_multiplicity=payout_multiplicity_for_group(
                                rows[0].condition_scope,
                                rows[0].condition_role,
                                action_code,
                            ),
                            execution_sequence=10 + len(action_ids),
                            status="VALIDATED",
                            source_payload_id=request.source_payload_id,
                        ).returning(m.condition_group_action.c.condition_group_action_id)
                    ).scalar_one()
                )
        elif action_code == "REDEEM_PARENT":
            action_ids.append(
                connection.execute(
                    m.condition_group_action.insert().values(
                        condition_group_id=condition_group_id,
                        action_type="REDEEM_PARENT",
                        target_scope="PARENT",
                        target_reference_node_id=parent_id,
                        payment_timing="ON_AUTOCALL",
                        payment_schedule_id=schedule_id,
                        payment_date=rows[0].payment_date,
                        payout_multiplicity="ONCE_PER_PARENT",
                        execution_sequence=20,
                        status="VALIDATED",
                        source_payload_id=request.source_payload_id,
                    ).returning(m.condition_group_action.c.condition_group_action_id)
                ).scalar_one()
            )
        elif action_code == "FINAL_REDEMPTION":
            action_ids.append(
                connection.execute(
                    m.condition_group_action.insert().values(
                        condition_group_id=condition_group_id,
                        action_type="TERMINATE_PARENT",
                        target_scope="PARENT",
                        target_reference_node_id=parent_id,
                        payment_timing="ON_MATURITY",
                        payment_schedule_id=schedule_id,
                        payment_date=rows[0].payment_date,
                        payout_multiplicity="ONCE_PER_PARENT",
                        execution_sequence=20,
                        status="VALIDATED",
                        source_payload_id=request.source_payload_id,
                    ).returning(m.condition_group_action.c.condition_group_action_id)
                ).scalar_one()
            )
        elif action_code == "PAY_CONSOLATION":
            row = rows[0]
            action_ids.append(
                connection.execute(
                    m.condition_group_action.insert().values(
                        condition_group_id=condition_group_id,
                        action_type="PAY_CONSOLATION",
                        target_scope="PARENT",
                        target_reference_node_id=parent_id,
                        payment_rate=row.payout_rate,
                        payment_currency_id=request.issue_currency_id,
                        payment_basis="PCT_OF_MAX_PAYOFF",
                        payment_timing="ON_MATURITY",
                        payment_schedule_id=schedule_id,
                        payment_date=row.payment_date,
                        payout_multiplicity="ONCE_PER_PARENT",
                        execution_sequence=20,
                        status="VALIDATED",
                        source_payload_id=request.source_payload_id,
                    ).returning(m.condition_group_action.c.condition_group_action_id)
                ).scalar_one()
            )

    coupon_programme_id: UUID | None = None
    if coupon_rows:
        coupon_programme_id = connection.execute(
            m.structured_product_coupon_programme.insert().values(
                structured_product_terms_id=terms_id,
                programme_code="MAIN_COUPON",
                payment_mode="PERIODIC",
                memory_mode=request.memory_mode,
                coupon_currency_id=request.issue_currency_id,
                # Generic coupon rates are per-period values. Range accrual
                # stores its annualised rate only in the focused terms table;
                # the lifecycle service applies the qualifying fraction.
                default_coupon_rate=None if is_range_accrual else request.coupon_rate,
                schedule_id=coupon_schedule_id,
                final_payment_treatment=request.final_payment_treatment,
                status="VALIDATED",
                source_payload_id=request.source_payload_id,
            ).returning(m.structured_product_coupon_programme.c.coupon_programme_id)
        ).scalar_one()
        coupon_dates = sorted({row.observation_date for row in coupon_rows})
        for period_sequence, observation_date in enumerate(coupon_dates, start=1):
            period_rows = [row for row in coupon_rows if row.observation_date == observation_date]
            connection.execute(
                m.structured_product_coupon_period.insert().values(
                    coupon_programme_id=coupon_programme_id,
                    period_sequence=period_sequence,
                    observation_event_id=coupon_schedule_event_ids[observation_date],
                    payment_date=min(row.payment_date for row in period_rows),
                    eligibility_condition_group_id=coupon_condition_group_ids.get(observation_date),
                    # A range-accrual period carries the eligibility window,
                    # not a per-period coupon rate. Its annualised rate lives
                    # in secm.structured_product_range_accrual_terms.
                    coupon_rate=None if is_range_accrual else request.coupon_rate,
                    memory_eligible=request.memory_mode != "NONE",
                    status="VALIDATED",
                    source_payload_id=request.source_payload_id,
                )
            )

    initial_fixing_ids: list[UUID] = []
    initial_fixing_id_by_underlying: dict[UUID, UUID] = {}
    for underlying in request.underlyings:
        fixing_id = connection.execute(
            m.structured_product_initial_fixing.insert().values(
                structured_product_terms_id=terms_id,
                underlying_reference_node_id=underlying.reference_node_id,
                fixing_date=underlying.fixing_date,
                fixing_value=underlying.initial_fixing,
                fixing_basis=underlying.fixing_basis,
                fixing_source=underlying.fixing_source,
                market_data_observation_id=underlying.market_data_observation_id,
                market_data_resolution_snapshot_id=underlying.market_data_resolution_snapshot_id,
                source_system_id=underlying.source_system_id or request.source_system_id,
                source_payload_id=underlying.source_payload_id or request.source_payload_id,
                status="ACCEPTED",
            ).returning(m.structured_product_initial_fixing.c.structured_product_initial_fixing_id)
        ).scalar_one()
        initial_fixing_ids.append(fixing_id)
        initial_fixing_id_by_underlying[underlying.reference_node_id] = fixing_id
    for row_id, option_terms_id in option_terms_by_row_id.items():
        row = next(item for item in component_rows if item.row_id == row_id)
        fixing_id = initial_fixing_id_by_underlying[row.underlying_reference_node_id]
        connection.execute(
            m.option_terms.update()
            .where(m.option_terms.c.option_terms_id == option_terms_id)
            .values(strike_reference_initial_fixing_id=fixing_id)
        )
    return {
        "parentId": str(parent_id),
        "termsId": str(terms_id),
        "componentInstrumentIds": [str(value) for value in component_instrument_ids],
        "compositionIds": [str(value) for value in composition_ids],
        "conditionGroupIds": [str(value) for value in condition_group_ids],
        "actionIds": [str(value) for value in action_ids],
        "initialFixingIds": [str(value) for value in initial_fixing_ids],
        "scheduleId": str(schedule_id),
        "couponScheduleId": str(coupon_schedule_id),
        "couponProgrammeId": str(coupon_programme_id) if coupon_programme_id else None,
    }


def submit_structured_product_proposal(
    connection: Connection,
    tenant_id: UUID,
    actor_id: UUID,
    request: AutocallDraftRequest,
) -> StructuredProductProposalView:
    """Validate and persist a structured-product draft for steward review."""

    request = validate_autocall_draft(request)
    if request.submission_mode == "AUTOMATED" and request.source_system_id is None:
        raise InvalidWorkflowState("Automated structured-product proposals require sourceSystemId")
    if request.idempotency_key:
        if request.source_system_id is None:
            raise InvalidWorkflowState("idempotencyKey requires sourceSystemId")
        existing = connection.execute(
            select(m.reference_data_proposal.c.reference_data_proposal_id)
            .where(m.reference_data_proposal.c.source_system_id == request.source_system_id)
            .where(m.reference_data_proposal.c.idempotency_key == request.idempotency_key)
            .where(m.reference_data_proposal.c.tenant_id == tenant_id)
        ).scalar_one_or_none()
        if existing is not None:
            return _structured_product_view(connection, tenant_id, existing)
    if request.internal_code:
        duplicate = connection.execute(
            select(m.financial_reference_node.c.reference_node_id)
            .where(m.financial_reference_node.c.internal_code == request.internal_code)
            .where(m.financial_reference_node.c.status == "ACTIVE")
        ).scalar_one_or_none()
        if duplicate is not None:
            raise InvalidWorkflowState("A reference node with this internal code already exists")
    _structured_product_catalogue_reference(connection, m.currency, m.currency.c.currency_id, request.issue_currency_id, "Issue currency")
    _structured_product_catalogue_reference(connection, m.market_calendar, m.market_calendar.c.market_calendar_id, request.calendar_id, "Calendar")
    for underlying in request.underlyings:
        _visible_reference_node(connection, tenant_id, underlying.reference_node_id)
    if request.source_system_id is not None:
        _structured_product_catalogue_reference(
            connection,
            m.integration_source_system,
            m.integration_source_system.c.integration_source_system_id,
            request.source_system_id,
            "Source system",
        )
    payload = request.model_dump(mode="json", by_alias=True, exclude_none=True)
    payload["proposedByUserAccountId"] = str(actor_id)
    proposal_id = connection.execute(
        m.reference_data_proposal.insert().values(
            tenant_id=tenant_id,
            proposal_type="CREATE_STRUCTURED_PRODUCT",
            proposed_payload=json.dumps(payload, sort_keys=True),
            source_payload_id=request.source_payload_id,
            source_system_id=request.source_system_id,
            submission_mode=request.submission_mode,
            idempotency_key=request.idempotency_key,
            match_status="NEW",
            confidence_score=request.confidence_score,
            payload_schema_version="structured-product.v1",
            status="PENDING",
        ).returning(m.reference_data_proposal.c.reference_data_proposal_id)
    ).scalar_one()
    return _structured_product_view(connection, tenant_id, proposal_id)


def decide_structured_product_proposal(
    connection: Connection,
    tenant_id: UUID,
    actor_id: UUID,
    proposal_id: UUID,
    decision: str,
    reason: str,
) -> StructuredProductProposalView:
    """Record a steward decision and atomically materialise an approved graph."""

    proposal = connection.execute(
        select(m.reference_data_proposal)
        .where(m.reference_data_proposal.c.reference_data_proposal_id == proposal_id)
        .where(m.reference_data_proposal.c.tenant_id == tenant_id)
        .with_for_update()
    ).mappings().first()
    if proposal is None:
        raise RepositoryNotFound("Structured-product proposal does not exist")
    if proposal.proposal_type != "CREATE_STRUCTURED_PRODUCT":
        raise InvalidWorkflowState("This endpoint only handles structured-product creation proposals")
    if proposal.status != "PENDING":
        raise InvalidWorkflowState("Structured-product proposal has already received a decision")
    request = validate_autocall_draft(AutocallDraftRequest.model_validate(json.loads(proposal.proposed_payload)))
    graph: dict[str, object] = {}
    if decision == "APPROVED":
        graph = _materialize_structured_product(connection, tenant_id, actor_id, request)
    evidence = {"manualDecision": True, "reason": reason, **graph}
    now = datetime.now(timezone.utc)
    connection.execute(
        m.reference_data_approval.insert().values(
            reference_data_proposal_id=proposal_id,
            decision=decision,
            decided_by_user_account_id=actor_id,
            decision_method="MANUAL",
            decision_evidence_json=evidence,
            decided_at_utc=now,
            reason=reason,
        )
    )
    connection.execute(
        m.reference_data_proposal.update()
        .where(m.reference_data_proposal.c.reference_data_proposal_id == proposal_id)
        .values(status=decision, reference_node_id=UUID(graph["parentId"]) if graph.get("parentId") else None)
    )
    return _structured_product_view(connection, tenant_id, proposal_id)


def work_queue(connection: Connection, tenant_id: UUID, api_version: str, correlation_id: str) -> WorkQueueView:
    from .contracts import ApiMeta

    items: list[WorkQueueItemView] = []
    proposals = connection.execute(
        select(
            m.reference_data_proposal.c.reference_data_proposal_id,
            m.reference_data_proposal.c.proposal_type,
            m.reference_data_proposal.c.proposed_payload,
            m.reference_data_proposal.c.proposed_at_utc,
        )
        .where(m.reference_data_proposal.c.tenant_id == tenant_id)
        .where(m.reference_data_proposal.c.status == "PENDING")
        .order_by(m.reference_data_proposal.c.proposed_at_utc)
    ).mappings().all()
    import json

    for proposal in proposals:
        payload = json.loads(proposal.proposed_payload)
        # All canonical creation workflows belong in the reference-data review
        # queue. Treating one as a mapping makes the proposal look unrelated to
        # its approval endpoint and hides the steward action that is required.
        is_reference_create = proposal.proposal_type in {
            "CREATE",
            "CREATE_LISTING",
            "CREATE_BOND",
            "CREATE_CRYPTO_ASSET",
            "CREATE_INDEX",
            "CREATE_INDEX_FAMILY",
            "CREATE_ETP",
            "CREATE_FX_FORWARD",
            "CREATE_STRUCTURED_PRODUCT",
        }
        if proposal.proposal_type == "CREATE_LISTING":
            listing_payload = payload.get("listing", {})
            title = f"Review listing · {listing_payload.get('tradingSymbol', 'new listing')}"
            detail = (
                f"{payload.get('submissionMode', 'MANUAL')} listing proposal · "
                f"parent instrument {payload.get('instrumentId', 'not supplied')}"
            )
        elif proposal.proposal_type == "CREATE_BOND":
            title = f"Review bond · {payload.get('canonicalName', 'new bond')}"
            detail = (
                f"{payload.get('submissionMode', 'MANUAL')} bond proposal · "
                f"{payload.get('couponType', 'unknown coupon type')} · "
                f"{payload.get('enrichmentStatus', 'PENDING_ENRICHMENT')}"
            )
        elif proposal.proposal_type == "CREATE_CRYPTO_ASSET":
            title = f"Review cryptoasset · {payload.get('canonicalName', 'new cryptoasset')}"
            detail = (
                f"{payload.get('submissionMode', 'MANUAL')} cryptoasset proposal · "
                f"{payload.get('nativeSymbol', 'no symbol')} · {payload.get('assetSubtype', 'unknown subtype')}"
            )
        elif proposal.proposal_type == "CREATE_INDEX_FAMILY":
            title = f"Review index family · {payload.get('canonicalName', 'new family')}"
            detail = f"{payload.get('submissionMode', 'MANUAL')} conceptual family proposal"
        elif proposal.proposal_type == "CREATE_ETP":
            title = f"Review {payload.get('etpKind', 'ETP')} · {payload.get('canonicalName', 'new exchange-traded product')}"
            detail = f"{payload.get('submissionMode', 'MANUAL')} economic product proposal · listing is a separate workflow"
        elif proposal.proposal_type == "CREATE_INDEX":
            title = f"Review index · {payload.get('canonicalName', 'new index')}"
            detail = f"{payload.get('submissionMode', 'MANUAL')} concrete index variant · {payload.get('indexKind', 'unknown kind')}"
        elif proposal.proposal_type == "CREATE_FX_FORWARD":
            title = f"Review FX forward · {payload.get('canonicalName', 'new FX forward')}"
            detail = (
                f"{payload.get('submissionMode', 'MANUAL')} OTC FX-forward proposal · "
                f"{payload.get('quoteConvention', 'unknown convention')} · "
                f"matures {payload.get('maturityDate', 'date not supplied')}"
            )
        elif proposal.proposal_type == "CREATE_STRUCTURED_PRODUCT":
            title = f"Review {payload.get('productSubtype', 'structured product').replace('_', ' ').lower()} · {payload.get('canonicalName', 'new structured product')}"
            detail = (
                f"{payload.get('submissionMode', 'MANUAL')} structured-product proposal · "
                f"{len(payload.get('underlyings', []))} underlyings · "
                f"{len(payload.get('rows', []))} schedule rows"
            )
        elif is_reference_create:
            title = f"Review {payload.get('canonicalName', 'reference-data create')}"
            detail = f"{payload.get('submissionMode', 'MANUAL')} equity proposal · {payload.get('isin', 'no ISIN')}"
        else:
            title = f"Verify {payload.get('externalId', 'external mapping')}"
            detail = f"{payload.get('namespace', 'unknown namespace')} → {payload.get('targetObjectId', '')}"
        items.append(
            WorkQueueItemView(
                itemId=f"reference:{proposal.reference_data_proposal_id}" if is_reference_create else f"mapping:{proposal.reference_data_proposal_id}",
                category="REFERENCE_DATA_REVIEW" if is_reference_create else "MAPPING_REVIEW",
                title=title,
                detail=detail,
                status="PENDING",
                proposalType=proposal.proposal_type,
                proposedAt=_iso(proposal.proposed_at_utc),
                submittedByUserAccountId=payload.get("proposedByUserAccountId"),
                referenceId=proposal.reference_data_proposal_id,
                reviewPath=(
                    f"/reference-data/review/{proposal.reference_data_proposal_id}"
                    if proposal.proposal_type in {
                        "IDENTIFIER_MAPPING",
                        "CREATE",
                        "CREATE_LISTING",
                        "CREATE_BOND",
                        "CREATE_CRYPTO_ASSET",
                        "CREATE_INDEX",
                        "CREATE_INDEX_FAMILY",
                        "CREATE_ETP",
                        "CREATE_FX_FORWARD",
                        "CREATE_STRUCTURED_PRODUCT",
                    }
                    else None
                ),
            )
        )
    nav_runs = connection.execute(
        select(m.nav_calculation_run.c.nav_calculation_run_id, m.nav_calculation_run.c.valuation_date)
        .where(m.nav_calculation_run.c.tenant_id == tenant_id)
        .where(m.nav_calculation_run.c.status.in_(["DRAFT", "REVIEW", "PENDING_REVIEW"]))
        .order_by(m.nav_calculation_run.c.valuation_date)
    ).mappings().all()
    for run in nav_runs:
        items.append(
            WorkQueueItemView(
                itemId=f"nav:{run.nav_calculation_run_id}",
                category="NAV_REVIEW",
                title=f"Soft-NAV review {run.valuation_date}",
                detail="Valuation run is awaiting review or approval.",
                status="PENDING",
                referenceId=run.nav_calculation_run_id,
            )
        )
    from collections import Counter

    counts = Counter(item.category for item in items)
    return WorkQueueView(
        counts={key: counts.get(key, 0) for key in ["MAPPING_REVIEW", "REFERENCE_DATA_REVIEW", "NAV_REVIEW", "MARKET_DATA_EXCEPTION"]},
        items=items,
        meta=ApiMeta(tenantContext=str(tenant_id), source="live-reference-api", apiVersion=api_version, correlationId=correlation_id),
    )


def list_market_data_series(
    connection: Connection,
    tenant_id: UUID,
    from_date: date | None,
    to_date: date | None,
    reference_node_id: UUID | None,
    series_type: str | None,
    limit: int,
    offset: int,
    api_version: str,
    correlation_id: str,
) -> MarketDataSeriesResponse:
    """Return a catalogue of precise series with a bounded observation window."""
    series = m.market_data_series
    observation = m.market_data_observation
    dataset = m.dataset
    product = m.provider_product
    provider = m.data_provider
    currency = m.currency.alias("series_currency")
    cut = m.valuation_cut
    entitlement = m.tenant_dataset_entitlement
    licence = m.data_licence
    assignment = m.dataset_licence_assignment
    reference_node = m.financial_reference_node.alias("series_reference_node")
    expected_calendar = m.market_calendar.alias("series_expected_calendar")
    filters = [series.c.status == "ACTIVE"]
    if reference_node_id is not None:
        filters.append(series.c.reference_node_id == reference_node_id)
    if series_type:
        filters.append(series.c.series_type == series_type)
    if from_date or to_date:
        obs_exists = select(1).select_from(observation).where(observation.c.market_data_series_id == series.c.market_data_series_id)
        if from_date:
            obs_exists = obs_exists.where(observation.c.market_date >= from_date)
        if to_date:
            obs_exists = obs_exists.where(observation.c.market_date <= to_date)
        filters.append(exists(obs_exists))
    rows = connection.execute(
        select(
            series.c.market_data_series_id,
            series.c.reference_node_id,
            reference_node.c.canonical_name.label("reference_node_name"),
            series.c.series_type,
            series.c.value_type,
            currency.c.currency_code,
            provider.c.data_provider_id,
            provider.c.provider_code,
            provider.c.display_name.label("provider_name"),
            dataset.c.dataset_id,
            dataset.c.dataset_code,
            dataset.c.display_name.label("dataset_name"),
            cut.c.cut_code,
            cut.c.timezone_name,
            series.c.expected_frequency_code,
            series.c.expected_market_calendar_id,
            expected_calendar.c.calendar_code.label("expected_calendar_code"),
            series.c.coverage_start_date,
            series.c.coverage_end_date,
        )
        .select_from(
            series.outerjoin(currency, series.c.currency_id == currency.c.currency_id)
            .join(reference_node, series.c.reference_node_id == reference_node.c.reference_node_id)
            .outerjoin(dataset, series.c.default_dataset_id == dataset.c.dataset_id)
            .outerjoin(product, dataset.c.provider_product_id == product.c.provider_product_id)
            .outerjoin(provider, product.c.data_provider_id == provider.c.data_provider_id)
            .outerjoin(cut, series.c.valuation_cut_id == cut.c.valuation_cut_id)
            .outerjoin(expected_calendar, series.c.expected_market_calendar_id == expected_calendar.c.market_calendar_id)
        )
        .where(*filters)
        .where(
            or_(
                series.c.default_dataset_id.is_(None),
                exists(
                    select(1)
                    .select_from(entitlement)
                    .where(entitlement.c.tenant_id == tenant_id)
                    .where(entitlement.c.dataset_id == series.c.default_dataset_id)
                    .where(entitlement.c.status == "ACTIVE")
                    .where(entitlement.c.valid_from <= date.today())
                    .where(or_(entitlement.c.valid_to.is_(None), entitlement.c.valid_to >= date.today())),
                ),
            )
        )
        .order_by(series.c.series_type, series.c.market_data_series_id)
        .offset(offset)
        .limit(limit)
    ).mappings().all()
    result: list[MarketDataSeriesView] = []
    for row in rows:
        obs_filters = [observation.c.market_data_series_id == row.market_data_series_id, observation.c.quality_status == "ACCEPTED"]
        if from_date:
            obs_filters.append(observation.c.market_date >= from_date)
        if to_date:
            obs_filters.append(observation.c.market_date <= to_date)
        observation_dataset = m.dataset.alias("observation_dataset")
        observation_product = m.provider_product.alias("observation_product")
        observation_provider = m.data_provider.alias("observation_provider")
        vintage = m.market_data_vintage
        obs_rows = connection.execute(
            select(
                observation.c.market_data_observation_id,
                observation.c.market_date,
                observation.c.observed_at_utc,
                observation.c.received_at_utc,
                observation.c.value,
                observation.c.value_basis,
                observation.c.quality_status,
                observation.c.acquisition_licence_id,
                licence.c.licence_code,
                licence.c.display_name.label("licence_name"),
                observation.c.dataset_id,
                observation_dataset.c.dataset_code,
                observation_provider.c.data_provider_id,
                observation_provider.c.provider_code,
                observation.c.market_data_vintage_id,
                vintage.c.source_vintage_key,
                observation.c.source_published_at_utc,
                observation.c.source_observation_key,
            )
            .select_from(
                observation.join(observation_dataset, observation.c.dataset_id == observation_dataset.c.dataset_id)
                .outerjoin(observation_product, observation_dataset.c.provider_product_id == observation_product.c.provider_product_id)
                .outerjoin(observation_provider, observation_product.c.data_provider_id == observation_provider.c.data_provider_id)
                .outerjoin(vintage, observation.c.market_data_vintage_id == vintage.c.market_data_vintage_id)
                .outerjoin(licence, observation.c.acquisition_licence_id == licence.c.data_licence_id)
            )
            .where(*obs_filters)
            .where(
                exists(
                    select(1)
                    .select_from(entitlement)
                    .where(entitlement.c.tenant_id == tenant_id)
                    .where(entitlement.c.dataset_id == observation.c.dataset_id)
                    .where(entitlement.c.status == "ACTIVE")
                    .where(entitlement.c.valid_from <= date.today())
                    .where(or_(entitlement.c.valid_to.is_(None), entitlement.c.valid_to >= date.today())),
                )
            )
            .order_by(observation.c.market_date)
            .limit(1000)
        ).mappings().all()
        first_licence = next((item for item in obs_rows if item.acquisition_licence_id), None)
        result.append(
            MarketDataSeriesView(
                seriesId=row.market_data_series_id,
                referenceNodeId=row.reference_node_id,
                referenceNodeName=row.reference_node_name,
                seriesType=row.series_type,
                valueType=row.value_type,
                currency=row.currency_code,
                providerId=row.data_provider_id,
                providerCode=row.provider_code,
                providerName=row.provider_name,
                datasetId=row.dataset_id,
                datasetCode=row.dataset_code,
                datasetName=row.dataset_name,
                licenceId=first_licence.acquisition_licence_id if first_licence else None,
                licenceCode=first_licence.licence_code if first_licence else None,
                licenceName=first_licence.licence_name if first_licence else None,
                valuationCut=row.cut_code,
                timezoneName=row.timezone_name,
                expectedFrequency=row.expected_frequency_code,
                expectedCalendarId=row.expected_market_calendar_id,
                expectedCalendarCode=row.expected_calendar_code,
                coverageStartDate=_iso(row.coverage_start_date),
                coverageEndDate=_iso(row.coverage_end_date),
                observations=[
                    MarketDataObservationView(
                        observationId=item.market_data_observation_id,
                        marketDate=_iso(item.market_date),
                        observedAt=_iso(item.observed_at_utc) or "",
                        receivedAt=_iso(item.received_at_utc) or "",
                        value=_decimal(item.value),
                        valueBasis=item.value_basis,
                        qualityStatus=item.quality_status,
                        providerId=item.data_provider_id,
                        providerCode=item.provider_code,
                        datasetId=item.dataset_id,
                        datasetCode=item.dataset_code,
                        licenceId=item.acquisition_licence_id,
                        licenceCode=item.licence_code,
                        vintageId=item.market_data_vintage_id,
                        vintageKey=item.source_vintage_key,
                        sourcePublishedAt=_iso(item.source_published_at_utc),
                        sourceObservationKey=item.source_observation_key,
                    )
                    for item in obs_rows
                ],
            )
        )
    return MarketDataSeriesResponse(
        data=result,
        meta=ApiMeta(tenantContext=str(tenant_id), source="live-reference-api", apiVersion=api_version, correlationId=correlation_id, limit=limit, offset=offset, total=len(result)),
    )


def _latest_observation(connection: Connection, series_id: UUID, as_of: date | None) -> object | None:
    observation = m.market_data_observation
    stmt = select(observation).where(observation.c.market_data_series_id == series_id).where(observation.c.quality_status == "ACCEPTED")
    if as_of:
        stmt = stmt.where(observation.c.market_date <= as_of)
    return connection.execute(stmt.order_by(observation.c.market_date.desc().nullslast(), observation.c.observed_at_utc.desc()).limit(1)).mappings().first()


def list_booked_trades(
    connection: Connection,
    tenant_id: UUID,
    portfolio_code: str | None,
    from_date: date | None,
    to_date: date | None,
    limit: int,
    offset: int,
    api_version: str,
    correlation_id: str,
    trade_id: UUID | None = None,
) -> TradeResponse:
    """Return booked economic executions visible to the tenant.

    This is intentionally a read model over ``trd.trade``. It does not expose
    orders, fills, or a universal multi-leg container; one row remains one
    booked economic event as defined by the trade domain.
    """
    trade = m.trade
    strategy = m.strategy
    subject_node = m.financial_reference_node.alias("trade_subject_node")
    instrument = m.instrument.alias("trade_instrument")
    instrument_node = m.financial_reference_node.alias("trade_instrument_node")
    instrument_type = m.instrument_type.alias("trade_instrument_type")
    listing = m.listing.alias("trade_listing")
    venue = m.market_venue.alias("trade_venue")
    venue_identifier = m.market_venue_identifier.alias("trade_venue_identifier")
    price_currency = m.currency.alias("trade_price_currency")
    reference_instrument = m.financial_reference_node.alias("trade_reference_instrument")
    filters = [trade.c.lifecycle_status == "BOOKED", strategy.c.tenant_id == tenant_id, strategy.c.status == "ACTIVE"]
    if portfolio_code:
        filters.append(strategy.c.strategy_code == portfolio_code)
    if trade_id:
        filters.append(trade.c.trade_id == trade_id)
    if from_date:
        filters.append(trade.c.trade_datetime_utc >= datetime.combine(from_date, datetime.min.time(), tzinfo=timezone.utc))
    if to_date:
        filters.append(trade.c.trade_datetime_utc < datetime.combine(to_date + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc))
    rows = connection.execute(
        select(
            trade,
            subject_node.c.canonical_name.label("subject_name"),
            instrument_node.c.reference_node_id.label("instrument_id"),
            instrument_node.c.canonical_name.label("instrument_name"),
            instrument_type.c.type_code.label("instrument_type"),
            listing.c.listing_node_id.label("listing_id"),
            listing.c.trading_symbol.label("listing_symbol"),
            venue.c.market_venue_id.label("venue_id"),
            venue_identifier.c.identifier_value.label("venue_mic"),
            venue.c.display_name.label("venue_name"),
            price_currency.c.currency_code.label("price_currency"),
            strategy.c.strategy_code,
            strategy.c.display_name.label("strategy_name"),
            reference_instrument.c.reference_node_id.label("reference_instrument_id"),
        )
        .select_from(
            trade.join(strategy, trade.c.strategy_id == strategy.c.strategy_id)
            .join(subject_node, trade.c.trade_subject_reference_node_id == subject_node.c.reference_node_id)
            .outerjoin(listing, listing.c.listing_node_id == trade.c.trade_subject_reference_node_id)
            .outerjoin(instrument, instrument.c.instrument_node_id == func.coalesce(listing.c.instrument_node_id, trade.c.trade_subject_reference_node_id))
            .outerjoin(instrument_node, instrument_node.c.reference_node_id == func.coalesce(listing.c.instrument_node_id, trade.c.trade_subject_reference_node_id))
            .outerjoin(instrument_type, instrument_type.c.instrument_type_id == instrument.c.instrument_type_id)
            .outerjoin(venue, venue.c.market_venue_id == listing.c.market_venue_id)
            .outerjoin(venue_identifier, and_(venue_identifier.c.market_venue_id == venue.c.market_venue_id, venue_identifier.c.is_primary.is_(True)))
            .outerjoin(price_currency, price_currency.c.currency_id == trade.c.price_currency_id)
            .outerjoin(reference_instrument, reference_instrument.c.reference_node_id == trade.c.reference_instrument_node_id)
        )
        .where(*filters)
        .order_by(trade.c.trade_datetime_utc.desc(), trade.c.trade_id.desc())
        .offset(offset)
        .limit(limit)
    ).mappings().all()
    result = [
        TradeView(
            tradeId=row.trade_id,
            subjectReferenceNodeId=row.trade_subject_reference_node_id,
            subjectName=row.subject_name,
            instrumentId=row.instrument_id,
            instrumentName=row.instrument_name,
            instrumentType=row.instrument_type,
            listingId=row.listing_id,
            listingSymbol=row.listing_symbol,
            venueMic=row.venue_mic,
            venueName=row.venue_name,
            strategyId=row.strategy_id,
            strategyCode=row.strategy_code,
            strategyName=row.strategy_name,
            tradeType=row.trade_type,
            tradePurpose=row.trade_purpose,
            marketActivity=row.market_activity,
            executionPrice=_decimal(row.execution_price) if row.execution_price is not None else None,
            lockedYtm=_decimal(row.locked_ytm) if row.locked_ytm is not None else None,
            priceBasis=row.price_basis,
            priceCurrency=row.price_currency,
            quantity=_decimal(row.quantity),
            quantityUnit=row.quantity_unit,
            tradeDatetimeUtc=_iso(row.trade_datetime_utc) or "",
            instructionDate=_iso(row.instruction_date),
            settlementDate=_iso(row.settlement_date),
            traderPersonId=row.trader_person_id,
            bookedByUserAccountId=row.booked_by_user_account_id,
            executionChannel=row.execution_channel,
            sourceSystemId=row.source_system_id,
            sourceReceivedAtUtc=_iso(row.source_received_at_utc),
            executionVenueId=row.venue_id,
            dealingCapacity=row.dealing_capacity,
            lifecycleStatus=row.lifecycle_status,
            referenceInstrumentId=row.reference_instrument_id,
            comment=row.comment,
        )
        for row in rows
    ]
    return TradeResponse(
        data=result,
        meta=ApiMeta(tenantContext=str(tenant_id), source="live-reference-api", apiVersion=api_version, correlationId=correlation_id, limit=limit, offset=offset, total=len(result)),
    )


def get_booked_trade_detail(
    connection: Connection,
    tenant_id: UUID,
    trade_id: UUID,
    api_version: str,
    correlation_id: str,
) -> TradeDetailResponse | None:
    """Return one booked execution and its normalized operational evidence."""
    listed = list_booked_trades(connection, tenant_id, None, None, None, 1, 0, api_version, correlation_id, trade_id=trade_id)
    if not listed.data:
        return None
    trade_view = listed.data[0]
    party_role = m.trade_party_role
    organisation = m.organisation
    person = m.person
    party_rows = connection.execute(
        select(
            party_role.c.trade_party_role_id,
            party_role.c.role,
            party_role.c.organisation_id,
            organisation.c.display_name.label("organisation_name"),
            party_role.c.person_id,
            person.c.display_name.label("person_name"),
        )
        .select_from(
            party_role.outerjoin(organisation, party_role.c.organisation_id == organisation.c.organisation_id)
            .outerjoin(person, party_role.c.person_id == person.c.person_id)
        )
        .where(party_role.c.trade_id == trade_id)
        .order_by(party_role.c.role, party_role.c.trade_party_role_id)
    ).mappings().all()
    fee = m.trade_fee
    payer = organisation.alias("fee_payer")
    recipient = organisation.alias("fee_recipient")
    fee_currency = m.currency.alias("fee_currency")
    fee_rows = connection.execute(
        select(
            fee,
            payer.c.display_name.label("payer_name"),
            recipient.c.display_name.label("recipient_name"),
            fee_currency.c.currency_code.label("fee_currency"),
        )
        .select_from(
            fee.outerjoin(payer, fee.c.fee_payer_organisation_id == payer.c.organisation_id)
            .outerjoin(recipient, fee.c.fee_recipient_organisation_id == recipient.c.organisation_id)
            .outerjoin(fee_currency, fee.c.fee_currency_id == fee_currency.c.currency_id)
        )
        .where(fee.c.trade_id == trade_id)
        .order_by(fee.c.trade_fee_id)
    ).mappings().all()
    external = m.trade_external_reference
    external_rows = connection.execute(select(external).where(external.c.trade_id == trade_id).order_by(external.c.trade_external_reference_id)).mappings().all()
    lifecycle = m.trade_lifecycle_event
    lifecycle_rows = connection.execute(select(lifecycle).where(lifecycle.c.trade_id == trade_id).order_by(lifecycle.c.sequence_no)).mappings().all()
    return TradeDetailResponse(
        data=TradeDetailView(
            trade=trade_view,
            parties=[
                TradePartyView(
                    tradePartyRoleId=row.trade_party_role_id,
                    role=row.role,
                    organisationId=row.organisation_id,
                    organisationName=row.organisation_name,
                    personId=row.person_id,
                    personName=row.person_name,
                    partyName=row.organisation_name or row.person_name or "Unnamed party",
                )
                for row in party_rows
            ],
            fees=[
                TradeFeeView(
                    tradeFeeId=row.trade_fee_id,
                    feeType=row.fee_type,
                    payerOrganisationId=row.fee_payer_organisation_id,
                    payerOrganisationName=row.payer_name,
                    recipientOrganisationId=row.fee_recipient_organisation_id,
                    recipientOrganisationName=row.recipient_name,
                    feeAmount=_decimal(row.fee_amount),
                    feeCurrency=row.fee_currency,
                    feeRate=_decimal(row.fee_rate) if row.fee_rate is not None else None,
                    feeRateUnit=row.fee_rate_unit,
                    feeBasis=row.fee_basis,
                    accrualDate=_iso(row.accrual_date),
                    settlementDate=_iso(row.settlement_date),
                    status=row.status,
                    externalReference=row.external_reference,
                )
                for row in fee_rows
            ],
            externalReferences=[
                TradeExternalReferenceView(
                    tradeExternalReferenceId=row.trade_external_reference_id,
                    sourceSystemId=row.source_system_id,
                    tradePartyRoleId=row.trade_party_role_id,
                    referenceType=row.reference_type,
                    referenceValue=row.reference_value,
                    sourceReceivedAtUtc=_iso(row.source_received_at_utc),
                )
                for row in external_rows
            ],
            lifecycleEvents=[
                TradeLifecycleEventView(
                    tradeLifecycleEventId=row.trade_lifecycle_event_id,
                    sequenceNo=row.sequence_no,
                    eventType=row.event_type,
                    eventDatetimeUtc=_iso(row.event_datetime_utc) or "",
                    sourceSystemId=row.source_system_id,
                    sourceEventId=row.source_event_id,
                    eventPayload=row.event_payload,
                    recordedByUserAccountId=row.recorded_by_user_account_id,
                    recordedAtUtc=_iso(row.recorded_at_utc) or "",
                )
                for row in lifecycle_rows
            ],
        ),
        meta=ApiMeta(tenantContext=str(tenant_id), source="live-reference-api", apiVersion=api_version, correlationId=correlation_id),
    )


_TRADE_BOOKING_ENDPOINT = "/v1/trades"


def _trade_booking_fingerprint(payload: TradeBookingRequest) -> str:
    canonical = json.dumps(payload.model_dump(mode="json", by_alias=True), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _trade_booking_idempotency_lock_key(tenant_id: UUID, idempotency_key: str) -> int:
    scope = f"{tenant_id}\x1f{_TRADE_BOOKING_ENDPOINT}\x1f{idempotency_key}"
    return int.from_bytes(hashlib.sha256(scope.encode("utf-8")).digest()[:8], byteorder="big", signed=True)


def book_listed_cash_trade(
    connection: Connection,
    tenant_id: UUID,
    actor_id: UUID,
    request: TradeBookingRequest,
    idempotency_key: str,
    request_id: str,
) -> TradeDetailResponse:
    """Create or replay one immutable listing-backed cash execution."""

    fingerprint = _trade_booking_fingerprint(request)
    connection.execute(select(func.pg_advisory_xact_lock(_trade_booking_idempotency_lock_key(tenant_id, idempotency_key))))
    existing = connection.execute(
        select(m.trade_booking_idempotency)
        .where(m.trade_booking_idempotency.c.tenant_id == tenant_id)
        .where(m.trade_booking_idempotency.c.endpoint == _TRADE_BOOKING_ENDPOINT)
        .where(m.trade_booking_idempotency.c.idempotency_key == idempotency_key)
        .with_for_update()
    ).mappings().first()
    if existing is not None:
        if existing["request_fingerprint"] != fingerprint:
            raise IdempotencyKeyConflict("Idempotency key was already used with a different request")
        replay = get_booked_trade_detail(connection, tenant_id, existing["trade_id"], "v1", request_id)
        if replay is None:
            raise RepositoryNotFound("Booked trade does not exist")
        return replay

    listing_row = connection.execute(
        select(
            m.listing.c.listing_node_id,
            m.listing.c.instrument_node_id,
            m.listing.c.market_venue_id,
            m.listing.c.trading_currency_id,
            m.currency.c.currency_code,
        )
        .select_from(m.listing.join(m.currency, m.currency.c.currency_id == m.listing.c.trading_currency_id))
        .join(m.financial_reference_node, m.financial_reference_node.c.reference_node_id == m.listing.c.listing_node_id)
        .where(m.listing.c.listing_node_id == request.listing_id)
        .where(m.listing.c.status == "ACTIVE")
        .where(m.financial_reference_node.c.status == "ACTIVE")
        .with_for_update()
    ).mappings().first()
    if listing_row is None:
        raise RepositoryNotFound("Active listing does not exist")
    strategy_row = connection.execute(
        select(m.strategy.c.strategy_id)
        .where(m.strategy.c.strategy_id == request.strategy_id)
        .where(m.strategy.c.tenant_id == tenant_id)
        .where(m.strategy.c.status == "ACTIVE")
        .with_for_update()
    ).mappings().first()
    if strategy_row is None:
        raise RepositoryNotFound("Active strategy does not exist")
    if request.counterparty_organisation_id is not None:
        organisation_id = connection.scalar(
            select(m.organisation.c.organisation_id)
            .where(m.organisation.c.organisation_id == request.counterparty_organisation_id)
            .where(m.organisation.c.status == "ACTIVE")
        )
        if organisation_id is None:
            raise InvalidCatalogueValue("counterpartyOrganisationId is not an active organisation")

    trade_id = uuid4()
    signed_quantity = request.quantity if request.side == "BUY" else -request.quantity
    trade_datetime_utc = request.trade_datetime.astimezone(timezone.utc)
    connection.execute(
        insert(m.trade).values(
            trade_id=trade_id,
            trade_subject_reference_node_id=listing_row["listing_node_id"],
            reference_instrument_node_id=listing_row["instrument_node_id"],
            strategy_id=strategy_row["strategy_id"],
            trade_type="INVESTMENT",
            trade_purpose="INVESTMENT",
            execution_price=request.execution_price,
            price_basis="UNIT_PRICE",
            price_currency_id=listing_row["trading_currency_id"],
            quantity=signed_quantity,
            quantity_unit="SHARES",
            trade_datetime_utc=trade_datetime_utc,
            settlement_date=request.settlement_date,
            booked_by_user_account_id=actor_id,
            execution_channel="MANUAL_UI",
            execution_venue_id=listing_row["market_venue_id"],
            lifecycle_status="BOOKED",
            created_by_user_account_id=actor_id,
            comment=request.comment,
        )
    )
    party_role_id = None
    if request.counterparty_organisation_id is not None:
        party_role_id = uuid4()
        connection.execute(insert(m.trade_party_role).values(trade_party_role_id=party_role_id, trade_id=trade_id, organisation_id=request.counterparty_organisation_id, role="COUNTERPARTY"))
    if request.external_reference:
        connection.execute(insert(m.trade_external_reference).values(trade_id=trade_id, trade_party_role_id=party_role_id, reference_type="SOURCE_TRADE_ID", reference_value=request.external_reference))
    connection.execute(insert(m.trade_lifecycle_event).values(trade_id=trade_id, sequence_no=1, event_type="BOOKED", event_datetime_utc=trade_datetime_utc, source_event_id=idempotency_key, payload_hash=fingerprint, recorded_by_user_account_id=actor_id))
    connection.execute(insert(m.trade_booking_idempotency).values(tenant_id=tenant_id, endpoint=_TRADE_BOOKING_ENDPOINT, idempotency_key=idempotency_key, request_fingerprint=fingerprint, trade_id=trade_id))
    result = get_booked_trade_detail(connection, tenant_id, trade_id, "v1", request_id)
    if result is None:
        raise RepositoryNotFound("Booked trade does not exist")
    return result


def _previous_business_day(value: date) -> date:
    current = value - timedelta(days=1)
    while current.weekday() >= 5:
        current -= timedelta(days=1)
    return current


def portfolio_pnl(connection: Connection, tenant_id: UUID, portfolio_code: str, as_of_date: date, api_version: str, correlation_id: str) -> PortfolioPnlResponse | None:
    """Compute a transparent, display-only price/FX P&L view from booked trades."""
    strategy = connection.execute(
        select(m.strategy.c.strategy_id, m.strategy.c.strategy_code, m.strategy.c.display_name, m.strategy.c.base_currency_id)
        .where(m.strategy.c.strategy_code == portfolio_code)
        .where(m.strategy.c.tenant_id == tenant_id)
        .where(m.strategy.c.status == "ACTIVE")
    ).mappings().first()
    if strategy is None:
        return None
    base_currency = connection.execute(select(m.currency.c.currency_code).where(m.currency.c.currency_id == strategy.base_currency_id)).scalar_one_or_none() or ""
    cut_code = "US_FUND_FX_1600_MVP" if portfolio_code.endswith("US_PORTFOLIO") else "UK_FUND_FX_1600_MVP"
    cut_row = connection.execute(select(m.valuation_cut).where(m.valuation_cut.c.cut_code == cut_code)).mappings().first()
    prev_date = _previous_business_day(as_of_date)
    subject_node = m.financial_reference_node.alias("subject_node")
    instrument_node = m.financial_reference_node.alias("instrument_node")
    listing = m.listing.alias("subject_listing")
    instrument = m.instrument.alias("instrument")
    instrument_type = m.instrument_type.alias("instrument_type")
    local_currency = m.currency.alias("local_currency")
    trades = connection.execute(
        select(
            m.trade.c.trade_subject_reference_node_id,
            m.trade.c.quantity,
            m.trade.c.price_currency_id,
            m.trade.c.execution_price,
            m.trade.c.price_basis,
            listing.c.listing_node_id,
            listing.c.instrument_node_id,
            listing.c.quote_factor,
            listing.c.unit_multiplier,
            subject_node.c.canonical_name.label("subject_name"),
            instrument_node.c.canonical_name.label("instrument_name"),
            instrument_type.c.type_code.label("instrument_type"),
            local_currency.c.currency_code.label("local_currency"),
        )
        .select_from(
            m.trade.join(subject_node, m.trade.c.trade_subject_reference_node_id == subject_node.c.reference_node_id)
            .outerjoin(listing, listing.c.listing_node_id == m.trade.c.trade_subject_reference_node_id)
            .outerjoin(instrument, instrument.c.instrument_node_id == func.coalesce(listing.c.instrument_node_id, m.trade.c.trade_subject_reference_node_id))
            .outerjoin(instrument_node, instrument_node.c.reference_node_id == func.coalesce(listing.c.instrument_node_id, m.trade.c.trade_subject_reference_node_id))
            .outerjoin(instrument_type, instrument_type.c.instrument_type_id == instrument.c.instrument_type_id)
            .outerjoin(local_currency, local_currency.c.currency_id == m.trade.c.price_currency_id)
        )
        .where(m.trade.c.strategy_id == strategy.strategy_id)
        .where(m.trade.c.lifecycle_status == "BOOKED")
        .where(m.trade.c.trade_datetime_utc < datetime.combine(as_of_date + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc))
        .order_by(m.trade.c.trade_subject_reference_node_id)
    ).mappings().all()
    gbpusd_node = connection.execute(select(m.financial_reference_node.c.reference_node_id).where(m.financial_reference_node.c.internal_code == "MVP_GBPUSD")).scalar_one_or_none()
    eurusd_node = connection.execute(select(m.financial_reference_node.c.reference_node_id).where(m.financial_reference_node.c.internal_code == "MVP_EURUSD")).scalar_one_or_none()

    def fx_series(pair_node: UUID | None):
        if pair_node is None:
            return None
        pair_cut_code = cut_code
        # GBP/USD and EUR/USD are separate economic series.  Keep the cut
        # family aligned with the portfolio context rather than silently using
        # the GBP cut for every currency conversion.
        if pair_node == eurusd_node:
            pair_cut_code = "EUR_FUND_US_1600_MVP" if portfolio_code.endswith("US_PORTFOLIO") else "EUR_FUND_FX_1600_MVP"
        pair_cut_id = connection.execute(
            select(m.valuation_cut.c.valuation_cut_id).where(m.valuation_cut.c.cut_code == pair_cut_code)
        ).scalar_one_or_none()
        return connection.execute(
            select(m.market_data_series.c.market_data_series_id)
            .where(m.market_data_series.c.reference_node_id == pair_node)
            .where(m.market_data_series.c.valuation_cut_id == pair_cut_id)
            .where(m.market_data_series.c.status == "ACTIVE")
            .limit(1)
        ).scalar_one_or_none()

    gbp_series = fx_series(gbpusd_node)
    eur_series = fx_series(eurusd_node)
    fx_cache: dict[UUID, tuple[Decimal, Decimal]] = {}
    for series_id in [item for item in (gbp_series, eur_series) if item]:
        close = _latest_observation(connection, series_id, as_of_date)
        open_ = _latest_observation(connection, series_id, prev_date)
        if close and open_:
            fx_cache[series_id] = (Decimal(str(open_.value)), Decimal(str(close.value)))

    def conversion(local: str | None) -> tuple[Decimal, Decimal]:
        if not local or local == base_currency:
            return Decimal(1), Decimal(1)
        gbp = fx_cache.get(gbp_series) if gbp_series else None
        eur = fx_cache.get(eur_series) if eur_series else None
        if base_currency == "USD" and local == "GBP" and gbp:
            return gbp
        if base_currency == "USD" and local == "EUR" and eur:
            return eur
        if base_currency == "GBP" and local == "USD" and gbp:
            return Decimal(1) / gbp[0], Decimal(1) / gbp[1]
        if base_currency == "GBP" and local == "EUR" and eur and gbp:
            return eur[0] / gbp[0], eur[1] / gbp[1]
        return Decimal(1), Decimal(1)

    lines: list[PortfolioPnlLine] = []
    for trade in trades:
        instrument_id = trade.instrument_node_id or trade.trade_subject_reference_node_id
        listing_id = trade.listing_node_id
        series_rows = connection.execute(
            select(m.market_data_series.c.market_data_series_id, m.market_data_series.c.series_type)
            .where(m.market_data_series.c.reference_node_id.in_([item for item in (listing_id, instrument_id) if item]))
            .where(m.market_data_series.c.status == "ACTIVE")
            .where(
                exists(
                    select(1)
                    .select_from(m.market_data_observation)
                    .where(m.market_data_observation.c.market_data_series_id == m.market_data_series.c.market_data_series_id)
                    .where(m.market_data_observation.c.quality_status == "ACCEPTED")
                    .where(m.market_data_observation.c.market_date <= as_of_date)
                )
            )
            .order_by((m.market_data_series.c.reference_node_id == listing_id).desc(), m.market_data_series.c.is_official.desc())
        ).all()
        selected_series = series_rows[0].market_data_series_id if series_rows else None
        opening = _latest_observation(connection, selected_series, prev_date) if selected_series else None
        closing = _latest_observation(connection, selected_series, as_of_date) if selected_series else None
        if not opening or not closing:
            continue
        scale = Decimal(str(trade.quote_factor or 1))
        if trade.price_basis == "PCT_OF_PAR":
            scale *= Decimal(100)
        multiplier = Decimal(str(trade.unit_multiplier or 1))
        quantity = Decimal(str(trade.quantity))
        open_price = Decimal(str(opening.value)) / scale
        close_price = Decimal(str(closing.value)) / scale
        local_price_pnl = quantity * (close_price - open_price) * multiplier
        open_fx, close_fx = conversion(trade.local_currency)
        opening_value = quantity * open_price * multiplier
        closing_value = quantity * close_price * multiplier
        total = closing_value * close_fx - opening_value * open_fx
        price_pnl = local_price_pnl * close_fx
        fx_pnl = total - price_pnl
        lines.append(PortfolioPnlLine(instrumentId=instrument_id, listingId=listing_id, instrumentName=trade.instrument_name or trade.subject_name, instrumentType=trade.instrument_type or "REFERENCE", quantity=_decimal(trade.quantity), localCurrency=trade.local_currency, baseCurrency=base_currency, openingPrice=_decimal(opening.value), closingPrice=_decimal(closing.value), openingFx=_decimal(open_fx), closingFx=_decimal(close_fx), localPricePnl=_decimal(local_price_pnl), fxPnl=_decimal(fx_pnl), totalPnl=_decimal(total), priceSeriesId=selected_series, closingObservationId=closing.market_data_observation_id))
    total_pnl = sum((Decimal(line.total_pnl) for line in lines), Decimal(0))
    valuation_cut = {"cutCode": cut_row.cut_code if cut_row else None, "displayName": cut_row.display_name if cut_row else None, "timezoneName": cut_row.timezone_name if cut_row else None, "localTime": cut_row.local_time if cut_row else None}
    view = PortfolioPnlView(portfolioCode=strategy.strategy_code, portfolioName=strategy.display_name, asOfDate=as_of_date.isoformat(), baseCurrency=base_currency, valuationCut=valuation_cut, lines=lines, totalPnl=_decimal(total_pnl), methodology="Display-only decomposition: local price movement at closing FX plus residual FX movement; derived from immutable booked trades and observations.")
    return PortfolioPnlResponse(data=view, meta=ApiMeta(tenantContext=str(tenant_id), source="live-reference-api", apiVersion=api_version, correlationId=correlation_id, total=len(lines)))


_MARKET_DATA_SNAPSHOT_ENDPOINT = "/v1/market-data-resolution-snapshots"


def _market_data_snapshot_fingerprint(payload: MarketDataResolutionSnapshotCreate) -> str:
    canonical = json.dumps(payload.model_dump(mode="json", by_alias=True), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _market_data_snapshot_idempotency_lock_key(tenant_id: UUID, idempotency_key: str) -> int:
    """Return a stable PostgreSQL advisory-lock key for one idempotency scope."""

    scope = f"{tenant_id}\x1f{_MARKET_DATA_SNAPSHOT_ENDPOINT}\x1f{idempotency_key}"
    return int.from_bytes(hashlib.sha256(scope.encode("utf-8")).digest()[:8], byteorder="big", signed=True)


def _market_data_snapshot_view(connection: Connection, tenant_id: UUID, snapshot_id: UUID) -> MarketDataResolutionSnapshotView:
    header = connection.execute(select(m.market_data_resolution_snapshot).where(m.market_data_resolution_snapshot.c.market_data_resolution_snapshot_id == snapshot_id).where(m.market_data_resolution_snapshot.c.tenant_id == tenant_id)).mappings().first()
    if header is None:
        raise RepositoryNotFound("Market-data resolution snapshot does not exist")
    rows = connection.execute(select(m.market_data_resolution_snapshot_item).where(m.market_data_resolution_snapshot_item.c.market_data_resolution_snapshot_id == snapshot_id).order_by(m.market_data_resolution_snapshot_item.c.request_sequence)).mappings().all()
    return MarketDataResolutionSnapshotView(
        marketDataResolutionSnapshotId=header["market_data_resolution_snapshot_id"], tenantId=header["tenant_id"], valuationPolicyId=header["valuation_policy_id"], valuationDate=header["valuation_date"], valuationCutId=header["valuation_cut_id"], marketDataAsOfUtc=header["market_data_as_of_utc"], usePurpose=header["use_purpose"], resolverVersion=header["resolver_version"], status=header["status"], createdAtUtc=header["created_at_utc"],
        items=[MarketDataResolutionSnapshotItemView(status=row["status"], subjectReferenceNodeId=row["subject_reference_node_id"], policyRuleId=row["policy_rule_id"], marketDataSeriesId=row["market_data_series_id"], marketDataObservationId=row["market_data_observation_id"], marketDataVintageId=row["market_data_vintage_id"], datasetId=row["dataset_id"], acquisitionLicenceId=row["acquisition_licence_id"], sourcePublishedAtUtc=row["source_published_at_utc"], receivedAtUtc=row["received_at_utc"], selectedValue=row["selected_value"], currencyId=row["currency_id"], pricingDateRequested=row["pricing_date_requested"], pricingDateUsed=row["pricing_date_used"], stalenessBusinessDays=row["staleness_business_days"], stalenessStatus=row["staleness_status"], selectionReason=row["selection_reason"], entitlementDecision=row["entitlement_decision"], exceptionCode=row["exception_code"]) for row in rows],
    )


def create_market_data_resolution_snapshot(connection: Connection, tenant_id: UUID, payload: MarketDataResolutionSnapshotCreate, idempotency_key: str, request_id: str) -> MarketDataResolutionSnapshotView:
    """Create or replay one tenant-scoped immutable evidence resource."""
    fingerprint = _market_data_snapshot_fingerprint(payload)
    connection.execute(
        select(func.pg_advisory_xact_lock(_market_data_snapshot_idempotency_lock_key(tenant_id, idempotency_key)))
    )
    existing = connection.execute(select(m.market_data_resolution_idempotency).where(m.market_data_resolution_idempotency.c.tenant_id == tenant_id).where(m.market_data_resolution_idempotency.c.endpoint == _MARKET_DATA_SNAPSHOT_ENDPOINT).where(m.market_data_resolution_idempotency.c.idempotency_key == idempotency_key).with_for_update()).mappings().first()
    if existing is not None:
        if existing["request_fingerprint"] != fingerprint:
            raise IdempotencyKeyConflict("Idempotency key was already used with a different request")
        return _market_data_snapshot_view(connection, tenant_id, existing["market_data_resolution_snapshot_id"])
    request = ResolutionRequest(tenant_id=tenant_id, subject_reference_node_id=payload.subject_reference_node_ids[0], valuation_policy_id=payload.valuation_policy_id, valuation_date=payload.valuation_date, valuation_cut_id=payload.valuation_cut_id, market_data_as_of_utc=payload.market_data_as_of_utc, use_purpose=payload.use_purpose)
    snapshot_id = persist_resolution_snapshot(connection, request, resolve_market_data_batch(connection, request, tuple(payload.subject_reference_node_ids)))
    connection.execute(insert(m.market_data_resolution_idempotency).values(tenant_id=tenant_id, endpoint=_MARKET_DATA_SNAPSHOT_ENDPOINT, idempotency_key=idempotency_key, request_fingerprint=fingerprint, market_data_resolution_snapshot_id=snapshot_id, expires_at_utc=datetime.now(timezone.utc) + timedelta(hours=24)))
    return _market_data_snapshot_view(connection, tenant_id, snapshot_id)


def get_market_data_resolution_snapshot(connection: Connection, tenant_id: UUID, snapshot_id: UUID) -> MarketDataResolutionSnapshotView:
    """Read persisted snapshot evidence without re-resolving present-day state."""
    return _market_data_snapshot_view(connection, tenant_id, snapshot_id)


def list_active_valuation_policies(connection: Connection, tenant_id: UUID, valuation_date: date) -> list[ActiveValuationPolicyView]:
    """Return only policies currently usable by the requesting tenant."""
    rows = connection.execute(
        select(m.valuation_policy, m.valuation_cut.c.cut_code, m.valuation_cut.c.display_name.label("cut_display_name"), m.valuation_cut.c.timezone_name, m.valuation_cut.c.local_time)
        .select_from(m.valuation_policy.join(m.valuation_cut, m.valuation_policy.c.valuation_cut_id == m.valuation_cut.c.valuation_cut_id))
        .where(m.valuation_policy.c.tenant_id == tenant_id)
        .where(m.valuation_policy.c.status == "ACTIVE")
        .where(m.valuation_policy.c.valid_from <= valuation_date)
        .where(or_(m.valuation_policy.c.valid_to.is_(None), m.valuation_policy.c.valid_to >= valuation_date))
        .order_by(m.valuation_policy.c.policy_code, m.valuation_policy.c.version_no.desc())
    ).mappings().all()
    return [ActiveValuationPolicyView(valuationPolicyId=row["valuation_policy_id"], tenantId=row["tenant_id"], policyCode=row["policy_code"], displayName=row["display_name"], valuationCutId=row["valuation_cut_id"], valuationCutCode=row["cut_code"], valuationCutDisplayName=row["cut_display_name"], timezoneName=row["timezone_name"], localTime=str(row["local_time"])) for row in rows]
