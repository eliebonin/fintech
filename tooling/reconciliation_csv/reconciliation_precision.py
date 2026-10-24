"""Reconciliation-only precision policy, explicitly authorized by the owner.

Never rely on PostgreSQL's implicit rounding. Source receipts are immutable;
the caller must retain this complete transformation beside the booked identity.
"""
from decimal import Decimal, InvalidOperation, ROUND_DOWN, localcontext


def native_decimal(source, *, scale='1', decimal_places=12):
    if type(decimal_places) is not int or not 0<=decimal_places<=12:
        raise ValueError('Native decimal places must be between zero and twelve')
    if not isinstance(source,str) or len(source)>200:
        raise ValueError('Bounded exact source decimal text required')
    try:
        with localcontext() as context:
            context.prec=250
            original=Decimal(source); multiplier=Decimal(scale)
            if not original.is_finite() or not multiplier.is_finite() or multiplier<=0:
                raise ValueError('Finite source and positive conversion required')
            if not -200<=original.as_tuple().exponent<=200 or not -200<=multiplier.as_tuple().exponent<=200:
                raise ValueError('Source decimal exponent exceeds bounded import precision')
            exact=original*multiplier
            if abs(exact)>=Decimal('1e18'):
                raise ValueError('Value exceeds native NUMERIC(30,12) range')
            stored=exact.quantize(Decimal(1).scaleb(-decimal_places),rounding=ROUND_DOWN)
            if stored==0:stored=abs(stored)
            return dict(sourceValue=source,scale=scale,exactConvertedValue=format(exact,'f'),
                value=format(stored,'f'),delta=format(stored-exact,'f'),
                precisionPolicy='TRUNCATE_TOWARD_ZERO',decimalPlaces=decimal_places,truncated=stored!=exact)
    except (InvalidOperation,OverflowError) as exc:
        raise ValueError('Invalid or out-of-range source decimal') from exc
