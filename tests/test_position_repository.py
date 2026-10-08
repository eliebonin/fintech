"""Owned-disposable ledger adapter checks; never target operator data."""
from dataclasses import replace
from uuid import uuid4
import pytest
from sqlalchemy import select
from tests.test_valuation_service import valued
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from positions.contracts import ProjectionRequest, PositionError
from positions.repository import iter_ledger_facts
from positions.reconstruction import reconstruct

def projection_request(r):
    return ProjectionRequest(r.tenant_id,r.strategy_id,r.closing_cutoff,r.information_cutoff,r.opening_cutoff,'PERIOD')

def test_all_chunks_and_frozen_factors(valued):
    c,r,trade=valued
    row=dict(c.execute(select(m.trade).where(m.trade.c.trade_id==trade)).mappings().one())
    ev=dict(c.execute(select(m.trade_lifecycle_event).where(m.trade_lifecycle_event.c.trade_id==trade)).mappings().one())
    identities=[uuid4() for _ in range(1001)]
    c.execute(m.trade.insert(),[row|dict(trade_id=i) for i in identities])
    c.execute(m.trade_lifecycle_event.insert(),[ev|dict(trade_id=i,trade_lifecycle_event_id=uuid4()) for i in identities])
    facts=list(iter_ledger_facts(c,projection_request(r)))
    assert len(facts)==1002 and {f.trade_id for f in facts}=={trade,*identities}
    p=reconstruct(facts,projection_request(r))
    assert p.buckets[0].closing_quantity==10020
    assert p.buckets[0].key.quote_factor==100

def test_keyset_reader_query_count_grows_by_chunks_not_trades(valued):
    from sqlalchemy import event as sql_event
    c,r,trade=valued
    row=dict(c.execute(select(m.trade).where(m.trade.c.trade_id==trade)).mappings().one())
    ev=dict(c.execute(select(m.trade_lifecycle_event).where(m.trade_lifecycle_event.c.trade_id==trade)).mappings().one())
    identities=[uuid4() for _ in range(500)]
    c.execute(m.trade.insert(),[row|dict(trade_id=i) for i in identities])
    c.execute(m.trade_lifecycle_event.insert(),[ev|dict(trade_id=i,trade_lifecycle_event_id=uuid4()) for i in identities])
    queries=[]
    def observe(conn,cursor,statement,parameters,context,executemany):
        if statement.lstrip().upper().startswith('SELECT'): queries.append(statement)
    sql_event.listen(c,'before_cursor_execute',observe)
    try: facts=list(iter_ledger_facts(c,projection_request(r)))
    finally: sql_event.remove(c,'before_cursor_execute',observe)
    assert len(facts)==501 and len(queries)<=9

def test_economic_and_recording_cutoffs_exclude_future_bookings(valued):
    from datetime import timedelta
    c,r,trade=valued
    row=dict(c.execute(select(m.trade).where(m.trade.c.trade_id==trade)).mappings().one())
    ev=dict(c.execute(select(m.trade_lifecycle_event).where(m.trade_lifecycle_event.c.trade_id==trade)).mappings().one())
    for change in [dict(trade_datetime_utc=r.closing_cutoff+timedelta(seconds=1)),
                   dict(created_at_utc=r.information_cutoff+timedelta(seconds=1))]:
        identity=uuid4(); new=row|dict(trade_id=identity)|change
        c.execute(m.trade.insert().values(**new))
        c.execute(m.trade_lifecycle_event.insert().values(**(ev|dict(trade_id=identity,trade_lifecycle_event_id=uuid4(),event_datetime_utc=new['trade_datetime_utc']))))
    assert [f.trade_id for f in iter_ledger_facts(c,projection_request(r))]==[trade]

def test_reader_enforces_strategy_tenant_scope(valued):
    c,r,_=valued
    with pytest.raises((PermissionError,ValueError)):
        list(iter_ledger_facts(c,projection_request(replace(r,tenant_id=ids['second_tenant']))))

def test_reader_does_not_treat_missing_lifecycle_as_empty(valued):
    c,r,trade=valued
    row=dict(c.execute(select(m.trade).where(m.trade.c.trade_id==trade)).mappings().one())
    c.execute(m.trade.insert().values(**(row|dict(trade_id=uuid4()))))
    with pytest.raises(PositionError,match='BOOKED'):
        list(iter_ledger_facts(c,projection_request(r)))
