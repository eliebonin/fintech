"""Make multi-underlying semantics and child-option strike anchors explicit."""

from alembic import op
import sqlalchemy as sa


revision = "20260910_38"
down_revision = "20260910_37"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # A scope such as WORST_OF is a reduction over underlying observations,
    # not merely a Boolean ALL/ANY label.  Keep the existing logical operator
    # for atomic predicates and persist the reduction separately.
    op.add_column(
        "structured_product_condition_group",
        sa.Column(
            "underlying_aggregation",
            sa.String(length=20),
            server_default=sa.text("'SINGLE'"),
            nullable=True,
            comment="How multiple underlying measurements reduce before the predicate: SINGLE, MIN for worst-of, MAX for best-of, or NONE for an unconditional gate.",
        ),
        schema="secm",
    )
    op.execute(
        sa.text(
            """
            UPDATE secm.structured_product_condition_group
            SET underlying_aggregation = CASE
                WHEN logical_operator = 'NONE' THEN 'NONE'
                WHEN underlying_scope = 'WORST_OF' THEN 'MIN'
                WHEN underlying_scope = 'BEST_OF' THEN 'MAX'
                ELSE 'SINGLE'
            END
            """
        )
    )
    op.alter_column("structured_product_condition_group", "underlying_aggregation", nullable=False, schema="secm")
    op.create_check_constraint(
        "ck_sp_condition_group_underlying_aggregation",
        "structured_product_condition_group",
        "underlying_aggregation IN ('SINGLE', 'MIN', 'MAX', 'NONE')",
        schema="secm",
    )

    # Percentage strikes on generated child options are percentages of the
    # product-specific initial fixing, not percentages of an unknown future
    # spot.  The FK makes the contractual anchor traversable in both review
    # and lifecycle code.
    op.add_column(
        "option_terms",
        sa.Column(
            "strike_reference_initial_fixing_id",
            sa.UUID(),
            nullable=True,
            comment="Immutable structured-product initial fixing that anchors a percentage strike; keeps a child option traceable to its parent terms version.",
        ),
        schema="secm",
    )
    op.create_foreign_key(
        "fk_option_terms_strike_reference_initial_fixing",
        "option_terms",
        "structured_product_initial_fixing",
        ["strike_reference_initial_fixing_id"],
        ["structured_product_initial_fixing_id"],
        source_schema="secm",
        referent_schema="secm",
    )
    op.drop_constraint("ck_option_terms_strike_basis", "option_terms", schema="secm", type_="check")
    op.create_check_constraint(
        "ck_option_terms_strike_basis",
        "option_terms",
        "strike_basis IN ('ABSOLUTE', 'INDEX_POINTS', 'FX_RATE', 'PERCENT_OF_SPOT', 'PERCENT_OF_INITIAL')",
        schema="secm",
    )
    op.drop_constraint("ck_option_terms_strike_currency", "option_terms", schema="secm", type_="check")
    op.create_check_constraint(
        "ck_option_terms_strike_currency",
        "option_terms",
        "strike_value IS NULL OR strike_basis IN ('INDEX_POINTS', 'PERCENT_OF_SPOT', 'PERCENT_OF_INITIAL') OR strike_currency_id IS NOT NULL",
        schema="secm",
    )
    op.drop_constraint("ck_option_strike_reset_basis", "option_strike_reset_rule", schema="secm", type_="check")
    op.create_check_constraint(
        "ck_option_strike_reset_basis",
        "option_strike_reset_rule",
        "strike_basis IN ('ABSOLUTE', 'INDEX_POINTS', 'FX_RATE', 'PERCENT_OF_SPOT', 'PERCENT_OF_INITIAL')",
        schema="secm",
    )

    op.create_table(
        "option_strike_adjustment",
        sa.Column("option_strike_adjustment_id", sa.UUID(), server_default=sa.text("uuidv7()"), nullable=False, comment="Immutable UUIDv7 identifier for one attributable contractual option-strike adjustment."),
        sa.Column("option_terms_id", sa.UUID(), nullable=False, comment="Option-terms version whose contractual strike was adjusted."),
        sa.Column("corporate_action_id", sa.UUID(), nullable=False, comment="Confirmed corporate action causing the contractual strike or deliverable adjustment."),
        sa.Column("effective_date", sa.Date(), nullable=False, comment="Business date on which the adjustment takes effect under the corporate action."),
        sa.Column("adjustment_kind", sa.String(length=40), nullable=False, comment="Adjustment reason such as STOCK_SPLIT, REVERSE_SPLIT, BONUS_ISSUE, SPECIAL_DIVIDEND, or OTHER."),
        sa.Column("pre_adjustment_strike_value", sa.Numeric(precision=30, scale=12), nullable=False, comment="Strike value immediately before this adjustment, expressed in the option terms strike basis."),
        sa.Column("post_adjustment_strike_value", sa.Numeric(precision=30, scale=12), nullable=False, comment="Strike value after applying the contractual corporate-action factor."),
        sa.Column("strike_factor", sa.Numeric(precision=30, scale=12), nullable=False, comment="Positive multiplicative factor applied to the pre-adjustment strike; for example 0.5 for a two-for-one split."),
        sa.Column("post_adjustment_fixing_value", sa.Numeric(precision=30, scale=12), nullable=True, comment="Adjusted reference fixing when the product's fixing basis also changes under the action."),
        sa.Column("status", sa.String(length=30), server_default=sa.text("'PROPOSED'"), nullable=False, comment="Lifecycle state: PROPOSED, ACCEPTED, SUPERSEDED, or REJECTED."),
        sa.Column("supersedes_adjustment_id", sa.UUID(), nullable=True, comment="Prior adjustment superseded by this corrected factor or result without mutating the original record."),
        sa.Column("source_payload_id", sa.UUID(), nullable=True, comment="Retained source payload evidencing the adjustment calculation or issuer notice."),
        sa.Column("recorded_at_utc", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False, comment="UTC timestamp at which Fortem recorded this adjustment record."),
        sa.PrimaryKeyConstraint("option_strike_adjustment_id"),
        sa.ForeignKeyConstraint(["option_terms_id"], ["secm.option_terms.option_terms_id"], name="fk_option_strike_adjustment_terms"),
        sa.ForeignKeyConstraint(["corporate_action_id"], ["secm.corporate_action.corporate_action_id"], name="fk_option_strike_adjustment_corporate_action"),
        sa.ForeignKeyConstraint(["supersedes_adjustment_id"], ["secm.option_strike_adjustment.option_strike_adjustment_id"], name="fk_option_strike_adjustment_supersedes"),
        sa.ForeignKeyConstraint(["source_payload_id"], ["ing.source_payload.source_payload_id"], name="fk_option_strike_adjustment_source_payload"),
        sa.UniqueConstraint("option_terms_id", "corporate_action_id", "effective_date", name="uq_option_strike_adjustment_action"),
        sa.CheckConstraint("adjustment_kind IN ('STOCK_SPLIT', 'REVERSE_SPLIT', 'BONUS_ISSUE', 'SPECIAL_DIVIDEND', 'OTHER')", name="ck_option_strike_adjustment_kind"),
        sa.CheckConstraint("pre_adjustment_strike_value > 0 AND post_adjustment_strike_value > 0", name="ck_option_strike_adjustment_values"),
        sa.CheckConstraint("strike_factor > 0", name="ck_option_strike_adjustment_factor"),
        sa.CheckConstraint("post_adjustment_fixing_value IS NULL OR post_adjustment_fixing_value > 0", name="ck_option_strike_adjustment_fixing"),
        sa.CheckConstraint("status IN ('PROPOSED', 'ACCEPTED', 'SUPERSEDED', 'REJECTED')", name="ck_option_strike_adjustment_status"),
        schema="secm",
    )
    op.create_index(
        "ix_option_strike_adjustment_terms_effective",
        "option_strike_adjustment",
        ["option_terms_id", "effective_date", "recorded_at_utc"],
        schema="secm",
    )


