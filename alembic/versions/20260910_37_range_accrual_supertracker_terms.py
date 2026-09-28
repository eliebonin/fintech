"""Add focused terms for range-accrual and supertracker products."""

from alembic import op
import sqlalchemy as sa


revision = "20260910_37"
down_revision = "20260910_36"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "structured_product_range_accrual_terms",
        sa.Column("range_accrual_terms_id", sa.UUID(), server_default=sa.text("uuidv7()"), nullable=False, comment="Immutable UUIDv7 identifier for the range-accrual-specific terms attached to one structured-product terms version."),
        sa.Column("structured_product_terms_id", sa.UUID(), nullable=False, comment="Structured-product terms version owning this range-accrual convention."),
        sa.Column("observation_frequency", sa.String(length=20), nullable=False, comment="Contractual range observation cadence: DAILY, WEEKLY, or MONTHLY."),
        sa.Column("accrual_basis", sa.String(length=30), nullable=False, comment="Denominator used for the accrual fraction: OBSERVATION_COUNT or CALENDAR_DAYS."),
        sa.Column("non_business_day_rule", sa.String(length=40), nullable=False, comment="Treatment of non-business dates in the observation series: BUSINESS_DAYS_ONLY, CARRY_FORWARD_PREVIOUS, or CALENDAR_DAYS."),
        sa.Column("lower_level", sa.Numeric(precision=30, scale=12), nullable=False, comment="Inclusive lower range boundary in percentage points of the contractual initial fixing; 70 means 70% of initial."),
        sa.Column("upper_level", sa.Numeric(precision=30, scale=12), nullable=False, comment="Inclusive upper range boundary in percentage points of the contractual initial fixing; 130 means 130% of initial."),
        sa.Column("coupon_rate_per_annum", sa.Numeric(precision=30, scale=12), nullable=False, comment="Annualised contractual coupon rate in percentage points; the lifecycle service multiplies it by the accrued observation fraction."),
        sa.Column("observation_schedule_id", sa.UUID(), nullable=True, comment="Coupon-period observation anchor schedule used by the onboarding slice; a lifecycle service may later materialise a separate detailed fixing schedule."),
        sa.Column("status", sa.String(length=30), nullable=False, server_default=sa.text("'DRAFT'"), comment="Lifecycle status such as DRAFT, VALIDATED, ACTIVE, SUPERSEDED, or RETIRED."),
        sa.Column("source_payload_id", sa.UUID(), nullable=True, comment="Retained source payload evidencing the range-accrual convention when available."),
        sa.PrimaryKeyConstraint("range_accrual_terms_id"),
        sa.ForeignKeyConstraint(["structured_product_terms_id"], ["secm.structured_product_terms.structured_product_terms_id"], name="fk_sp_range_accrual_terms_version"),
        sa.ForeignKeyConstraint(["observation_schedule_id"], ["secm.schedule.schedule_id"], name="fk_sp_range_accrual_terms_schedule"),
        sa.ForeignKeyConstraint(["source_payload_id"], ["ing.source_payload.source_payload_id"], name="fk_sp_range_accrual_terms_source_payload"),
        sa.UniqueConstraint("structured_product_terms_id", name="uq_sp_range_accrual_terms_version"),
        sa.CheckConstraint("observation_frequency IN ('DAILY', 'WEEKLY', 'MONTHLY')", name="ck_sp_range_accrual_observation_frequency"),
        sa.CheckConstraint("accrual_basis IN ('OBSERVATION_COUNT', 'CALENDAR_DAYS')", name="ck_sp_range_accrual_basis"),
        sa.CheckConstraint("non_business_day_rule IN ('BUSINESS_DAYS_ONLY', 'CARRY_FORWARD_PREVIOUS', 'CALENDAR_DAYS')", name="ck_sp_range_accrual_non_business_day_rule"),
        sa.CheckConstraint("lower_level >= 0 AND upper_level > lower_level", name="ck_sp_range_accrual_range_bounds"),
        sa.CheckConstraint("coupon_rate_per_annum >= 0", name="ck_sp_range_accrual_coupon_rate"),
        schema="secm",
    )

    op.create_table(
        "structured_product_supertracker_terms",
        sa.Column("supertracker_terms_id", sa.UUID(), server_default=sa.text("uuidv7()"), nullable=False, comment="Immutable UUIDv7 identifier for the supertracker-specific terms attached to one structured-product terms version."),
        sa.Column("structured_product_terms_id", sa.UUID(), nullable=False, comment="Structured-product terms version owning this supertracker payoff convention."),
        sa.Column("participation_rate", sa.Numeric(precision=30, scale=12), nullable=False, comment="Positive upside participation multiplier stored as a decimal; 1.35 means 135% leveraged exposure."),
        sa.Column("cap_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false"), comment="Whether the leveraged upside is capped by a short call component."),
        sa.Column("cap_return", sa.Numeric(precision=30, scale=12), nullable=True, comment="Maximum underlying return in percentage points before the upside cap call flattens the payoff; 25 means a 25% underlying return cap."),
        sa.Column("status", sa.String(length=30), nullable=False, server_default=sa.text("'DRAFT'"), comment="Lifecycle status such as DRAFT, VALIDATED, ACTIVE, SUPERSEDED, or RETIRED."),
        sa.Column("source_payload_id", sa.UUID(), nullable=True, comment="Retained source payload evidencing the supertracker convention when available."),
        sa.PrimaryKeyConstraint("supertracker_terms_id"),
        sa.ForeignKeyConstraint(["structured_product_terms_id"], ["secm.structured_product_terms.structured_product_terms_id"], name="fk_sp_supertracker_terms_version"),
        sa.ForeignKeyConstraint(["source_payload_id"], ["ing.source_payload.source_payload_id"], name="fk_sp_supertracker_terms_source_payload"),
        sa.UniqueConstraint("structured_product_terms_id", name="uq_sp_supertracker_terms_version"),
        sa.CheckConstraint("participation_rate > 0", name="ck_sp_supertracker_participation_rate"),
        sa.CheckConstraint("(cap_enabled = false AND cap_return IS NULL) OR (cap_enabled = true AND cap_return > 0)", name="ck_sp_supertracker_cap_terms"),
        schema="secm",
    )


def downgrade() -> None:
    op.drop_table("structured_product_supertracker_terms", schema="secm")
    op.drop_table("structured_product_range_accrual_terms", schema="secm")
