"""Add append-only trade lifecycle and correction events."""

from alembic import op
import sqlalchemy as sa


revision = "20260901_09"
down_revision = "20260901_08"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "trade_lifecycle_event",
        sa.Column("trade_lifecycle_event_id", sa.UUID(), primary_key=True, server_default=sa.text("uuidv7()"), comment="Immutable UUIDv7 identifier for one append-only lifecycle event on a booked trade."),
        sa.Column("trade_id", sa.UUID(), sa.ForeignKey("trd.trade.trade_id"), nullable=False, comment="Booked trade whose lifecycle this event changes or records."),
        sa.Column("sequence_no", sa.Integer(), nullable=False, comment="Strictly increasing sequence within the trade lifecycle event chain."),
        sa.Column("event_type", sa.String(length=30), nullable=False, comment="Lifecycle event such as BOOKED, AMENDED, CANCELLED, SUPERSEDED, NOVATED, or CORRECTED."),
        sa.Column("event_datetime_utc", sa.DateTime(timezone=True), nullable=False, comment="UTC time at which the lifecycle event became effective economically or operationally."),
        sa.Column("source_system_id", sa.String(length=100), nullable=True, comment="Source system or integration that supplied the lifecycle event."),
        sa.Column("source_event_id", sa.String(length=500), nullable=True, comment="Source event or message identifier used for idempotent processing."),
        sa.Column("payload_hash", sa.String(length=64), nullable=True, comment="Hash of the immutable source event payload or normalized correction details."),
        sa.Column("supersedes_event_id", sa.UUID(), sa.ForeignKey("trd.trade_lifecycle_event.trade_lifecycle_event_id"), nullable=True, comment="Prior lifecycle event superseded by this correction or replacement."),
        sa.Column("event_payload", sa.Text(), nullable=True, comment="Serialized normalized correction details; the original trade and source payload remain separately retained."),
        sa.Column("recorded_by_user_account_id", sa.UUID(), sa.ForeignKey("secm.user_account.user_account_id"), nullable=False, comment="Authenticated internal account or service that recorded this lifecycle event."),
        sa.Column("recorded_at_utc", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="UTC timestamp at which Fortem recorded the lifecycle event."),
        sa.UniqueConstraint("trade_id", "sequence_no", name="uq_trade_lifecycle_event_sequence"),
        sa.UniqueConstraint("source_system_id", "source_event_id", name="uq_trade_lifecycle_event_source_id"),
        schema="trd",
    )
    op.execute(
        """
        CREATE FUNCTION trd.prevent_trade_lifecycle_event_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'trade lifecycle events are immutable; append a new event instead';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_trade_lifecycle_event_immutable
        BEFORE UPDATE OR DELETE ON trd.trade_lifecycle_event
        FOR EACH ROW EXECUTE FUNCTION trd.prevent_trade_lifecycle_event_mutation()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_trade_lifecycle_event_immutable ON trd.trade_lifecycle_event")
    op.execute("DROP FUNCTION IF EXISTS trd.prevent_trade_lifecycle_event_mutation()")
    op.drop_table("trade_lifecycle_event", schema="trd")
