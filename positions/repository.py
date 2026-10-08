"""Scoped, keyset-batched immutable ledger reads in the caller's transaction."""
import json
from decimal import Decimal
from uuid import UUID
from sqlalchemy import select
from security_master_schema import models as m
from security_master_schema.tenancy import assert_tenant_owns_strategy
from .contracts import Booking, LedgerFact, PositionError

CHUNK_SIZE=500

def iter_ledger_facts(connection, request):
    assert_tenant_owns_strategy(connection,request.tenant_id,request.strategy_id)
    after=None
    while True:
        query=select(m.trade).where(m.trade.c.strategy_id==request.strategy_id,
            m.trade.c.trade_datetime_utc<=request.closing_cutoff,
            m.trade.c.created_at_utc<=request.information_cutoff)
        if after is not None: query=query.where(m.trade.c.trade_id>after)
        rows=connection.execute(query.order_by(m.trade.c.trade_id).limit(CHUNK_SIZE)).mappings().all()
        if not rows: return
        identities=[row['trade_id'] for row in rows]
        chains={identity:[] for identity in identities}; snapshots={}; definitions=set(); parents=set()
        for e in connection.execute(select(m.trade_lifecycle_event).where(
            m.trade_lifecycle_event.c.trade_id.in_(identities),
            m.trade_lifecycle_event.c.recorded_at_utc<=request.information_cutoff).order_by(
                m.trade_lifecycle_event.c.trade_id,m.trade_lifecycle_event.c.sequence_no)).mappings():
            chains[e['trade_id']].append(e)
            if e['event_type']=='BOOKED':
                try:
                    snapshot=json.loads(e['event_payload'] or '{}')
                    if snapshot['kind']!='CASH_BOOKING': raise PositionError('Unsupported booking economics')
                    definition=UUID(snapshot['instrumentDefinitionId']); parent=UUID(snapshot['instrumentId'])
                    snapshots[e['trade_id']]=(snapshot,definition,parent)
                    definitions.add(definition); parents.add(parent)
                except (KeyError,TypeError,ValueError) as exc:
                    raise PositionError('Missing frozen BOOKED conventions or unsupported booking economics') from exc
        products={row.instrument_definition_version_id:(row.instrument_node_id,row.type_code)
            for row in connection.execute(select(m.instrument_definition_version.c.instrument_definition_version_id,
                m.instrument_definition_version.c.instrument_node_id,m.instrument_type.c.type_code).join(m.instrument_type).where(
                    m.instrument_definition_version.c.instrument_definition_version_id.in_(definitions)))}
        etp={}
        if any(product=='ETP' for _,product in products.values()):
            for term in connection.execute(select(m.etp_terms).where(m.etp_terms.c.instrument_node_id.in_(parents))
                    .order_by(m.etp_terms.c.sequence_no.desc())).mappings():
                etp.setdefault(term['instrument_node_id'],[]).append(term)
        for row in rows:
            chain=chains[row['trade_id']]
            if not chain or row['trade_id'] not in snapshots: raise PositionError('Missing original BOOKED evidence')
            snapshot,definition,parent=snapshots[row['trade_id']]
            if definition not in products or products[definition][0]!=parent: raise PositionError('Frozen definition identity mismatch')
            product=products[definition][1]
            if product=='ETP':
                term=next((x for x in etp.get(parent,[]) if x['effective_from']<=row['trade_datetime_utc'].date()),None)
                product=term['etp_kind'] if term else None
            if product not in {'EQUITY','ETF'}: raise PositionError('Unsupported booking product')
            try:
                currency=UUID(snapshot['priceCurrencyId'])
                booking=Booking(row['trade_id'],row['trade_subject_reference_node_id'],currency,row['quantity_unit'],
                    row['quantity'],row['execution_price'],Decimal(snapshot['unitMultiplier']),Decimal(snapshot['quoteFactor']),definition,product)
            except (KeyError,ValueError,TypeError) as exc: raise PositionError('Invalid frozen BOOKED conventions') from exc
            if currency!=row['price_currency_id'] or row['price_basis']!='UNIT_PRICE':
                raise PositionError('Frozen booking price currency/basis is inconsistent')
            for e in chain:
                if e['event_type']=='BOOKED' and e['event_datetime_utc']!=row['trade_datetime_utc']:
                    raise PositionError('BOOKED execution time is inconsistent')
                yield LedgerFact(e['trade_lifecycle_event_id'],row['trade_id'],request.tenant_id,request.strategy_id,
                    e['sequence_no'],e['event_type'],e['event_datetime_utc'],e['recorded_at_utc'],
                    booking if e['event_type']=='BOOKED' else None)
        after=rows[-1]['trade_id']
