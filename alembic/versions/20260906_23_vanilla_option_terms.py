"""Add governed terms for vanilla CALL/PUT options."""

from alembic import op
import sqlalchemy as sa


revision = "20260906_23"
down_revision = "20260904_22"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "option_terms",
        sa.Column(
            "strike_basis",
            sa.String(length=30),
            server_default=sa.text("'ABSOLUTE'"),
            nullable=False,
            comment="Meaning of strike_value: ABSOLUTE monetary price, INDEX_POINTS, FX_RATE, or PERCENT_OF_SPOT.",
        ),
        schema="secm",
    )
    op.add_column(
        "option_terms",
        sa.Column(
            "premium_currency_id",
            sa.UUID(),
            nullable=True,
            comment="Convention or quoting currency for option premium. The amount and payment event remain trade-specific.",
        ),
        schema="secm",
    )
    op.add_column(
        "option_terms",
        sa.Column(
            "settlement_currency_id",
            sa.UUID(),
            nullable=True,
            comment="Currency of a cash settlement payoff; required for CASH and CASH_OR_PHYSICAL during canonical validation.",
        ),
        schema="secm",
    )
    op.add_column(
        "option_terms",
        sa.Column(
            "exercise_schedule_id",
            sa.UUID(),
            nullable=True,
            comment="Dated permitted exercise schedule for a BERMUDAN option; European and American options use common instrument dates unless a schedule is needed for extra rules.",
        ),
        schema="secm",
    )
    op.create_foreign_key(
        "fk_option_terms_premium_currency",
        "option_terms",
        "currency",
        ["premium_currency_id"],
        ["currency_id"],
        source_schema="secm",
        referent_schema="secm",
    )
    op.create_foreign_key(
        "fk_option_terms_settlement_currency",
        "option_terms",
        "currency",
        ["settlement_currency_id"],
        ["currency_id"],
        source_schema="secm",
        referent_schema="secm",
    )
    op.create_foreign_key(
        "fk_option_terms_exercise_schedule",
        "option_terms",
        "schedule",
        ["exercise_schedule_id"],
        ["schedule_id"],
        source_schema="secm",
        referent_schema="secm",
    )
    op.create_check_constraint(
        "ck_option_terms_type",
        "option_terms",
        "option_type IN ('CALL', 'PUT')",
        schema="secm",
    )
    op.create_check_constraint(
        "ck_option_terms_exercise_style",
        "option_terms",
        "exercise_style IN ('EUROPEAN', 'AMERICAN', 'BERMUDAN')",
        schema="secm",
    )
    op.create_check_constraint(
        "ck_option_terms_settlement_method",
        "option_terms",
        "settlement_method IN ('CASH', 'PHYSICAL', 'ELECTION', 'CASH_OR_PHYSICAL')",
        schema="secm",
    )
    op.create_check_constraint(
        "ck_option_terms_strike_basis",
        "option_terms",
        "strike_basis IN ('ABSOLUTE', 'INDEX_POINTS', 'FX_RATE', 'PERCENT_OF_SPOT')",
        schema="secm",
    )
    op.create_check_constraint(
        "ck_option_terms_strike_currency",
        "option_terms",
        "strike_value IS NULL OR strike_basis IN ('INDEX_POINTS', 'PERCENT_OF_SPOT') OR strike_currency_id IS NOT NULL",
        schema="secm",
    )
    op.create_check_constraint(
        "ck_option_terms_cash_currency",
        "option_terms",
        "settlement_method NOT IN ('CASH', 'CASH_OR_PHYSICAL') OR settlement_currency_id IS NOT NULL",
        schema="secm",
    )
    op.create_check_constraint(
        "ck_option_terms_bermudan_schedule",
        "option_terms",
        "exercise_style <> 'BERMUDAN' OR exercise_schedule_id IS NOT NULL",
        schema="secm",
    )


def downgrade() -> None:
    for name in (
        "ck_option_terms_bermudan_schedule",
        "ck_option_terms_cash_currency",
        "ck_option_terms_strike_currency",
        "ck_option_terms_strike_basis",
        "ck_option_terms_settlement_method",
        "ck_option_terms_exercise_style",
        "ck_option_terms_type",
    ):
        op.drop_constraint(name, "option_terms", schema="secm", type_="check")
    for name in (
        "fk_option_terms_exercise_schedule",
        "fk_option_terms_settlement_currency",
        "fk_option_terms_premium_currency",
    ):
        op.drop_constraint(name, "option_terms", schema="secm", type_="foreignkey")
    for column_name in ("exercise_schedule_id", "settlement_currency_id", "premium_currency_id", "strike_basis"):
        op.drop_column("option_terms", column_name, schema="secm")
