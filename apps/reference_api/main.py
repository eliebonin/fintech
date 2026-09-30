"""FastAPI application factory for canonical reference-data services."""

from datetime import date
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Response, status
from sqlalchemy import Engine, select

from security_master_schema import models as m

from .config import Settings
from .problem_details import ApiProblem, configure_problem_details, current_request_id
from .contracts import (
    BondProposalRequest,
    BondProposalResponse,
    CryptoAssetProposalRequest,
    CryptoAssetProposalResponse,
    CurrencyResponse,
    DayCountConventionResponse,
    EquityListingCreateProposalRequest,
    EtpProposalRequest,
    EtpProposalResponse,
    FxForwardProposalRequest,
    FxForwardProposalResponse,
    InstrumentSearchResponse,
    InstrumentView,
    ReferenceNodeSearchResponse,
    IndexFamilyOptionResponse,
    IndexFamilyProposalRequest,
    IndexFamilyProposalResponse,
    IndexKindResponse,
    IndexProposalRequest,
    IndexProposalResponse,
    EquityProposalRequest,
    EquityProposalResponse,
    MappingDecisionRequest,
    MappingProposalRequest,
    MappingProposalView,
    MarketDataResolutionSnapshotCreate,
    MarketDataResolutionSnapshotView,
    ActiveValuationPolicyView,
    MarketDataSeriesResponse,
    MarketVenueResponse,
    PortfolioPnlResponse,
    OrganisationOptionResponse,
    ReferenceDataProposalResponse,
    ReturnProfileResponse,
    StructuredProductProposalResponse,
    TradeDetailResponse,
    TradeResponse,
    WorkQueueView,
    StrategyCreateRequest,
    StrategyResponse,
    StrategyListResponse,
    StrategyStatusRequest,
    TenantMembershipResponse,
    TenantMembershipView,
    TenantWorkspaceResponse,
    TenantWorkspaceView,
)
from .structured_product_contracts import AutocallDraftRequest, StructuredProductDraftError
from .db import get_engine
from .repository import IdempotencyKeyConflict, InvalidCatalogueValue, InvalidWorkflowState, RepositoryNotFound, create_market_data_resolution_snapshot, create_mapping_proposal, decide_crypto_asset_proposal, decide_etp_proposal, decide_fx_forward_proposal, decide_index_family_proposal, decide_index_proposal, decide_mapping_proposal, decide_bond_proposal, decide_equity_proposal, decide_reference_data_proposal, decide_structured_product_proposal, get_market_data_resolution_snapshot, get_booked_trade_detail, get_crypto_asset_proposal, get_instrument, get_reference_data_proposal, list_active_valuation_policies, list_booked_trades, list_currencies, list_day_count_conventions, list_index_families, list_index_kinds, list_market_data_series, list_market_venues, list_organisations, list_return_profiles, parse_currency_groups, portfolio_pnl, search_instruments, search_reference_nodes, submit_bond_proposal, submit_crypto_asset_proposal, submit_etp_proposal, submit_fx_forward_proposal, submit_equity_listing_proposal, submit_equity_proposal, submit_index_family_proposal, submit_index_proposal, submit_structured_product_proposal, work_queue
from .tenant_context import TenantContext, get_tenant_context, require_actor
from .tenant_context import ActorContext, get_actor_context
from .repository import create_strategy
from .repository import list_strategies
from .repository import get_strategy
from .repository import archive_strategy
from security_master_schema.tenant_workspace import TenantActionForbidden, list_active_tenant_memberships, require_tenant_action, resolve_platform_role, resolve_tenant_workspace


def _correlation_id(value: str | None) -> str:
    """Retain response metadata compatibility while using the request boundary ID."""

    return current_request_id()


