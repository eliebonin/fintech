"""Pure derivation rules for append-only trade lifecycle events."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


class TradeLifecycleError(ValueError):
    """Raised when an event chain is invalid or cannot derive current state."""


SUPPORTED_EVENT_TYPES = {"BOOKED", "AMENDED", "CANCELLED", "SUPERSEDED", "NOVATED", "CORRECTED"}


@dataclass(frozen=True)
class TradeLifecycleEvent:
    sequence_no: int
    event_type: str
    event_datetime_utc: datetime
    supersedes_sequence_no: int | None
    trade_id: UUID | None = None


def derive_trade_state(trade_id: UUID, events: tuple[TradeLifecycleEvent, ...]) -> str:
    """Return the latest effective lifecycle state without mutating the trade row."""

    if not events:
        raise TradeLifecycleError("A trade must have at least one lifecycle event")
    if any(event.trade_id not in (None, trade_id) for event in events):
        raise TradeLifecycleError("Lifecycle event belongs to another trade")
    if any(event.event_type not in SUPPORTED_EVENT_TYPES for event in events):
        raise TradeLifecycleError("Unsupported trade lifecycle event type")
    sequences = [event.sequence_no for event in events]
    if len(sequences) != len(set(sequences)):
        raise TradeLifecycleError("Lifecycle sequence numbers must be unique")
    superseded = {event.supersedes_sequence_no for event in events if event.supersedes_sequence_no is not None}
    effective = [event for event in events if event.sequence_no not in superseded]
    if not effective:
        raise TradeLifecycleError("Lifecycle chain has no effective event")
    selected = max(effective, key=lambda event: (event.sequence_no, event.event_datetime_utc))
    return selected.event_type
