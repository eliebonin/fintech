"""Quantity-only consumer of the shared ledger/lifecycle/share-ratio engine.

No prices or financial values are manufactured: execution price can be absent,
zero or negative, and product pricing support does not govern holdings support.
"""
from dataclasses import replace
from datetime import datetime, timezone
from .contracts import PositionError, PositionKey
from .equity import finite
from .reconstruction import reconstruct


def holdings_key(booking,tenant,strategy):
    if booking.quantity_unit not in {'SHARES','UNITS','NOMINAL','CONTRACTS','CURRENCY_AMOUNT'}:
        raise PositionError('Unsupported holdings quantity unit')
    if finite(booking.quantity,'quantity')==0:
        raise PositionError('Booked quantity must be nonzero')
    finite(booking.unit_multiplier,'unit multiplier',positive=True)
    finite(booking.quote_factor,'quote factor',positive=True)
    return PositionKey(tenant,strategy,booking.subject_id,booking.currency_id,
        booking.quantity_unit,booking.product_basis,booking.unit_multiplier,booking.quote_factor)


def project_holdings(facts,request,*,basis='EXECUTED',splits=()):
    if basis not in {'EXECUTED','VALUATION_RECOGNISED'}:
        raise ValueError('Unsupported holdings date basis')
    if basis=='EXECUTED':
        facts=[replace(f,booking=replace(f.booking,valuation_effective_date=None)) if f.booking else f for f in facts]
    # An all-history period preserves flat episodes and every contributing
    # execution for drill-down. It is not a period P&L or a remaining-lot report.
    period=replace(request,mode='PERIOD',opening_cutoff=datetime.min.replace(tzinfo=timezone.utc),daily=False)
    return reconstruct(facts,period,splits=splits,key_builder=holdings_key)
