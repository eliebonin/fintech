"""Harden percentage-strike anchors and correction revisions."""

from alembic import op
import sqlalchemy as sa


revision = "20260910_39"
down_revision = "20260910_38"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "structured_product_condition_group",
        "logical_operator",
        comment="How independent Boolean members combine: ALL, ANY, or NONE; NONE denotes an unconditional gate or one aggregate underlying predicate evaluated after MIN/MAX reduction.",
        schema="secm",
    )
    # An initial-fixing FK is meaningful only when the option strike is
    # expressed as a percentage of that fixing.  This prevents a direct SQL
    # writer from attaching an apparently valid but semantically unrelated
    # fixing to an absolute/index-point/FX strike.
    op.create_check_constraint(
        "ck_option_terms_initial_fixing_basis",
        "option_terms",
        "strike_reference_initial_fixing_id IS NULL OR strike_basis = 'PERCENT_OF_INITIAL'",
        schema="secm",
    )

    # Corrections are append-only.  The original uniqueness key prevented a
    # corrected row for the same corporate action/effective date from being
    # inserted, even when it correctly superseded the prior row.
    op.add_column(
        "option_strike_adjustment",
        sa.Column(
            "revision_no",
            sa.Integer(),
            server_default=sa.text("1"),
            nullable=True,
            comment="Positive correction revision for the same option terms, corporate action, and effective date; incremented when a later record supersedes an earlier one.",
        ),
        schema="secm",
    )
    op.execute(
        sa.text(
            "UPDATE secm.option_strike_adjustment SET revision_no = 1 WHERE revision_no IS NULL"
        )
    )
    op.alter_column(
        "option_strike_adjustment",
        "revision_no",
        nullable=False,
        schema="secm",
    )
    op.drop_constraint(
        "uq_option_strike_adjustment_action",
        "option_strike_adjustment",
        schema="secm",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_option_strike_adjustment_revision",
        "option_strike_adjustment",
        ["option_terms_id", "corporate_action_id", "effective_date", "revision_no"],
        schema="secm",
    )
    op.create_check_constraint(
        "ck_option_strike_adjustment_revision",
        "option_strike_adjustment",
        "revision_no > 0",
        schema="secm",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_option_strike_adjustment_revision",
        "option_strike_adjustment",
        schema="secm",
        type_="check",
    )
    op.alter_column(
        "structured_product_condition_group",
        "logical_operator",
        comment="How atomic members aggregate: ALL, ANY, or NONE.",
        schema="secm",
    )
    op.drop_constraint(
        "uq_option_strike_adjustment_revision",
        "option_strike_adjustment",
        schema="secm",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_option_strike_adjustment_action",
        "option_strike_adjustment",
        ["option_terms_id", "corporate_action_id", "effective_date"],
        schema="secm",
    )
    op.drop_column("option_strike_adjustment", "revision_no", schema="secm")
    op.drop_constraint(
        "ck_option_terms_initial_fixing_basis",
        "option_terms",
        schema="secm",
        type_="check",
    )
