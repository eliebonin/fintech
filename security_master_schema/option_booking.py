"""Exact premium and execution rules for the bounded listed-option slice."""
from datetime import datetime
from decimal import Decimal, localcontext


class OptionBookingError(ValueError):
    def __init__(self, code, field, message):
        self.code, self.field = code, field
        super().__init__(message)


def gross_option_premium(quantity, premium: Decimal, multiplier: Decimal, quote_factor: Decimal) -> Decimal:
    quantity = Decimal(quantity)
    if not all(value.is_finite() for value in (quantity,premium,multiplier,quote_factor)):
        raise OptionBookingError('option.invalid_economics','executionPrice','Option economics must be finite.')
    if quantity <= 0 or quantity != quantity.to_integral_value():
        raise OptionBookingError('option.invalid_quantity','quantity','Enter a positive integer number of contracts.')
    if premium < 0 or multiplier <= 0 or quote_factor <= 0:
        raise OptionBookingError('option.invalid_economics','executionPrice','Premium must be non-negative and quote conversion factors positive.')
    with localcontext() as ctx:
        ctx.prec=80
        result=quantity*premium*multiplier/quote_factor
        if result >= Decimal('1e18') or result != result.quantize(Decimal('1e-12')):
            raise OptionBookingError('option.unrepresentable_premium','executionPrice','Gross premium exceeds supported exact precision; no silent rounding is applied.')
        return result


def validate_option_execution(execution: datetime, cutoff: datetime, position_effect: str):
    if execution.tzinfo is None or execution.utcoffset() is None or cutoff.tzinfo is None or cutoff.utcoffset() is None:
        raise OptionBookingError('option.invalid_time','tradeDatetime','Execution and trading cutoff must include timezone offsets.')
    if execution > cutoff:
        raise OptionBookingError('option.execution_after_cutoff','tradeDatetime','Execution cannot be after the approved trading cutoff.')
    if position_effect not in {'OPEN','CLOSE'}:
        raise OptionBookingError('option.invalid_position_effect','positionEffect','Choose OPEN or CLOSE; split mixed executions explicitly.')
