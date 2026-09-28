"""Add frozen evidence and request deduplication to market-data snapshots.

Revision ID: 20260928_46
Revises: 20260911_45
"""

import sqlalchemy as sa
from alembic import op


revision = "20260928_46"
down_revision = "20260911_45"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Store immutable replay evidence and tenant-scoped create idempotency."""

    op.add_column(
        "market_data_resolution_snapshot",
        sa.Column(
            "use_purpose",
            sa.String(length=50),
            nullable=False,
            server_default=sa.text("'UNKNOWN'"),
            comment="Entitled use purpose evaluated when this immutable snapshot was created.",
        ),
        schema="md",
    )
    op.add_column(
        "market_data_resolution_snapshot_item",
        sa.Column("market_data_vintage_id", sa.UUID(), nullable=True),
        schema="md",
    )
    op.add_column(
        "market_data_resolution_snapshot_item",
        sa.Column("acquisition_licence_id", sa.UUID(), nullable=True),
        schema="md",
    )
    op.add_column(
        "market_data_resolution_snapshot_item",
        sa.Column("source_published_at_utc", sa.DateTime(timezone=True), nullable=True),
        schema="md",
    )
    op.add_column(
        "market_data_resolution_snapshot_item",
        sa.Column("received_at_utc", sa.DateTime(timezone=True), nullable=True),
        schema="md",
    )
    op.create_foreign_key(
        "fk_resolution_snapshot_item_vintage",
        "market_data_resolution_snapshot_item",
        "market_data_vintage",
        ["market_data_vintage_id"],
        ["market_data_vintage_id"],
        source_schema="md",
        referent_schema="md",
    )
    op.create_foreign_key(
        "fk_resolution_snapshot_item_licence",
        "market_data_resolution_snapshot_item",
        "data_licence",
        ["acquisition_licence_id"],
        ["data_licence_id"],
        source_schema="md",
        referent_schema="md",
    )
    op.create_table(
        "market_data_resolution_idempotency",
        sa.Column("market_data_resolution_idempotency_id", sa.UUID(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("endpoint", sa.String(length=200), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("market_data_resolution_snapshot_id", sa.UUID(), nullable=False),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("expires_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["ten.tenant.tenant_id"], name="fk_market_data_resolution_idempotency_tenant"),
        sa.ForeignKeyConstraint(["market_data_resolution_snapshot_id"], ["md.market_data_resolution_snapshot.market_data_resolution_snapshot_id"], name="fk_market_data_resolution_idempotency_snapshot"),
        sa.PrimaryKeyConstraint("market_data_resolution_idempotency_id"),
        sa.UniqueConstraint("tenant_id", "endpoint", "idempotency_key", name="uq_market_data_resolution_idempotency_scope"),
        schema="md",
    )
    op.create_index(
        "ix_market_data_resolution_idempotency_snapshot",
        "market_data_resolution_idempotency",
        ["market_data_resolution_snapshot_id"],
        schema="md",
    )


def downgrade() -> None:
    """Remove only the evidence and idempotency objects introduced here."""

    op.drop_index("ix_market_data_resolution_idempotency_snapshot", table_name="market_data_resolution_idempotency", schema="md")
    op.drop_table("market_data_resolution_idempotency", schema="md")
    op.drop_constraint("fk_resolution_snapshot_item_licence", "market_data_resolution_snapshot_item", schema="md", type_="foreignkey")
    op.drop_constraint("fk_resolution_snapshot_item_vintage", "market_data_resolution_snapshot_item", schema="md", type_="foreignkey")
    op.drop_column("market_data_resolution_snapshot_item", "received_at_utc", schema="md")
    op.drop_column("market_data_resolution_snapshot_item", "source_published_at_utc", schema="md")
    op.drop_column("market_data_resolution_snapshot_item", "acquisition_licence_id", schema="md")
    op.drop_column("market_data_resolution_snapshot_item", "market_data_vintage_id", schema="md")
    op.drop_column("market_data_resolution_snapshot", "use_purpose", schema="md")
