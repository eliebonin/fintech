"""Use only the owned disposable runner; original legacy evidence is preserved."""
from datetime import timedelta
from dataclasses import replace
from uuid import uuid4
import pytest
from sqlalchemy import select
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from apps.reference_api.contracts import CancelBookingRequest
from apps.reference_api.trade_corrections import cancel_booking
from apps.reference_api.trade_properties import TradeFieldError
from tests.test_valuation_service import valued,service
from tests.test_position_repository import projection_request
from positions.repository import iter_ledger_facts
from positions.reconstruction import reconstruct
from positions.contracts import PositionError


def legacy(c,trade,*,execution=None,recorded=None):
    row=dict(c.execute(select(m.trade).where(m.trade.c.trade_id==trade)).mappings().one())
    event=dict(c.execute(select(m.trade_lifecycle_event).where(m.trade_lifecycle_event.c.trade_id==trade)).mappings().one())
    identity=uuid4()
    if execution is not None:
        row['trade_datetime_utc']=execution;event['event_datetime_utc']=execution
    if recorded is not None:
        row['created_at_utc']=recorded;event['recorded_at_utc']=recorded
    c.execute(m.trade.insert().values(**(row|dict(trade_id=identity,valuation_effective_date=None,valuation_date_basis=None,valuation_override_reason=None))))
    c.execute(m.trade_lifecycle_event.insert().values(**(event|dict(trade_id=identity,trade_lifecycle_event_id=uuid4(),event_payload='{}'))))
    return identity


def test_legacy_cancel_only_path_preserves_original_and_replays_idempotently(valued):
    c,r,trade=valued;identity=legacy(c,trade);key=str(uuid4())
    request=CancelBookingRequest(expectedSequenceNo=1,reason='Legacy test booking')
    result=cancel_booking(c,r.tenant_id,ids['demo_user_account'],identity,request,key,'legacy-test').data
    assert result.trade.lifecycle_status=='CANCELLED'
    assert result.lifecycle_events[0].event_payload=='{}'
    replay=cancel_booking(c,r.tenant_id,ids['demo_user_account'],identity,request,key,'legacy-retry').data
    assert len(replay.lifecycle_events)==2


def test_cancelled_legacy_record_does_not_block_later_valuation_and_retains_audit(valued):
    c,r,trade=valued;identity=legacy(c,trade)
    cancel_booking(c,r.tenant_id,ids['demo_user_account'],identity,CancelBookingRequest(expectedSequenceNo=1,reason='Legacy test booking'),str(uuid4()),'legacy-test')
    r=replace(r,opening_cutoff=r.opening_cutoff+timedelta(days=1))
    facts=list(iter_ledger_facts(c,projection_request(r)))
    assert [f.kind for f in facts if f.trade_id==identity]==['BOOKED','CANCELLED']
    projection=reconstruct(facts,projection_request(r))
    assert projection.buckets[0].opening_quantity==projection.buckets[0].closing_quantity==10
    assert identity not in projection.buckets[0].trade_ids


def test_unrecorded_cancellation_does_not_hide_active_missing_evidence(valued):
    # PostgreSQL now() is transaction-stable; make the historical knowledge
    # boundary explicit instead of assuming inserts get distinct timestamps.
    c,r,trade=valued;identity=legacy(c,trade,recorded=r.information_cutoff-timedelta(hours=2))
    before=c.scalar(select(m.trade_lifecycle_event.c.recorded_at_utc).where(m.trade_lifecycle_event.c.trade_id==identity))
    cancel_booking(c,r.tenant_id,ids['demo_user_account'],identity,CancelBookingRequest(expectedSequenceNo=1,reason='Legacy'),str(uuid4()),'legacy-test')
    with pytest.raises(PositionError,match='BOOKED'):
        list(iter_ledger_facts(c,projection_request(replace(r,information_cutoff=before))))


def test_legacy_cannot_be_replaced_without_original_economics(valued):
    from apps.reference_api.trade_corrections import _chain
    c,r,trade=valued;identity=legacy(c,trade)
    row=c.execute(select(m.trade).where(m.trade.c.trade_id==identity)).mappings().one()
    with pytest.raises(TradeFieldError): _chain(c,row,1)


def test_full_valuation_keeps_supported_trade_pnl_when_legacy_record_is_cancelled(valued):
    from decimal import Decimal
    c,r,trade=valued;identity=legacy(c,trade,execution=r.opening_cutoff-timedelta(days=1))
    cancel_booking(c,r.tenant_id,ids['demo_user_account'],identity,CancelBookingRequest(expectedSequenceNo=1,reason='Legacy test'),str(uuid4()),'legacy-test')
    result=service().calculate(c,r)
    assert result.period.market_pnl==Decimal('109.877')
    assert all(identity not in line.bucket.trade_ids for line in result.period.lines)
