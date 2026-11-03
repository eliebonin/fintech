"""Exact market attribution for compatible equity-like normalized values.

This is not a universal derivative pricer: product basis and units must already
be known, and futures exposure or a forward rate is not an equity asset value.
"""
from dataclasses import dataclass
from decimal import Decimal, Inexact, localcontext
# Existing public imports remain identical objects; new shared consumers use the owner.
from security_master_schema.evidence import finite_decimal, canonical_payload, evidence_hash

MARKET = frozenset({'PRICE', 'FX', 'PRICE_FX_CROSS', 'MODEL_MARK_CHANGE'})
CASH = frozenset({'CASH_FX'})
INCOME = frozenset({'ACCRUAL', 'CARRY', 'COUPON', 'DIVIDEND', 'RESET', 'CASHFLOW'})
COSTS = frozenset({'BROKER_FEE', 'CUSTODY_FEE', 'MANAGEMENT_FEE', 'PERFORMANCE_FEE', 'TAX', 'OTHER_COST', 'ADJUSTMENT'})


@dataclass(frozen=True)
class MarketInputs:
    quantity: Decimal
    opening_price: Decimal
    closing_price: Decimal
    opening_fx: Decimal
    closing_fx: Decimal
    unit_multiplier: Decimal = Decimal('1')
    quote_factor: Decimal = Decimal('1')


@dataclass(frozen=True)
class MarketAttribution:
    price: Decimal
    fx: Decimal
    cross: Decimal
    market_pnl: Decimal
    opening_value: Decimal
    closing_value: Decimal

    def components(self) -> dict[str, Decimal]:
        return {'PRICE': self.price, 'FX': self.fx, 'PRICE_FX_CROSS': self.cross}


def attribute_market(inputs: MarketInputs) -> MarketAttribution:
    """Decompose opening-holding or execution-to-close P&L without float loss."""
    for name, value in vars(inputs).items():
        finite_decimal(value, name, positive=name != 'quantity')
    with localcontext() as context:
        context.prec = 512
        context.traps[Inexact] = True
        try:
            units = inputs.quantity * inputs.unit_multiplier / inputs.quote_factor
            price = units * (inputs.closing_price - inputs.opening_price) * inputs.opening_fx
            fx = units * inputs.opening_price * (inputs.closing_fx - inputs.opening_fx)
            cross = units * (inputs.closing_price - inputs.opening_price) * (inputs.closing_fx - inputs.opening_fx)
            opening = units * inputs.opening_price * inputs.opening_fx
            closing = units * inputs.closing_price * inputs.closing_fx
            total = price + fx + cross
            if total != closing - opening:
                raise ValueError('Market components do not reconcile')
            return MarketAttribution(price, fx, cross, total, opening, closing)
        except Inexact as error:
            raise ValueError('Normalization requires an explicit rounding policy') from error


def validate_totals(components: dict[str, Decimal], *, market: Decimal, gross: Decimal, net: Decimal) -> None:
    """Income and controlled adjustments do not change clean market movement."""
    if set(components) - MARKET - CASH - INCOME - COSTS:
        raise ValueError('Unsupported P&L component')
    for name, amount in list(components.items()) + [('market', market), ('gross', gross), ('net', net)]:
        finite_decimal(amount, name)
    with localcontext() as context:
        context.prec = 512
        calculated_market = sum((v for k, v in components.items() if k in MARKET), Decimal('0'))
        calculated_gross = calculated_market + sum((v for k, v in components.items() if k in INCOME | CASH), Decimal('0'))
        calculated_net = calculated_gross + sum((v for k, v in components.items() if k in COSTS), Decimal('0'))
        if (market, gross, net) != (calculated_market, calculated_gross, calculated_net):
            raise ValueError('P&L components do not reconcile to stored totals')
