"""Principal-only closing economics; no arbitrary redemption-price defaults."""
from decimal import localcontext
from valuation.economics import finite_decimal


def closing_movements(buckets,price):
    finite_decimal(price,'contractual redemption price',positive=True)
    result=[]
    with localcontext() as ctx:
        ctx.prec=512
        for bucket in buckets:
            if bucket.key.quantity_unit!='NOMINAL' or bucket.key.unit_multiplier!=1 or bucket.key.quote_factor!=100:
                raise ValueError('Plain maturity requires native unadjusted nominal / 100 conventions')
            q=bucket.closing_quantity
            if not q: continue
            finite_decimal(q,'remaining nominal')
            result.append(dict(quantity=format(-q,'f'),price=format(price,'f'),cleanAmount=format(abs(q)*price/100,'f')))
    return result