def downgrade() -> None:
    op.drop_index("ix_option_strike_adjustment_terms_effective", table_name="option_strike_adjustment", schema="secm")
    op.drop_table("option_strike_adjustment", schema="secm")
    op.drop_constraint("ck_option_strike_reset_basis", "option_strike_reset_rule", schema="secm", type_="check")
    op.create_check_constraint(
        "ck_option_strike_reset_basis",
        "option_strike_reset_rule",
        "strike_basis IN ('ABSOLUTE', 'INDEX_POINTS', 'FX_RATE', 'PERCENT_OF_SPOT')",
        schema="secm",
    )
    op.drop_constraint("ck_option_terms_strike_currency", "option_terms", schema="secm", type_="check")
    op.create_check_constraint(
        "ck_option_terms_strike_currency",
        "option_terms",
        "strike_value IS NULL OR strike_basis IN ('INDEX_POINTS', 'PERCENT_OF_SPOT') OR strike_currency_id IS NOT NULL",
        schema="secm",
    )
    op.drop_constraint("ck_option_terms_strike_basis", "option_terms", schema="secm", type_="check")
    op.create_check_constraint(
        "ck_option_terms_strike_basis",
        "option_terms",
        "strike_basis IN ('ABSOLUTE', 'INDEX_POINTS', 'FX_RATE', 'PERCENT_OF_SPOT')",
        schema="secm",
    )
    op.drop_constraint("fk_option_terms_strike_reference_initial_fixing", "option_terms", schema="secm", type_="foreignkey")
    op.drop_column("option_terms", "strike_reference_initial_fixing_id", schema="secm")
    op.drop_constraint("ck_sp_condition_group_underlying_aggregation", "structured_product_condition_group", schema="secm", type_="check")
    op.drop_column("structured_product_condition_group", "underlying_aggregation", schema="secm")
