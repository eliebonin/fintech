"""Small provider-neutral contracts for the existing daily PRICE-series flow."""
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True)
class ListingContext:
    currency: str
    mic: str
    timezone_name: str


@dataclass(frozen=True)
class ProviderSpec:
    source_system_id: str
    series_types: tuple[str, ...]
    max_payload_bytes: int
    max_window_days: int


@dataclass(frozen=True)
class DailyPoint:
    field: str
    market_date: date
    observed_at: datetime
    value: Decimal
    value_basis: str
    series_type: str


@dataclass(frozen=True)
class ParsedDelivery:
    points: tuple[DailyPoint, ...]
    rejections: tuple[dict, ...]
    vintage_value_basis: str
    timestamp_semantics: str


class DeliveryParser(Protocol):
    def __call__(self, payload: dict, *, symbol: str, listing: ListingContext,
                 start: date, end: date, received_at: datetime) -> ParsedDelivery: ...
