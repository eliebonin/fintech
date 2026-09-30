"""Add durable idempotency storage for listed-cash trade booking.

Revision ID: 20260930_49
Revises: 20260929_48
"""

import sqlalchemy as sa
from alembic import op


revision = "20260930_49"
down_revision = "20260929_48"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Record one immutable booked trade for each tenant-scoped retry key."""

    op.create_table(
        "trade_booking_idempotency",
        sa.Column("trade_booking_idempotency_id", sa.UUID(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("endpoint", sa.String(length=200), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("trade_id", sa.UUID(), nullable=False),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["ten.tenant.tenant_id"], name="fk_trade_booking_idempotency_tenant"),
        sa.ForeignKeyConstraint(["trade_id"], ["trd.trade.trade_id"], name="fk_trade_booking_idempotency_trade"),
        sa.PrimaryKeyConstraint("trade_booking_idempotency_id"),
        sa.UniqueConstraint("tenant_id", "endpoint", "idempotency_key", name="uq_trade_booking_idempotency_scope"),
        schema="trd",
    )
    op.create_index("ix_trade_booking_idempotency_trade", "trade_booking_idempotency", ["trade_id"], schema="trd")


def downgrade() -> None:
    """Remove only the idempotency records introduced by this revision."""

    op.drop_index("ix_trade_booking_idempotency_trade", table_name="trade_booking_idempotency", schema="trd")
    op.drop_table("trade_booking_idempotency", schema="trd")
