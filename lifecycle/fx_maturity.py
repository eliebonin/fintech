"""Rate-based FX exposure closure; never creates payment or cash holdings."""
from decimal import Decimal, localcontext
from valuation.economics import finite_decimal


def validated_override(value):
    if value is None:return None
    if not isinstance(value,dict) or set(value)!={'rate','sourceReference','reason'}:
        raise ValueError('Manual rate requires rate, source reference and reason')
    if not isinstance(value['rate'],str) or len(value['rate'])>64:raise ValueError('Manual rate must be a decimal string')
    try:rate=Decimal(value['rate'])
    except Exception as exc:raise ValueError('Invalid manual rate') from exc
    finite_decimal(rate,'manual closing rate',positive=True)
    with localcontext() as context:
        context.prec=80
        if rate>=Decimal('1e18') or rate!=rate.quantize(Decimal('1e-12')):raise ValueError('Manual rate requires at most 18 integer and 12 decimal digits')
    for field in ('sourceReference','reason'):
        if not isinstance(value[field],str) or not value[field].strip() or len(value[field])>2000:raise ValueError('Manual rate source and reason are required')
    return dict(rate=format(rate,'f'),sourceReference=value['sourceReference'].strip(),reason=value['reason'].strip())


def closing_economics(quantity: Decimal, rate: Decimal) -> dict:
    finite_decimal(quantity, 'remaining base amount')
    finite_decimal(rate, 'maturity FX rate', positive=True)
    if not quantity: raise ValueError('No remaining forward exposure')
    with localcontext() as context:
        context.prec=512
        return dict(quantity=format(-quantity,'f'),price=format(rate,'f'),
            quoteAmount=format(abs(quantity)*rate,'f'),paymentRecognised=False)
