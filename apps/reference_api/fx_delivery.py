"""Bounded delivery evidence for immutable deliverable FX booking snapshots."""
import json
from datetime import date, datetime, timezone
from decimal import Decimal
from hashlib import sha256
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator, model_validator
from sqlalchemy import select
from security_master_schema import models as m
from security_master_schema.fx_delivery import DeliveryError, DeliveryRecord, replay_delivery
from security_master_schema.fx_forward_booking import decimal_text
from security_master_schema.tenant_workspace import TenantActionForbidden
from .booking_controls import authorize_booking, find_booking_replay, record_booking_replay
from .booking_errors import RepositoryNotFound, IdempotencyKeyConflict
from .contracts import ApiMeta, FxForwardTradeEconomicsView
from .problem_details import ApiProblem, ValidationIssue, current_api_version, current_request_id
from .tenant_context import TenantContext, get_tenant_context
from .trade_properties import TradeFieldError

ENDPOINT = '/v1/trades/fx-delivery'


class DeliveryRequest(BaseModel):
    expected_sequence_no: StrictInt = Field(alias='expectedSequenceNo', ge=1)
    action: Literal['CONFIRM', 'REVERSE']
    effective_at: datetime = Field(alias='effectiveAt')
    evidence: str = Field(min_length=1, max_length=1000)
    leg: Literal['RECEIVE', 'PAY'] | None = None
    amount: Decimal | None = Field(default=None, gt=0, lt=Decimal('1e40'), max_digits=64, decimal_places=24)
    target_sequence_no: StrictInt | None = Field(default=None, alias='targetSequenceNo', ge=2)
    model_config = ConfigDict(populate_by_name=True, extra='forbid')

    @field_validator('amount', mode='before')
    @classmethod
    def exact_amount(cls, value):
        if value is not None and not isinstance(value, (str, Decimal)):
            raise ValueError('Send an exact decimal amount as a string.')
        return value

    @field_validator('evidence', mode='before')
    @classmethod
    def trim(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator('effective_at')
    @classmethod
    def utc(cls, value):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError('Effective time must include a timezone offset.')
        return value.astimezone(timezone.utc)

    @model_validator(mode='after')
    def action_fields(self):
        if self.action == 'CONFIRM' and (self.leg is None or self.amount is None or self.target_sequence_no is not None):
            raise ValueError('Confirmation needs one leg and an amount, not a reversal target.')
        if self.action == 'REVERSE' and (self.target_sequence_no is None or self.leg is not None or self.amount is not None):
            raise ValueError('Reversal needs one confirmation sequence, not a leg or amount.')
        return self


class DeliveryView(BaseModel):
    trade_id: UUID = Field(alias='tradeId')
    expected_sequence_no: int = Field(alias='expectedSequenceNo')
    status: Literal['PENDING', 'DUE', 'PARTIAL', 'DELIVERED']
    settlement_date: date = Field(alias='settlementDate')
    receive_currency: str = Field(alias='receiveCurrency')
    pay_currency: str = Field(alias='payCurrency')
    receive_confirmed: str = Field(alias='receiveConfirmed')
    pay_confirmed: str = Field(alias='payConfirmed')
    receive_outstanding: str = Field(alias='receiveOutstanding')
    pay_outstanding: str = Field(alias='payOutstanding')
    reversible_sequences: list[int] = Field(alias='reversibleSequences')
    model_config = ConfigDict(populate_by_name=True)


class DeliveryResponse(BaseModel):
    data: DeliveryView
    meta: ApiMeta


class DeliveryConflict(TradeFieldError):
    code = 'fx_delivery.conflict'


def _load(connection, tenant, trade_id, *, lock=False):
    query = select(m.trade).join(m.strategy, m.strategy.c.strategy_id == m.trade.c.strategy_id).where(
        m.trade.c.trade_id == trade_id, m.strategy.c.tenant_id == tenant)
    if lock:
        query = query.with_for_update(of=m.trade)
    trade = connection.execute(query).mappings().first()
    if trade is None:
        raise RepositoryNotFound('Booked trade does not exist')
    events = connection.execute(select(m.trade_lifecycle_event).where(m.trade_lifecycle_event.c.trade_id == trade_id)
        .order_by(m.trade_lifecycle_event.c.sequence_no)).mappings().all()
    try:
        if trade.lifecycle_status != 'BOOKED' or trade.trade_type != 'INVESTMENT' or not events or events[0].event_type != 'BOOKED':
            raise ValueError()
        booked = json.loads(events[0].event_payload)
        if booked.get('schemaVersion') != 1 or booked.get('kind') != 'FX_FORWARD_BOOKING':
            raise ValueError()
        economics = FxForwardTradeEconomicsView.model_validate(booked['economics'])
        if economics.receive_currency == economics.pay_currency:
            raise ValueError()
        records = []
        for index, event in enumerate(events):
            if event.sequence_no != index + 1:
                raise ValueError()
            if index == 0:
                continue
            payload = json.loads(event.event_payload)
            if index == 1 and event.event_type == 'CORRECTED':
                if payload.get('schemaVersion') != 1 or payload.get('kind') != 'BOOKING_CORRECTION' or payload.get('action') != 'REPLACES_BOOKING' or UUID(payload['replacementTradeId']) != trade_id or UUID(payload['originalTradeId']) == trade_id or not payload['reason'].strip():
                    raise ValueError()
                continue
            if payload.get('schemaVersion') != 1 or payload.get('kind') != 'FX_DELIVERY' or event.event_type != 'FX_DELIVERY':
                raise ValueError()
            request = DeliveryRequest.model_validate(payload['request'])
            if request.expected_sequence_no != event.sequence_no - 1 or request.effective_at != event.event_datetime_utc or event.supersedes_event_id is not None:
                raise ValueError()
            records.append(_record(request, event.sequence_no))
        return economics, events, records
    except (ValueError, TypeError, KeyError, AttributeError):
        raise DeliveryConflict('tradeId', 'Supported immutable FX booking/delivery evidence is unavailable; do not infer settlement.') from None


def _record(request, sequence):
    return DeliveryRecord(sequence, request.action, request.effective_at, request.evidence,
        request.leg, request.amount, request.target_sequence_no)


def _response(tenant, trade_id, economics, sequence, records, request_id):
    try:
        progress = replay_delivery(Decimal(economics.receive_amount), Decimal(economics.pay_amount),
            date.fromisoformat(economics.settlement_date), records, now=datetime.now(timezone.utc))
    except DeliveryError as error:
        raise DeliveryConflict('delivery', str(error)) from error
    data = DeliveryView(tradeId=trade_id, expectedSequenceNo=sequence, status=progress.status,
        settlementDate=economics.settlement_date, receiveCurrency=economics.receive_currency, payCurrency=economics.pay_currency,
        receiveConfirmed=decimal_text(progress.receive_confirmed), payConfirmed=decimal_text(progress.pay_confirmed),
        receiveOutstanding=decimal_text(progress.receive_outstanding), payOutstanding=decimal_text(progress.pay_outstanding),
        reversibleSequences=list(progress.reversible_sequences))
    return DeliveryResponse(data=data, meta=ApiMeta(tenantContext=str(tenant), source='live-reference-api', apiVersion=current_api_version(), correlationId=request_id))


def get_delivery(connection, tenant, trade_id, request_id):
    economics, events, records = _load(connection, tenant, trade_id)
    return _response(tenant, trade_id, economics, events[-1].sequence_no, records, request_id)


def record_delivery(connection, tenant, actor, trade_id, request, key, request_id):
    with connection.begin_nested():
        authorize_booking(connection, tenant, actor)
        normalized = request.model_dump(mode='json', by_alias=True, exclude_none=True)
        if request.amount is not None:
            normalized['amount'] = decimal_text(request.amount)
        fingerprint = sha256(json.dumps(dict(tradeId=str(trade_id), request=normalized), sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        replay = find_booking_replay(connection, tenant, ENDPOINT, key, fingerprint)
        if replay is not None:
            return get_delivery(connection, tenant, replay, request_id)
        economics, events, records = _load(connection, tenant, trade_id, lock=True)
        sequence = events[-1].sequence_no
        if sequence != request.expected_sequence_no:
            raise DeliveryConflict('expectedSequenceNo', 'Trade history changed. Reload delivery evidence before another action.')
        result = _response(tenant, trade_id, economics, sequence + 1, records + [_record(request, sequence + 1)], request_id)
        payload = dict(schemaVersion=1, kind='FX_DELIVERY', request=normalized)
        connection.execute(m.trade_lifecycle_event.insert().values(trade_id=trade_id, sequence_no=sequence + 1,
            event_type='FX_DELIVERY', event_datetime_utc=request.effective_at, event_payload=json.dumps(payload, sort_keys=True),
            payload_hash=fingerprint, recorded_by_user_account_id=actor, source_system_id=f'fortem:fx-delivery:{tenant}', source_event_id=key))
        record_booking_replay(connection, tenant, ENDPOINT, key, fingerprint, trade_id)
        return result


def delivery_router(connection_dependency, assert_membership):
    router = APIRouter()

    def handle(call):
        try:
            return call()
        except RepositoryNotFound as error:
            raise HTTPException(404, str(error)) from error
        except TenantActionForbidden as error:
            raise HTTPException(403, 'FX delivery recording is not permitted.') from error
        except IdempotencyKeyConflict as error:
            raise ApiProblem(409, 'idempotency.key_reused', 'Idempotency conflict', str(error)) from error
        except DeliveryConflict as error:
            raise ApiProblem(409, error.code, 'FX delivery evidence could not be processed', str(error),
                errors=[ValidationIssue(location=['body', error.field], message=str(error), kind='value_error')]) from error

    @router.get('/v1/trades/{trade_id}/fx-delivery', response_model=DeliveryResponse)
    def read(trade_id: UUID, context: TenantContext = Depends(get_tenant_context), connection=Depends(connection_dependency, scope='function')):
        assert_membership(connection, context)
        return handle(lambda: get_delivery(connection, context.tenant_id, trade_id, current_request_id()))

    @router.post('/v1/trades/{trade_id}/fx-delivery', response_model=DeliveryResponse)
    def write(trade_id: UUID, request: DeliveryRequest, key: str = Header(alias='Idempotency-Key', min_length=1, max_length=255),
        context: TenantContext = Depends(get_tenant_context), connection=Depends(connection_dependency, scope='function')):
        actor = assert_membership(connection, context)
        return handle(lambda: record_delivery(connection, context.tenant_id, actor, trade_id, request, key, current_request_id()))

    return router
