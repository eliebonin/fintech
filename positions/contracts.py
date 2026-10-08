"""Immutable contracts shared by ledger adapters and economic consumers."""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

class PositionError(ValueError):
    """Position evidence cannot safely represent the requested economic state."""

@dataclass(frozen=True)
class ProjectionRequest:
    tenant_id: UUID
    strategy_id: UUID
    closing_cutoff: datetime
    information_cutoff: datetime
    opening_cutoff: datetime | None = None
    mode: str = 'AS_OF'

@dataclass(frozen=True)
class PositionKey:
    tenant_id: UUID
    strategy_id: UUID
    subject_id: UUID
    currency_id: UUID
    quantity_unit: str
    product_basis: str
    unit_multiplier: Decimal
    quote_factor: Decimal

@dataclass(frozen=True)
class Booking:
    trade_id: UUID
    subject_id: UUID
    currency_id: UUID
    quantity_unit: str
    quantity: Decimal
    price: Decimal
    unit_multiplier: Decimal
    quote_factor: Decimal
    definition_id: UUID
    product_basis: str

@dataclass(frozen=True)
class LedgerFact:
    event_id: UUID
    trade_id: UUID
    tenant_id: UUID
    strategy_id: UUID
    sequence: int
    kind: str
    effective_at: datetime
    recorded_at: datetime
    booking: Booking | None = None

@dataclass(frozen=True)
class ExecutionEffect:
    key: PositionKey
    booking: Booking
    event_id: UUID
    effective_at: datetime
    recorded_at: datetime

@dataclass(frozen=True)
class PositionBucket:
    key: PositionKey
    opening_quantity: Decimal
    closing_quantity: Decimal
    trade_ids: tuple[UUID, ...]
    definition_ids: tuple[UUID, ...]

@dataclass(frozen=True)
class ExposureInterval:
    key: PositionKey
    started_at: datetime
    ended_at: datetime
    trade_ids: tuple[UUID, ...]

@dataclass(frozen=True)
class PositionProjection:
    request: ProjectionRequest
    buckets: tuple[PositionBucket, ...]
    executions: tuple[ExecutionEffect, ...]
    exposures: tuple[ExposureInterval, ...]  # All history for unit/identity safety, not mark requests.
    facts: tuple[LedgerFact, ...]
    facts_scanned: int
    complete_knowledge: bool
    input_hash: str
    engine_version: str = 'position-reconstruction-v1'
