"""Point-in-time rules for market-data source vintages.

The current value a vendor displays and the value that was knowable at a
historic information cut are different questions.  A vintage records the
source publication and Fortem receipt facts needed to answer the latter.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID


class VintageEligibilityError(ValueError):
    """Raised when a vintage query does not have a timezone-aware cutoff."""


@dataclass(frozen=True)
class MarketDataVintage:
    vintage_id: UUID
    source_published_at_utc: datetime | None
    received_at_utc: datetime
    value_basis: str
    vintage_status: str


def is_vintage_eligible(vintage: MarketDataVintage, information_cutoff_utc: datetime) -> bool:
    """Return whether this source version was knowable by an information cut.

    Receipt is always required to precede the cut.  When a provider publication
    timestamp is available it must also precede the cut; this prevents a late
    vendor correction or restated history from silently entering a historic
    valuation replay.  Equality at the cutoff is allowed.
    """

    if (
        information_cutoff_utc.tzinfo is None
        or information_cutoff_utc.utcoffset() is None
        or information_cutoff_utc.utcoffset() != timedelta(0)
    ):
        raise VintageEligibilityError("Information cutoff must be timezone-aware UTC")
    if (
        vintage.received_at_utc.tzinfo is None
        or vintage.received_at_utc.utcoffset() is None
        or vintage.received_at_utc.utcoffset() != timedelta(0)
    ):
        raise VintageEligibilityError("Vintage receipt timestamp must be timezone-aware")
    if vintage.source_published_at_utc is not None and (
        vintage.source_published_at_utc.tzinfo is None
        or vintage.source_published_at_utc.utcoffset() is None
        or vintage.source_published_at_utc.utcoffset() != timedelta(0)
    ):
        raise VintageEligibilityError("Source publication timestamp must be timezone-aware")
    return vintage.received_at_utc <= information_cutoff_utc and (
        vintage.source_published_at_utc is None
        or vintage.source_published_at_utc <= information_cutoff_utc
    )
