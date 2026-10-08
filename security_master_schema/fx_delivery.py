"""Current recorded delivery evidence; not positions, cash postings or as-of accounting."""
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, localcontext


class DeliveryError(ValueError):
    pass


@dataclass(frozen=True)
class DeliveryRecord:
    sequence: int
    action: str
    effective_at: datetime
    evidence: str
    leg: str | None = None
    amount: Decimal | None = None
    target_sequence: int | None = None


@dataclass(frozen=True)
class DeliveryProgress:
    status: str
    receive_confirmed: Decimal
    pay_confirmed: Decimal
    receive_outstanding: Decimal
    pay_outstanding: Decimal
    reversible_sequences: tuple[int, ...]


def _amount(value: Decimal):
    if not isinstance(value, Decimal) or not value.is_finite() or value <= 0 or value >= Decimal('1e40') or value.as_tuple().exponent < -24:
        raise DeliveryError('Amount must be positive, finite and within 40 integer / 24 decimal digits.')


def replay_delivery(receive: Decimal, pay: Decimal, due: date, records: list[DeliveryRecord], *, now: datetime) -> DeliveryProgress:
    _amount(receive)
    _amount(pay)
    totals = {'RECEIVE': receive, 'PAY': pay}
    confirmed = {'RECEIVE': Decimal(0), 'PAY': Decimal(0)}
    active: dict[int, DeliveryRecord] = {}
    previous = 1
    # Explicit precision prevents ordinary decimal context rounding large amounts.
    with localcontext() as context:
        context.prec = 80
        for record in records:
            if record.sequence <= previous:
                raise DeliveryError('Delivery evidence must have unique increasing sequences.')
            previous = record.sequence
            if not record.evidence.strip():
                raise DeliveryError('A source evidence reference or reversal reason is required.')
            at = record.effective_at
            if at.tzinfo is None or at.utcoffset() is None:
                raise DeliveryError('Effective time must include a timezone offset.')
            at = at.astimezone(timezone.utc)
            if at > now or at.date() < due:
                raise DeliveryError('Actual delivery evidence cannot be future-dated or precede contractual settlement.')
            if record.action == 'CONFIRM':
                if record.leg not in totals or record.target_sequence is not None:
                    raise DeliveryError('Select one inherited currency leg.')
                _amount(record.amount)
                confirmed[record.leg] += record.amount
                if confirmed[record.leg] > totals[record.leg]:
                    raise DeliveryError('Confirmation exceeds the outstanding booked currency obligation.')
                active[record.sequence] = record
            elif record.action == 'REVERSE':
                target = active.get(record.target_sequence)
                if target is None or record.leg is not None or record.amount is not None:
                    raise DeliveryError('Reversal must reference one unreversed delivery confirmation.')
                if at < target.effective_at:
                    raise DeliveryError('Reversal effective time cannot precede the original confirmation.')
                confirmed[target.leg] -= target.amount
                del active[record.target_sequence]
            else:
                raise DeliveryError('Unsupported delivery action.')
        remaining = {leg: totals[leg] - confirmed[leg] for leg in totals}
        status = 'DELIVERED' if all(value == 0 for value in remaining.values()) else 'PARTIAL' if any(confirmed.values()) else 'DUE' if now.date() >= due else 'PENDING'
        return DeliveryProgress(status, confirmed['RECEIVE'], confirmed['PAY'], remaining['RECEIVE'], remaining['PAY'], tuple(active))
