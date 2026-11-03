"""Bounded-query execution facts, never position/P&L-based report populations."""
from collections import defaultdict
from datetime import date,datetime,time,timezone
from decimal import Decimal
from uuid import UUID
import json
from sqlalchemy import select,func
from security_master_schema import models as m
from security_master_schema.reference_visibility import visible_clause

def canonical(value):
    if isinstance(value,dict):return {str(k):canonical(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [canonical(v) for v in value]
    if isinstance(value,(Decimal,UUID)):return str(value)
    if isinstance(value,(datetime,date)):return value.isoformat()
    return value

def executions(c,tenant,strategy,start,end,*,lock=False,trade_id=None):
    start=datetime.combine(start,time.min,timezone.utc)
    end=datetime.combine(end,time.max,timezone.utc)
    query=select(m.trade).join(m.strategy).where(m.strategy.c.tenant_id==tenant,
        m.trade.c.strategy_id==strategy,m.trade.c.trade_datetime_utc>=start,m.trade.c.trade_datetime_utc<=end)
    if trade_id is not None:query=query.where(m.trade.c.trade_id==trade_id)
    if lock:query=query.order_by(m.trade.c.trade_id).with_for_update(of=m.trade)
    rows=list(c.execute(query).mappings());events=defaultdict(list);descriptions={}
    for offset in range(0,len(rows),500):
        chunk=rows[offset:offset+500];ids=[r['trade_id'] for r in chunk]
        for event in c.execute(select(m.trade_lifecycle_event).where(m.trade_lifecycle_event.c.trade_id.in_(ids))
                .order_by(m.trade_lifecycle_event.c.sequence_no)).mappings():
            events[event['trade_id']].append(dict(event))
        node=m.financial_reference_node;listing=m.listing;instrument=m.instrument
        visible=visible_clause(node.c.reference_node_id,tenant)&visible_clause(
            func.coalesce(listing.c.instrument_node_id,node.c.reference_node_id),tenant)
        for r in c.execute(select(node.c.reference_node_id,node.c.canonical_name,m.instrument_type.c.type_code)
            .select_from(node.outerjoin(listing,listing.c.listing_node_id==node.c.reference_node_id)
                .outerjoin(instrument,instrument.c.instrument_node_id==func.coalesce(listing.c.instrument_node_id,node.c.reference_node_id))
                .outerjoin(m.instrument_type,m.instrument_type.c.instrument_type_id==instrument.c.instrument_type_id))
            .where(node.c.reference_node_id.in_([x['trade_subject_reference_node_id'] for x in chunk]),visible)).mappings():
            descriptions[r['reference_node_id']]=dict(r)
    currencies={r[0]:r[1] for r in c.execute(select(m.currency.c.currency_id,m.currency.c.currency_code))}
    result={}
    for row in rows:
        history=events[row['trade_id']];booked=next((e for e in history if e['event_type']=='BOOKED'),None)
        try:terms=json.loads(booked['event_payload']) if booked and booked['event_payload'] else {}
        except (ValueError,TypeError):terms={}
        desc=descriptions.get(row['trade_subject_reference_node_id'],{})
        # Conservatively require review of any post-booking lifecycle transition.
        state=history[-1]['event_type'] if history else row['lifecycle_status']
        facts=dict(instrumentName=desc.get('canonical_name','Reference unavailable'),
            instrumentType=desc.get('type_code','UNKNOWN'),subjectId=str(row['trade_subject_reference_node_id']),
            tradeType=row['trade_type'],lifecycleStatus=state,quantity=str(row['quantity']),
            quantityUnit=row['quantity_unit'],executionPrice=str(row['execution_price']) if row['execution_price'] is not None else None,
            priceBasis=row['price_basis'],priceCurrency=currencies.get(row['price_currency_id']),
            executionTime=row['trade_datetime_utc'].astimezone(timezone.utc).isoformat(),bookingTerms=terms,
            referenceVisible=bool(desc))
        result[row['trade_id']]=dict(facts=canonical(facts),source=canonical(dict(trade=dict(row),events=history)))
    return result
