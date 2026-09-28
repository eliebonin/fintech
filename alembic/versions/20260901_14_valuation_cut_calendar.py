"""Link named valuation cuts to the shared calendar domain."""

from alembic import op
import sqlalchemy as sa


revision = "20260901_14"
down_revision = "20260901_13"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add an optional calendar reference without invalidating existing cuts."""

    op.add_column(
        "valuation_cut",
        sa.Column(
            "market_calendar_id",
            sa.UUID(),
            nullable=True,
            comment="Optional calendar governing valid session dates and roll behaviour for this valuation cut.",
        ),
        schema="md",
    )
    op.create_foreign_key(
        "fk_valuation_cut_calendar",
        "valuation_cut",
        "market_calendar",
        ["market_calendar_id"],
        ["market_calendar_id"],
        source_schema="md",
        referent_schema="cal",
    )


def downgrade() -> None:
    """Remove the optional calendar reference from valuation cuts."""

    op.drop_constraint("fk_valuation_cut_calendar", "valuation_cut", schema="md", type_="foreignkey")
    op.drop_column("valuation_cut", "market_calendar_id", schema="md")
