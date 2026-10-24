"""Shared certificate quote dimensions; no HTTP, database or pricing dependencies."""
from decimal import Decimal,InvalidOperation

KIND='ACTIVELY_MANAGED_CERTIFICATE'


def _positive(value,label):
    if isinstance(value,(float,bool)) or value is None:raise ValueError(f'Explicit {label} required')
    try:result=Decimal(value)
    except (InvalidOperation,TypeError,ValueError):raise ValueError(f'Invalid {label}') from None
    if not result.is_finite() or result<=0:raise ValueError(f'Positive finite {label} required')
    return result


def quotation_factors(convention,quantity_unit):
    """Return multiplier/divisor, applying denomination only to certificate counts.

    A percentage quote 98 means 98%, not 0.98 currency per certificate. Nominal
    quantities already contain denomination; multiplying it again is incorrect.
    """
    if (convention.get('kind')!=KIND or convention.get('quantityUnit')!=quantity_unit
            or convention.get('funding')!='FULLY_FUNDED' or convention.get('accrual')!='NONE'):
        raise ValueError('Compatible fully funded AMC quotation required')
    factor=_positive(convention.get('quoteFactor'),'quote divisor')
    basis=convention.get('priceBasis')
    if basis=='UNIT_PRICE' and quantity_unit=='UNITS':return Decimal(1),factor
    if basis!='PCT_OF_PAR' or factor!=100:raise ValueError('Percentage AMC quotes require divisor 100; unit quotes require certificate units')
    if quantity_unit=='NOMINAL':return Decimal(1),factor
    if quantity_unit=='UNITS':return _positive(convention.get('denomination'),'nominal per certificate'),factor
    raise ValueError('Unsupported AMC quantity unit')


def matching_quotation(conventions,quantity_unit,multiplier,factor):
    """Validate every contributing trade; never infer a denomination from price."""
    if not conventions:raise ValueError('Frozen AMC quotation required')
    bases=set()
    for cv in conventions:
        if quotation_factors(cv,quantity_unit)!=(multiplier,factor):
            raise ValueError('AMC frozen factors disagree with approved booking dimensions')
        bases.add(cv['priceBasis'])
    if len(bases)!=1:raise ValueError('Incompatible AMC price quotation bases on the same position')
    return next(iter(bases))
