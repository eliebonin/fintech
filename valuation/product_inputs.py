"""Explicit product capabilities. Booking support is not valuation readiness."""
from dataclasses import dataclass
from decimal import Decimal,localcontext
from .economics import finite_decimal


def option_mark_context(projection,subject,cutoff):
    """Canonical contract premium; listing/underlying multipliers are not reapplied."""
    from datetime import date
    from uuid import UUID
    conventions=set()
    for fact in projection.facts:
        booking=fact.booking
        if not booking or booking.subject_id!=subject:continue
        proof=booking.product_evidence or {}
        try:
            if booking.product_basis!='OPTION' or booking.quantity_unit!='CONTRACTS' or proof['optionPriceBasis']!='PREMIUM_POINTS':
                raise ValueError('Frozen option contract-premium quotation required')
            expiry=date.fromisoformat(proof['expiryDate'])
            if cutoff.date()>expiry:raise ValueError('Unclosed option exposure after expiry requires Ops lifecycle handling')
            def text(value):
                result=format(value,'f')
                return result.rstrip('0').rstrip('.') if '.' in result else result
            conventions.add((UUID(proof['instrumentId']),text(booking.unit_multiplier),text(booking.quote_factor),expiry))
        except (KeyError,TypeError) as exc:raise ValueError('Frozen option contract-premium quotation required') from exc
    if len(conventions)!=1:raise ValueError('Unique compatible frozen option premium quotation required')
    canonical,multiplier,factor,_=next(iter(conventions))
    return canonical,(('OPTION_PRICE_BASIS','PREMIUM_POINTS'),('PREMIUM_MULTIPLIER',multiplier),('QUOTE_FACTOR',factor),('QUANTITY_UNIT','CONTRACTS'))


def swap_mark_dimensions(projection,subject,cutoff):
    """Bind a supplied whole-swap mark to its booked units, never its underlying."""
    from datetime import date
    conventions=set()
    for fact in projection.facts:
        booking=fact.booking
        if not booking or booking.subject_id!=subject:continue
        proof=booking.product_evidence or {}
        try:
            basis='WHOLE_SWAP_MTM_PER_'+('UNIT' if booking.quantity_unit=='UNITS' else 'NOTIONAL')
            if (booking.product_basis!='SWAP' or proof['swapPriceBasis']!=basis
                or booking.unit_multiplier!=1 or Decimal(proof['quoteFactor'])!=booking.quote_factor):
                raise ValueError('Frozen compatible whole-swap quotation required')
            maturity=date.fromisoformat(proof['maturityDate'])
            if cutoff.date()>maturity:raise ValueError('Unclosed swap exposure after maturity requires Ops closure')
            factor=format(booking.quote_factor,'f')
            if '.' in factor:factor=factor.rstrip('0').rstrip('.')
            conventions.add((basis,booking.quantity_unit,factor,maturity))
        except (KeyError,TypeError) as exc:raise ValueError('Frozen compatible whole-swap quotation required') from exc
    if len(conventions)!=1:raise ValueError('Frozen unique whole-swap quotation required')
    basis,unit,factor,_=next(iter(conventions))
    return (('SWAP_PRICE_BASIS',basis),('QUANTITY_UNIT',unit),('QUOTE_FACTOR',factor))


def supported_product(product,unit):
    from positions.contracts import POSITION_UNITS
    expected={'EQUITY':'PRICE','ETF':'PRICE','FUND':'NAV','ACTIVELY_MANAGED_CERTIFICATE':'PRICE','BOND':'CLEAN_PLUS_ACCRUAL','CASH':'FX_ONLY','FX_FORWARD':'FORWARD_RATE_DIFFERENCE','SWAP':'WHOLE_SWAP_MARK','OPTION':'OPTION_PREMIUM'}
    if product not in expected or unit not in POSITION_UNITS.get(product,()):
        raise ValueError(f'{product}/{unit} is not valuation-ready: explicit unit economics and final marks required')
    return expected[product]


def clean_bond_price(price,quote_type,accrued_per_100=None):
    finite_decimal(price,'bond price',positive=True)
    if quote_type=='CLEAN': return price
    if quote_type!='DIRTY' or accrued_per_100 is None: raise ValueError('Dirty bond price requires assessed accrued interest per 100 nominal')
    finite_decimal(accrued_per_100,'accrued per 100')
    with localcontext() as ctx:
        ctx.prec=512
        clean=price-accrued_per_100
    return finite_decimal(clean,'clean bond price',positive=True)


@dataclass(frozen=True)
class ProductInputs:
    capability: str
    mark_basis: str
    requires_daily_accrual: bool


def prepare_product_inputs(c,request,position,selected_inputs):
    key=position.key;capability=supported_product(key.product_basis,key.quantity_unit)
    if key.product_basis=='FUND' and (key.unit_multiplier!=1 or key.quote_factor!=1):
        raise ValueError('Fund NAV valuation requires native per-unit quotations; explicit listing unit normalization is not enabled')
    if key.product_basis=='BOND':
        if key.unit_multiplier!=1 or key.quote_factor!=100: raise ValueError('Bond valuation requires nominal / 100 quotations')
        # A dirty mark requires its own per-nominal source evidence; the position's
        # accrued balance is not an interchangeable per-unit market quotation.
        if selected_inputs.get('bondPriceType')!='CLEAN':
            raise ValueError('Bond market mark needs explicit CLEAN quotation; DIRTY needs assessed per-nominal normalization evidence')
    return ProductInputs(capability,'CLEAN' if key.product_basis=='BOND' else 'NAV' if key.product_basis=='FUND' else 'AS_TRADED',key.product_basis=='BOND')
