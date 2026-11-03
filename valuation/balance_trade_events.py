"""Read-only bond trade annotations using the accrued-balance ledger conventions."""
from datetime import datetime,time,timezone
from decimal import Decimal
from uuid import UUID
from sqlalchemy import select,union_all
from security_master_schema import models as m
from security_master_schema.strategy_access import require_strategy_action
from security_master_schema.reference_visibility import visible_clause
from positions.contracts import ProjectionRequest
from positions.repository import iter_ledger_facts
from positions.reconstruction import reconstruct,canonical
from .accrued_balance_inputs import _facts


def trade_events(c,tenant,actor,strategy,instrument,start,end,information):
    require_strategy_action(c,tenant,actor,'VALUATION_READ',strategy)
    require_strategy_action(c,tenant,actor,'TRADE_READ',strategy)
    if end<start:raise ValueError('From date must be on or before To date')
    if not c.scalar(select(m.instrument.c.instrument_node_id).join(m.instrument_type).where(
        m.instrument.c.instrument_node_id==instrument,m.instrument_type.c.type_code=='BOND',visible_clause(m.instrument.c.instrument_node_id,tenant))):
        raise LookupError('Canonical bond unavailable')
    subjects=union_all(select(m.instrument.c.instrument_node_id).where(m.instrument.c.instrument_node_id==instrument),
        select(m.listing.c.listing_node_id).where(m.listing.c.instrument_node_id==instrument,visible_clause(m.listing.c.listing_node_id,tenant)))
    request=ProjectionRequest(tenant,strategy,datetime.combine(end,time.max,timezone.utc),information)
    projection=reconstruct(tuple(iter_ledger_facts(c,request,subject_ids=subjects)),request)
    facts=[fact for fact in _facts(projection) if UUID(fact.booking.product_evidence['instrumentId'])==instrument
        and start<=(fact.booking.valuation_effective_date or fact.effective_at.astimezone(timezone.utc).date())<=end]
    # Enrich selected rows in bounded batches. Ledger facts remain the authority
    # for units/signs/accruals; current labels are not frozen balance-build proof.
    identities=list(dict.fromkeys(fact.trade_id for fact in facts));metadata={};parties={}
    for offset in range(0,len(identities),500):
        chunk=identities[offset:offset+500]
        metadata.update({row.trade_id:row for row in c.execute(select(m.trade.c.trade_id,m.trade.c.trade_datetime_utc,
            m.trade.c.settlement_date,m.trade.c.trade_type).where(m.trade.c.strategy_id==strategy,m.trade.c.trade_id.in_(chunk)))})
        for row in c.execute(select(m.trade_party_role.c.trade_id,m.organisation.c.display_name).join(m.organisation,
            m.trade_party_role.c.organisation_id==m.organisation.c.organisation_id).where(
            m.trade_party_role.c.trade_id.in_(chunk),m.trade_party_role.c.role=='COUNTERPARTY')):
            parties.setdefault(row.trade_id,set()).add(row.display_name)
    currencies=dict(c.execute(select(m.currency.c.currency_id,m.currency.c.currency_code).where(
        m.currency.c.currency_id.in_({fact.booking.currency_id for fact in facts}))).all()) if facts else {}
    result=[]
    for fact in facts:
        booking=fact.booking;row=metadata[fact.trade_id];details=booking.product_evidence.get('bondDetails') or {}
        accrued=Decimal(details['accruedInterestAmount']) if details.get('accruedInterestAmount') is not None else None
        if booking.product_evidence.get('redemptionEvidence'):accrued=Decimal(0)
        if booking.quantity<0 and accrued is not None:accrued=accrued.copy_negate()
        result.append(canonical(dict(tradeId=fact.trade_id,instrumentId=instrument,
            balanceDate=booking.valuation_effective_date or fact.effective_at.astimezone(timezone.utc).date(),
            executionDatetime=row.trade_datetime_utc,settlementDate=row.settlement_date,
            side='BUY' if booking.quantity>0 else 'SELL',signedQuantity=booking.quantity,quantityUnit=booking.quantity_unit,
            tradeAccruedAmount=accrued,currency=currencies[booking.currency_id],
            counterparty=', '.join(sorted(parties[fact.trade_id])) if fact.trade_id in parties else None,tradeType=row.trade_type)))
    return sorted(result,key=lambda item:(item['balanceDate'],item['executionDatetime'],item['tradeId']))
