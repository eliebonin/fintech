"""Exact monetary measures only: no prices selected here, no NAV, weights or P&L."""
from decimal import Decimal,localcontext,Inexact
from .economics import finite_decimal

ONE=Decimal(1)


def fx_forward_legs(base_amount,agreed_rate):
    """Signed undiscounted contractual amounts, not discounted risk or MTM."""
    finite_decimal(agreed_rate,'agreed forward rate',positive=True)
    return dict(baseAmount=finite_decimal(base_amount,'base amount'),
        quoteAmount=scaled(base_amount,agreed_rate,multiplier=ONE).copy_negate())


def scaled(quantity,price,multiplier=ONE,quote_factor=ONE):
    for value,name,positive in ((quantity,'quantity',False),(price,'price',False),
            (multiplier,'multiplier',True),(quote_factor,'quote factor',True)):
        finite_decimal(value,name,positive=positive)
    try:
        with localcontext() as ctx:
            ctx.prec=512;ctx.traps[Inexact]=True
            return finite_decimal(quantity*price*multiplier/quote_factor,'measure')
    except ArithmeticError as exc:raise ValueError('Measure cannot be represented exactly') from exc


def cash_security(quantity,price,multiplier=ONE,quote_factor=ONE):
    if price is not None:finite_decimal(price,'security price')
    if price is not None and price<0:raise ValueError('Security price cannot be negative')
    amount=None if price is None else scaled(quantity,price,multiplier,quote_factor)
    return dict(referenceNotional=amount,economicExposure=amount,marketValue=amount)


def bond(face,*,dirty=None,clean=None,accrued=None,quote_factor=Decimal(100)):
    finite_decimal(face,'outstanding face')
    finite_decimal(quote_factor,'quote factor',positive=True)
    clean_value=None if clean is None else scaled(face,clean,quote_factor=quote_factor)
    if dirty is not None:
        market=scaled(face,dirty,quote_factor=quote_factor);route='DIRTY_PRICE'
    elif clean_value is not None and accrued is not None:
        finite_decimal(accrued,'accrued balance')
        with localcontext() as ctx:
            ctx.prec=512;market=clean_value+accrued
        route='CLEAN_PLUS_ACCRUED_BALANCE'
    else:market=None;route='INCOMPLETE'
    if (dirty is not None and dirty<0) or (clean is not None and clean<0):raise ValueError('Bond price cannot be negative')
    return dict(referenceNotional=face,economicExposure=face,marketValue=market,
        cleanMarketValue=clean_value,accruedBalance=accrued,route=route)


def unit_swap(quantity,notional_per_unit,leverage,underlying_price,whole_swap_mark,quote_factor,
        *,orientation='RECEIVE',underlying_multiplier=ONE,underlying_quote_factor=ONE):
    finite_decimal(notional_per_unit,'reference notional per unit',positive=True)
    finite_decimal(leverage,'leverage',positive=True)
    if orientation not in ('RECEIVE','PAY'):raise ValueError('Explicit performance orientation required')
    reference=scaled(quantity,notional_per_unit)
    direction=ONE if orientation=='RECEIVE' else -ONE
    exposure=None
    if underlying_price is not None:
        finite_decimal(underlying_price,'underlying price')
        if underlying_price<0:raise ValueError('Underlying price cannot be negative')
        with localcontext() as ctx:
            ctx.prec=512
            exposure=scaled(quantity,underlying_price,underlying_multiplier,underlying_quote_factor)*leverage*direction
    # The whole-swap quote already contains financing, orientation and leverage.
    market=None if whole_swap_mark is None else scaled(quantity,whole_swap_mark,quote_factor=quote_factor)
    return dict(referenceNotional=reference,economicExposure=exposure,marketValue=market)


def nominal_swap(quantity,whole_swap_mark,quote_factor):
    finite_decimal(quantity,'outstanding nominal')
    return dict(referenceNotional=quantity,economicExposure=None,
        marketValue=None if whole_swap_mark is None else scaled(quantity,whole_swap_mark,quote_factor=quote_factor))


def linear_future(contracts,price,monetary_multiplier,quote_factor,*,allow_negative=False):
    """Current signed market notional; clearing MTM cannot be inferred from it."""
    finite_decimal(contracts,'contracts')
    if contracts!=contracts.to_integral_value():raise ValueError('Whole canonical futures contracts required')
    finite_decimal(monetary_multiplier,'monetary multiplier',positive=True)
    finite_decimal(quote_factor,'quote factor',positive=True)
    if price is not None:
        finite_decimal(price,'futures price')
        if price<0 and not allow_negative:raise ValueError('Negative futures prices are not approved for this contract')
    amount=None if price is None else scaled(contracts,price,monetary_multiplier,quote_factor)
    # No cleared settlement boundary / outstanding variation-margin evidence.
    # Neither the full notional nor an assumed zero is a contract market value.
    return dict(referenceNotional=amount,economicExposure=amount,marketValue=None)


def vanilla_option(contracts,premium,multiplier,quote_factor,strike,deliverable_units):
    """Premium value and labelled strike notional; never infer delta exposure."""
    finite_decimal(contracts,'contracts')
    if contracts!=contracts.to_integral_value():raise ValueError('Whole canonical option contracts required')
    finite_decimal(strike,'strike',positive=True)
    finite_decimal(deliverable_units,'deliverable units',positive=True)
    market=cash_security(contracts,premium,multiplier,quote_factor)['marketValue']
    return dict(referenceNotional=scaled(contracts,strike,deliverable_units),economicExposure=None,marketValue=market)
