"""Explicit real ledger cash flows. Recognition is distinct from settlement."""
from dataclasses import dataclass,replace
from datetime import datetime,time,timezone
from decimal import Decimal,localcontext
import json
from uuid import UUID
from sqlalchemy import select
from security_master_schema import models as m
from positions.contracts import LedgerFact,PositionKey,PositionBucket
from .economics import finite_decimal,evidence_hash,canonical_payload,MarketAttribution
from .position_calculation import PositionLine
from .fx import resolve_fx

COMPONENTS=frozenset({'DIVIDEND','RESET','COUPON','CASHFLOW','BROKER_FEE','CUSTODY_FEE','MANAGEMENT_FEE','PERFORMANCE_FEE','TAX','OTHER_COST'})
ENDPOINT='/v1/valuation/economic-flows'


def flow_component(component,role,amount,fx):
    finite_decimal(amount,'cash amount');finite_decimal(fx,'flow FX',positive=True)
    if component not in COMPONENTS or role not in {'INCOME','PAYMENT_ONLY'}:
        raise ValueError('Unsupported explicit economic flow classification')
    if component=='COUPON' and role!='PAYMENT_ONLY':
        raise ValueError('Bond coupon receipts are payment-only; record earned interest as daily accrual')
    with localcontext() as ctx:
        ctx.prec=512
        return (None,Decimal(0)) if role=='PAYMENT_ONLY' else (component,amount*fx)


def book_flow(c,tenant,actor,payload,key):
    from apps.reference_api.booking_controls import authorize_booking,lock_booking_strategy,find_booking_replay,record_booking_replay
    from apps.reference_api.product_booking import require_visible
    authorize_booking(c,tenant,actor)
    amount=payload['amount'];flow_component(payload['component'],payload['recognitionRole'],amount,Decimal(1))
    if amount==0: raise ValueError('Book a nonzero cash amount; confirmed zero coverage is not a trade')
    if not payload['sourceReference'].strip() or payload['economicDate']>datetime.now(timezone.utc).date():
        raise ValueError('Source reference and nonfuture economic date required')
    digest=evidence_hash(payload)
    replay=find_booking_replay(c,tenant,ENDPOINT,key,digest)
    if replay: return replay
    lock_booking_strategy(c,tenant,payload['strategyId'])
    require_visible(c,tenant,payload['instrumentId'])
    if not c.scalar(select(m.instrument.c.instrument_node_id).where(m.instrument.c.instrument_node_id==payload['instrumentId'])):
        raise ValueError('Economic flows must reference a canonical instrument')
    if not c.scalar(select(m.currency.c.currency_id).where(m.currency.c.currency_id==payload['currencyId'],m.currency.c.status=='ACTIVE')):
        raise ValueError('Active flow currency required')
    effective=datetime.combine(payload['economicDate'],time(0),timezone.utc)
    snapshot=canonical_payload(payload | dict(schemaVersion=1,kind='ECONOMIC_FLOW_BOOKING'))
    identity=c.scalar(m.trade.insert().values(strategy_id=payload['strategyId'],trade_subject_reference_node_id=payload['instrumentId'],
        reference_instrument_node_id=payload['instrumentId'],trade_type=payload['component'],quantity=amount,quantity_unit='CURRENCY_AMOUNT',
        execution_price=Decimal(1),price_basis='CASH_AMOUNT',price_currency_id=payload['currencyId'],trade_datetime_utc=effective,
        settlement_date=payload.get('paymentDate'),booked_by_user_account_id=actor,created_by_user_account_id=actor,execution_channel='API',
        comment=payload['sourceReference']).returning(m.trade.c.trade_id))
    c.execute(m.trade_lifecycle_event.insert().values(trade_id=identity,sequence_no=1,event_type='BOOKED',event_datetime_utc=effective,
        recorded_by_user_account_id=actor,event_payload=json.dumps(snapshot),payload_hash=digest,source_event_id=key))
    record_booking_replay(c,tenant,ENDPOINT,key,digest,identity)
    return identity


def cancel_flow(c,tenant,actor,trade_id,reason,key):
    """Cancel an erroneous flow booking, not settle or reverse instrument exposure."""
    from apps.reference_api.booking_controls import authorize_booking,find_booking_replay,record_booking_replay
    authorize_booking(c,tenant,actor,action='TRADE_CORRECT')
    if not isinstance(reason,str) or not reason.strip() or len(reason)>2000: raise ValueError('Cancellation reason required')
    endpoint=ENDPOINT+'/cancel';digest=evidence_hash(dict(tradeId=trade_id,reason=reason))
    replay=find_booking_replay(c,tenant,endpoint,key,digest)
    if replay: return replay
    row=c.execute(select(m.trade).join(m.strategy).where(m.trade.c.trade_id==trade_id,
        m.strategy.c.tenant_id==tenant).with_for_update(of=m.trade)).mappings().one_or_none()
    if row is None: raise LookupError('Economic flow not found')
    chain=c.execute(select(m.trade_lifecycle_event).where(m.trade_lifecycle_event.c.trade_id==trade_id)
        .order_by(m.trade_lifecycle_event.c.sequence_no)).mappings().all()
    if (row['price_basis']!='CASH_AMOUNT' or row['trade_type'] not in COMPONENTS or row['lifecycle_status']!='BOOKED'
        or len(chain)!=1 or chain[0]['sequence_no']!=1 or chain[0]['event_type']!='BOOKED'
        or json.loads(chain[0]['event_payload'] or '{}').get('kind')!='ECONOMIC_FLOW_BOOKING'):
        raise ValueError('Only active typed economic-flow bookings can be cancelled here')
    payload=dict(schemaVersion=1,kind='ECONOMIC_FLOW_CANCELLATION',tradeId=str(trade_id),reason=reason.strip())
    c.execute(m.trade_lifecycle_event.insert().values(trade_id=trade_id,sequence_no=2,event_type='CANCELLED',
        event_datetime_utc=row['trade_datetime_utc'],supersedes_event_id=chain[0]['trade_lifecycle_event_id'],
        recorded_by_user_account_id=actor,event_payload=json.dumps(payload),payload_hash=digest,source_event_id=key))
    c.execute(m.trade.update().where(m.trade.c.trade_id==trade_id).values(lifecycle_status='CANCELLED'))
    record_booking_replay(c,tenant,endpoint,key,digest,trade_id)
    return trade_id


