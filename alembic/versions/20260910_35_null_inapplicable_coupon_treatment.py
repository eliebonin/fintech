"""Represent coupon final treatment as not applicable when memory is off."""

from alembic import op


revision = "20260910_35"
down_revision = "20260910_34"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Remove misleading treatment values from no-memory coupon programmes."""

    op.execute(
        """
        UPDATE secm.structured_product_coupon_programme
        SET final_payment_treatment = NULL
        WHERE memory_mode = 'NONE'
          AND final_payment_treatment IS NOT NULL
        """
    )


def downgrade() -> None:
    """Restore the former inert default for no-memory programmes."""

    op.execute(
        """
        UPDATE secm.structured_product_coupon_programme
        SET final_payment_treatment = 'PAY_SEPARATELY'
        WHERE memory_mode = 'NONE'
          AND final_payment_treatment IS NULL
        """
    )
