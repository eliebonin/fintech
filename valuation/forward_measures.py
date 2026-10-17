"""Contractual currency obligations from validated, retained forward bookings.

This adapter selects no marks and makes no discounted-MTM or cash claim.
"""
import json
from dataclasses import dataclass,field
from datetime import date
from decimal import Decimal,localcontext,Inexact
from uuid import UUID
from sqlalchemy import select
from security_master_schema import models as m
from positions.fx_forward import normalize_booking
from .position_measures import fx_forward_legs


@dataclass(frozen=True)
class ForwardBookingPopulation:
    request: object
    transaction: object
    trades: dict
    events: dict
    currency_cache: dict=field(default_factory=dict)


def load_contract_bookings(c,request,buckets):
    """Batch retained proof IO; no netting or relaxation of per-fill checks."""
    identities=set()
    for bucket in buckets:
        if (bucket.key.tenant_id,bucket.key.strategy_id)!=(request.tenant_id,request.strategy_id):
            raise ValueError('Forward position scope mismatch')
        identities.update(bucket.trade_ids)
    trades={};events={};ordered=sorted(identities)
    for offset in range(0,len(ordered),500):
        page=ordered[offset:offset+500]
        for row in c.execute(select(m.trade).where(m.trade.c.trade_id.in_(page),
                m.trade.c.strategy_id==request.strategy_id,m.trade.c.created_at_utc<=request.information_cutoff)
                .order_by(m.trade.c.trade_id)).mappings():
            trades[row['trade_id']]=row
        for event in c.execute(select(m.trade_lifecycle_event).where(
                m.trade_lifecycle_event.c.trade_id.in_(page),m.trade_lifecycle_event.c.event_type=='BOOKED',
                m.trade_lifecycle_event.c.recorded_at_utc<=request.information_cutoff)).mappings():
            events[event['trade_id']]=event
    return ForwardBookingPopulation(request,c.get_transaction(),trades,events)


def contractual_legs(c,request,bucket,*,population=None):
    key=bucket.key
    if (key.tenant_id,key.strategy_id)!=(request.tenant_id,request.strategy_id):
        raise ValueError('Forward position scope mismatch')
    if key.quantity_unit!='CURRENCY_AMOUNT' or key.unit_multiplier!=1 or key.quote_factor!=1:
        raise ValueError('Forward needs unscaled base-currency amounts')
    if population is None:population=load_contract_bookings(c,request,[bucket])
    if population.request!=request or population.transaction is not c.get_transaction():
        raise ValueError('Forward booking population scope or transaction mismatch')
    trades=[population.trades[identity] for identity in sorted(set(bucket.trade_ids)) if identity in population.trades]
    events={identity:population.events[identity] for identity in bucket.trade_ids if identity in population.events}
    if len(trades)!=len(bucket.trade_ids) or len(events)!=len(trades):
        raise ValueError('Retained scoped forward booking evidence is incomplete')
    agreements=[];base=Decimal(0);quote=Decimal(0);proofs=[]
    with localcontext() as ctx:
        ctx.prec=512;ctx.traps[Inexact]=True
        for row in trades:
            if row['trade_subject_reference_node_id']!=key.subject_id or row['price_currency_id']!=key.currency_id:
                raise ValueError('Forward booking differs from projected identity/currency')
            event=events[row['trade_id']];snapshot=json.loads(event['event_payload'])
            if snapshot.get('kind') not in {'FX_FORWARD_BOOKING','FX_FORWARD_MATURITY'}:
                raise ValueError('Frozen deliverable-forward booking required')
            cv=normalize_booking(c,row,snapshot,event,currency_cache=population.currency_cache)
            agreements.append(tuple(Decimal(cv[f]) if f=='agreedRate' else cv[f] for f in ('instrumentId','baseCurrencyId','priceCurrencyId',
                'agreedRate','maturityDate','quoteConvention','settlementType')))
            legs=fx_forward_legs(row['quantity'],Decimal(cv['agreedRate']))
            base+=legs['baseAmount'];quote+=legs['quoteAmount']
            proofs.append(dict(tradeId=str(row['trade_id']),conventions=cv,bookedPayloadHash=event['payload_hash']))
    if len(set(agreements))!=1:
        raise ValueError('Mixed forward agreements require separate contractual positions; currency legs cannot be netted at a sampled rate')
    if base!=bucket.closing_quantity:
        raise ValueError('Forward obligations differ from reconstructed quantity')
    return dict(baseCurrencyId=UUID(cv['baseCurrencyId']),quoteCurrencyId=UUID(cv['priceCurrencyId']),
        baseAmount=base,quoteAmount=quote,maturityDate=date.fromisoformat(cv['maturityDate']),bookings=proofs)
