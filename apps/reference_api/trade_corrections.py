"""Append-only corrections of booking records, NOT contractual termination."""
import json
from hashlib import sha256
from .problem_details import current_api_version
from sqlalchemy import update
from security_master_schema import models as m
from .booking_controls import authorize_trade_action, find_booking_replay, record_booking_replay
from .booking_errors import RepositoryNotFound
from .trade_properties import TradeFieldError
from trading.corrections import CorrectionConflict, _original, _chain, _append, prepare_correction, complete_correction

CANCEL_ENDPOINT='/v1/trades/cancel-booking'


def cancel_booking(connection, tenant, actor, trade_id, request, key, request_id):
    from .repository import get_booked_trade_detail
    with connection.begin_nested():
        authorize_trade_action(connection,tenant,actor,trade_id,'TRADE_CORRECT')
        normalized=request.model_dump(mode='json',by_alias=True)|dict(tradeId=str(trade_id))
        fingerprint=sha256(json.dumps(normalized,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        replay=find_booking_replay(connection,tenant,CANCEL_ENDPOINT,key,fingerprint)
        if replay is not None:
            result=get_booked_trade_detail(connection,tenant,replay,current_api_version(),request_id)
            if result is None: raise RepositoryNotFound('Booked trade does not exist')
            return result
        original=_original(connection,tenant,trade_id)
        events,_=_chain(connection,original,request.expected_sequence_no,allow_legacy_cancel=True)
        payload=dict(schemaVersion=1,kind='BOOKING_CORRECTION',action='CANCEL_BOOKING',reason=request.reason,originalTradeId=str(trade_id))
        _append(connection,actor,original,events,'CANCELLED',payload,source_system=f'platform:booking-cancel:{tenant}',source_event=key,fingerprint=fingerprint)
        connection.execute(update(m.trade).where(m.trade.c.trade_id==trade_id).values(lifecycle_status='CANCELLED'))
        record_booking_replay(connection,tenant,CANCEL_ENDPOINT,key,fingerprint,trade_id)
        return get_booked_trade_detail(connection,tenant,trade_id,current_api_version(),request_id)


def correction_router(connection_dependency, assert_membership):
    from uuid import UUID
    from fastapi import Depends, Header, HTTPException
    from .request_audit import AuditRouter as APIRouter
    from .contracts import CancelBookingRequest, TradeDetailResponse
    from .tenant_context import TenantContext,get_tenant_context
    from .problem_details import ApiProblem,ValidationIssue,current_request_id
    from .booking_errors import IdempotencyKeyConflict
    from security_master_schema.tenant_workspace import TenantActionForbidden
    router=APIRouter()

    @router.post('/v1/trades/{trade_id}/cancel-booking',response_model=TradeDetailResponse)
    def cancel(trade_id:UUID,request:CancelBookingRequest,key:str=Header(alias='Idempotency-Key',min_length=1,max_length=255),
        context:TenantContext=Depends(get_tenant_context),connection=Depends(connection_dependency, scope='function')):
        actor=assert_membership(connection,context)
        try: return cancel_booking(connection,context.tenant_id,actor,trade_id,request,key,current_request_id())
        except TenantActionForbidden as error: raise HTTPException(403,'Trade record correction is not permitted.') from error
        except RepositoryNotFound as error: raise HTTPException(404,str(error)) from error
        except IdempotencyKeyConflict as error: raise ApiProblem(409,'idempotency.key_reused','Idempotency conflict',str(error)) from error
        except TradeFieldError as error:
            raise ApiProblem(409 if isinstance(error,CorrectionConflict) else 422,getattr(error,'code','request.validation_failed'),
                'Booking record could not be cancelled',str(error),errors=[ValidationIssue(location=['body',error.field],message=str(error),kind='value_error')]) from error
    return router
