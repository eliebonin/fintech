"""Clarify operational mapping and trade-reference roles."""

from alembic import op


revision = "20260907_28"
down_revision = "20260907_27"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "external_object_mapping",
        "mapping_role",
        schema="ing",
        comment="Mapping role such as PRIMARY, TRADING_ROUTE, ALIAS, LEGACY, or SOURCE_REFERENCE.",
    )
    op.alter_column(
        "trade_external_reference",
        "reference_type",
        schema="trd",
        comment="Reference type such as SOURCE_TRADE_ID, EXECUTION_LISTING_IDENTIFIER, AGENT_SUBRED_REFERENCE, or BASKET_REFERENCE.",
    )


def downgrade() -> None:
    op.alter_column(
        "external_object_mapping",
        "mapping_role",
        schema="ing",
        comment="Mapping role such as PRIMARY, ALIAS, LEGACY, or SOURCE_REFERENCE.",
    )
    op.alter_column(
        "trade_external_reference",
        "reference_type",
        schema="trd",
        comment="Reference type such as SOURCE_TRADE_ID, AGENT_SUBRED_REFERENCE, or BASKET_REFERENCE.",
    )
