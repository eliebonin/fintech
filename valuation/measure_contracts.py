"""Read-only validation of original product bookings for paged measure previews.

The quantity ledger deliberately permits incomplete old pricing metadata. These
adapters validate only requested product buckets, so an invalid contract cannot
hide other positions or trigger a substitution of current reference terms.
"""
from datetime import date
from decimal import Decimal
from uuid import UUID
from sqlalchemy import select
from security_master_schema import models as m
from security_master_schema.structured_note_valuation import quotation_factors
from security_master_schema.swap_terms import parse_swap_terms


class MeasureBookings:
    def __init__(self,c,request,buckets,descriptions):
        self.c=c;self.descriptions=descriptions;self.validated={};self.identities={}
        ids={trade for b in buckets if b.key.product_basis in {'OPTION','STRUCTURED_PRODUCT','FUTURE','SWAP'} for trade in b.trade_ids}
        self.rows={}
        ordered=sorted(ids,key=str)
        # Batch every requested trade; this bounds SQL parameters, not history.
        for offset in range(0,len(ordered),500):
            self.rows.update((r['trade_id'],r) for r in c.execute(select(m.trade).join(m.strategy,
                m.strategy.c.strategy_id==m.trade.c.strategy_id).where(m.trade.c.trade_id.in_(ordered[offset:offset+500]),
                m.trade.c.strategy_id==request.strategy_id,m.strategy.c.tenant_id==request.tenant_id)).mappings())

    def validate(self,bucket):
        for identity in bucket.trade_ids:
            if identity in self.validated:continue
            row=self.rows.get(identity)
            if row is None:raise ValueError('Scoped original booking is unavailable')
            snapshot=self.descriptions[identity]['bookingEvidence'];product=bucket.key.product_basis
            if product=='OPTION':
                from positions.option import normalize_booking
                proof=normalize_booking(self.c,row,snapshot,None)
            elif product=='STRUCTURED_PRODUCT':
                from positions.structured_note import normalize_booking
                proof=normalize_booking(self.c,row,snapshot,identity_cache=self.identities)
            elif product=='FUTURE':
                from positions.future import normalize_booking
                proof=normalize_booking(self.c,row,snapshot,identity_cache=self.identities)
            elif product=='SWAP':
                from security_master_schema.swap_valuation import frozen_swap_conventions
                proof=frozen_swap_conventions(row,snapshot)
            else:raise ValueError('Unsupported measure booking adapter')
            if (Decimal(proof['unitMultiplier'])!=bucket.key.unit_multiplier or Decimal(proof['quoteFactor'])!=bucket.key.quote_factor
                or UUID(proof['priceCurrencyId'])!=bucket.key.currency_id):
                raise ValueError('Original booked factors/currency differ from the position')
            self.validated[identity]=proof


def option_terms(bucket,terms,currencies,day):
    key=bucket.key
    fields=('instrumentId','listingId','optionType','underlyingId','strike','strikeCurrency','deliverableUnits',
        'expiryDate','premiumCurrency','premiumMultiplier','quoteFactor')
    def semantics(t):
        numeric={'strike','deliverableUnits','premiumMultiplier','quoteFactor'}
        return tuple(Decimal(t[f]) if f in numeric else t.get(f) for f in fields)
    if len({semantics(t) for t in terms})!=1:
        raise ValueError('One compatible frozen option contract is required')
    t=terms[0]
    if key.quantity_unit!='CONTRACTS' or UUID(t['listingId'])!=key.subject_id:
        raise ValueError('Frozen option listing/quantity basis differs')
    if day>date.fromisoformat(t['expiryDate']):raise ValueError('Open option after expiry requires Ops lifecycle handling; no automatic zero is assumed')
    strike_currency=next((identity for identity,code in currencies.items() if code==t['strikeCurrency']),None)
    if strike_currency is None:raise ValueError('Frozen option strike currency is unavailable')
    if Decimal(t['premiumMultiplier'])!=key.unit_multiplier or Decimal(t['quoteFactor'])!=key.quote_factor:
        raise ValueError('Frozen option premium factors differ')
    return t,strike_currency


def note_terms(bucket,terms,day):
    key=bucket.key;cvs=[t['convention'] for t in terms]
    fingerprints={(cv.get('priceBasis'),cv.get('quantityUnit'),cv.get('accrual'),cv.get('funding'),
        quotation_factors(cv,key.quantity_unit),Decimal(cv['denomination']) if cv.get('denomination') is not None else None) for cv in cvs}
    if len(fingerprints)!=1 or len({t['instrumentId'] for t in terms})!=1:
        raise ValueError('One compatible frozen funded-note quotation is required')
    for t,cv in zip(terms,cvs):
        if (quotation_factors(cv,key.quantity_unit)!=(key.unit_multiplier,key.quote_factor)
            or UUID(cv['priceCurrencyId'])!=key.currency_id
            or UUID(t.get('listingId') or t['instrumentId'])!=key.subject_id):
            raise ValueError('Frozen note units, currency or subject differ')
        if t.get('maturityDate') and day>date.fromisoformat(t['maturityDate']):
            raise ValueError('Open structured note after maturity requires Ops closure; no automatic zero is assumed')
    return cvs[0]


def swap_terms(bucket,terms,day):
    parsed=[parse_swap_terms(t['swapDetails']['genericTerms']) for t in terms]
    semantics=[g.model_dump(mode='python',exclude={'source_reference','tenant_identifier'}) for g in parsed]
    if any(value!=semantics[0] for value in semantics[1:]):
        raise ValueError('One compatible frozen swap contract is required')
    g=parsed[0];key=bucket.key
    if (g.quantity_unit!=key.quantity_unit or g.quote_currency_id!=key.currency_id
        or g.quote_factor!=key.quote_factor or key.unit_multiplier!=1):
        raise ValueError('Frozen whole-swap quantity/currency/quote divisor mismatch')
    if any(UUID(t['instrumentId'])!=key.subject_id for t in terms):raise ValueError('Frozen swap identity differs')
    if day>g.maturity_date:raise ValueError('Open swap after maturity requires Ops closure; no automatic zero is assumed')
    return g
