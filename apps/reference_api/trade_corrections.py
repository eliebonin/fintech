"""Append-only corrections of booking records, NOT contractual termination."""
import json
from hashlib import sha256
from .problem_details import current_api_version
from uuid import UUID

from sqlalchemy import select, update
from security_master_schema import models as m
from .booking_controls import authorize_booking, find_booking_replay, record_booking_replay
from .booking_errors import RepositoryNotFound
from .trade_properties import TradeFieldError

CANCEL_ENDPOINT='/v1/trades/cancel-booking'


class CorrectionConflict(TradeFieldError):
    code='trade.correction_conflict'


def _original(connection, tenant, trade_id):
    # Ownership is through the historical strategy, not current instrument visibility.
    row=connection.execute(select(m.trade).join(m.strategy,m.strategy.c.strategy_id==m.trade.c.strategy_id)
        .where(m.trade.c.trade_id==trade_id,m.strategy.c.tenant_id==tenant)
        .with_for_update(of=m.trade)).mappings().first()
    if row is None: raise RepositoryNotFound('Booked trade does not exist')
    return row


def _chain(connection, original, expected_sequence):
    events=connection.execute(select(m.trade_lifecycle_event).where(
        m.trade_lifecycle_event.c.trade_id==original.trade_id).order_by(m.trade_lifecycle_event.c.sequence_no)).mappings().all()
    if not events or events[-1].sequence_no!=expected_sequence:
        raise CorrectionConflict('expectedSequenceNo','Trade history changed or has no supported BOOKED evidence. Reload the detail.')
    if original.lifecycle_status!='BOOKED':
        raise CorrectionConflict('tradeId','Only active booking records can be corrected; this record was already cancelled or superseded.')
    if len(events)>2 or [e.sequence_no for e in events]!=list(range(1,len(events)+1)) or events[0].event_type!='BOOKED':
        raise CorrectionConflict('tradeId','This lifecycle chain requires a separately supported workflow.')
    try:
        payload=json.loads(events[0].event_payload or '{}')
        if payload.get('schemaVersion')!=1: raise ValueError()
        kind={'CASH_BOOKING':'CASH','FX_FORWARD_BOOKING':'FX_FORWARD','OPTION_BOOKING':'OPTION'}.get(payload.get('kind'))
        if payload.get('kind')=='PRODUCT_BOOKING': kind=payload['economics']['terms']['kind']
        if kind not in {'CASH','FX_FORWARD','OPTION','STRUCTURED_PRODUCT','FUTURE','BOND','SWAP'}: raise ValueError()
        if len(events)==2:
            link=json.loads(events[1].event_payload or '{}')
            if events[1].event_type!='CORRECTED' or link.get('schemaVersion')!=1 or link.get('kind')!='BOOKING_CORRECTION' or link.get('action')!='REPLACES_BOOKING': raise ValueError()
            if UUID(link['replacementTradeId'])!=original.trade_id or UUID(link['originalTradeId'])==original.trade_id: raise ValueError()
            if not isinstance(link.get('reason'),str) or not link['reason'].strip(): raise ValueError()
    except (ValueError,TypeError,KeyError,AttributeError):
        raise CorrectionConflict('tradeId','Immutable alpha booking evidence is unavailable or this lifecycle is unsupported.') from None
    if original.trade_type!='INVESTMENT':
        raise CorrectionConflict('tradeId','Only supported investment booking records can be corrected.')
    return events,kind


def prepare_correction(connection, tenant, request, kind):
    correction=request.correction
    if correction is None: return
    original=_original(connection,tenant,correction.trade_id)
    _,original_kind=_chain(connection,original,correction.expected_sequence_no)
    if original.strategy_id!=request.strategy_id or original_kind!=kind:
        raise TradeFieldError('correction','A replacement must retain the original strategy and booking product category.')


def _append(connection, actor, original, events, event_type, payload, *, source_system=None, source_event=None, fingerprint=None):
    connection.execute(m.trade_lifecycle_event.insert().values(trade_id=original.trade_id,
        sequence_no=events[-1].sequence_no+1,event_type=event_type,event_datetime_utc=original.trade_datetime_utc,
        supersedes_event_id=events[-1].trade_lifecycle_event_id,event_payload=json.dumps(payload,sort_keys=True),
        payload_hash=fingerprint or sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest(),
        recorded_by_user_account_id=actor,source_system_id=source_system,source_event_id=source_event))


def complete_correction(connection, tenant, actor, request, new_trade_id):
    correction=request.correction
    if correction is None: return
    original=_original(connection,tenant,correction.trade_id)
    events,_=_chain(connection,original,correction.expected_sequence_no)
    payload=dict(schemaVersion=1,kind='BOOKING_CORRECTION',reason=correction.reason,
        originalTradeId=str(original.trade_id),replacementTradeId=str(new_trade_id))
    _append(connection,actor,original,events,'SUPERSEDED',payload|dict(action='REPLACED_BOOKING'))
    replacement=connection.execute(select(m.trade).where(m.trade.c.trade_id==new_trade_id)).mappings().one()
    new_events=connection.execute(select(m.trade_lifecycle_event).where(m.trade_lifecycle_event.c.trade_id==new_trade_id)
        .order_by(m.trade_lifecycle_event.c.sequence_no)).mappings().all()
    _append(connection,actor,replacement,new_events,'CORRECTED',payload|dict(action='REPLACES_BOOKING'))
    connection.execute(update(m.trade).where(m.trade.c.trade_id==original.trade_id).values(lifecycle_status='SUPERSEDED'))


def cancel_booking(connection, tenant, actor, trade_id, request, key, request_id):
    from .repository import get_booked_trade_detail
    with connection.begin_nested():
        authorize_booking(connection,tenant,actor)
        normalized=request.model_dump(mode='json',by_alias=True)|dict(tradeId=str(trade_id))
        fingerprint=sha256(json.dumps(normalized,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        replay=find_booking_replay(connection,tenant,CANCEL_ENDPOINT,key,fingerprint)
        if replay is not None:
            result=get_booked_trade_detail(connection,tenant,replay,current_api_version(),request_id)
            if result is None: raise RepositoryNotFound('Booked trade does not exist')
            return result
        original=_original(connection,tenant,trade_id)
        events,_=_chain(connection,original,request.expected_sequence_no)
        payload=dict(schemaVersion=1,kind='BOOKING_CORRECTION',action='CANCEL_BOOKING',reason=request.reason,originalTradeId=str(trade_id))
        _append(connection,actor,original,events,'CANCELLED',payload,source_system=f'fortem:booking-cancel:{tenant}',source_event=key,fingerprint=fingerprint)
        connection.execute(update(m.trade).where(m.trade.c.trade_id==trade_id).values(lifecycle_status='CANCELLED'))
        record_booking_replay(connection,tenant,CANCEL_ENDPOINT,key,fingerprint,trade_id)
        return get_booked_trade_detail(connection,tenant,trade_id,current_api_version(),request_id)


def correction_router(connection_dependency, assert_membership):
    from uuid import UUID
    from fastapi import APIRouter, Depends, Header, HTTPException
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
