"""Owned disposable tests for built-in recognition persistence and protection."""
import json
from datetime import date
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError,DBAPIError
import pytest
from tests.test_valuation_service import valued
from positions.repository import iter_ledger_facts
from tests.test_position_repository import projection_request
from security_master_schema import models as m
from uuid import uuid4
from tests.test_cash_booking_integrity import connection, payload, book
from tests.test_trade_corrections import replacement


def test_booking_defaults_and_correction_preserve_original_date(connection):
    first=book(connection).data
    assert first.trade.valuation_effective_date=='2026-09-30'
    assert first.trade.valuation_date_basis=='UTC_TRADE_DATE'
    corrected=replacement(connection,first.trade.trade_id,
        valuationEffectiveDate='2026-10-01',valuationOverrideReason='After reporting boundary').data
    assert corrected.trade.valuation_effective_date=='2026-10-01'
    row=connection.execute(select(m.trade).where(m.trade.c.trade_id==first.trade.trade_id)).mappings().one()
    assert row['valuation_effective_date']==date(2026,9,30)
    assert json.loads(first.lifecycle_events[0].event_payload)['valuationRecognition']['date']=='2026-09-30'

def insert_deferred(c,original,day=date(2026,10,2)):
    row=dict(c.execute(select(m.trade).where(m.trade.c.trade_id==original)).mappings().one())
    event=dict(c.execute(select(m.trade_lifecycle_event).where(m.trade_lifecycle_event.c.trade_id==original)).mappings().one())
    identity=uuid4()
    row.update(trade_id=identity,valuation_effective_date=day,valuation_date_basis='EXPLICIT_OVERRIDE',valuation_override_reason='After reporting boundary')
    snapshot=json.loads(event['event_payload']); snapshot['valuationRecognition']=dict(date=day.isoformat(),timezone='UTC',basis='EXPLICIT_OVERRIDE',reason='After reporting boundary')
    c.execute(m.trade.insert().values(**row))
    c.execute(m.trade_lifecycle_event.insert().values(**(event|dict(trade_id=identity,trade_lifecycle_event_id=uuid4(),event_payload=json.dumps(snapshot)))))
    return identity

def test_future_recognition_excluded_from_reader_then_included(valued):
    from dataclasses import replace
    from datetime import timedelta
    c,r,trade=valued
    added=insert_deferred(c,trade)
    assert {f.trade_id for f in iter_ledger_facts(c,projection_request(r))}=={trade}
    later=replace(projection_request(r),closing_cutoff=r.closing_cutoff+timedelta(days=1))
    facts=list(iter_ledger_facts(c,later))
    assert {f.trade_id for f in facts}=={trade,added}
    assert next(f.booking for f in facts if f.trade_id==added).valuation_effective_date==date(2026,10,2)

def test_recognition_columns_cannot_be_updated_in_place(valued):
    c,r,trade=valued
    added=insert_deferred(c,trade)
    with pytest.raises(DBAPIError,match='immutable'):
        with c.begin_nested():
            c.execute(m.trade.update().where(m.trade.c.trade_id==added).values(valuation_override_reason='changed'))

def test_missing_frozen_recognition_fails_closed(valued):
    from dataclasses import replace
    from datetime import timedelta
    from positions.contracts import PositionError
    c,r,trade=valued
    row=dict(c.execute(select(m.trade).where(m.trade.c.trade_id==trade)).mappings().one())
    event=dict(c.execute(select(m.trade_lifecycle_event).where(m.trade_lifecycle_event.c.trade_id==trade)).mappings().one())
    identity=uuid4()
    c.execute(m.trade.insert().values(**(row|dict(trade_id=identity,valuation_effective_date=date(2026,9,30),valuation_date_basis='UTC_TRADE_DATE'))))
    c.execute(m.trade_lifecycle_event.insert().values(**(event|dict(trade_id=identity,trade_lifecycle_event_id=uuid4()))))
    with pytest.raises(PositionError,match='frozen valuation recognition'):
        list(iter_ledger_facts(c,projection_request(r)))
