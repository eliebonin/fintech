from trading.profiles.validation import annotation_profile_values,annotation_event_proof
"""Instrument-backed FX booking and immutable historical economics."""
from datetime import date, datetime, timezone
from .resource_limits import governance_date
from .problem_details import current_api_version
from decimal import Decimal
from hashlib import sha256
import json
from uuid import UUID, uuid4
from sqlalchemy import select, func, or_, and_
from sqlalchemy.engine import Connection
from security_master_schema import models as m
from security_master_schema.fx_forward_booking import FxForwardBookingTerms, FxForwardBookingError, resolve_fx_forward_settlement, derive_fx_forward_obligations, fx_forward_terms_fingerprint, decimal_text
from .contracts import FxForwardBookingRequest, FxForwardBookingInstrumentView, FxForwardTradeEconomicsView
from .booking_controls import authorize_booking, lock_booking_strategy, find_booking_replay, record_booking_replay

ENDPOINT = "/v1/trades/fx-forwards"


from security_master_schema.fx_forward_reference import _contract_query, _terms, load_fx_forward_booking_terms


def _view(row, as_of=None):
    values = dict(instrumentId=row.instrument_node_id, name=row.canonical_name, baseCurrency=row.base_currency, quoteCurrency=row.quote_currency,
        quoteConvention=row.quote_convention, agreedRate=decimal_text(row.agreed_forward_rate) if row.agreed_forward_rate is not None else None,
        maturityDate=str(row.maturity_date) if row.maturity_date else None, settlementDate=None, settlementType=row.settlement_type, termsFingerprint=None, bookingEligible=False)
    try:
        terms = _terms(row, as_of)
        values.update(settlementDate=str(resolve_fx_forward_settlement(terms)), termsFingerprint=fx_forward_terms_fingerprint(terms), bookingEligible=True)
    except FxForwardBookingError as error:
        values.update(ineligibilityCode=error.code, ineligibilityMessage=str(error))
    return FxForwardBookingInstrumentView(**values)


def search_fx_forward_booking_instruments(connection, tenant_id, query, limit, offset, as_of=None):
    statement = _contract_query(tenant_id)
    if query.strip():
        term = query.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        statement = statement.where(or_(m.financial_reference_node.c.canonical_name.ilike(f"%{term}%", escape="\\"), m.financial_reference_node.c.internal_code.ilike(f"%{term}%", escape="\\")))
    total = connection.scalar(select(func.count()).select_from(statement.subquery()))
    rows = connection.execute(statement.order_by(m.financial_reference_node.c.canonical_name, m.instrument.c.instrument_node_id).limit(limit).offset(offset)).mappings()
    return [_view(row, as_of) for row in rows], total


def get_fx_forward_booking_instrument(connection, tenant_id, instrument_id, as_of=None):
    from .repository import RepositoryNotFound
    row = connection.execute(_contract_query(tenant_id).where(m.instrument.c.instrument_node_id == instrument_id)).mappings().first()
    if row is None: raise RepositoryNotFound("Visible FX-forward instrument does not exist")
    return _view(row, as_of)


def load_fx_forward_trade_economics(connection: Connection, trade_ids) -> dict[UUID, FxForwardTradeEconomicsView]:
    if not trade_ids: return {}
    rows = connection.execute(select(m.trade_lifecycle_event.c.trade_id, m.trade_lifecycle_event.c.event_payload)
        .where(m.trade_lifecycle_event.c.trade_id.in_(trade_ids), m.trade_lifecycle_event.c.sequence_no == 1, m.trade_lifecycle_event.c.event_type == "BOOKED"))
    result = {}
    for trade_id, raw in rows:
        if not raw: continue
        payload = json.loads(raw)
        if isinstance(payload, dict) and payload.get("kind") == "FX_FORWARD_BOOKING" and payload.get("schemaVersion") == 1:
            result[trade_id] = FxForwardTradeEconomicsView.model_validate(payload["economics"])
    return result


def _fingerprint(connection, tenant_id, request):
    from .repository import _trade_booking_fingerprint
    # Existing helper canonicalizes governed values even after retirement.
    proxy = request.model_dump(mode="json", by_alias=True) | {"marketActivity":None}
    class FingerprintInput:
        properties = request.properties
        def model_dump(self, **kwargs): return proxy
    proxy["quantity"] = decimal_text(request.quantity)
    proxy["tradeDatetime"] = request.trade_datetime.astimezone(timezone.utc).isoformat()
    return _trade_booking_fingerprint(FingerprintInput(), connection, tenant_id)


