"""Persist explicit inclusivity for structured-product barrier bounds."""

from alembic import op
import sqlalchemy as sa


revision = "20260909_33"
down_revision = "20260909_32"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "barrier_rule",
        sa.Column(
            "lower_bound_inclusive",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
            comment="Whether a lower range bound is inclusive; scalar GE/LE and GT/LT operators remain authoritative for single-bound predicates.",
        ),
        schema="secm",
    )
    op.add_column(
        "barrier_rule",
        sa.Column(
            "upper_bound_inclusive",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
            comment="Whether an upper range bound is inclusive; a consolation range uses false to exclude the final payoff barrier.",
        ),
        schema="secm",
    )
    op.create_check_constraint(
        "ck_barrier_rule_bound_inclusivity",
        "barrier_rule",
        "(comparison_operator IN ('BETWEEN', 'OUTSIDE')) OR ((comparison_operator IN ('GE', 'LE') AND lower_bound_inclusive = true) OR (comparison_operator IN ('GT', 'LT') AND lower_bound_inclusive = false))",
        schema="secm",
    )


def downgrade() -> None:
    op.drop_constraint("ck_barrier_rule_bound_inclusivity", "barrier_rule", schema="secm", type_="check")
    op.drop_column("barrier_rule", "upper_bound_inclusive", schema="secm")
    op.drop_column("barrier_rule", "lower_bound_inclusive", schema="secm")
