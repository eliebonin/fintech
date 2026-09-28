"""Persist non-call and row-level structured-product settlement dates."""

from alembic import op
import sqlalchemy as sa


revision = "20260910_34"
down_revision = "20260909_33"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "structured_product_terms",
        sa.Column(
            "first_autocall_observation_date",
            sa.Date(),
            nullable=True,
            comment="Earliest scheduled date on which an early parent autocall/redemption test is permitted; earlier coupon observations may still occur.",
        ),
        schema="secm",
    )
    op.add_column(
        "condition_group_action",
        sa.Column(
            "payment_date",
            sa.Date(),
            nullable=True,
            comment="Action-specific settlement/payment date overriding the schedule event default when an outcome row is manually adjusted.",
        ),
        schema="secm",
    )
    op.create_check_constraint(
        "ck_sp_coupon_programme_final_payment_treatment",
        "structured_product_coupon_programme",
        "final_payment_treatment IS NULL OR final_payment_treatment IN ('PAY_SEPARATELY', 'INCLUDE_IN_REDEMPTION', 'FORFEIT')",
        schema="secm",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_sp_coupon_programme_final_payment_treatment",
        "structured_product_coupon_programme",
        schema="secm",
        type_="check",
    )
    op.drop_column("condition_group_action", "payment_date", schema="secm")
    op.drop_column("structured_product_terms", "first_autocall_observation_date", schema="secm")
