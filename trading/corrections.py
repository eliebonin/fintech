"""Append-only linked replacement helpers shared by booking commands.

Cancellation orchestration and HTTP routing remain in their current adapter.
"""
import json
from hashlib import sha256
from uuid import UUID
from sqlalchemy import select, update
from security_master_schema import models as m
from security_master_schema.booking_controls import authorize_trade_action
from security_master_schema.errors import RepositoryNotFound, TradeFieldError


class CorrectionConflict(TradeFieldError):
    code='trade.correction_conflict'


def _original(connection, tenant, trade_id):
    # Ownership is through the historical strategy, not current instrument visibility.
    row=connection.execute(select(m.trade).join(m.strategy,m.strategy.c.strategy_id==m.trade.c.strategy_id)
        .where(m.trade.c.trade_id==trade_id,m.strategy.c.tenant_id==tenant)
        .with_for_update(of=m.trade)).mappings().first()
    if row is None: raise RepositoryNotFound('Booked trade does not exist')
    return row


def _chain(connection, original, expected_sequence, *, allow_legacy_cancel=False):
    events=connection.execute(select(m.trade_lifecycle_event).where(
        m.trade_lifecycle_event.c.trade_id==original.trade_id).order_by(m.trade_lifecycle_event.c.sequence_no)).mappings().all()
    if not events or events[-1].sequence_no!=expected_sequence:
        raise CorrectionConflict('expectedSequenceNo','Trade history changed or has no supported BOOKED evidence. Reload the detail.')
    if original.lifecycle_status!='BOOKED':
        raise CorrectionConflict('tradeId','Only active booking records can be corrected; this record was already cancelled or superseded.')
    if len(events)>2 or [e.sequence_no for e in events]!=list(range(1,len(events)+1)) or events[0].event_type!='BOOKED':
        raise CorrectionConflict('tradeId','This lifecycle chain requires a separately supported workflow.')
    from security_master_schema.quantity_movements import KINDS,movement_proof
    if original.trade_type!='INVESTMENT' and not (allow_legacy_cancel and original.trade_type in KINDS):
        raise CorrectionConflict('tradeId','Only supported investment booking records can be corrected.')
    try:
        payload=json.loads(events[0].event_payload or '{}')
        # Cancelling an erroneous record needs identity/history, not invented
        # product conventions. Only the original empty legacy shape qualifies;
        # replacement and malformed/new-format evidence remain fail-closed.
        if (allow_legacy_cancel and payload=={} and len(events)==1 and
            events[0].event_datetime_utc==original.trade_datetime_utc and
            all(original[key] is None for key in ('valuation_effective_date','valuation_date_basis','valuation_override_reason'))):
            return events,None
        if payload.get('schemaVersion')!=1: raise ValueError()
        kind={'CASH_BOOKING':'CASH','FX_FORWARD_BOOKING':'FX_FORWARD','OPTION_BOOKING':'OPTION'}.get(payload.get('kind'))
        if payload.get('kind')=='PRODUCT_BOOKING': kind=payload['economics']['terms']['kind']
        if kind not in {'CASH','FX_FORWARD','OPTION','STRUCTURED_PRODUCT','FUTURE','BOND','SWAP','ACTIVELY_MANAGED_CERTIFICATE'}: raise ValueError()
        if original.trade_type in KINDS or payload.get('quantityMovement') is not None:
            if not allow_legacy_cancel or kind!='CASH' or len(events)!=1:raise ValueError()
            movement_proof(payload,product=payload.get('productBasis'),price=original.execution_price,
                quantity=original.quantity,trade_type=original.trade_type)
            return events,kind
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


def prepare_correction(connection, tenant, request, kind, *, actor):
    correction=request.correction
    if correction is None: return
    authorize_trade_action(connection,tenant,actor,correction.trade_id,'TRADE_CORRECT')
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
