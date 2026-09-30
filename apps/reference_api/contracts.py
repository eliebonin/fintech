"""Stable, view-oriented API contracts for the reference-data service."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ApiMeta(BaseModel):
    tenant_context: str = Field(alias="tenantContext")
    source: str
    api_version: str = Field(alias="apiVersion")
    correlation_id: str = Field(alias="correlationId")
    limit: int | None = None
    offset: int | None = None
    total: int | None = None

    model_config = ConfigDict(populate_by_name=True)


class TenantMembershipView(BaseModel):
    tenant_id: UUID = Field(alias="tenantId")
    tenant_code: str = Field(alias="tenantCode")
    tenant_name: str = Field(alias="tenantName")
    membership_role: str = Field(alias="membershipRole")
    model_config = ConfigDict(populate_by_name=True)


class TenantMembershipResponse(BaseModel):
    data: list[TenantMembershipView]
    platform_role: str | None = Field(default=None, alias="platformRole")
    model_config = ConfigDict(populate_by_name=True)


class TenantWorkspaceView(BaseModel):
    tenant_id: UUID = Field(alias="tenantId")
    tenant_code: str = Field(alias="tenantCode")
    tenant_name: str = Field(alias="tenantName")
    membership_role: str = Field(alias="membershipRole")
    module_codes: list[str] = Field(alias="moduleCodes")
    platform_role: str | None = Field(default=None, alias="platformRole")
    model_config = ConfigDict(populate_by_name=True)


class TenantWorkspaceResponse(BaseModel):
    data: TenantWorkspaceView
    model_config = ConfigDict(populate_by_name=True)


class StrategyCreateRequest(BaseModel):
    strategy_code: str = Field(alias="strategyCode", min_length=1, max_length=100)
    display_name: str = Field(alias="displayName", min_length=1, max_length=250)
    strategy_type: str = Field(alias="strategyType")
    base_currency_code: str | None = Field(default=None, alias="baseCurrencyCode")
    operating_model_label: str | None = Field(default=None, alias="operatingModelLabel")
    model_config = ConfigDict(populate_by_name=True)

    @field_validator("operating_model_label")
    @classmethod
    def _label_not_blank(cls, value: str | None) -> str | None:
        return value.strip() if value else None


class StrategyStatusRequest(BaseModel):
    status: str


class StrategyView(BaseModel):
    strategy_id: UUID = Field(alias="strategyId")
    tenant_id: UUID = Field(alias="tenantId")
    strategy_code: str = Field(alias="strategyCode")
    display_name: str = Field(alias="displayName")
    strategy_type: str = Field(alias="strategyType")
    base_currency_code: str | None = Field(alias="baseCurrencyCode")
    status: str
    model_config = ConfigDict(populate_by_name=True)


class StrategyResponse(BaseModel):
    data: StrategyView
    model_config = ConfigDict(populate_by_name=True)


class StrategyListResponse(BaseModel):
    data: list[StrategyView]
    model_config = ConfigDict(populate_by_name=True)


class MarketDataResolutionSnapshotCreate(BaseModel):
    """One coherent, bounded set of inputs resolved at a UTC information cut."""

    subject_reference_node_ids: list[UUID] = Field(
        alias="subjectReferenceNodeIds", min_length=1, max_length=50,
        json_schema_extra={"uniqueItems": True},
    )
    valuation_policy_id: UUID = Field(alias="valuationPolicyId")
    valuation_date: date = Field(alias="valuationDate")
    valuation_cut_id: UUID = Field(alias="valuationCutId")
    market_data_as_of_utc: datetime = Field(alias="marketDataAsOfUtc")
    use_purpose: str = Field(alias="usePurpose", min_length=1, max_length=50)

    @field_validator("subject_reference_node_ids")
    @classmethod
    def _subjects_are_unique(cls, value: list[UUID]) -> list[UUID]:
        if len(set(value)) != len(value):
            raise ValueError("subjectReferenceNodeIds must be unique")
        return value

    @field_validator("market_data_as_of_utc")
    @classmethod
    def _as_of_is_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None or value.utcoffset().total_seconds() != 0:
            raise ValueError("marketDataAsOfUtc must be timezone-aware UTC")
        return value

    model_config = ConfigDict(populate_by_name=True)


class MarketDataResolutionSnapshotItemView(BaseModel):
    status: str
    subject_reference_node_id: UUID = Field(alias="subjectReferenceNodeId")
    policy_rule_id: UUID | None = Field(alias="policyRuleId")
    market_data_series_id: UUID | None = Field(alias="marketDataSeriesId")
    market_data_observation_id: UUID | None = Field(alias="marketDataObservationId")
    market_data_vintage_id: UUID | None = Field(alias="marketDataVintageId")
    dataset_id: UUID | None = Field(alias="datasetId")
    acquisition_licence_id: UUID | None = Field(alias="acquisitionLicenceId")
    source_published_at_utc: datetime | None = Field(alias="sourcePublishedAtUtc")
    received_at_utc: datetime | None = Field(alias="receivedAtUtc")
    selected_value: Decimal | None = Field(alias="selectedValue")
    currency_id: UUID | None = Field(alias="currencyId")
    pricing_date_requested: date | None = Field(alias="pricingDateRequested")
    pricing_date_used: date | None = Field(alias="pricingDateUsed")
    staleness_business_days: int | None = Field(alias="stalenessBusinessDays")
    staleness_status: str = Field(alias="stalenessStatus")
    selection_reason: str = Field(alias="selectionReason")
    entitlement_decision: str = Field(alias="entitlementDecision")
    exception_code: str | None = Field(alias="exceptionCode")

    model_config = ConfigDict(populate_by_name=True)


class MarketDataResolutionSnapshotView(BaseModel):
    market_data_resolution_snapshot_id: UUID = Field(alias="marketDataResolutionSnapshotId")
    tenant_id: UUID = Field(alias="tenantId")
    valuation_policy_id: UUID = Field(alias="valuationPolicyId")
    valuation_date: date = Field(alias="valuationDate")
    valuation_cut_id: UUID = Field(alias="valuationCutId")
    market_data_as_of_utc: datetime = Field(alias="marketDataAsOfUtc")
    use_purpose: str = Field(alias="usePurpose")
    resolver_version: str = Field(alias="resolverVersion")
    status: str
    created_at_utc: datetime = Field(alias="createdAtUtc")
    items: list[MarketDataResolutionSnapshotItemView]

    model_config = ConfigDict(populate_by_name=True)


class ActiveValuationPolicyView(BaseModel):
    valuation_policy_id: UUID = Field(alias="valuationPolicyId")
    tenant_id: UUID = Field(alias="tenantId")
    policy_code: str = Field(alias="policyCode")
    display_name: str = Field(alias="displayName")
    valuation_cut_id: UUID = Field(alias="valuationCutId")
    valuation_cut_code: str = Field(alias="valuationCutCode")
    valuation_cut_display_name: str = Field(alias="valuationCutDisplayName")
    timezone_name: str = Field(alias="timezoneName")
    local_time: str = Field(alias="localTime")

    model_config = ConfigDict(populate_by_name=True)


class MarketVenueView(BaseModel):
    """Active canonical venue option used by listing onboarding."""

    market_venue_id: UUID = Field(alias="marketVenueId")
    venue_code: str = Field(alias="venueCode")
    venue_identifier_scheme: str = Field(alias="venueIdentifierScheme")
    display_name: str = Field(alias="displayName")
    venue_type: str = Field(alias="venueType")
    country_code: str | None = Field(default=None, alias="countryCode")
    timezone_name: str | None = Field(default=None, alias="timezoneName")

    model_config = ConfigDict(populate_by_name=True)


class MarketVenueResponse(BaseModel):
    data: list[MarketVenueView]
    meta: ApiMeta


class DayCountConventionView(BaseModel):
    """Active governed day-count convention option for instrument terms."""

    day_count_convention_id: UUID = Field(alias="dayCountConventionId")
    code: str
    display_name: str = Field(alias="displayName")
    description: str
    standard_source: str | None = Field(default=None, alias="standardSource")

    model_config = ConfigDict(populate_by_name=True)


class DayCountConventionResponse(BaseModel):
    data: list[DayCountConventionView]
    meta: ApiMeta


class InstrumentIdentifierView(BaseModel):
    scheme: str
    value: str
    scope: str


class ExternalMappingView(BaseModel):
    namespace: str
    external_id: str = Field(alias="externalId")
    status: str
    mapping_role: str = Field(alias="mappingRole")

    model_config = ConfigDict(populate_by_name=True)


class MarketDataPointView(BaseModel):
    series: str
    value: str
    currency: str | None
    market_date: str | None = Field(alias="marketDate")
    valuation_cut: str | None = Field(alias="valuationCut")
    provider: str
    dataset: str
    vintage: str
    received_at: str = Field(alias="receivedAt")
    value_basis: str = Field(alias="valueBasis")
    reference_node_id: UUID | None = Field(default=None, alias="referenceNodeId")

    model_config = ConfigDict(populate_by_name=True)


class MarketDataObservationView(BaseModel):
    observation_id: UUID = Field(alias="observationId")
    market_date: str | None = Field(alias="marketDate")
    observed_at: str = Field(alias="observedAt")
    received_at: str = Field(alias="receivedAt")
    value: str
    value_basis: str = Field(alias="valueBasis")
    quality_status: str = Field(alias="qualityStatus")
    provider_id: UUID | None = Field(alias="providerId")
    provider_code: str | None = Field(alias="providerCode")
    dataset_id: UUID = Field(alias="datasetId")
    dataset_code: str = Field(alias="datasetCode")
    licence_id: UUID | None = Field(alias="licenceId")
    licence_code: str | None = Field(alias="licenceCode")
    vintage_id: UUID | None = Field(alias="vintageId")
    vintage_key: str | None = Field(alias="vintageKey")
    source_published_at: str | None = Field(alias="sourcePublishedAt")
    source_observation_key: str | None = Field(alias="sourceObservationKey")

    model_config = ConfigDict(populate_by_name=True)


class MarketDataSeriesView(BaseModel):
    series_id: UUID = Field(alias="seriesId")
    reference_node_id: UUID = Field(alias="referenceNodeId")
    reference_node_name: str = Field(alias="referenceNodeName")
    series_type: str = Field(alias="seriesType")
    value_type: str = Field(alias="valueType")
    currency: str | None
    provider_id: UUID | None = Field(alias="providerId")
    provider_code: str | None = Field(alias="providerCode")
    provider_name: str | None = Field(alias="providerName")
    dataset_id: UUID | None = Field(alias="datasetId")
    dataset_code: str | None = Field(alias="datasetCode")
    dataset_name: str | None = Field(alias="datasetName")
    licence_id: UUID | None = Field(alias="licenceId")
    licence_code: str | None = Field(alias="licenceCode")
    licence_name: str | None = Field(alias="licenceName")
    valuation_cut: str | None = Field(alias="valuationCut")
    timezone_name: str | None = Field(alias="timezoneName")
    expected_frequency: str = Field(alias="expectedFrequency")
    expected_calendar_id: UUID | None = Field(alias="expectedCalendarId")
    expected_calendar_code: str | None = Field(alias="expectedCalendarCode")
    coverage_start_date: str | None = Field(alias="coverageStartDate")
    coverage_end_date: str | None = Field(alias="coverageEndDate")
    observations: list[MarketDataObservationView] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)


class MarketDataSeriesResponse(BaseModel):
    data: list[MarketDataSeriesView]
    meta: ApiMeta


class PortfolioPnlLine(BaseModel):
    instrument_id: UUID = Field(alias="instrumentId")
    listing_id: UUID | None = Field(alias="listingId")
    instrument_name: str = Field(alias="instrumentName")
    instrument_type: str = Field(alias="instrumentType")
    quantity: str
    local_currency: str | None = Field(alias="localCurrency")
    base_currency: str | None = Field(alias="baseCurrency")
    opening_price: str | None = Field(alias="openingPrice")
    closing_price: str | None = Field(alias="closingPrice")
    opening_fx: str = Field(alias="openingFx")
    closing_fx: str = Field(alias="closingFx")
    local_price_pnl: str = Field(alias="localPricePnl")
    fx_pnl: str = Field(alias="fxPnl")
    total_pnl: str = Field(alias="totalPnl")
    price_series_id: UUID | None = Field(alias="priceSeriesId")
    closing_observation_id: UUID | None = Field(alias="closingObservationId")

    model_config = ConfigDict(populate_by_name=True)


class PortfolioPnlView(BaseModel):
    portfolio_code: str = Field(alias="portfolioCode")
    portfolio_name: str = Field(alias="portfolioName")
    as_of_date: str = Field(alias="asOfDate")
    base_currency: str = Field(alias="baseCurrency")
    valuation_cut: dict[str, str | None] = Field(alias="valuationCut")
    lines: list[PortfolioPnlLine]
    total_pnl: str = Field(alias="totalPnl")
    methodology: str

    model_config = ConfigDict(populate_by_name=True)


class PortfolioPnlResponse(BaseModel):
    data: PortfolioPnlView
    meta: ApiMeta


class TradeView(BaseModel):
    trade_id: UUID = Field(alias="tradeId")
    trade_subject_reference_node_id: UUID = Field(alias="subjectReferenceNodeId")
    subject_name: str = Field(alias="subjectName")
    instrument_id: UUID | None = Field(alias="instrumentId")
    instrument_name: str | None = Field(alias="instrumentName")
    instrument_type: str | None = Field(alias="instrumentType")
    listing_id: UUID | None = Field(alias="listingId")
    listing_symbol: str | None = Field(alias="listingSymbol")
    venue_mic: str | None = Field(alias="venueMic")
    venue_name: str | None = Field(alias="venueName")
    strategy_id: UUID = Field(alias="strategyId")
    strategy_code: str = Field(alias="strategyCode")
    strategy_name: str = Field(alias="strategyName")
    trade_type: str = Field(alias="tradeType")
    trade_purpose: str | None = Field(alias="tradePurpose")
    market_activity: str | None = Field(alias="marketActivity")
    execution_price: str | None = Field(alias="executionPrice")
    locked_ytm: str | None = Field(alias="lockedYtm")
    price_basis: str | None = Field(alias="priceBasis")
    price_currency: str | None = Field(alias="priceCurrency")
    quantity: str = Field(alias="quantity")
    quantity_unit: str = Field(alias="quantityUnit")
    trade_datetime_utc: str = Field(alias="tradeDatetimeUtc")
    instruction_date: str | None = Field(alias="instructionDate")
    settlement_date: str | None = Field(alias="settlementDate")
    trader_person_id: UUID | None = Field(alias="traderPersonId")
    booked_by_user_account_id: UUID = Field(alias="bookedByUserAccountId")
    execution_channel: str = Field(alias="executionChannel")
    source_system_id: str | None = Field(alias="sourceSystemId")
    source_received_at_utc: str | None = Field(alias="sourceReceivedAtUtc")
    execution_venue_id: UUID | None = Field(alias="executionVenueId")
    dealing_capacity: str | None = Field(alias="dealingCapacity")
    lifecycle_status: str = Field(alias="lifecycleStatus")
    reference_instrument_id: UUID | None = Field(alias="referenceInstrumentId")
    comment: str | None = None

    model_config = ConfigDict(populate_by_name=True)


class TradeResponse(BaseModel):
    data: list[TradeView]
    meta: ApiMeta


class TradePartyView(BaseModel):
    trade_party_role_id: UUID = Field(alias="tradePartyRoleId")
    role: str
    organisation_id: UUID | None = Field(alias="organisationId")
    organisation_name: str | None = Field(alias="organisationName")
    person_id: UUID | None = Field(alias="personId")
    person_name: str | None = Field(alias="personName")
    party_name: str = Field(alias="partyName")

    model_config = ConfigDict(populate_by_name=True)


class TradeFeeView(BaseModel):
    trade_fee_id: UUID = Field(alias="tradeFeeId")
    fee_type: str = Field(alias="feeType")
    payer_organisation_id: UUID | None = Field(alias="payerOrganisationId")
    payer_organisation_name: str | None = Field(alias="payerOrganisationName")
    recipient_organisation_id: UUID | None = Field(alias="recipientOrganisationId")
    recipient_organisation_name: str | None = Field(alias="recipientOrganisationName")
    fee_amount: str = Field(alias="feeAmount")
    fee_currency: str | None = Field(alias="feeCurrency")
    fee_rate: str | None = Field(alias="feeRate")
    fee_rate_unit: str | None = Field(alias="feeRateUnit")
    fee_basis: str = Field(alias="feeBasis")
    accrual_date: str | None = Field(alias="accrualDate")
    settlement_date: str | None = Field(alias="settlementDate")
    status: str
    external_reference: str | None = Field(alias="externalReference")

    model_config = ConfigDict(populate_by_name=True)


class TradeExternalReferenceView(BaseModel):
    trade_external_reference_id: UUID = Field(alias="tradeExternalReferenceId")
    source_system_id: str | None = Field(alias="sourceSystemId")
    trade_party_role_id: UUID | None = Field(alias="tradePartyRoleId")
    reference_type: str = Field(alias="referenceType")
    reference_value: str = Field(alias="referenceValue")
    source_received_at_utc: str | None = Field(alias="sourceReceivedAtUtc")

    model_config = ConfigDict(populate_by_name=True)


class TradeLifecycleEventView(BaseModel):
    trade_lifecycle_event_id: UUID = Field(alias="tradeLifecycleEventId")
    sequence_no: int = Field(alias="sequenceNo")
    event_type: str = Field(alias="eventType")
    event_datetime_utc: str = Field(alias="eventDatetimeUtc")
    source_system_id: str | None = Field(alias="sourceSystemId")
    source_event_id: str | None = Field(alias="sourceEventId")
    event_payload: str | None = Field(alias="eventPayload")
    recorded_by_user_account_id: UUID = Field(alias="recordedByUserAccountId")
    recorded_at_utc: str = Field(alias="recordedAtUtc")

    model_config = ConfigDict(populate_by_name=True)


class TradeDetailView(BaseModel):
    trade: TradeView
    parties: list[TradePartyView] = Field(default_factory=list)
    fees: list[TradeFeeView] = Field(default_factory=list)
    external_references: list[TradeExternalReferenceView] = Field(default_factory=list, alias="externalReferences")
    lifecycle_events: list[TradeLifecycleEventView] = Field(default_factory=list, alias="lifecycleEvents")

    model_config = ConfigDict(populate_by_name=True)


class TradeDetailResponse(BaseModel):
    data: TradeDetailView
    meta: ApiMeta


class InstrumentListingView(BaseModel):
    listing_id: UUID = Field(alias="listingId")
    market_venue_mic: str = Field(alias="marketVenueMic")
    venue_name: str = Field(alias="venueName")
    trading_symbol: str | None = Field(alias="tradingSymbol")
    trading_currency: str | None = Field(alias="tradingCurrency")
    status: str
    quote_factor: str = Field(alias="quoteFactor")
    unit_multiplier: str = Field(alias="unitMultiplier")
    identifiers: list[InstrumentIdentifierView]
    market_data: list[MarketDataPointView] = Field(alias="marketData")

    model_config = ConfigDict(populate_by_name=True)


class InstrumentView(BaseModel):
    instrument_id: UUID = Field(alias="instrumentId")
    canonical_name: str = Field(alias="canonicalName")
    instrument_type: str = Field(alias="instrumentType")
    asset_class: str = Field(alias="assetClass")
    status: str
    issuer: str | None
    base_currency: str | None = Field(alias="baseCurrency")
    definition_version: int = Field(alias="definitionVersion")
    effective_from: str | None = Field(alias="effectiveFrom")
    identifiers: list[InstrumentIdentifierView]
    mappings: list[ExternalMappingView]
    listings: list[InstrumentListingView]
    instrument_market_data: list[MarketDataPointView] = Field(alias="instrumentMarketData")
    taxonomy: list[str]
    notes: str

    model_config = ConfigDict(populate_by_name=True)


class InstrumentSearchResponse(BaseModel):
    data: list[InstrumentView]
    meta: ApiMeta


class ReferenceNodeOptionView(BaseModel):
    """Compact tenant-visible reference node option for underlying selection."""

    reference_node_id: UUID = Field(alias="referenceNodeId")
    canonical_name: str = Field(alias="canonicalName")
    internal_code: str | None = Field(default=None, alias="internalCode")
    node_type: str = Field(alias="nodeType")
    instrument_type: str | None = Field(default=None, alias="instrumentType")
    asset_class: str | None = Field(default=None, alias="assetClass")
    base_currency: str | None = Field(default=None, alias="baseCurrency")
    status: str
    is_tradable: bool = Field(alias="isTradable")
    parent_reference_node_id: UUID | None = Field(default=None, alias="parentReferenceNodeId")
    market_venue_mic: str | None = Field(default=None, alias="marketVenueMic")
    venue_name: str | None = Field(default=None, alias="venueName")
    trading_symbol: str | None = Field(default=None, alias="tradingSymbol")
    trading_currency: str | None = Field(default=None, alias="tradingCurrency")

    model_config = ConfigDict(populate_by_name=True)


class ReferenceNodeSearchResponse(BaseModel):
    data: list[ReferenceNodeOptionView]
    meta: ApiMeta


class MappingProposalRequest(BaseModel):
    namespace: str = Field(min_length=1, max_length=150)
    external_object_type: str = Field(alias="externalObjectType", min_length=1, max_length=50)
    external_id: str = Field(alias="externalId", min_length=1, max_length=500)
    target_object_type: str = Field(alias="targetObjectType", min_length=1, max_length=50)
    target_object_id: UUID = Field(alias="targetObjectId")
    context_market_venue_id: UUID | None = Field(default=None, alias="contextMarketVenueId")
    valid_from: date = Field(alias="validFrom")
    reason: str = Field(min_length=1, max_length=2000)

    model_config = ConfigDict(populate_by_name=True)


class MappingProposalView(BaseModel):
    proposal_id: UUID = Field(alias="proposalId")
    status: str
    proposal_type: str = Field(alias="proposalType")
    proposed_at: str = Field(alias="proposedAt")
    namespace: str
    external_id: str = Field(alias="externalId")
    target_object_type: str = Field(alias="targetObjectType")
    target_object_id: UUID = Field(alias="targetObjectId")

    model_config = ConfigDict(populate_by_name=True)


class MappingDecisionRequest(BaseModel):
    decision: str = Field(pattern="^(APPROVED|REJECTED)$")
    reason: str = Field(min_length=1, max_length=2000)


class ReferenceDataProposalView(BaseModel):
    """Tenant-scoped, type-neutral view used by the steward review screen.

    The payload is intentionally retained as a structured proposal rather than
    flattened into a union of every instrument-specific contract.  The
    type-specific approval service remains the authority for validation and
    materialisation; this view gives the UI one stable envelope for discovery,
    evidence, and decision status.
    """

    proposal_id: UUID = Field(alias="proposalId")
    reference_node_id: UUID | None = Field(default=None, alias="referenceNodeId")
    proposal_type: str = Field(alias="proposalType")
    status: str
    submission_mode: str = Field(alias="submissionMode")
    match_status: str | None = Field(default=None, alias="matchStatus")
    confidence_score: str | None = Field(default=None, alias="confidenceScore")
    payload_schema_version: str = Field(alias="payloadSchemaVersion")
    proposed_payload: dict[str, Any] = Field(alias="proposedPayload")
    proposed_at: str = Field(alias="proposedAt")
    decision: str | None = None
    decision_method: str | None = Field(default=None, alias="decisionMethod")
    decision_evidence: dict[str, Any] | None = Field(default=None, alias="decisionEvidence")
    decision_reason: str | None = Field(default=None, alias="decisionReason")
    decided_at: str | None = Field(default=None, alias="decidedAt")

    model_config = ConfigDict(populate_by_name=True)


class ReferenceDataProposalResponse(BaseModel):
    data: ReferenceDataProposalView
    meta: ApiMeta


class EquityListingProposal(BaseModel):
    """Venue representation included in an onboarding proposal.

    The endpoint name is retained for backwards compatibility, but the
    listing contract is deliberately reusable for equities, cryptoassets, and
    other approved instruments. Venue/product identifiers are operational
    listing identifiers, not provider aliases for the economic instrument.
    """

    market_venue_id: UUID = Field(alias="marketVenueId")
    trading_symbol: str = Field(alias="tradingSymbol", min_length=1, max_length=100)
    figi: str | None = Field(default=None, min_length=1, max_length=50)
    venue_product_id: str | None = Field(default=None, alias="venueProductId", min_length=1, max_length=250)
    fix_security_id: str | None = Field(default=None, alias="fixSecurityId", min_length=1, max_length=250)
    trading_currency_id: UUID = Field(alias="tradingCurrencyId")
    quote_factor: Decimal = Field(default=Decimal("1"), alias="quoteFactor", gt=0)
    unit_multiplier: Decimal = Field(default=Decimal("1"), alias="unitMultiplier", gt=0)
    is_primary_listing: bool = Field(default=False, alias="isPrimaryListing")
    effective_from: date = Field(alias="effectiveFrom")

    model_config = ConfigDict(populate_by_name=True)


class BondProposalRequest(BaseModel):
    """Sparse bond identity proposal; detailed economics may be provider-enriched."""

    canonical_name: str = Field(alias="canonicalName", min_length=1, max_length=500)
    internal_code: str | None = Field(default=None, alias="internalCode", max_length=100)
    issuer_organisation_id: UUID | None = Field(default=None, alias="issuerOrganisationId")
    base_currency_id: UUID | None = Field(default=None, alias="baseCurrencyId")
    effective_from: date = Field(alias="effectiveFrom")
    issue_date: date | None = Field(default=None, alias="issueDate")
    interest_accrual_date: date | None = Field(default=None, alias="interestAccrualDate")
    first_coupon_date: date | None = Field(default=None, alias="firstCouponDate")
    maturity_date: date | None = Field(default=None, alias="maturityDate")
    final_settlement_date: date | None = Field(default=None, alias="finalSettlementDate")
    isin: str | None = Field(default=None, min_length=1, max_length=50)
    figi: str | None = Field(default=None, min_length=1, max_length=50)
    sedol: str | None = Field(default=None, min_length=1, max_length=50)
    cusip: str | None = Field(default=None, min_length=1, max_length=50)
    coupon_type: str = Field(alias="couponType", pattern="^(FIXED|ZERO|FLOATING)$")
    par_amount: Decimal | None = Field(default=None, alias="parAmount", gt=0)
    coupon_rate: Decimal | None = Field(default=None, alias="couponRate", ge=0)
    coupon_frequency_per_year: int | None = Field(default=None, alias="couponFrequencyPerYear", gt=0)
    day_count_convention: str | None = Field(default=None, alias="dayCountConvention", max_length=60, description="Governed day-count convention code from GET /v1/day-count-conventions; omit when not yet known.")
    floating_reference_index: str | None = Field(default=None, alias="floatingReferenceIndex", max_length=150)
    floating_spread: Decimal | None = Field(default=None, alias="floatingSpread")
    redemption_amount_per_par: Decimal | None = Field(default=None, alias="redemptionAmountPerPar", gt=0)
    submission_mode: str = Field(default="MANUAL", alias="submissionMode", pattern="^(MANUAL|AUTOMATED)$")
    source_system_id: UUID | None = Field(default=None, alias="sourceSystemId")
    source_payload_id: UUID | None = Field(default=None, alias="sourcePayloadId")
    source_namespace: str | None = Field(default=None, alias="sourceNamespace", max_length=150)
    source_external_id: str | None = Field(default=None, alias="sourceExternalId", max_length=500)
    idempotency_key: str | None = Field(default=None, alias="idempotencyKey", max_length=500)
    confidence_score: Decimal | None = Field(default=None, alias="confidenceScore", ge=0, le=1)

    model_config = ConfigDict(populate_by_name=True)


class BondProposalView(BaseModel):
    proposal_id: UUID = Field(alias="proposalId")
    status: str
    proposal_type: str = Field(alias="proposalType")
    submission_mode: str = Field(alias="submissionMode")
    coupon_type: str = Field(alias="couponType")
    enrichment_status: str = Field(alias="enrichmentStatus")
    instrument_id: UUID | None = Field(default=None, alias="instrumentId")
    proposed_at: str = Field(alias="proposedAt")

    model_config = ConfigDict(populate_by_name=True)


class BondProposalResponse(BaseModel):
    data: BondProposalView
    meta: ApiMeta


class FxForwardProposalRequest(BaseModel):
    """Manual-first proposal for one OTC FX-forward economic contract.

    The base/quote currencies and forward rate describe the contractual
    exchange-rate convention.  Maturity and settlement dates are written to
    the common instrument-date record; a trade-specific monetary MTM remains
    a valuation/market-data concern rather than a term on this contract.
    """

    canonical_name: str = Field(alias="canonicalName", min_length=1, max_length=500)
    internal_code: str | None = Field(default=None, alias="internalCode", max_length=100)
    effective_from: date = Field(alias="effectiveFrom")
    base_currency_id: UUID = Field(alias="baseCurrencyId")
    quote_currency_id: UUID = Field(alias="quoteCurrencyId")
    quote_convention: str = Field(alias="quoteConvention", min_length=3, max_length=40, pattern="^[A-Z0-9_]+$")
    agreed_forward_rate: Decimal = Field(alias="agreedForwardRate", gt=0)
    settlement_type: str = Field(alias="settlementType", pattern="^(DELIVERABLE|NDF|CASH)$")
    fixing_currency_id: UUID | None = Field(default=None, alias="fixingCurrencyId")
    maturity_date: date = Field(alias="maturityDate")
    settlement_date: date | None = Field(default=None, alias="settlementDate")
    cash_settlement_date: date | None = Field(default=None, alias="cashSettlementDate")
    final_settlement_date: date | None = Field(default=None, alias="finalSettlementDate")
    submission_mode: str = Field(default="MANUAL", alias="submissionMode", pattern="^(MANUAL|AUTOMATED)$")
    source_system_id: UUID | None = Field(default=None, alias="sourceSystemId")
    source_payload_id: UUID | None = Field(default=None, alias="sourcePayloadId")
    idempotency_key: str | None = Field(default=None, alias="idempotencyKey", max_length=500)
    confidence_score: Decimal | None = Field(default=None, alias="confidenceScore", ge=0, le=1)

    model_config = ConfigDict(populate_by_name=True)


class FxForwardProposalView(BaseModel):
    proposal_id: UUID = Field(alias="proposalId")
    status: str
    proposal_type: str = Field(alias="proposalType")
    submission_mode: str = Field(alias="submissionMode")
    base_currency_id: UUID = Field(alias="baseCurrencyId")
    quote_currency_id: UUID = Field(alias="quoteCurrencyId")
    quote_convention: str = Field(alias="quoteConvention")
    agreed_forward_rate: str = Field(alias="agreedForwardRate")
    settlement_type: str = Field(alias="settlementType")
    maturity_date: date = Field(alias="maturityDate")
    instrument_id: UUID | None = Field(default=None, alias="instrumentId")
    proposed_at: str = Field(alias="proposedAt")

    model_config = ConfigDict(populate_by_name=True)


class FxForwardProposalResponse(BaseModel):
    data: FxForwardProposalView
    meta: ApiMeta


class EtpProposalRequest(BaseModel):
    """Manual-first proposal for an ETF, ETC, ETN, ETV, or ETI economic instrument."""

    canonical_name: str = Field(alias="canonicalName", min_length=1, max_length=500)
    internal_code: str | None = Field(default=None, alias="internalCode", max_length=100)
    issuer_organisation_id: UUID | None = Field(default=None, alias="issuerOrganisationId")
    base_currency_id: UUID | None = Field(default=None, alias="baseCurrencyId")
    effective_from: date = Field(alias="effectiveFrom")
    etp_kind: str = Field(alias="etpKind", pattern="^(ETF|ETC|ETN|ETV|ETI)$")
    legal_form: str = Field(alias="legalForm", min_length=1, max_length=50)
    replication_method: str = Field(default="NOT_APPLICABLE", alias="replicationMethod", max_length=30)
    collateralisation_type: str = Field(default="NOT_APPLICABLE", alias="collateralisationType", max_length=30)
    redemption_model: str = Field(alias="redemptionModel", min_length=1, max_length=40)
    distribution_policy: str | None = Field(default=None, alias="distributionPolicy", max_length=30)
    reference_node_id: UUID | None = Field(default=None, alias="referenceNodeId")
    isin: str | None = Field(default=None, min_length=1, max_length=50)
    submission_mode: str = Field(default="MANUAL", alias="submissionMode", pattern="^(MANUAL|AUTOMATED)$")
    source_system_id: UUID | None = Field(default=None, alias="sourceSystemId")
    source_payload_id: UUID | None = Field(default=None, alias="sourcePayloadId")
    idempotency_key: str | None = Field(default=None, alias="idempotencyKey", max_length=500)
    confidence_score: Decimal | None = Field(default=None, alias="confidenceScore", ge=0, le=1)

    model_config = ConfigDict(populate_by_name=True)


class EtpProposalView(BaseModel):
    proposal_id: UUID = Field(alias="proposalId")
    status: str
    proposal_type: str = Field(alias="proposalType")
    submission_mode: str = Field(alias="submissionMode")
    etp_kind: str = Field(alias="etpKind")
    instrument_id: UUID | None = Field(default=None, alias="instrumentId")
    proposed_at: str = Field(alias="proposedAt")

    model_config = ConfigDict(populate_by_name=True)


class EtpProposalResponse(BaseModel):
    data: EtpProposalView
    meta: ApiMeta


class CurrencyView(BaseModel):
    """Active currency or cryptoasset currency role used by onboarding."""

    currency_id: UUID = Field(alias="currencyId")
    currency_code: str = Field(alias="currencyCode")
    display_name: str = Field(alias="displayName")
    currency_kind: str = Field(alias="currencyKind")

    model_config = ConfigDict(populate_by_name=True)


class CurrencyGroupView(BaseModel):
    """A presentation group of currencies selected by the caller."""

    group_code: str = Field(alias="groupCode")
    label: str
    items: list[CurrencyView]

    model_config = ConfigDict(populate_by_name=True)


class CurrencyResponse(BaseModel):
    data: list[CurrencyGroupView]
    meta: ApiMeta


class ReturnProfileView(BaseModel):
    """Governed performance-return semantics for an index variant."""

    return_profile_id: UUID = Field(alias="returnProfileId")
    profile_code: str = Field(alias="profileCode")
    display_name: str = Field(alias="displayName")
    description: str
    base_return_basis: str = Field(alias="baseReturnBasis")
    income_treatment: str = Field(alias="incomeTreatment")

    model_config = ConfigDict(populate_by_name=True)


class ReturnProfileResponse(BaseModel):
    data: list[ReturnProfileView]
    meta: ApiMeta


class IndexKindView(BaseModel):
    """Governed index-kind semantics used by onboarding and Operations UI."""

    index_kind_code: str = Field(alias="indexKindCode")
    display_name: str = Field(alias="displayName")
    description: str
    dissemination_class: str = Field(alias="disseminationClass")
    methodology_ownership: str = Field(alias="methodologyOwnership")
    example_text: str | None = Field(default=None, alias="exampleText")
    status: str

    model_config = ConfigDict(populate_by_name=True)


class IndexKindResponse(BaseModel):
    data: list[IndexKindView]
    meta: ApiMeta


class OrganisationOptionView(BaseModel):
    """Active organisation option for an administrative instrument role."""

    organisation_id: UUID = Field(alias="organisationId")
    display_name: str = Field(alias="displayName")
    legal_name: str | None = Field(default=None, alias="legalName")
    status: str

    model_config = ConfigDict(populate_by_name=True)


class OrganisationOptionResponse(BaseModel):
    data: list[OrganisationOptionView]
    meta: ApiMeta


class IndexFamilyOptionView(BaseModel):
    """Visible active index family option used by index onboarding."""

    index_family_id: UUID = Field(alias="indexFamilyId")
    family_node_id: UUID = Field(alias="familyNodeId")
    family_name: str = Field(alias="familyName")
    provider_organisation_id: UUID | None = Field(default=None, alias="providerOrganisationId")
    provider_organisation_name: str | None = Field(default=None, alias="providerOrganisationName")

    model_config = ConfigDict(populate_by_name=True)


class IndexFamilyOptionResponse(BaseModel):
    data: list[IndexFamilyOptionView]
    meta: ApiMeta


class IndexFamilyProposalRequest(BaseModel):
    """Manual-first proposal for one conceptual, non-tradable index family."""

    canonical_name: str = Field(alias="canonicalName", min_length=1, max_length=500)
    internal_code: str | None = Field(default=None, alias="internalCode", max_length=100)
    provider_organisation_id: UUID | None = Field(default=None, alias="providerOrganisationId")
    submission_mode: str = Field(default="MANUAL", alias="submissionMode", pattern="^(MANUAL|AUTOMATED)$")
    source_system_id: UUID | None = Field(default=None, alias="sourceSystemId")
    source_payload_id: UUID | None = Field(default=None, alias="sourcePayloadId")
    idempotency_key: str | None = Field(default=None, alias="idempotencyKey", max_length=500)
    confidence_score: Decimal | None = Field(default=None, alias="confidenceScore", ge=0, le=1)

    model_config = ConfigDict(populate_by_name=True)


class IndexFamilyProposalView(BaseModel):
    proposal_id: UUID = Field(alias="proposalId")
    status: str
    proposal_type: str = Field(alias="proposalType")
    submission_mode: str = Field(alias="submissionMode")
    family_name: str = Field(alias="familyName")
    family_id: UUID | None = Field(default=None, alias="familyId")
    family_node_id: UUID | None = Field(default=None, alias="familyNodeId")
    proposed_at: str = Field(alias="proposedAt")

    model_config = ConfigDict(populate_by_name=True)


class IndexFamilyProposalResponse(BaseModel):
    data: IndexFamilyProposalView
    meta: ApiMeta


class IndexProposalRequest(BaseModel):
    """Manual-first proposal for one concrete index return/currency variant."""

    canonical_name: str = Field(alias="canonicalName", min_length=1, max_length=500)
    internal_code: str | None = Field(default=None, alias="internalCode", max_length=100)
    effective_from: date = Field(alias="effectiveFrom")
    index_kind: str = Field(alias="indexKind", min_length=1, max_length=40)
    index_family_id: UUID | None = Field(default=None, alias="indexFamilyId")
    index_family_name: str | None = Field(default=None, alias="indexFamilyName", max_length=500)
    return_profile_id: UUID | None = Field(default=None, alias="returnProfileId")
    base_currency_id: UUID | None = Field(default=None, alias="baseCurrencyId")
    administrator_organisation_id: UUID | None = Field(default=None, alias="administratorOrganisationId")
    calculation_agent_organisation_id: UUID | None = Field(default=None, alias="calculationAgentOrganisationId")
    base_date: date | None = Field(default=None, alias="baseDate")
    base_level: Decimal | None = Field(default=None, alias="baseLevel")
    methodology_reference: str | None = Field(default=None, alias="methodologyReference", max_length=500)
    weighting_method: str | None = Field(default=None, alias="weightingMethod", max_length=100)
    rebalance_frequency: str | None = Field(default=None, alias="rebalanceFrequency", max_length=100)
    calculation_frequency: str | None = Field(default=None, alias="calculationFrequency", max_length=100)
    dividend_treatment: str | None = Field(default=None, alias="dividendTreatment", max_length=100)
    launch_date: date | None = Field(default=None, alias="launchDate")
    is_backtested_history: bool = Field(default=False, alias="isBacktestedHistory")
    methodology_document_uri: str | None = Field(default=None, alias="methodologyDocumentUri", max_length=1000)
    submission_mode: str = Field(default="MANUAL", alias="submissionMode", pattern="^(MANUAL|AUTOMATED)$")
    source_system_id: UUID | None = Field(default=None, alias="sourceSystemId")
    source_payload_id: UUID | None = Field(default=None, alias="sourcePayloadId")
    source_namespace: str | None = Field(default=None, alias="sourceNamespace", max_length=150)
    source_external_id: str | None = Field(default=None, alias="sourceExternalId", max_length=500)
    idempotency_key: str | None = Field(default=None, alias="idempotencyKey", max_length=500)
    confidence_score: Decimal | None = Field(default=None, alias="confidenceScore", ge=0, le=1)

    model_config = ConfigDict(populate_by_name=True)


class IndexProposalView(BaseModel):
    proposal_id: UUID = Field(alias="proposalId")
    status: str
    proposal_type: str = Field(alias="proposalType")
    submission_mode: str = Field(alias="submissionMode")
    index_kind: str = Field(alias="indexKind")
    index_id: UUID | None = Field(default=None, alias="indexId")
    proposed_at: str = Field(alias="proposedAt")

    model_config = ConfigDict(populate_by_name=True)


class IndexProposalResponse(BaseModel):
    data: IndexProposalView
    meta: ApiMeta


class EquityProposalRequest(BaseModel):
    """Canonical equity facts accepted from a steward or governed adapter."""

    canonical_name: str = Field(alias="canonicalName", min_length=1, max_length=500)
    internal_code: str | None = Field(default=None, alias="internalCode", max_length=100)
    issuer_organisation_id: UUID | None = Field(default=None, alias="issuerOrganisationId")
    base_currency_id: UUID = Field(alias="baseCurrencyId")
    effective_from: date = Field(alias="effectiveFrom")
    isin: str | None = Field(default=None, min_length=1, max_length=50)
    figi: str | None = Field(default=None, min_length=1, max_length=50)
    sedol: str | None = Field(default=None, min_length=1, max_length=50)
    cusip: str | None = Field(default=None, min_length=1, max_length=50)
    cfi: str | None = Field(default=None, min_length=1, max_length=20)
    # Instrument creation is intentionally independent from venue listings.
    # An OTC/economic instrument may legitimately have zero listings at first.
    listings: list[EquityListingProposal] = Field(default_factory=list, max_length=20)
    submission_mode: str = Field(default="MANUAL", alias="submissionMode", pattern="^(MANUAL|AUTOMATED)$")
    source_system_id: UUID | None = Field(default=None, alias="sourceSystemId")
    source_payload_id: UUID | None = Field(default=None, alias="sourcePayloadId")
    source_namespace: str | None = Field(default=None, alias="sourceNamespace", max_length=150)
    source_external_id: str | None = Field(default=None, alias="sourceExternalId", max_length=500)
    source_object_type: str = Field(default="INSTRUMENT", alias="sourceObjectType", pattern="^(INSTRUMENT|LISTING)$")
    automation_policy_code: str | None = Field(default=None, alias="automationPolicyCode", max_length=100)
    idempotency_key: str | None = Field(default=None, alias="idempotencyKey", max_length=500)
    confidence_score: Decimal | None = Field(default=None, alias="confidenceScore", ge=0, le=1)

    model_config = ConfigDict(populate_by_name=True)


class EquityListingCreateProposalRequest(BaseModel):
    """Proposal to add one venue listing to an already-approved instrument."""

    instrument_id: UUID = Field(alias="instrumentId")
    listing: EquityListingProposal
    submission_mode: str = Field(default="MANUAL", alias="submissionMode", pattern="^(MANUAL|AUTOMATED)$")
    source_system_id: UUID | None = Field(default=None, alias="sourceSystemId")
    source_payload_id: UUID | None = Field(default=None, alias="sourcePayloadId")
    source_namespace: str | None = Field(default=None, alias="sourceNamespace", max_length=150)
    source_external_id: str | None = Field(default=None, alias="sourceExternalId", max_length=500)
    idempotency_key: str | None = Field(default=None, alias="idempotencyKey", max_length=500)
    confidence_score: Decimal | None = Field(default=None, alias="confidenceScore", ge=0, le=1)

    model_config = ConfigDict(populate_by_name=True)


class CryptoAssetProposalRequest(BaseModel):
    """Manual-first proposal for one canonical cryptoasset economic instrument.

    The proposal creates the economic DIGITAL_ASSET identity and its optional
    currency role.  Chain deployments and venue listings are deliberately
    separate follow-up workflows because one asset may exist on multiple
    networks and trade on many venues.
    """

    canonical_name: str = Field(alias="canonicalName", min_length=1, max_length=500)
    internal_code: str | None = Field(default=None, alias="internalCode", max_length=100)
    effective_from: date = Field(alias="effectiveFrom")
    asset_subtype: str = Field(alias="assetSubtype", pattern="^(NATIVE|TOKEN|STABLECOIN|WRAPPED|BRIDGED|OTHER)$")
    native_symbol: str = Field(alias="nativeSymbol", min_length=1, max_length=50)
    protocol_name: str | None = Field(default=None, alias="protocolName", max_length=150)
    issuer_organisation_id: UUID | None = Field(default=None, alias="issuerOrganisationId")
    decimals: int | None = Field(default=None, ge=0, le=36, description="Smallest-unit decimal precision when known; used for the cryptoasset currency role and deployments.")
    submission_mode: str = Field(default="MANUAL", alias="submissionMode", pattern="^(MANUAL|AUTOMATED)$")
    source_system_id: UUID | None = Field(default=None, alias="sourceSystemId")
    source_payload_id: UUID | None = Field(default=None, alias="sourcePayloadId")
    idempotency_key: str | None = Field(default=None, alias="idempotencyKey", max_length=500)
    confidence_score: Decimal | None = Field(default=None, alias="confidenceScore", ge=0, le=1)

    model_config = ConfigDict(populate_by_name=True)


class CryptoAssetProposalView(BaseModel):
    proposal_id: UUID = Field(alias="proposalId")
    status: str
    proposal_type: str = Field(alias="proposalType")
    submission_mode: str = Field(alias="submissionMode")
    canonical_name: str = Field(alias="canonicalName")
    internal_code: str | None = Field(default=None, alias="internalCode")
    effective_from: date = Field(alias="effectiveFrom")
    asset_subtype: str = Field(alias="assetSubtype")
    native_symbol: str = Field(alias="nativeSymbol")
    protocol_name: str | None = Field(default=None, alias="protocolName")
    issuer_organisation_id: UUID | None = Field(default=None, alias="issuerOrganisationId")
    decimals: int | None = None
    instrument_id: UUID | None = Field(default=None, alias="instrumentId")
    currency_id: UUID | None = Field(default=None, alias="currencyId")
    currency_code: str | None = Field(default=None, alias="currencyCode")
    proposed_at: str = Field(alias="proposedAt")

    model_config = ConfigDict(populate_by_name=True)


class CryptoAssetProposalResponse(BaseModel):
    data: CryptoAssetProposalView
    meta: ApiMeta


class EquityProposalView(BaseModel):
    proposal_id: UUID = Field(alias="proposalId")
    status: str
    proposal_type: str = Field(alias="proposalType")
    submission_mode: str = Field(alias="submissionMode")
    match_status: str = Field(alias="matchStatus")
    confidence_score: str | None = Field(default=None, alias="confidenceScore")
    automation_policy_id: UUID | None = Field(default=None, alias="automationPolicyId")
    instrument_id: UUID | None = Field(default=None, alias="instrumentId")
    listing_ids: list[UUID] = Field(default_factory=list, alias="listingIds")
    proposed_at: str = Field(alias="proposedAt")
    decision_method: str | None = Field(default=None, alias="decisionMethod")
    decision_evidence: dict[str, object] | None = Field(default=None, alias="decisionEvidence")

    model_config = ConfigDict(populate_by_name=True)


class EquityProposalResponse(BaseModel):
    data: EquityProposalView
    meta: ApiMeta


class StructuredProductProposalView(BaseModel):
    """Stable view of a structured-product proposal and its generated graph."""

    proposal_id: UUID = Field(alias="proposalId")
    status: str
    proposal_type: str = Field(alias="proposalType")
    submission_mode: str = Field(alias="submissionMode")
    product_subtype: str = Field(alias="productSubtype")
    instrument_id: UUID | None = Field(default=None, alias="instrumentId")
    terms_id: UUID | None = Field(default=None, alias="termsId")
    component_instrument_ids: list[UUID] = Field(default_factory=list, alias="componentInstrumentIds")
    composition_ids: list[UUID] = Field(default_factory=list, alias="compositionIds")
    condition_group_ids: list[UUID] = Field(default_factory=list, alias="conditionGroupIds")
    action_ids: list[UUID] = Field(default_factory=list, alias="actionIds")
    initial_fixing_ids: list[UUID] = Field(default_factory=list, alias="initialFixingIds")
    proposed_at: str = Field(alias="proposedAt")
    decision_evidence: dict[str, Any] | None = Field(default=None, alias="decisionEvidence")

    model_config = ConfigDict(populate_by_name=True)


class StructuredProductProposalResponse(BaseModel):
    data: StructuredProductProposalView
    meta: ApiMeta


class WorkQueueItemView(BaseModel):
    item_id: str = Field(alias="itemId")
    category: str
    title: str
    detail: str
    status: str
    proposal_type: str | None = Field(default=None, alias="proposalType")
    reference_id: UUID | None = Field(default=None, alias="referenceId")
    review_path: str | None = Field(default=None, alias="reviewPath")

    model_config = ConfigDict(populate_by_name=True)


class WorkQueueView(BaseModel):
    counts: dict[str, int]
    items: list[WorkQueueItemView]
    meta: ApiMeta


class ErrorView(BaseModel):
    code: str
    message: str
    correlation_id: str = Field(alias="correlationId")

    model_config = ConfigDict(populate_by_name=True)
