"""Shared listed-cash booking command; HTTP-free, caller-owned transactions."""
from datetime import timezone
from uuid import UUID
from sqlalchemy.engine import Connection
from security_master_schema.booking_controls import (
    authorize_booking, find_booking_replay, record_booking_replay,
    validate_execution_date, lock_booking_strategy,
)
from .booking_contracts import TradeBookingRequest, BookingResult
from . import booking_store
from .annotations import validate_trade_annotations
from .cash_reference import load_cash_booking_listing
from .corrections import prepare_correction, complete_correction


def book_cash_trade(connection: Connection, tenant_id: UUID, actor_id: UUID,
                    request: TradeBookingRequest, idempotency_key: str) -> BookingResult:
    """Create/replay an immutable execution; a refusal rolls back only this unit.

    The caller owns outer commit and audit. Current action/strategy authority
    precedes retry lookup; historical eligibility is reapplied only to new work.
    """
    with connection.begin_nested():
        authorize_booking(connection,tenant_id,actor_id,strategy_id=request.strategy_id)
        if request.execution_price<=0:
            from security_master_schema.errors import TradeFieldError
            raise TradeFieldError('executionPrice','Ordinary cash purchases and sales require a positive execution price; use a typed unit movement for transfers or reinvestments.')
        fingerprint=booking_store.booking_fingerprint(request,connection,tenant_id)
        endpoint=booking_store.CASH_BOOKING_ENDPOINT
        existing=find_booking_replay(connection,tenant_id,endpoint,idempotency_key,fingerprint)
        if existing is not None:
            booking_store.require_owned_execution(connection,tenant_id,request.strategy_id,existing)
            return BookingResult(existing)

        validate_execution_date(request.trade_datetime)
        strategy_id=lock_booking_strategy(connection,tenant_id,request.strategy_id)
        prepare_correction(connection,tenant_id,request,'CASH',actor=actor_id)
        listing_row=load_cash_booking_listing(connection,tenant_id,request.listing_id,
            request.trade_datetime.astimezone(timezone.utc).date())
        annotation_values=validate_trade_annotations(connection,tenant_id,request,actor_id=actor_id)
        trade_id=booking_store.insert_cash_execution(connection,tenant_id,actor_id,request,
            listing_row,strategy_id,annotation_values,fingerprint,idempotency_key)
        record_booking_replay(connection,tenant_id,endpoint,idempotency_key,fingerprint,trade_id)
        complete_correction(connection,tenant_id,actor_id,request,trade_id)
        return BookingResult(trade_id)