def create_app(*, settings: Settings | None = None, engine: Engine | None = None) -> FastAPI:
    resolved_settings = settings or Settings.from_environment()
    app = FastAPI(title="Reference Data API", version=resolved_settings.api_version)
    configure_problem_details(app)

    def connection_dependency():
        with (engine or get_engine(resolved_settings)).begin() as connection:
            yield connection

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "reference-api"}

    @app.get("/v1/session/memberships", response_model=TenantMembershipResponse)
    def memberships(context: ActorContext = Depends(get_actor_context), connection=Depends(connection_dependency)) -> TenantMembershipResponse:
        _assert_active_actor(connection, context.user_account_id)
        rows = list_active_tenant_memberships(connection, context.user_account_id, date.today())
        return TenantMembershipResponse(data=[TenantMembershipView(tenantId=row.tenant_id, tenantCode=row.tenant_code, tenantName=row.tenant_name, membershipRole=row.membership_role) for row in rows], platformRole=resolve_platform_role(connection, context.user_account_id, date.today()))

    @app.get("/v1/tenant-workspace", response_model=TenantWorkspaceResponse)
    def tenant_workspace(context: TenantContext = Depends(get_tenant_context), connection=Depends(connection_dependency)) -> TenantWorkspaceResponse:
        actor_id = _assert_tenant_membership(connection, context)
        try:
            workspace = resolve_tenant_workspace(connection, context.tenant_id, actor_id, date.today())
        except TenantActionForbidden as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant is outside the actor's active memberships") from exc
        return TenantWorkspaceResponse(data=TenantWorkspaceView(
            tenantId=workspace.tenant_id,
            tenantCode=workspace.tenant_code,
            tenantName=workspace.tenant_name,
            membershipRole=workspace.membership_role,
            moduleCodes=sorted(workspace.module_codes),
            platformRole=workspace.platform_role,
        ))

    @app.post("/v1/strategies", response_model=StrategyResponse, status_code=status.HTTP_201_CREATED)
    def create_tenant_strategy(request: StrategyCreateRequest, context: TenantContext = Depends(get_tenant_context), connection=Depends(connection_dependency)) -> StrategyResponse:
        actor_id = _assert_tenant_membership(connection, context)
        try:
            require_tenant_action(resolve_tenant_workspace(connection, context.tenant_id, actor_id, date.today()), "STRATEGY_WRITE")
            with connection.begin_nested():
                return StrategyResponse(data=create_strategy(connection, context.tenant_id, actor_id, request))
        except TenantActionForbidden as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant membership is not permitted to manage strategies") from exc
        except ValueError as exc:
            raise ApiProblem(status.HTTP_422_UNPROCESSABLE_ENTITY, "request.validation_failed", "Request validation failed", "One or more request fields are invalid.") from exc

    @app.get("/v1/strategies", response_model=StrategyListResponse)
    def tenant_strategies(context: TenantContext = Depends(get_tenant_context), connection=Depends(connection_dependency)) -> StrategyListResponse:
        _assert_tenant_membership(connection, context)
        return list_strategies(connection, context.tenant_id)

    @app.get("/v1/strategies/{strategy_id}", response_model=StrategyResponse)
    def tenant_strategy_detail(strategy_id: UUID, context: TenantContext = Depends(get_tenant_context), connection=Depends(connection_dependency)) -> StrategyResponse:
        _assert_tenant_membership(connection, context)
        result = get_strategy(connection, context.tenant_id, strategy_id)
        if result is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")
        return StrategyResponse(data=result)

    @app.post("/v1/strategies/{strategy_id}/status", response_model=StrategyResponse)
    def tenant_strategy_status(strategy_id: UUID, request: StrategyStatusRequest, context: TenantContext = Depends(get_tenant_context), connection=Depends(connection_dependency)) -> StrategyResponse:
        actor_id = _assert_tenant_membership(connection, context)
        try:
            require_tenant_action(resolve_tenant_workspace(connection, context.tenant_id, actor_id, date.today()), "STRATEGY_WRITE")
            with connection.begin_nested():
                result = archive_strategy(connection, context.tenant_id, strategy_id, request)
        except TenantActionForbidden as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant membership is not permitted to manage strategies") from exc
        if result is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")
        return StrategyResponse(data=result)

    @app.get("/v1/instruments/search")
    def search(
        q: str = Query(default="", max_length=200),
        instrument_type: str | None = Query(default=None, max_length=80),
        asset_class: str | None = Query(default=None, max_length=80),
        status: str | None = Query(default=None, max_length=80),
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
        context: TenantContext = Depends(get_tenant_context),
        connection=Depends(connection_dependency),
        x_correlation_id: str | None = Header(default=None),
    ) -> InstrumentSearchResponse:
        _assert_tenant_membership(connection, context)
        return search_instruments(
            connection,
            context.tenant_id,
            q,
            limit,
            offset,
            resolved_settings.api_version,
            _correlation_id(x_correlation_id),
            instrument_type,
            asset_class,
            status,
        )

    @app.get("/v1/instruments/{instrument_id}")
    def detail(
        instrument_id: UUID,
        context: TenantContext = Depends(get_tenant_context),
        connection=Depends(connection_dependency),
        x_correlation_id: str | None = Header(default=None),
    ) -> dict[str, object]:
        _assert_tenant_membership(connection, context)
        instrument = get_instrument(connection, context.tenant_id, instrument_id)
        if instrument is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instrument not found")
        return {
            "data": instrument,
            "meta": {
                "tenantContext": str(context.tenant_id),
                "source": "live-reference-api",
                "apiVersion": resolved_settings.api_version,
                "correlationId": _correlation_id(x_correlation_id),
            },
        }

    @app.get("/v1/reference-nodes/search", response_model=ReferenceNodeSearchResponse)
    def reference_nodes_search(
        q: str = Query(default="", max_length=200),
        node_type: str | None = Query(default=None, max_length=300),
        instrument_type: str | None = Query(default=None, max_length=300),
        asset_class: str | None = Query(default=None, max_length=80),
        reference_level: str = Query(default="ANY", pattern="^(ANY|ECONOMIC|LISTING)$"),
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
        context: TenantContext = Depends(get_tenant_context),
        connection=Depends(connection_dependency),
        x_correlation_id: str | None = Header(default=None),
    ) -> ReferenceNodeSearchResponse:
        """Search visible instrument and non-instrument reference nodes."""

        _assert_tenant_membership(connection, context)
        return search_reference_nodes(
            connection,
            context.tenant_id,
            q,
            limit,
            offset,
            resolved_settings.api_version,
            _correlation_id(x_correlation_id),
            node_type,
            instrument_type,
            asset_class,
            reference_level,
        )

    @app.get("/v1/reference-data-proposals/{proposal_id}", response_model=ReferenceDataProposalResponse)
    def get_reference_proposal(
        proposal_id: UUID,
        context: TenantContext = Depends(get_tenant_context),
        connection=Depends(connection_dependency),
        x_correlation_id: str | None = Header(default=None),
    ) -> ReferenceDataProposalResponse:
        """Return a single tenant-scoped proposal for the generic review UI."""

        _assert_tenant_membership(connection, context)
        try:
            proposal = get_reference_data_proposal(connection, context.tenant_id, proposal_id)
        except RepositoryNotFound as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        return ReferenceDataProposalResponse(
            data=proposal,
            meta={
                "tenantContext": str(context.tenant_id),
                "source": "live-reference-api",
                "apiVersion": resolved_settings.api_version,
                "correlationId": _correlation_id(x_correlation_id),
            },
        )

    @app.post("/v1/reference-data-proposals/{proposal_id}/decision", response_model=ReferenceDataProposalResponse)
    def decide_reference_proposal(
        proposal_id: UUID,
        request: MappingDecisionRequest,
        context: TenantContext = Depends(get_tenant_context),
        connection=Depends(connection_dependency),
        x_correlation_id: str | None = Header(default=None),
    ) -> ReferenceDataProposalResponse:
        """Dispatch a steward decision while retaining type-specific validation."""

        actor_id = _assert_tenant_membership(connection, context)
        try:
            with connection.begin_nested():
                proposal = decide_reference_data_proposal(
                    connection,
                    context.tenant_id,
                    actor_id,
                    proposal_id,
                    request.decision,
                    request.reason,
                )
        except RepositoryNotFound as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except InvalidWorkflowState as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        return ReferenceDataProposalResponse(
            data=proposal,
            meta={
                "tenantContext": str(context.tenant_id),
                "source": "live-reference-api",
                "apiVersion": resolved_settings.api_version,
                "correlationId": _correlation_id(x_correlation_id),
            },
        )

    @app.post("/v1/reference-mapping-proposals", response_model=MappingProposalView, status_code=status.HTTP_201_CREATED)
    def propose_mapping(
        request: MappingProposalRequest,
        context: TenantContext = Depends(get_tenant_context),
        connection=Depends(connection_dependency),
    ) -> MappingProposalView:
        actor_id = _assert_tenant_membership(connection, context)
        try:
            with connection.begin_nested():
                return create_mapping_proposal(connection, context.tenant_id, actor_id, request)
        except RepositoryNotFound as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    @app.post("/v1/reference-mapping-proposals/{proposal_id}/decision", response_model=MappingProposalView)
    def decide_mapping(
        proposal_id: UUID,
        request: MappingDecisionRequest,
        context: TenantContext = Depends(get_tenant_context),
        connection=Depends(connection_dependency),
    ) -> MappingProposalView:
        actor_id = _assert_tenant_membership(connection, context)
        try:
            with connection.begin_nested():
                return decide_mapping_proposal(connection, context.tenant_id, actor_id, proposal_id, request.decision, request.reason)
        except RepositoryNotFound as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except InvalidWorkflowState as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    @app.post("/v1/equity-proposals", response_model=EquityProposalResponse, status_code=status.HTTP_201_CREATED)
    def propose_equity(
        request: EquityProposalRequest,
        context: TenantContext = Depends(get_tenant_context),
        connection=Depends(connection_dependency),
        x_correlation_id: str | None = Header(default=None),
    ) -> EquityProposalResponse:
        actor_id = _assert_tenant_membership(connection, context)
        try:
            with connection.begin_nested():
                proposal = submit_equity_proposal(connection, context.tenant_id, actor_id, request)
        except RepositoryNotFound as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except InvalidWorkflowState as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        return EquityProposalResponse(
            data=proposal,
            meta={
                "tenantContext": str(context.tenant_id),
                "source": "live-reference-api",
                "apiVersion": resolved_settings.api_version,
                "correlationId": _correlation_id(x_correlation_id),
            },
        )

    @app.post("/v1/bond-proposals", response_model=BondProposalResponse, status_code=status.HTTP_201_CREATED)
    def propose_bond(
        request: BondProposalRequest,
        context: TenantContext = Depends(get_tenant_context),
        connection=Depends(connection_dependency),
        x_correlation_id: str | None = Header(default=None),
    ) -> BondProposalResponse:
        actor_id = _assert_tenant_membership(connection, context)
        try:
            with connection.begin_nested():
                proposal = submit_bond_proposal(connection, context.tenant_id, actor_id, request)
        except RepositoryNotFound as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except InvalidWorkflowState as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        return BondProposalResponse(
            data=proposal,
            meta={
                "tenantContext": str(context.tenant_id),
                "source": "live-reference-api",
                "apiVersion": resolved_settings.api_version,
                "correlationId": _correlation_id(x_correlation_id),
            },
        )

    @app.post("/v1/bond-proposals/{proposal_id}/decision", response_model=BondProposalResponse)
    def decide_bond(
        proposal_id: UUID,
        request: MappingDecisionRequest,
        context: TenantContext = Depends(get_tenant_context),
        connection=Depends(connection_dependency),
        x_correlation_id: str | None = Header(default=None),
    ) -> BondProposalResponse:
        actor_id = _assert_tenant_membership(connection, context)
        try:
            with connection.begin_nested():
                proposal = decide_bond_proposal(connection, context.tenant_id, actor_id, proposal_id, request.decision, request.reason)
        except RepositoryNotFound as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except InvalidWorkflowState as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        return BondProposalResponse(
            data=proposal,
            meta={
                "tenantContext": str(context.tenant_id),
                "source": "live-reference-api",
                "apiVersion": resolved_settings.api_version,
                "correlationId": _correlation_id(x_correlation_id),
            },
        )

    @app.post("/v1/etp-proposals", response_model=EtpProposalResponse, status_code=status.HTTP_201_CREATED)
    def propose_etp(
        request: EtpProposalRequest,
        context: TenantContext = Depends(get_tenant_context),
        connection=Depends(connection_dependency),
        x_correlation_id: str | None = Header(default=None),
    ) -> EtpProposalResponse:
        actor_id = _assert_tenant_membership(connection, context)
        try:
            with connection.begin_nested():
                proposal = submit_etp_proposal(connection, context.tenant_id, actor_id, request)
        except RepositoryNotFound as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except InvalidWorkflowState as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        return EtpProposalResponse(data=proposal, meta={"tenantContext": str(context.tenant_id), "source": "live-reference-api", "apiVersion": resolved_settings.api_version, "correlationId": _correlation_id(x_correlation_id)})

    @app.post("/v1/etp-proposals/{proposal_id}/decision", response_model=EtpProposalResponse)
    def decide_etp(
        proposal_id: UUID,
        request: MappingDecisionRequest,
        context: TenantContext = Depends(get_tenant_context),
        connection=Depends(connection_dependency),
        x_correlation_id: str | None = Header(default=None),
    ) -> EtpProposalResponse:
        actor_id = _assert_tenant_membership(connection, context)
        try:
            with connection.begin_nested():
                proposal = decide_etp_proposal(connection, context.tenant_id, actor_id, proposal_id, request.decision, request.reason)
        except RepositoryNotFound as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except InvalidWorkflowState as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        return EtpProposalResponse(data=proposal, meta={"tenantContext": str(context.tenant_id), "source": "live-reference-api", "apiVersion": resolved_settings.api_version, "correlationId": _correlation_id(x_correlation_id)})

    @app.post("/v1/fx-forward-proposals", response_model=FxForwardProposalResponse, status_code=status.HTTP_201_CREATED)
    def propose_fx_forward(
        request: FxForwardProposalRequest,
        context: TenantContext = Depends(get_tenant_context),
        connection=Depends(connection_dependency),
        x_correlation_id: str | None = Header(default=None),
    ) -> FxForwardProposalResponse:
        actor_id = _assert_tenant_membership(connection, context)
        try:
            with connection.begin_nested():
                proposal = submit_fx_forward_proposal(connection, context.tenant_id, actor_id, request)
        except RepositoryNotFound as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except InvalidWorkflowState as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        return FxForwardProposalResponse(
            data=proposal,
            meta={
                "tenantContext": str(context.tenant_id),
                "source": "live-reference-api",
                "apiVersion": resolved_settings.api_version,
                "correlationId": _correlation_id(x_correlation_id),
            },
        )

    @app.post("/v1/fx-forward-proposals/{proposal_id}/decision", response_model=FxForwardProposalResponse)
    def decide_fx_forward(
        proposal_id: UUID,
        request: MappingDecisionRequest,
        context: TenantContext = Depends(get_tenant_context),
        connection=Depends(connection_dependency),
        x_correlation_id: str | None = Header(default=None),
    ) -> FxForwardProposalResponse:
        actor_id = _assert_tenant_membership(connection, context)
        try:
            with connection.begin_nested():
                proposal = decide_fx_forward_proposal(connection, context.tenant_id, actor_id, proposal_id, request.decision, request.reason)
        except RepositoryNotFound as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except InvalidWorkflowState as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        return FxForwardProposalResponse(
            data=proposal,
            meta={
                "tenantContext": str(context.tenant_id),
                "source": "live-reference-api",
                "apiVersion": resolved_settings.api_version,
                "correlationId": _correlation_id(x_correlation_id),
            },
        )

    @app.post("/v1/listing-proposals", response_model=EquityProposalResponse, status_code=status.HTTP_201_CREATED)
    @app.post("/v1/equity-listing-proposals", response_model=EquityProposalResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
    def propose_equity_listing(
        request: EquityListingCreateProposalRequest,
        context: TenantContext = Depends(get_tenant_context),
        connection=Depends(connection_dependency),
        x_correlation_id: str | None = Header(default=None),
    ) -> EquityProposalResponse:
        actor_id = _assert_tenant_membership(connection, context)
        try:
            with connection.begin_nested():
                proposal = submit_equity_listing_proposal(connection, context.tenant_id, actor_id, request)
        except RepositoryNotFound as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except InvalidWorkflowState as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        return EquityProposalResponse(
            data=proposal,
            meta={
                "tenantContext": str(context.tenant_id),
                "source": "live-reference-api",
                "apiVersion": resolved_settings.api_version,
                "correlationId": _correlation_id(x_correlation_id),
            },
        )

    @app.post("/v1/equity-proposals/{proposal_id}/decision", response_model=EquityProposalResponse)
    def decide_equity(
        proposal_id: UUID,
        request: MappingDecisionRequest,
        context: TenantContext = Depends(get_tenant_context),
        connection=Depends(connection_dependency),
        x_correlation_id: str | None = Header(default=None),
    ) -> EquityProposalResponse:
        actor_id = _assert_tenant_membership(connection, context)
        try:
            with connection.begin_nested():
                proposal = decide_equity_proposal(connection, context.tenant_id, actor_id, proposal_id, request.decision, request.reason)
        except RepositoryNotFound as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except InvalidWorkflowState as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        return EquityProposalResponse(
            data=proposal,
            meta={
                "tenantContext": str(context.tenant_id),
                "source": "live-reference-api",
                "apiVersion": resolved_settings.api_version,
                "correlationId": _correlation_id(x_correlation_id),
            },
        )

    @app.post("/v1/crypto-asset-proposals", response_model=CryptoAssetProposalResponse, status_code=status.HTTP_201_CREATED)
    def propose_crypto_asset(
        request: CryptoAssetProposalRequest,
        context: TenantContext = Depends(get_tenant_context),
        connection=Depends(connection_dependency),
        x_correlation_id: str | None = Header(default=None),
    ) -> CryptoAssetProposalResponse:
        actor_id = _assert_tenant_membership(connection, context)
        try:
            with connection.begin_nested():
                proposal = submit_crypto_asset_proposal(connection, context.tenant_id, actor_id, request)
        except RepositoryNotFound as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except InvalidWorkflowState as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        return CryptoAssetProposalResponse(
            data=proposal,
            meta={
                "tenantContext": str(context.tenant_id),
                "source": "live-reference-api",
                "apiVersion": resolved_settings.api_version,
                "correlationId": _correlation_id(x_correlation_id),
            },
        )

    @app.get("/v1/crypto-asset-proposals/{proposal_id}", response_model=CryptoAssetProposalResponse)
    def get_crypto_asset(
        proposal_id: UUID,
        context: TenantContext = Depends(get_tenant_context),
        connection=Depends(connection_dependency),
        x_correlation_id: str | None = Header(default=None),
    ) -> CryptoAssetProposalResponse:
        _assert_tenant_membership(connection, context)
        try:
            proposal = get_crypto_asset_proposal(connection, context.tenant_id, proposal_id)
        except RepositoryNotFound as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        return CryptoAssetProposalResponse(
            data=proposal,
            meta={
                "tenantContext": str(context.tenant_id),
                "source": "live-reference-api",
                "apiVersion": resolved_settings.api_version,
                "correlationId": _correlation_id(x_correlation_id),
            },
        )

    @app.post("/v1/crypto-asset-proposals/{proposal_id}/decision", response_model=CryptoAssetProposalResponse)
    def decide_crypto_asset(
        proposal_id: UUID,
        request: MappingDecisionRequest,
        context: TenantContext = Depends(get_tenant_context),
        connection=Depends(connection_dependency),
        x_correlation_id: str | None = Header(default=None),
    ) -> CryptoAssetProposalResponse:
        actor_id = _assert_tenant_membership(connection, context)
        try:
            with connection.begin_nested():
                proposal = decide_crypto_asset_proposal(connection, context.tenant_id, actor_id, proposal_id, request.decision, request.reason)
        except RepositoryNotFound as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except InvalidWorkflowState as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        return CryptoAssetProposalResponse(
            data=proposal,
            meta={
                "tenantContext": str(context.tenant_id),
                "source": "live-reference-api",
                "apiVersion": resolved_settings.api_version,
                "correlationId": _correlation_id(x_correlation_id),
            },
        )

    @app.post("/v1/index-proposals", response_model=IndexProposalResponse, status_code=status.HTTP_201_CREATED)
    def propose_index(
        request: IndexProposalRequest,
        context: TenantContext = Depends(get_tenant_context),
        connection=Depends(connection_dependency),
        x_correlation_id: str | None = Header(default=None),
    ) -> IndexProposalResponse:
        actor_id = _assert_tenant_membership(connection, context)
        try:
            with connection.begin_nested():
                proposal = submit_index_proposal(connection, context.tenant_id, actor_id, request)
        except RepositoryNotFound as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except InvalidCatalogueValue as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
        except InvalidWorkflowState as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        return IndexProposalResponse(
            data=proposal,
            meta={
                "tenantContext": str(context.tenant_id),
                "source": "live-reference-api",
                "apiVersion": resolved_settings.api_version,
                "correlationId": _correlation_id(x_correlation_id),
            },
        )

    @app.post("/v1/index-proposals/{proposal_id}/decision", response_model=IndexProposalResponse)
    def decide_index(
        proposal_id: UUID,
        request: MappingDecisionRequest,
        context: TenantContext = Depends(get_tenant_context),
        connection=Depends(connection_dependency),
        x_correlation_id: str | None = Header(default=None),
    ) -> IndexProposalResponse:
        actor_id = _assert_tenant_membership(connection, context)
        try:
            with connection.begin_nested():
                proposal = decide_index_proposal(connection, context.tenant_id, actor_id, proposal_id, request.decision, request.reason)
        except RepositoryNotFound as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except InvalidWorkflowState as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        return IndexProposalResponse(
            data=proposal,
            meta={
                "tenantContext": str(context.tenant_id),
                "source": "live-reference-api",
                "apiVersion": resolved_settings.api_version,
                "correlationId": _correlation_id(x_correlation_id),
            },
        )

    @app.post("/v1/index-family-proposals", response_model=IndexFamilyProposalResponse, status_code=status.HTTP_201_CREATED)
    def propose_index_family(
        request: IndexFamilyProposalRequest,
        context: TenantContext = Depends(get_tenant_context),
        connection=Depends(connection_dependency),
        x_correlation_id: str | None = Header(default=None),
    ) -> IndexFamilyProposalResponse:
        actor_id = _assert_tenant_membership(connection, context)
        try:
            with connection.begin_nested():
                proposal = submit_index_family_proposal(connection, context.tenant_id, actor_id, request)
        except RepositoryNotFound as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except InvalidWorkflowState as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        return IndexFamilyProposalResponse(
            data=proposal,
            meta={
                "tenantContext": str(context.tenant_id),
                "source": "live-reference-api",
                "apiVersion": resolved_settings.api_version,
                "correlationId": _correlation_id(x_correlation_id),
            },
        )

    @app.post("/v1/index-family-proposals/{proposal_id}/decision", response_model=IndexFamilyProposalResponse)
    def decide_index_family(
        proposal_id: UUID,
        request: MappingDecisionRequest,
        context: TenantContext = Depends(get_tenant_context),
        connection=Depends(connection_dependency),
        x_correlation_id: str | None = Header(default=None),
    ) -> IndexFamilyProposalResponse:
        actor_id = _assert_tenant_membership(connection, context)
        try:
            with connection.begin_nested():
                proposal = decide_index_family_proposal(connection, context.tenant_id, actor_id, proposal_id, request.decision, request.reason)
        except RepositoryNotFound as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except InvalidWorkflowState as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        return IndexFamilyProposalResponse(
            data=proposal,
            meta={
                "tenantContext": str(context.tenant_id),
                "source": "live-reference-api",
                "apiVersion": resolved_settings.api_version,
                "correlationId": _correlation_id(x_correlation_id),
            },
        )

    @app.post("/v1/structured-product-proposals", response_model=StructuredProductProposalResponse, status_code=status.HTTP_201_CREATED)
    def propose_structured_product(
        request: AutocallDraftRequest,
        context: TenantContext = Depends(get_tenant_context),
        connection=Depends(connection_dependency),
        x_correlation_id: str | None = Header(default=None),
    ) -> StructuredProductProposalResponse:
        actor_id = _assert_tenant_membership(connection, context)
        try:
            with connection.begin_nested():
                proposal = submit_structured_product_proposal(connection, context.tenant_id, actor_id, request)
        except RepositoryNotFound as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except InvalidWorkflowState as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        except StructuredProductDraftError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        return StructuredProductProposalResponse(
            data=proposal,
            meta={
                "tenantContext": str(context.tenant_id),
                "source": "live-reference-api",
                "apiVersion": resolved_settings.api_version,
                "correlationId": _correlation_id(x_correlation_id),
            },
        )

    @app.post("/v1/structured-product-proposals/{proposal_id}/decision", response_model=StructuredProductProposalResponse)
    def decide_structured_product(
        proposal_id: UUID,
        request: MappingDecisionRequest,
        context: TenantContext = Depends(get_tenant_context),
        connection=Depends(connection_dependency),
        x_correlation_id: str | None = Header(default=None),
    ) -> StructuredProductProposalResponse:
        actor_id = _assert_tenant_membership(connection, context)
        try:
            with connection.begin_nested():
                proposal = decide_structured_product_proposal(connection, context.tenant_id, actor_id, proposal_id, request.decision, request.reason)
        except RepositoryNotFound as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except InvalidWorkflowState as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        except StructuredProductDraftError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        return StructuredProductProposalResponse(
            data=proposal,
            meta={
                "tenantContext": str(context.tenant_id),
                "source": "live-reference-api",
                "apiVersion": resolved_settings.api_version,
                "correlationId": _correlation_id(x_correlation_id),
            },
        )

    @app.get("/v1/work-queue", response_model=WorkQueueView)
    def queue(
        context: TenantContext = Depends(get_tenant_context),
        connection=Depends(connection_dependency),
        x_correlation_id: str | None = Header(default=None),
    ) -> WorkQueueView:
        _assert_tenant_membership(connection, context)
        return work_queue(connection, context.tenant_id, resolved_settings.api_version, _correlation_id(x_correlation_id))

    @app.post(
        "/v1/market-data-resolution-snapshots",
        response_model=MarketDataResolutionSnapshotView,
        status_code=status.HTTP_201_CREATED,
    )
    def create_market_data_snapshot(
        request: MarketDataResolutionSnapshotCreate,
        response: Response,
        idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=1, max_length=255),
        context: TenantContext = Depends(get_tenant_context),
        connection=Depends(connection_dependency),
    ) -> MarketDataResolutionSnapshotView:
        _assert_tenant_membership(connection, context)
        try:
            with connection.begin_nested():
                snapshot = create_market_data_resolution_snapshot(
                    connection, context.tenant_id, request, idempotency_key, current_request_id()
                )
        except IdempotencyKeyConflict as exc:
            raise ApiProblem(status.HTTP_409_CONFLICT, "idempotency.key_reused", "Idempotency key conflict", "The idempotency key has already been used for a different request.") from exc
        except (ValueError, PermissionError) as exc:
            raise ApiProblem(status.HTTP_422_UNPROCESSABLE_ENTITY, "market_data.invalid_context", "Invalid Market Data resolution context", "The policy, valuation cut, or information cut is invalid for this request.") from exc
        response.headers["Location"] = f"/v1/market-data-resolution-snapshots/{snapshot.market_data_resolution_snapshot_id}"
        return snapshot

    @app.get("/v1/market-data-resolution-snapshots/{snapshot_id}", response_model=MarketDataResolutionSnapshotView)
    def get_market_data_snapshot(
        snapshot_id: UUID,
        context: TenantContext = Depends(get_tenant_context),
        connection=Depends(connection_dependency),
    ) -> MarketDataResolutionSnapshotView:
        _assert_tenant_membership(connection, context)
        try:
            return get_market_data_resolution_snapshot(connection, context.tenant_id, snapshot_id)
        except RepositoryNotFound as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Market-data resolution snapshot not found") from exc

    @app.get("/v1/market-data/valuation-policies", response_model=list[ActiveValuationPolicyView])
    def active_valuation_policies(
        valuation_date: date = Query(alias="valuationDate"),
        context: TenantContext = Depends(get_tenant_context),
        connection=Depends(connection_dependency),
    ) -> list[ActiveValuationPolicyView]:
        _assert_tenant_membership(connection, context)
        return list_active_valuation_policies(connection, context.tenant_id, valuation_date)

    @app.get("/v1/market-data/series", response_model=MarketDataSeriesResponse)
    def market_data_series_catalogue(
        from_date: date | None = Query(default=None, alias="fromDate"),
        to_date: date | None = Query(default=None, alias="toDate"),
        reference_node_id: UUID | None = Query(default=None, alias="referenceNodeId"),
        series_type: str | None = Query(default=None, alias="seriesType", max_length=50),
        limit: int = Query(default=20, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
        context: TenantContext = Depends(get_tenant_context),
        connection=Depends(connection_dependency),
        x_correlation_id: str | None = Header(default=None),
    ) -> MarketDataSeriesResponse:
        _assert_tenant_membership(connection, context)
        if from_date and to_date and from_date > to_date:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="fromDate must be on or before toDate")
        return list_market_data_series(connection, context.tenant_id, from_date, to_date, reference_node_id, series_type, limit, offset, resolved_settings.api_version, _correlation_id(x_correlation_id))

    @app.get("/v1/market-venues", response_model=MarketVenueResponse)
    def market_venues(
        limit: int = Query(default=100, ge=1, le=500),
        offset: int = Query(default=0, ge=0),
        context: TenantContext = Depends(get_tenant_context),
        connection=Depends(connection_dependency),
        x_correlation_id: str | None = Header(default=None),
    ) -> MarketVenueResponse:
        _assert_tenant_membership(connection, context)
        return list_market_venues(connection, context.tenant_id, limit, offset, resolved_settings.api_version, _correlation_id(x_correlation_id))

    @app.get("/v1/day-count-conventions", response_model=DayCountConventionResponse)
    def day_count_conventions(
        context: TenantContext = Depends(get_tenant_context),
        connection=Depends(connection_dependency),
        x_correlation_id: str | None = Header(default=None),
    ) -> DayCountConventionResponse:
        _assert_tenant_membership(connection, context)
        return list_day_count_conventions(connection, context.tenant_id, resolved_settings.api_version, _correlation_id(x_correlation_id))

    @app.get("/v1/currencies", response_model=CurrencyResponse)
    def currencies(
        groups: str = Query(default="REGULAR", max_length=100),
        context: TenantContext = Depends(get_tenant_context),
        connection=Depends(connection_dependency),
        x_correlation_id: str | None = Header(default=None),
    ) -> CurrencyResponse:
        _assert_tenant_membership(connection, context)
        try:
            selected_groups = ",".join(parse_currency_groups(groups))
        except InvalidCatalogueValue as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
        return list_currencies(connection, context.tenant_id, resolved_settings.api_version, _correlation_id(x_correlation_id), selected_groups)

    @app.get("/v1/return-profiles", response_model=ReturnProfileResponse)
    def return_profiles(
        context: TenantContext = Depends(get_tenant_context),
        connection=Depends(connection_dependency),
        x_correlation_id: str | None = Header(default=None),
    ) -> ReturnProfileResponse:
        _assert_tenant_membership(connection, context)
        return list_return_profiles(connection, context.tenant_id, resolved_settings.api_version, _correlation_id(x_correlation_id))

    @app.get("/v1/index-kind-catalogue", response_model=IndexKindResponse)
    def index_kind_catalogue(
        context: TenantContext = Depends(get_tenant_context),
        connection=Depends(connection_dependency),
        x_correlation_id: str | None = Header(default=None),
    ) -> IndexKindResponse:
        _assert_tenant_membership(connection, context)
        return list_index_kinds(connection, context.tenant_id, resolved_settings.api_version, _correlation_id(x_correlation_id))

    @app.get("/v1/organisations", response_model=OrganisationOptionResponse)
    def organisations(
        q: str = Query(default="", max_length=200),
        limit: int = Query(default=100, ge=1, le=500),
        context: TenantContext = Depends(get_tenant_context),
        connection=Depends(connection_dependency),
        x_correlation_id: str | None = Header(default=None),
    ) -> OrganisationOptionResponse:
        _assert_tenant_membership(connection, context)
        return list_organisations(connection, context.tenant_id, resolved_settings.api_version, _correlation_id(x_correlation_id), q, limit)

    @app.get("/v1/index-families", response_model=IndexFamilyOptionResponse)
    def index_families(
        context: TenantContext = Depends(get_tenant_context),
        connection=Depends(connection_dependency),
        x_correlation_id: str | None = Header(default=None),
    ) -> IndexFamilyOptionResponse:
        _assert_tenant_membership(connection, context)
        return list_index_families(connection, context.tenant_id, resolved_settings.api_version, _correlation_id(x_correlation_id))

    @app.get("/v1/trades", response_model=TradeResponse)
    def booked_trades(
        portfolio_code: str | None = Query(default=None, alias="portfolioCode", max_length=100),
        from_date: date | None = Query(default=None, alias="fromDate"),
        to_date: date | None = Query(default=None, alias="toDate"),
        limit: int = Query(default=50, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
        context: TenantContext = Depends(get_tenant_context),
        connection=Depends(connection_dependency),
        x_correlation_id: str | None = Header(default=None),
    ) -> TradeResponse:
        _assert_tenant_membership(connection, context)
        if from_date and to_date and from_date > to_date:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="fromDate must be on or before toDate")
        return list_booked_trades(connection, context.tenant_id, portfolio_code, from_date, to_date, limit, offset, resolved_settings.api_version, _correlation_id(x_correlation_id))

    @app.get("/v1/trades/{trade_id}", response_model=TradeDetailResponse)
    def booked_trade_detail(
        trade_id: UUID,
        context: TenantContext = Depends(get_tenant_context),
        connection=Depends(connection_dependency),
        x_correlation_id: str | None = Header(default=None),
    ) -> TradeDetailResponse:
        _assert_tenant_membership(connection, context)
        result = get_booked_trade_detail(connection, context.tenant_id, trade_id, resolved_settings.api_version, _correlation_id(x_correlation_id))
        if result is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booked trade not found")
        return result

    @app.get("/v1/portfolios/{portfolio_code}/pnl", response_model=PortfolioPnlResponse)
    def portfolio_pnl_view(
        portfolio_code: str,
        as_of_date: date = Query(alias="asOfDate"),
        context: TenantContext = Depends(get_tenant_context),
        connection=Depends(connection_dependency),
        x_correlation_id: str | None = Header(default=None),
    ) -> PortfolioPnlResponse:
        _assert_tenant_membership(connection, context)
        result = portfolio_pnl(connection, context.tenant_id, portfolio_code, as_of_date, resolved_settings.api_version, _correlation_id(x_correlation_id))
        if result is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")
        return result

    return app


def _assert_active_actor(connection, actor_id: UUID) -> None:
    actor = connection.execute(
        select(m.user_account.c.user_account_id)
        .where(m.user_account.c.user_account_id == actor_id)
        .where(m.user_account.c.status == "ACTIVE")
    ).scalar_one_or_none()
    if actor is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is not active")


def _assert_tenant_membership(connection, context: TenantContext) -> UUID:
    """Require an active account and effective membership for the tenant."""

    actor_id = require_actor(context)
    _assert_active_actor(connection, actor_id)
    membership = connection.execute(
        select(m.tenant_user_account.c.tenant_user_account_id)
        .where(m.tenant_user_account.c.tenant_id == context.tenant_id)
        .where(m.tenant_user_account.c.user_account_id == actor_id)
        .where(m.tenant_user_account.c.status == "ACTIVE")
        .where(m.tenant_user_account.c.valid_from <= date.today())
        .where(
            (m.tenant_user_account.c.valid_to.is_(None))
            | (m.tenant_user_account.c.valid_to >= date.today())
        )
    ).scalar_one_or_none()
    if membership is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is not an active member of this tenant")
    return actor_id


app = create_app()
