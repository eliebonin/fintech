"""Fully funded note quotation and original immutable execution evidence."""
from copy import deepcopy
from decimal import Decimal,InvalidOperation,localcontext,Inexact
from hashlib import sha256
import json
from uuid import UUID


def positive(value,label):
    if value is None or isinstance(value,(float,bool)):raise ValueError(f'Explicit {label} required')
    try:result=Decimal(value)
    except (InvalidOperation,TypeError,ValueError):raise ValueError(f'Invalid {label}') from None
    if not result.is_finite() or result<=0:raise ValueError(f'Positive finite {label} required')
    return result


def quotation_factors(convention,quantity_unit):
    if (convention.get('kind')!='STRUCTURED_PRODUCT' or convention.get('funding')!='FULLY_FUNDED'
        or convention.get('quantityUnit')!=quantity_unit or convention.get('accrual') not in ('NONE','CLEAN','DIRTY')):
        raise ValueError('Explicit compatible fully funded structured-note quotation required')
    factor=positive(convention.get('quoteFactor'),'quote divisor');basis=convention.get('priceBasis')
    if basis=='UNIT_PRICE' and quantity_unit=='UNITS':return Decimal(1),factor
    if basis!='PCT_OF_PAR' or factor!=100:raise ValueError('Percentage notes require divisor 100')
    if quantity_unit=='NOMINAL':return Decimal(1),factor
    if quantity_unit=='UNITS':return positive(convention.get('denomination'),'denomination'),factor
    raise ValueError('Unsupported structured-note quantity basis')


def frozen_note_conventions(row,snapshot,identities):
    try:
        economics=snapshot['economics'];terms=economics['terms'];cv=terms['convention']
        multiplier,factor=quotation_factors(cv,row['quantity_unit'])
        parent=UUID(terms['instrumentId']);listing=terms.get('listingId')
        subject=UUID(listing) if listing else parent
        if (snapshot['kind']!='PRODUCT_BOOKING' or terms['kind']!='STRUCTURED_PRODUCT'
            or parent!=row['reference_instrument_node_id'] or subject!=row['trade_subject_reference_node_id']
            or row['price_currency_id']!=UUID(cv['priceCurrencyId']) or row['price_basis']!=cv['priceBasis']
            or terms['executionRoute']!=('LISTED' if listing else 'OTC')
            or row['execution_venue_id']!=(UUID(identities['venueId']) if listing else None)):
            raise ValueError('Frozen note identity, currency or quotation differs')
        original=deepcopy(terms);original.update(bookingEligible=False,termsFingerprint=None);original.pop('readinessStatus',None)
        digest=sha256(json.dumps(dict(identities)|original,sort_keys=True,default=str).encode()).hexdigest()
        if digest!=terms['termsFingerprint']:raise ValueError('Original structured-note fingerprint differs')
        quantity=Decimal(row['quantity']);price=Decimal(row['execution_price'])
        if not quantity.is_finite() or not quantity or not price.is_finite() or price<0:raise ValueError('Invalid note execution')
        with localcontext() as ctx:
            ctx.prec=512;ctx.traps[Inexact]=True
            quoted=abs(quantity)*price*multiplier/factor
        details=economics.get('structuredDetails') or {}
        accrued=Decimal(details['accruedInterestAmount']) if details.get('accruedInterestAmount') is not None else None
        if accrued is not None and not accrued.is_finite():raise ValueError('Finite accrued amount required')
        with localcontext() as ctx:
            ctx.prec=512;ctx.traps[Inexact]=True
            total=quoted+accrued if cv['accrual']=='CLEAN' and accrued is not None else quoted
        if total<0:raise ValueError('Negative funded-note consideration')
        if (Decimal(economics['amount'])!=total or economics.get('direction')!=('PAY' if quantity>0 else 'RECEIVE')):
            raise ValueError('Frozen note consideration differs from quantity/quote')
        if details and (details['priceType']!=cv['accrual'] or Decimal(details['quotedAmount'])!=quoted):
            raise ValueError('Frozen note accrued-price evidence differs')
        if details:
            expected_kind='QUOTED_AMOUNT_EXCLUDING_UNASSESSED_ACCRUAL' if cv['accrual']=='CLEAN' and accrued is None else 'CONSIDERATION'
            if economics.get('amountKind')!=expected_kind or details.get('considerationAmount')!=(None if expected_kind!='CONSIDERATION' else str(economics['amount'])):
                raise ValueError('Frozen note consideration completeness differs')
        return dict(kind='STRUCTURED_NOTE_BOOKING',instrumentId=str(parent),instrumentDefinitionId=identities['definitionId'],
            priceCurrencyId=cv['priceCurrencyId'],unitMultiplier=str(multiplier),quoteFactor=str(factor),
            productBasis='STRUCTURED_PRODUCT',priceBasis=cv['priceBasis'],noteConvention=deepcopy(cv),
            notePriceType=cv['accrual'],maturityDate=terms.get('maturityDate'),noteDetails=details,
            originalContextFingerprint=terms['termsFingerprint'])
    except (KeyError,TypeError,ArithmeticError) as exc:
        raise ValueError('Complete consistent frozen structured-note evidence required') from exc
