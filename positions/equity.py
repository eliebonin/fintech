"""Frozen equity-like units; no live security-master or price dependencies."""
from decimal import Decimal
from .contracts import Booking, PositionError, PositionKey,POSITION_UNITS

def finite(value, name, *, positive=False):
    if not isinstance(value, Decimal) or not value.is_finite():
        raise PositionError(f'{name} must be a finite Decimal')
    if len(value.as_tuple().digits)>60 or abs(value.as_tuple().exponent)>60 or abs(value.adjusted())>60:
        raise PositionError(f'{name} exceeds supported precision')
    if positive and value<=0: raise PositionError(f'{name} must be positive')
    return value

def booking_key(booking: Booking, tenant_id, strategy_id) -> PositionKey:
    if booking.quantity_unit not in POSITION_UNITS.get(booking.product_basis,()):
        raise PositionError('Unsupported booking economics; frozen compatible product units required')
    if finite(booking.quantity,'quantity') == 0: raise PositionError('Booked quantity must be nonzero')
    for field in ('price','unit_multiplier','quote_factor'):
        finite(getattr(booking,field),field,positive=True)
    return PositionKey(tenant_id,strategy_id,booking.subject_id,booking.currency_id,
        booking.quantity_unit,booking.product_basis,booking.unit_multiplier,booking.quote_factor)
