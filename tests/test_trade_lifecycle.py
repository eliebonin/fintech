"""Append-only trade lifecycle tests."""

from datetime import datetime, timezone
from uuid import UUID

import pytest

from security_master_schema.trade_lifecycle import (
    TradeLifecycleError,
    TradeLifecycleEvent,
    derive_trade_state,
)


TRADE_ID = UUID("00000000-0000-7000-8000-000000000401")


def test_trade_state_uses_latest_non_superseded_lifecycle_event() -> None:
    state = derive_trade_state(
        TRADE_ID,
        (
            TradeLifecycleEvent(1, "BOOKED", datetime(2026, 9, 1, 10, tzinfo=timezone.utc), None),
            TradeLifecycleEvent(2, "AMENDED", datetime(2026, 9, 1, 11, tzinfo=timezone.utc), None),
            TradeLifecycleEvent(3, "CANCELLED", datetime(2026, 9, 1, 12, tzinfo=timezone.utc), 2),
        ),
    )
    assert state == "CANCELLED"


def test_events_for_another_trade_or_unknown_event_are_rejected() -> None:
    with pytest.raises(TradeLifecycleError):
        derive_trade_state(
            TRADE_ID,
            (TradeLifecycleEvent(1, "AMENDED", datetime.now(timezone.utc), None, trade_id=UUID("00000000-0000-7000-8000-000000000402")),),
        )
