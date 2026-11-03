"""Native fund-unit transfers/reinvestments; no execution cash or implied income."""
from datetime import timezone
from decimal import Decimal,localcontext
from typing import Literal
from pydantic import Field,model_validator
from .booking_contracts import TradeBookingRequest,BookingResult
from . import booking_store
from security_master_schema.booking_controls import authorize_booking,find_booking_replay,record_booking_replay,validate_execution_date,lock_booking_strategy

ENDPOINT='/native/fund-unit-movements'


class FundUnitMovementRequest(TradeBookingRequest):
    execution_price:Decimal=Field(default=Decimal(0),alias='executionPrice',ge=0,le=0)
    movement_kind:Literal['TRANSFER','REINVESTMENT']=Field(alias='movementKind')
    movement_reason:str=Field(alias='movementReason',min_length=1,max_length=2000)

    @model_validator(mode='after')
    def movement(self):
        if not self.movement_reason.strip():raise ValueError('Movement reason required')
        if self.correction is not None:raise ValueError('Cancel an incorrect movement before submitting a replacement')
        if self.movement_kind=='REINVESTMENT' and self.side!='BUY':raise ValueError('Reinvestment credits must add units')
        with localcontext() as ctx:
            ctx.prec=100
            if not self.quantity.is_finite() or abs(self.quantity)>=Decimal('1e18') or self.quantity!=self.quantity.quantize(Decimal('1e-12')):
                raise ValueError('Movement quantity exceeds native exact precision')
        return self


def book_fund_unit_movement(c,tenant,actor,request:FundUnitMovementRequest,key):
    from .cash_reference import load_cash_booking_listing
    from .annotations import validate_trade_annotations
    with c.begin_nested():
        authorize_booking(c,tenant,actor,strategy_id=request.strategy_id)
        digest=booking_store.booking_fingerprint(request,c,tenant)
        replay=find_booking_replay(c,tenant,ENDPOINT,key,digest)
        if replay is not None:
            booking_store.require_owned_execution(c,tenant,request.strategy_id,replay)
            return BookingResult(replay)
        validate_execution_date(request.trade_datetime)
        listing=load_cash_booking_listing(c,tenant,request.listing_id,request.trade_datetime.astimezone(timezone.utc).date())
        if listing['booking_snapshot']['productBasis']!='FUND':raise ValueError('Fund unit movements require an approved fund share-class listing')
        strategy=lock_booking_strategy(c,tenant,request.strategy_id)
        annotations=validate_trade_annotations(c,tenant,request)
        signed=request.quantity if request.side=='BUY' else request.quantity.copy_negate()
        proof=dict(schemaVersion=1,kind=request.movement_kind,signedQuantity=format(signed,'f'),reason=request.movement_reason.strip(),
            recognitionBasis='POLICY_DAY_END',incomeRecognition='UNASSESSED' if request.movement_kind=='REINVESTMENT' else 'NOT_APPLICABLE')
        identity=booking_store.insert_cash_execution(c,tenant,actor,request,listing,strategy,annotations,digest,key,quantity_movement=proof)
        record_booking_replay(c,tenant,ENDPOINT,key,digest,identity)
        return BookingResult(identity)
