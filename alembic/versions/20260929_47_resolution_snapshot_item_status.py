"""Persist the immutable public outcome for each resolution snapshot item.

Revision ID: 20260929_47
Revises: 20260928_46
"""

import sqlalchemy as sa
from alembic import op


revision = "20260929_47"
down_revision = "20260928_46"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "market_data_resolution_snapshot_item",
        sa.Column("status", sa.String(length=30), nullable=False, server_default=sa.text("'MISSING'")),
        schema="md",
    )
    op.add_column(
        "market_data_resolution_snapshot_item",
        sa.Column("request_sequence", sa.Integer(), nullable=False, server_default=sa.text("0")),
        schema="md",
    )
    op.create_index(
        "uq_market_data_resolution_snapshot_item_sequence",
        "market_data_resolution_snapshot_item",
        ["market_data_resolution_snapshot_id", "request_sequence"],
        unique=True,
        schema="md",
    )


def downgrade() -> None:
    op.drop_index("uq_market_data_resolution_snapshot_item_sequence", table_name="market_data_resolution_snapshot_item", schema="md")
    op.drop_column("market_data_resolution_snapshot_item", "request_sequence", schema="md")
    op.drop_column("market_data_resolution_snapshot_item", "status", schema="md")