def book_fx_forward_trade(connection: Connection, tenant_id: UUID, actor_id: UUID, request: FxForwardBookingRequest, idempotency_key: str, request_id: str):
    from .valuation_recognition import trade_values, frozen_recognition
    from .repository import IdempotencyKeyConflict, RepositoryNotFound, get_booked_trade_detail, persist_trade_annotations
    from .trade_properties import validate_trade_annotations
    # Savepoint also makes direct repository callers atomic on validation/persistence errors.
    with connection.begin_nested():
        authorize_booking(connection, tenant_id, actor_id,strategy_id=request.strategy_id)
        fingerprint = _fingerprint(connection, tenant_id, request)
        existing = find_booking_replay(connection, tenant_id, ENDPOINT, idempotency_key, fingerprint)
        if existing:
            detail = get_booked_trade_detail(connection, tenant_id, existing, current_api_version(), request_id)
            if detail is None: raise RepositoryNotFound("Booked trade does not exist")
            return detail
        from .booking_controls import validate_execution_date
        execution_date = validate_execution_date(request.trade_datetime)
        from .trade_corrections import prepare_correction, complete_correction
        strategy = lock_booking_strategy(connection,tenant_id,request.strategy_id)
        prepare_correction(connection, tenant_id, request, 'FX_FORWARD', actor=actor_id)
        terms = load_fx_forward_booking_terms(connection, tenant_id, request.instrument_id, for_update=True, as_of=execution_date)
        if fx_forward_terms_fingerprint(terms) != request.expected_terms_fingerprint:
            raise FxForwardBookingError("fx_forward.terms_changed", "instrumentId", "The contract terms changed. Reselect the contract before booking.")
        obligations = derive_fx_forward_obligations(terms, request.side, request.quantity)
        execution = request.trade_datetime.astimezone(timezone.utc)
        if execution.date() > obligations.settlement_date:
            raise FxForwardBookingError("fx_forward.execution_after_settlement", "tradeDatetime", "Execution cannot be after contract settlement.")
        effective = connection.execute(select(m.instrument.c.effective_from, m.instrument.c.effective_to).where(m.instrument.c.instrument_node_id == terms.instrument_id)).one()
        if (effective.effective_from and execution.date() < effective.effective_from) or (effective.effective_to and execution.date() > effective.effective_to):
            raise FxForwardBookingError("fx_forward.inactive_contract", "tradeDatetime", "Execution is outside the instrument's effective dates.")
        values = validate_trade_annotations(connection, tenant_id, request,actor_id=actor_id,native_required={"COUNTERPARTY"})
        trade_id = uuid4()
        connection.execute(m.trade.insert().values(trade_id=trade_id, trade_subject_reference_node_id=terms.instrument_id, reference_instrument_node_id=terms.instrument_id,
            strategy_id=strategy, trade_type="INVESTMENT", trade_purpose=request.trade_purpose, execution_price=terms.agreed_rate, price_basis="RATE", price_currency_id=terms.quote_currency_id,
            quantity=obligations.signed_base_quantity, quantity_unit="CURRENCY_AMOUNT", trade_datetime_utc=execution, settlement_date=obligations.settlement_date, **trade_values(request),**annotation_profile_values(values),
            booked_by_user_account_id=actor_id, execution_channel="MANUAL_UI", lifecycle_status="BOOKED", created_by_user_account_id=actor_id, trader_person_id=request.trader_person_id, comment=request.comment))
        economics = FxForwardTradeEconomicsView(baseCurrency=terms.base_currency, quoteCurrency=terms.quote_currency, quoteConvention=terms.quote_convention, agreedRate=decimal_text(terms.agreed_rate), settlementDate=str(obligations.settlement_date),
            receiveCurrency=obligations.receive_currency, receiveAmount=decimal_text(obligations.receive_amount), payCurrency=obligations.pay_currency, payAmount=decimal_text(obligations.pay_amount), termsFingerprint=request.expected_terms_fingerprint)
        snapshot = dict(schemaVersion=1, kind="FX_FORWARD_BOOKING", baseCurrencyId=str(terms.base_currency_id), quoteCurrencyId=str(terms.quote_currency_id), economics=economics.model_dump(by_alias=True)) | frozen_recognition(request)
        definition=connection.scalar(select(m.instrument_definition_version.c.instrument_definition_version_id).where(
            m.instrument_definition_version.c.instrument_node_id==terms.instrument_id,m.instrument_definition_version.c.is_current,m.instrument_definition_version.c.status=='APPROVED'))
        snapshot['valuationConventions']=dict(instrumentDefinitionId=str(definition),instrumentId=str(terms.instrument_id),
            baseCurrencyId=str(terms.base_currency_id),priceCurrencyId=str(terms.quote_currency_id),quoteConvention=terms.quote_convention,
            agreedRate=decimal_text(terms.agreed_rate),maturityDate=str(terms.maturity_date),settlementType=terms.settlement_type,unitMultiplier='1',quoteFactor='1')
        connection.execute(m.trade_lifecycle_event.insert().values(trade_id=trade_id, sequence_no=1, event_type="BOOKED", event_datetime_utc=execution, source_event_id=idempotency_key, payload_hash=fingerprint, event_payload=json.dumps(snapshot | annotation_event_proof(values), sort_keys=True), recorded_by_user_account_id=actor_id))
        persist_trade_annotations(connection, tenant_id, trade_id, request, values)
        record_booking_replay(connection, tenant_id, ENDPOINT, idempotency_key, fingerprint, trade_id)
        complete_correction(connection, tenant_id, actor_id, request, trade_id)
        return get_booked_trade_detail(connection, tenant_id, trade_id, current_api_version(), request_id)


