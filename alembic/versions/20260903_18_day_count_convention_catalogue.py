"""Add the governed day-count convention catalogue and bond-term reference."""

from alembic import op
import sqlalchemy as sa


revision = "20260903_18"
down_revision = "20260902_17"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the shared convention vocabulary without changing existing bond values."""

    op.create_table(
        "day_count_convention",
        sa.Column("day_count_convention_id", sa.UUID(), server_default=sa.text("uuidv7()"), nullable=False, comment="Immutable UUIDv7 identifier for a governed day-count convention."),
        sa.Column("code", sa.String(length=60), nullable=False, comment="Stable controlled code such as ACT_360, ACT_ACT_ICMA, or 30E_360."),
        sa.Column("display_name", sa.String(length=150), nullable=False, comment="Human-readable name shown to Operations and API consumers."),
        sa.Column("description", sa.Text(), nullable=False, comment="Plain-language description of the accrual convention and its intended scope."),
        sa.Column("standard_source", sa.String(length=100), nullable=True, comment="Optional standards or market-practice source, such as ISDA or ICMA."),
        sa.Column("status", sa.String(length=30), server_default=sa.text("'ACTIVE'"), nullable=False, comment="Lifecycle status of the convention, normally ACTIVE or RETIRED."),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False, comment="Display ordering value for dropdowns and operational catalogues."),
        sa.PrimaryKeyConstraint("day_count_convention_id"),
        sa.UniqueConstraint("code", name="uq_day_count_convention_code"),
        schema="secm",
    )
    op.add_column(
        "bond_terms",
        sa.Column("day_count_convention_id", sa.UUID(), nullable=True, comment="Governed day-count convention used for coupon accrual; null means not yet sourced or applicable."),
        schema="secm",
    )
    op.create_foreign_key(
        "fk_bond_terms_day_count_convention",
        "bond_terms",
        "day_count_convention",
        ["day_count_convention_id"],
        ["day_count_convention_id"],
        source_schema="secm",
        referent_schema="secm",
    )
    op.create_index(
        "ix_day_count_convention_status_order",
        "day_count_convention",
        ["status", "sort_order", "code"],
        schema="secm",
    )


def downgrade() -> None:
    """Remove only the additive convention reference and catalogue."""

    op.drop_index("ix_day_count_convention_status_order", table_name="day_count_convention", schema="secm")
    op.drop_constraint("fk_bond_terms_day_count_convention", "bond_terms", schema="secm", type_="foreignkey")
    op.drop_column("bond_terms", "day_count_convention_id", schema="secm")
    op.drop_table("day_count_convention", schema="secm")
