"""Exact market attribution for compatible equity-like normalized values.

This is not a universal derivative pricer: product basis and units must already
be known, and futures exposure or a forward rate is not an equity asset value.
"""
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, Inexact, localcontext
from hashlib import sha256
import json
from uuid import UUID

MARKET = frozenset({'PRICE', 'FX', 'PRICE_FX_CROSS', 'MODEL_MARK_CHANGE'})
INCOME = frozenset({'ACCRUAL', 'CARRY', 'COUPON', 'DIVIDEND', 'RESET', 'CASHFLOW'})
COSTS = frozenset({'BROKER_FEE', 'CUSTODY_FEE', 'MANAGEMENT_FEE', 'PERFORMANCE_FEE', 'TAX', 'OTHER_COST', 'ADJUSTMENT'})


def finite_decimal(value: Decimal, name: str, *, positive: bool = False) -> Decimal:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise ValueError(f'{name} must be a finite Decimal')
    if len(value.as_tuple().digits) > 60 or abs(value.as_tuple().exponent) > 60 or abs(value.adjusted()) > 60:
        raise ValueError(f'{name} exceeds supported precision')
    if positive and value <= 0:
        raise ValueError(f'{name} must be positive')
    return value


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
    if set(components) - MARKET - INCOME - COSTS:
        raise ValueError('Unsupported P&L component')
    for name, amount in list(components.items()) + [('market', market), ('gross', gross), ('net', net)]:
        finite_decimal(amount, name)
    with localcontext() as context:
        context.prec = 512
        calculated_market = sum((v for k, v in components.items() if k in MARKET), Decimal('0'))
        calculated_gross = calculated_market + sum((v for k, v in components.items() if k in INCOME), Decimal('0'))
        calculated_net = calculated_gross + sum((v for k, v in components.items() if k in COSTS), Decimal('0'))
        if (market, gross, net) != (calculated_market, calculated_gross, calculated_net):
            raise ValueError('P&L components do not reconcile to stored totals')


def canonical_payload(value):
    """Canonical evidence uses exact decimal strings, never binary floats."""
    if isinstance(value, Decimal):
        finite_decimal(value, 'evidence')
        if value == 0:
            return '0'
        rendered = format(value, 'f')
        return rendered.rstrip('0').rstrip('.') if '.' in rendered else rendered
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError('Evidence timestamps must be timezone aware')
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        if any(not isinstance(key, str) for key in value):
            raise ValueError('Evidence mapping keys must be strings')
        return {key: canonical_payload(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [canonical_payload(item) for item in value]
    if isinstance(value, float):
        raise ValueError('Binary floats are not financial evidence')
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise ValueError('Unsupported financial evidence value')


def evidence_hash(payload: dict) -> str:
    encoded = json.dumps(canonical_payload(payload), sort_keys=True, separators=(',', ':'), ensure_ascii=True)
    return sha256(encoded.encode('utf-8')).hexdigest()
