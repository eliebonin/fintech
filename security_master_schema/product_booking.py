"""Exact execution economics for bounded structured securities, futures and bonds."""
from decimal import Decimal, localcontext


def exact_amount(value: Decimal) -> Decimal:
    if not value.is_finite() or abs(value) >= Decimal('1e18'):
        raise ValueError('Amount exceeds supported precision.')
    with localcontext() as context:
        context.prec = 100
        if value != value.quantize(Decimal('1e-12')):
            raise ValueError('Amount cannot be represented exactly with 12 decimals.')
    return value


def execution_amount(quantity, price, *, quantity_unit, price_basis, quote_factor,
                     denomination=None, multiplier=None):
    with localcontext() as context:
        context.prec = 100
        quantity, price, quote_factor = map(Decimal, (quantity, price, quote_factor))
        if quantity <= 0 or quote_factor <= 0:
            raise ValueError('Quantity and quotation divisor must be positive.')
        if price_basis == 'INDEX_POINTS':
            if quantity_unit != 'CONTRACTS' or multiplier is None or Decimal(multiplier) <= 0:
                raise ValueError('Explicit futures multiplier and contracts are required.')
            amount = quantity * price * Decimal(multiplier) / quote_factor
        elif price_basis == 'PCT_OF_PAR':
            nominal = quantity
            if quantity_unit == 'UNITS':
                if denomination is None or Decimal(denomination) <= 0:
                    raise ValueError('Unit percentage quotes require denomination.')
                nominal *= Decimal(denomination)
            elif quantity_unit != 'NOMINAL':
                raise ValueError('Percentage quotes require nominal or units.')
            amount = nominal * price / quote_factor
        elif price_basis == 'UNIT_PRICE' and quantity_unit == 'UNITS':
            amount = quantity * price / quote_factor
        else:
            raise ValueError('Unsupported quantity/price convention.')
        return exact_amount(amount)


def validate_increment(value, increment, *, minimum=None):
    value, increment = Decimal(value), Decimal(increment)
    with localcontext() as context:
        context.prec = 100
        if increment <= 0 or not value.is_finite():
            raise ValueError('Invalid increment or value.')
        anchor = Decimal(minimum) if minimum is not None else Decimal(0)
        if minimum is not None and value < anchor:
            raise ValueError('Quantity is below the approved minimum.')
        if (value - anchor) % increment:
            raise ValueError('Value does not match the approved increment.')


def bond_amounts(quantity, price, price_type, accrued_interest):
    """Total signed accrual, not a per-unit quote; never add it to dirty twice."""
    quoted = execution_amount(quantity, price, quantity_unit='NOMINAL', price_basis='PCT_OF_PAR', quote_factor=100)
    accrued = exact_amount(Decimal(accrued_interest))
    with localcontext() as context:
        context.prec = 100
        if price_type == 'CLEAN':
            clean, dirty = quoted, exact_amount(quoted + accrued)
        elif price_type == 'DIRTY':
            clean, dirty = exact_amount(quoted - accrued), quoted
        else:
            raise ValueError('Confirm CLEAN or DIRTY quotation.')
    if clean < 0 or dirty < 0:
        raise ValueError('Clean and dirty consideration must be non-negative.')
    return clean, dirty