@dataclass(frozen=True)
class EconomicFlow:
    trade_id: UUID
    instrument_id: UUID
    economic_date: object
    component: str | None
    local_amount: Decimal
    base_amount: Decimal
    currency_id: UUID
    evidence: dict
    facts: tuple
    fx: object


def load_economic_flows(c,request):
    from security_master_schema.tenancy import assert_tenant_owns_strategy
    assert_tenant_owns_strategy(c,request.tenant_id,request.strategy_id)
    rows=c.execute(select(m.trade).where(m.trade.c.strategy_id==request.strategy_id,m.trade.c.price_basis=='CASH_AMOUNT',
        m.trade.c.created_at_utc<=request.information_cutoff,m.trade.c.trade_datetime_utc>request.opening_cutoff,
        m.trade.c.trade_datetime_utc<=request.closing_cutoff).order_by(m.trade.c.trade_id)).mappings().all()
    flows=[]
    for row in rows:
        chain=c.execute(select(m.trade_lifecycle_event).where(m.trade_lifecycle_event.c.trade_id==row['trade_id'],
            m.trade_lifecycle_event.c.recorded_at_utc<=request.information_cutoff).order_by(m.trade_lifecycle_event.c.sequence_no)).mappings().all()
        if not chain or [e['sequence_no'] for e in chain]!=list(range(1,len(chain)+1)) or chain[0]['event_type']!='BOOKED':
            raise ValueError('Missing frozen booked economic-flow evidence')
        if any(e['event_type'] in ('CANCELLED','SUPERSEDED') for e in chain): continue
        if any(e['event_type'] not in ('BOOKED','CORRECTED') for e in chain): raise ValueError('Unsupported cash-flow lifecycle')
        payload=json.loads(chain[0]['event_payload'] or '{}')
        if (payload.get('kind')!='ECONOMIC_FLOW_BOOKING' or payload.get('schemaVersion')!=1
            or UUID(payload['instrumentId'])!=row['reference_instrument_node_id']
            or UUID(payload['strategyId'])!=request.strategy_id or UUID(payload['currencyId'])!=row['price_currency_id']
            or Decimal(payload['amount'])!=row['quantity'] or row['quantity_unit']!='CURRENCY_AMOUNT'
            or row['execution_price']!=1 or row['trade_type']!=payload['component']
            or payload['economicDate']!=row['trade_datetime_utc'].date().isoformat()
            or chain[0]['event_datetime_utc']!=row['trade_datetime_utc']):
            raise ValueError('Inconsistent frozen monetary cash-flow conventions')
        fx=resolve_fx(c,request,row['price_currency_id'],request.reporting_currency_id,row['trade_datetime_utc'].date())
        component,base=flow_component(payload['component'],payload['recognitionRole'],row['quantity'],fx.rate)
        facts=tuple(LedgerFact(e['trade_lifecycle_event_id'],row['trade_id'],request.tenant_id,request.strategy_id,
            e['sequence_no'],e['event_type'],e['event_datetime_utc'],e['recorded_at_utc']) for e in chain)
        flows.append(EconomicFlow(row['trade_id'],row['reference_instrument_node_id'],row['trade_datetime_utc'].date(),component,
            row['quantity'],base,row['price_currency_id'],dict(tradeId=str(row['trade_id']),booking=payload,fx=fx.evidence),facts,fx))
    return tuple(flows)


def attach_flows(projection,period,flows):
    """Cash amount buckets hold no shares or fictitious execution effects."""
    groups={};zero=Decimal(0)
    for flow in flows:
        key=PositionKey(projection.request.tenant_id,projection.request.strategy_id,flow.instrument_id,flow.currency_id,
            'CURRENCY_AMOUNT','ECONOMIC_FLOW',Decimal(1),Decimal(1))
        groups.setdefault(key,[]).append(flow)
    lines=list(period.lines);buckets=list(projection.buckets);facts=list(projection.facts)
    for key,records in groups.items():
        bucket=PositionBucket(key,zero,zero,tuple(f.trade_id for f in records),())
        components={}
        with localcontext() as ctx:
            ctx.prec=512
            for flow in records:
                if flow.component: components[flow.component]=components.get(flow.component,zero)+flow.base_amount
        lines.append(PositionLine(bucket,MarketAttribution(zero,zero,zero,zero,zero,zero),zero,components,
            tuple(f.evidence for f in records)))
        buckets.append(bucket)
        facts.extend(fact for flow in records for fact in flow.facts)
    return replace(projection,buckets=tuple(buckets),facts=tuple(facts)),replace(period,lines=tuple(lines))
