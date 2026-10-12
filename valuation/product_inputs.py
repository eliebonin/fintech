"""Explicit product capabilities. Booking support is not valuation readiness."""
from dataclasses import dataclass
from decimal import Decimal,localcontext
from .economics import finite_decimal


def supported_product(product,unit):
    from positions.contracts import POSITION_UNITS
    expected={'EQUITY':'PRICE','ETF':'PRICE','FUND':'NAV','BOND':'CLEAN_PLUS_ACCRUAL','CASH':'FX_ONLY'}
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
