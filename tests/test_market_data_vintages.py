"""Point-in-time eligibility tests for market-data vintages."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest

from security_master_schema.market_data_vintages import (
    MarketDataVintage,
    VintageEligibilityError,
    is_vintage_eligible,
)


_CUT = datetime(2026, 8, 31, 18, 0, tzinfo=timezone.utc)


def test_vintage_is_eligible_only_when_published_and_received_by_information_cut() -> None:
    vintage = MarketDataVintage(
        vintage_id=UUID("00000000-0000-7000-8000-000000000051"),
        source_published_at_utc=datetime(2026, 8, 31, 17, 0, tzinfo=timezone.utc),
        received_at_utc=datetime(2026, 8, 31, 17, 30, tzinfo=timezone.utc),
        value_basis="RAW",
        vintage_status="CURRENT",
    )
    assert is_vintage_eligible(vintage, _CUT)


def test_late_receipt_or_late_publication_is_not_historically_knowable() -> None:
    late_receipt = MarketDataVintage(
        vintage_id=UUID("00000000-0000-7000-8000-000000000052"),
        source_published_at_utc=datetime(2026, 8, 31, 17, 0, tzinfo=timezone.utc),
        received_at_utc=datetime(2026, 8, 31, 19, 0, tzinfo=timezone.utc),
        value_basis="VENDOR_ADJUSTED",
        vintage_status="CORRECTED",
    )
    assert not is_vintage_eligible(late_receipt, _CUT)


def test_naive_cutoff_is_rejected() -> None:
    vintage = MarketDataVintage(
        vintage_id=UUID("00000000-0000-7000-8000-000000000053"),
        source_published_at_utc=None,
        received_at_utc=datetime(2026, 8, 31, 17, 30, tzinfo=timezone.utc),
        value_basis="RAW",
        vintage_status="CURRENT",
    )
    with pytest.raises(VintageEligibilityError):
        is_vintage_eligible(vintage, datetime(2026, 8, 31, 18, 0))


def test_non_utc_cutoff_is_rejected() -> None:
    vintage = MarketDataVintage(
        vintage_id=UUID("00000000-0000-7000-8000-000000000054"),
        source_published_at_utc=None,
        received_at_utc=datetime(2026, 8, 31, 17, 30, tzinfo=timezone.utc),
        value_basis="RAW",
        vintage_status="CURRENT",
    )
    with pytest.raises(VintageEligibilityError):
        is_vintage_eligible(
            vintage,
            datetime(2026, 8, 31, 19, 0, tzinfo=timezone(timedelta(hours=1))),
        )
