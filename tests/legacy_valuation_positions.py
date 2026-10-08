"""Recorded-time replay and an economic trading bridge, not a cash ledger."""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, localcontext
from uuid import UUID
from valuation.economics import MarketInputs, MarketAttribution, attribute_market, finite_decimal


def aware(value: datetime) -> None:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError('Cutoffs and event times must be timezone aware')


@dataclass(frozen=True)
class BookedLot:
    trade_id: UUID
    subject_id: UUID
    quantity: Decimal
    price: Decimal
    currency_id: UUID
    quantity_unit: str
    unit_multiplier: Decimal
    quote_factor: Decimal
    executed_at: datetime


@dataclass(frozen=True)
class BookingEvent:
    event_id: UUID
    trade_id: UUID
    sequence: int
    kind: str
    effective_at: datetime
    recorded_at: datetime
    lot: BookedLot | None = None


def replay_bookings(events: list[BookingEvent], economic_cutoff: datetime, information_cutoff: datetime) -> tuple[BookedLot, ...]:
    """Replay only evidence effective and known by the two independent cutoffs.

    Cancellation is a booking correction, not contractual cash settlement.
    Unimplemented lifecycle effects deliberately fail rather than disappear.
    """
    aware(economic_cutoff)
    aware(information_cutoff)
    grouped: dict[UUID, list[BookingEvent]] = {}
    for event in events:
        aware(event.effective_at)
        aware(event.recorded_at)
        if event.recorded_at <= information_cutoff and event.effective_at <= economic_cutoff:
            grouped.setdefault(event.trade_id, []).append(event)
    active = []
    for trade_id, chain in sorted(grouped.items(), key=lambda item: str(item[0])):
        chain = sorted(chain, key=lambda event: event.sequence)
        if [event.sequence for event in chain] != list(range(1, len(chain) + 1)):
            raise ValueError('Missing or duplicate lifecycle sequence evidence')
        if chain[0].kind != 'BOOKED' or chain[0].lot is None:
            raise ValueError('Missing original BOOKED economics')
        lot = chain[0].lot
        if lot.trade_id != trade_id or lot.executed_at != chain[0].effective_at:
            raise ValueError('BOOKED identity or execution time is inconsistent')
        aware(lot.executed_at)
        if lot.quantity_unit not in {'SHARES', 'UNITS'}:
            raise ValueError('Unsupported quantity unit for equity valuation')
        finite_decimal(lot.quantity, 'quantity')
        if lot.quantity == 0:
            raise ValueError('Booked quantity must be nonzero')
        for name in ('price', 'unit_multiplier', 'quote_factor'):
            finite_decimal(getattr(lot, name), name, positive=True)
        removed = False
        for event in chain[1:]:
            if event.kind in {'CANCELLED', 'SUPERSEDED'}:
                if removed:
                    raise ValueError('Booking already removed from the economic history')
                removed = True
            elif event.kind == 'CORRECTED':
                if removed:
                    raise ValueError('Correction lineage cannot resurrect a removed booking')
            else:
                raise ValueError(f'Unsupported lifecycle effect: {event.kind}')
        if not removed:
            active.append(lot)
    return tuple(active)


@dataclass(frozen=True)
class PeriodMarks:
    opening_price: Decimal | None
    closing_price: Decimal
    opening_fx: Decimal
    closing_fx: Decimal


@dataclass(frozen=True)
class PeriodLine:
    lot: BookedLot
    basis: str
    attribution: MarketAttribution


@dataclass(frozen=True)
class PeriodAttribution:
    lines: tuple[PeriodLine, ...]
    market_pnl: Decimal
    opening_value: Decimal
    closing_value: Decimal
    execution_value: Decimal


def attribute_period(events: list[BookingEvent], opening_cutoff: datetime, closing_cutoff: datetime,
                     information_cutoff: datetime, marks: dict[UUID, PeriodMarks], *,
                     execution_fx: dict[UUID, Decimal]) -> PeriodAttribution:
    """Opening lots plus signed executions reconcile the change in securities.

    Sale executions contribute even at a zero closing holding. Execution FX is
    explicit: it is never guessed from a closing spot rate.
    """
    aware(opening_cutoff)
    aware(closing_cutoff)
    if closing_cutoff <= opening_cutoff:
        raise ValueError('Closing cutoff must follow opening cutoff')
    opening = replay_bookings(events, opening_cutoff, information_cutoff)
    closing = replay_bookings(events, closing_cutoff, information_cutoff)
    opening_ids = {lot.trade_id for lot in opening}
    if opening_ids - {lot.trade_id for lot in closing}:
        raise ValueError('Unsupported in-period removal requires economic lifecycle treatment')
    lines = []
    with localcontext() as context:
        context.prec = 512
        starting = ending = executions = total = Decimal('0')
        for lot in closing:
            mark = marks.get(lot.subject_id)
            if mark is None:
                raise ValueError(f'Missing period mark for {lot.subject_id}')
            is_opening = lot.trade_id in opening_ids
            if is_opening and mark.opening_price is None:
                raise ValueError(f'Missing opening price for {lot.subject_id}')
            price0 = mark.opening_price if is_opening else lot.price
            if not is_opening and lot.trade_id not in execution_fx:
                raise ValueError(f'Missing execution FX for {lot.trade_id}')
            fx0 = mark.opening_fx if is_opening else execution_fx[lot.trade_id]
            attributed = attribute_market(MarketInputs(lot.quantity, price0, mark.closing_price, fx0,
                                                        mark.closing_fx, lot.unit_multiplier, lot.quote_factor))
            lines.append(PeriodLine(lot, 'OPENING_HOLDING' if is_opening else 'PERIOD_EXECUTION', attributed))
            total += attributed.market_pnl
            ending += attributed.closing_value
            if is_opening:
                starting += attributed.opening_value
            else:
                executions += attributed.opening_value
        if total != ending - starting - executions:
            raise ValueError('Opening/closing trading bridge does not reconcile')
    return PeriodAttribution(tuple(lines), total, starting, ending, executions)
