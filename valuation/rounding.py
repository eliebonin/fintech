"""Explicit financial storage precision; calculation evidence remains exact."""
from decimal import Decimal, ROUND_HALF_EVEN, localcontext
from .economics import MARKET, CASH, INCOME, COSTS, validate_totals

POLICY = {'version': 1, 'scale': 12, 'mode': 'ROUND_HALF_EVEN',
          'totals': 'SUM_ROUNDED_COMPONENTS'}
QUANTUM = Decimal('0.000000000001')


class StorageAmountError(ValueError):
    """Safe operational explanation, without provider or database payloads."""


def storage_amount(value):
    if not isinstance(value, Decimal) or not value.is_finite():
        raise StorageAmountError('Valuation storage amount must be finite.')
    if value.copy_abs() >= Decimal('1e18'):
        raise StorageAmountError('Valuation storage overflow: amount exceeds NUMERIC(30,12).')
    with localcontext() as ctx:
        ctx.prec = 512
        rounded = value.quantize(QUANTUM, rounding=ROUND_HALF_EVEN)
    if rounded.copy_abs() >= Decimal('1e18'):
        raise StorageAmountError('Valuation storage overflow after rounding to 12 decimal places.')
    return rounded


def rounded_result(components, *, market, gross, net):
    """Round components once; derive totals, recording every resulting delta."""
    for value in (*components.values(), market, gross, net):
        storage_amount(value)  # Reject nonfinite/overflow before reconciliation.
    validate_totals(components, market=market, gross=gross, net=net)
    with localcontext() as ctx:
        ctx.prec = 512
        stored = {k: storage_amount(v) for k, v in components.items()}
        rounded_market = sum((v for k, v in stored.items() if k in MARKET), Decimal(0))
        rounded_gross = rounded_market + sum((v for k, v in stored.items() if k in INCOME | CASH), Decimal(0))
        rounded_net = rounded_gross + sum((v for k, v in stored.items() if k in COSTS), Decimal(0))
        for value in (rounded_market, rounded_gross, rounded_net):
            storage_amount(value)
        exact = dict(components=dict(components), market=market, gross=gross, net=net)
        result = dict(components=stored, market=rounded_market, gross=rounded_gross, net=rounded_net)
        adjustments = {k: result[k] - exact[k] for k in ('market', 'gross', 'net')}
        adjustments['components'] = {k: stored[k] - v for k, v in components.items()}
    return result | {'evidence': dict(policy=POLICY, exact=exact, adjustments=adjustments)}
