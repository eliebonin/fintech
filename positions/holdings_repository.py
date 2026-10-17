"""Batched quantity-only ledger adapter; never select prices or compute value."""
import json
from datetime import date,datetime,timezone
from decimal import Decimal,InvalidOperation
from uuid import UUID
from sqlalchemy import select
from security_master_schema import models as m
from .contracts import Booking,LedgerFact,PositionError


def holding_contract_date(payload):
    """Display-only frozen date; never substitute settlement/current master terms."""
    try:
        terms=payload.get('economics',{}).get('terms',{})
        convention=terms.get('convention') or {}
        if convention.get('kind')=='FUTURE' and convention.get('lastTradingAtUtc'):
            stamp=datetime.fromisoformat(convention['lastTradingAtUtc'].replace('Z','+00:00'))
            if stamp.tzinfo is None:return None,None
            return stamp.astimezone(timezone.utc).date().isoformat(),'Last trading'
        for source,field,label in ((terms,'expiryDate','Expiry'),(terms,'maturityDate','Maturity'),
                (payload.get('valuationConventions') or {},'maturityDate','Maturity')):
            if source.get(field):return date.fromisoformat(source[field]).isoformat(),label
    except (ValueError,TypeError,AttributeError):pass
    return None,None


def holding_conventions(payload,unit):
    try:
        terms=payload.get('economics',{}).get('terms',{})
        convention=terms.get('convention') or {}
        frozen=payload.get('valuationConventions') or payload
        multiplier=frozen.get('unitMultiplier',terms.get('premiumMultiplier',convention.get('monetaryMultiplier',1)))
        factor=frozen.get('quoteFactor',terms.get('quoteFactor',convention.get('quoteFactor',1)))
        product=payload.get('productBasis') or convention.get('kind') or terms.get('kind') or payload.get('kind') or 'BOOKED_UNITS'
        if payload.get('kind') in {'FX_FORWARD_BOOKING','FX_FORWARD_MATURITY'}:product='FX_FORWARD'
        return product,Decimal(str(multiplier)),Decimal(str(factor))
    except (InvalidOperation,TypeError,ValueError,AttributeError):
        raise PositionError('Frozen holdings unit conventions are invalid') from None


def load_holdings_facts(c,request):
    facts=[]; descriptions={}; after=None; product_types={}
    node=m.financial_reference_node; currency=m.currency
    while True:
        query=select(m.trade,node.c.canonical_name,currency.c.currency_code).join(node,
            node.c.reference_node_id==m.trade.c.trade_subject_reference_node_id).outerjoin(currency,
            currency.c.currency_id==m.trade.c.price_currency_id).where(
                m.trade.c.strategy_id==request.strategy_id,m.trade.c.trade_datetime_utc<=request.closing_cutoff,
                m.trade.c.created_at_utc<=request.information_cutoff,
                # Cash flows and dated cash snapshots are not security positions.
                m.trade.c.price_basis.is_distinct_from('CASH_AMOUNT'))
        if after:query=query.where(m.trade.c.trade_id>after)
        rows=c.execute(query.order_by(m.trade.c.trade_id).limit(500)).mappings().all()
        if not rows:break
        ids=[r['trade_id'] for r in rows]; chains={identity:[] for identity in ids}
        for event in c.execute(select(m.trade_lifecycle_event).where(
            m.trade_lifecycle_event.c.trade_id.in_(ids),m.trade_lifecycle_event.c.recorded_at_utc<=request.information_cutoff)
            .order_by(m.trade_lifecycle_event.c.trade_id,m.trade_lifecycle_event.c.sequence_no)).mappings():
            chains[event['trade_id']].append(event)
        # Parse once, collect every retained cash definition in this keyset page,
        # then read types together. Keep missing/invalid evidence fail-closed;
        # there is no current-definition substitution or total-history limit.
        parsed={};definitions=set()
        for identity,events in chains.items():
            for event in events:
                try:payload=json.loads(event['event_payload'] or '{}')
                except (ValueError,TypeError):raise PositionError(f'Trade {identity}: invalid lifecycle evidence') from None
                parsed[event['trade_lifecycle_event_id']]=payload
                if event['event_type']=='BOOKED' and isinstance(payload,dict) and payload.get('kind')=='CASH_BOOKING' and payload.get('instrumentDefinitionId'):
                    definitions.add(UUID(payload['instrumentDefinitionId']))
        missing=definitions-product_types.keys()
        if missing:
            product_types.update(dict(c.execute(select(m.instrument_definition_version.c.instrument_definition_version_id,
                m.instrument_type.c.type_code).select_from(m.instrument_type.join(m.instrument_definition_version,
                    m.instrument_definition_version.c.instrument_type_id==m.instrument_type.c.instrument_type_id))
                .where(m.instrument_definition_version.c.instrument_definition_version_id.in_(missing))).all()))
        for row in rows:
            identity=row['trade_id']; events=chains[identity]
            contract_date,contract_date_label=None,None
            booking_evidence={}
            if not events:raise PositionError(f"Trade {identity}: missing BOOKED lifecycle evidence")
            if row['price_currency_id'] is None:raise PositionError(f"Trade {identity}: missing quantity grouping currency")
            for event in events:
                payload=parsed[event['trade_lifecycle_event_id']]
                booking=None
                if event['event_type']=='BOOKED':
                    booking_evidence=payload
                    contract_date,contract_date_label=holding_contract_date(payload)
                    if event['event_datetime_utc']!=row['trade_datetime_utc']:
                        raise PositionError('BOOKED execution time differs from retained trade')
                    # Quantity, currency and unit are immutable booking columns.
                    # Frozen unit conventions distinguish incompatible versions;
                    # missing old valuation snapshots do not invent a market price.
                    product,multiplier,factor=holding_conventions(payload,row['quantity_unit'])
                    if payload.get('kind')=='CASH_BOOKING' and payload.get('instrumentDefinitionId'):
                        definition=UUID(payload['instrumentDefinitionId'])
                        if not product_types.get(definition):raise PositionError('Missing booked instrument definition')
                        product='ETF' if product_types[definition]=='ETP' else product_types[definition]
                    if product=='FUND_SHARE_CLASS':product='FUND'
                    booking=Booking(identity,row['trade_subject_reference_node_id'],row['price_currency_id'],row['quantity_unit'],
                        row['quantity'],row['execution_price'],Decimal(str(multiplier)),Decimal(str(factor)),
                        UUID(payload['instrumentDefinitionId']) if payload.get('instrumentDefinitionId') else row['reference_instrument_node_id'] or row['trade_subject_reference_node_id'],
                        product,row['valuation_effective_date'])
                facts.append(LedgerFact(event['trade_lifecycle_event_id'],identity,request.tenant_id,request.strategy_id,
                    event['sequence_no'],event['event_type'],event['event_datetime_utc'],event['recorded_at_utc'],booking,
                    payload if event['event_type'] in {'CORRECTED','SUPERSEDED'} else None))
            descriptions[identity]=dict(name=row['canonical_name'],currency=row['currency_code'],tradeType=row['trade_type'],
                bookingEvidence=booking_evidence,
                contractDate=contract_date,contractDateLabel=contract_date_label,
                instrumentId=str(row['reference_instrument_node_id'] or row['trade_subject_reference_node_id']),
                executionPrice=str(row['execution_price']) if row['execution_price'] is not None else None,
                settlementDate=row['settlement_date'],executionDate=row['trade_datetime_utc'])
        after=rows[-1]['trade_id']
    return facts,descriptions