def fx_forward_booking_router(connection_dependency, assert_membership):
    from fastapi import Depends, Header, Query, Response, HTTPException
    from .request_audit import AuditRouter as APIRouter
    from .tenant_context import TenantContext, get_tenant_context
    from .contracts import ApiMeta, FxForwardBookingInstrumentSearchResponse, FxForwardBookingInstrumentResponse, TradeDetailResponse
    from .problem_details import ApiProblem, ValidationIssue, current_request_id
    from .repository import RepositoryNotFound, IdempotencyKeyConflict
    from .trade_properties import TradeFieldError
    from security_master_schema.tenant_workspace import require_tenant_action, resolve_tenant_workspace, TenantActionForbidden
    router = APIRouter()

    def authorized(context, connection):
        actor = assert_membership(connection, context)
        try: require_tenant_action(resolve_tenant_workspace(connection, context.tenant_id, actor, governance_date()), "TRADE_WRITE")
        except TenantActionForbidden as error: raise HTTPException(403, "Trade booking is not permitted") from error
        return actor

    def meta(context, **kwargs):
        return ApiMeta(tenantContext=str(context.tenant_id), source="live-reference-api", apiVersion=current_api_version(), correlationId=current_request_id(), **kwargs)

    @router.get("/v1/trades/fx-forward-instruments", response_model=FxForwardBookingInstrumentSearchResponse)
    def search(q: str = Query(default="", max_length=250), limit: int = Query(default=25, ge=1, le=100), offset: int = Query(default=0, ge=0), as_of: date | None = Query(default=None, alias="asOfDate"), context: TenantContext = Depends(get_tenant_context), connection=Depends(connection_dependency, scope='function')):
        authorized(context, connection)
        data, total = search_fx_forward_booking_instruments(connection, context.tenant_id, q, limit, offset, as_of)
        from .instrument_display import decorate_response
        return decorate_response(connection,context.tenant_id,FxForwardBookingInstrumentSearchResponse(data=data, meta=meta(context, total=total, limit=limit, offset=offset)),[item.instrument_id for item in data])

    @router.get("/v1/trades/fx-forward-instruments/{instrument_id}", response_model=FxForwardBookingInstrumentResponse)
    def instrument(instrument_id: UUID, as_of: date | None = Query(default=None, alias="asOfDate"), context: TenantContext = Depends(get_tenant_context), connection=Depends(connection_dependency, scope='function')):
        authorized(context, connection)
        try: data = get_fx_forward_booking_instrument(connection, context.tenant_id, instrument_id, as_of)
        except RepositoryNotFound as error: raise HTTPException(404, str(error)) from error
        from .instrument_display import decorate_response
        return decorate_response(connection,context.tenant_id,FxForwardBookingInstrumentResponse(data=data, meta=meta(context)),[data.instrument_id])

    @router.post(ENDPOINT, response_model=TradeDetailResponse, status_code=201)
    def book(request: FxForwardBookingRequest, response: Response, idempotency_key: str = Header(alias="Idempotency-Key", min_length=1, max_length=255), context: TenantContext = Depends(get_tenant_context), connection=Depends(connection_dependency, scope='function')):
        actor = authorized(context, connection)
        try: result = book_fx_forward_trade(connection, context.tenant_id, actor, request, idempotency_key, current_request_id())
        except RepositoryNotFound as error: raise HTTPException(404, str(error)) from error
        except IdempotencyKeyConflict as error: raise ApiProblem(409, "idempotency.key_reused", "Idempotency key conflict", str(error)) from error
        except (FxForwardBookingError, TradeFieldError) as error:
            code = getattr(error, "code", "request.validation_failed")
            raise ApiProblem(409 if code in {"fx_forward.terms_changed", "trade.correction_conflict"} else 422, code, "FX-forward booking could not be completed", str(error), errors=[ValidationIssue(location=["body", error.field], message=str(error), kind="value_error")]) from error
        response.headers["Location"] = f"/v1/trades/{result.data.trade.trade_id}"
        return result
    return router
