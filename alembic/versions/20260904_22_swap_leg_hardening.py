"""Harden leg-based swaps and remove duplicate swap dates."""

from alembic import op
import sqlalchemy as sa


revision = "20260904_22"
down_revision = "20260904_21"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                  FROM secm.swap_terms s
                  JOIN secm.instrument_dates d
                    ON d.instrument_node_id = s.instrument_node_id
                 WHERE (s.effective_date IS NOT NULL AND d.effective_date IS NOT NULL AND s.effective_date <> d.effective_date)
                    OR (s.termination_date IS NOT NULL AND d.maturity_date IS NOT NULL AND s.termination_date <> d.maturity_date)
            ) THEN
                RAISE EXCEPTION 'Cannot remove duplicate swap dates while secm.swap_terms conflicts with secm.instrument_dates';
            END IF;
        END $$;
        """
    )
    op.execute(
        """
        INSERT INTO secm.instrument_dates (instrument_node_id, effective_date, maturity_date)
        SELECT s.instrument_node_id, s.effective_date, s.termination_date
          FROM secm.swap_terms s
         WHERE (s.effective_date IS NOT NULL OR s.termination_date IS NOT NULL)
           AND NOT EXISTS (
               SELECT 1
                 FROM secm.instrument_dates d
                WHERE d.instrument_node_id = s.instrument_node_id
           );
        """
    )
    op.execute(
        """
        UPDATE secm.instrument_dates d
           SET effective_date = COALESCE(d.effective_date, s.effective_date),
               maturity_date = COALESCE(d.maturity_date, s.termination_date)
          FROM secm.swap_terms s
         WHERE d.instrument_node_id = s.instrument_node_id;
        """
    )
    op.drop_column("swap_terms", "effective_date", schema="secm")
    op.drop_column("swap_terms", "termination_date", schema="secm")
    op.create_check_constraint(
        "ck_swap_terms_type",
        "swap_terms",
        "swap_type IN ('TOTAL_RETURN', 'INTEREST_RATE', 'CROSS_CURRENCY', 'INFLATION', 'CREDIT', 'COMMODITY')",
        schema="secm",
    )
    op.create_check_constraint("ck_swap_leg_number", "swap_leg", "leg_number > 0", schema="secm")
    op.create_check_constraint(
        "ck_swap_leg_role",
        "swap_leg",
        "leg_role IN ('PERFORMANCE', 'FUNDING', 'COUPON', 'PROTECTION', 'FEE')",
        schema="secm",
    )
    op.create_check_constraint(
        "ck_swap_leg_pay_receive",
        "swap_leg",
        "pay_receive IN ('PAY', 'RECEIVE')",
        schema="secm",
    )
    op.create_check_constraint(
        "ck_swap_leg_role_requirements",
        "swap_leg",
        "(leg_role <> 'PERFORMANCE' OR (reference_node_id IS NOT NULL AND return_profile_id IS NOT NULL)) "
        "AND (leg_role <> 'FUNDING' OR (reference_node_id IS NOT NULL AND currency_id IS NOT NULL))",
        schema="secm",
    )
    op.alter_column(
        "instrument",
        "base_currency_id",
        schema="secm",
        comment="Primary contractual or denomination currency of the instrument; it is never a strategy reporting currency.",
    )
    op.alter_column(
        "swap_leg",
        "spread",
        schema="secm",
        comment="Contractual spread over the leg's reference rate or performance where applicable, stored as a decimal rate: 0.015 means 1.50% or 150 bps.",
    )


def downgrade() -> None:
    op.alter_column(
        "swap_leg",
        "spread",
        schema="secm",
        comment="Contractual spread over the leg's reference rate or performance where applicable.",
    )
    op.alter_column(
        "instrument",
        "base_currency_id",
        schema="secm",
        comment="Primary contractual, denomination, or reporting currency of the instrument.",
    )
    op.drop_constraint("ck_swap_leg_role_requirements", "swap_leg", schema="secm", type_="check")
    op.drop_constraint("ck_swap_leg_pay_receive", "swap_leg", schema="secm", type_="check")
    op.drop_constraint("ck_swap_leg_role", "swap_leg", schema="secm", type_="check")
    op.drop_constraint("ck_swap_leg_number", "swap_leg", schema="secm", type_="check")
    op.drop_constraint("ck_swap_terms_type", "swap_terms", schema="secm", type_="check")
    op.add_column(
        "swap_terms",
        sa.Column("termination_date", sa.Date(), nullable=True, comment="Legacy duplicate swap termination date; common instrument dates are canonical."),
        schema="secm",
    )
    op.add_column(
        "swap_terms",
        sa.Column("effective_date", sa.Date(), nullable=True, comment="Legacy duplicate swap effective date; common instrument dates are canonical."),
        schema="secm",
    )
