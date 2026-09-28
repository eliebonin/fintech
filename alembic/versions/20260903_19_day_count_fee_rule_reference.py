"""Reference the governed day-count catalogue from contractual fee rules."""

from alembic import op
import sqlalchemy as sa


revision = "20260903_19"
down_revision = "20260903_18"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add an optional canonical day-count reference while retaining source text."""

    op.add_column(
        "fee_rule",
        sa.Column("day_count_convention_id", sa.UUID(), nullable=True, comment="Governed day-count convention used for prorating a time-based fee; null means not applicable or not yet sourced."),
        schema="fee",
    )
    op.create_foreign_key(
        "fk_fee_rule_day_count_convention",
        "fee_rule",
        "day_count_convention",
        ["day_count_convention_id"],
        ["day_count_convention_id"],
        source_schema="fee",
        referent_schema="secm",
    )


def downgrade() -> None:
    """Remove the additive fee-rule reference only."""

    op.drop_constraint("fk_fee_rule_day_count_convention", "fee_rule", schema="fee", type_="foreignkey")
    op.drop_column("fee_rule", "day_count_convention_id", schema="fee")
