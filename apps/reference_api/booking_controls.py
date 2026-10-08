"""Shared booking safeguards, independent of product economics and HTTP routes."""
from datetime import date, datetime, timezone
from .resource_limits import governance_date
from hashlib import sha256
from uuid import UUID

from sqlalchemy import Connection, select, func

from security_master_schema import models as m
from security_master_schema.tenant_workspace import (
    TenantActionForbidden, require_tenant_action, resolve_tenant_workspace,
)
from .booking_errors import RepositoryNotFound, IdempotencyKeyConflict


def validate_execution_date(execution: datetime, *, today: date | None = None) -> date:
    """New recordings use UTC economic dates; authorized replay bypasses this rule."""
    from .trade_properties import TradeFieldError
    if execution.tzinfo is None or execution.utcoffset() is None:
        raise TradeFieldError('tradeDatetime', 'Execution must include a timezone offset.')
    execution_date = execution.astimezone(timezone.utc).date()
    if execution_date > (today or datetime.now(timezone.utc).date()):
        raise TradeFieldError('tradeDatetime', 'Future UTC execution dates cannot be recorded as executed trades.')
    return execution_date


def authorize_booking(connection: Connection, tenant_id: UUID, actor_id: UUID) -> None:
    active = connection.scalar(select(m.user_account.c.user_account_id).where(
        m.user_account.c.user_account_id == actor_id, m.user_account.c.status == 'ACTIVE'))
    if active is None:
        raise TenantActionForbidden('User account is not active')
    require_tenant_action(resolve_tenant_workspace(connection, tenant_id, actor_id, governance_date()), 'TRADE_WRITE')


def lock_booking_strategy(connection: Connection, tenant_id: UUID, strategy_id: UUID) -> UUID:
    strategy = connection.scalar(select(m.strategy.c.strategy_id).where(
        m.strategy.c.strategy_id == strategy_id, m.strategy.c.tenant_id == tenant_id,
        m.strategy.c.status == 'ACTIVE').with_for_update())
    if strategy is None:
        raise RepositoryNotFound('Active strategy does not exist')
    return strategy


def booking_lock_key(tenant_id: UUID, endpoint: str, key: str) -> int:
    scope = f'{tenant_id}\x1f{endpoint}\x1f{key}'
    return int.from_bytes(sha256(scope.encode()).digest()[:8], 'big', signed=True)


def find_booking_replay(connection: Connection, tenant_id: UUID, endpoint: str, key: str, fingerprint: str) -> UUID | None:
    connection.execute(select(func.pg_advisory_xact_lock(booking_lock_key(tenant_id, endpoint, key))))
    row = connection.execute(select(m.trade_booking_idempotency).where(
        m.trade_booking_idempotency.c.tenant_id == tenant_id,
        m.trade_booking_idempotency.c.endpoint == endpoint,
        m.trade_booking_idempotency.c.idempotency_key == key).with_for_update()).mappings().first()
    if row is None:
        return None
    if row['request_fingerprint'] != fingerprint:
        raise IdempotencyKeyConflict('Idempotency key was already used with a different request')
    return row['trade_id']


def record_booking_replay(connection: Connection, tenant_id: UUID, endpoint: str, key: str, fingerprint: str, trade_id: UUID) -> None:
    connection.execute(m.trade_booking_idempotency.insert().values(tenant_id=tenant_id, endpoint=endpoint,
        idempotency_key=key, request_fingerprint=fingerprint, trade_id=trade_id))
