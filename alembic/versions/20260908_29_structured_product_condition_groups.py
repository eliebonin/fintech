"""Replace standalone barriers with first-class structured-product condition groups."""

from alembic import op
import sqlalchemy as sa


revision = "20260908_29"
down_revision = "20260907_28"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The project is pre-production: retain neither independent barrier actions
    # nor their overloaded rule shape.  Recreate the barrier layer around a
    # single group result that can produce ordered actions exactly once.
    op.drop_table("barrier_action", schema="secm")
    op.drop_table("barrier_rule", schema="secm")

    op.create_table(
        "structured_product_condition_group",
        sa.Column("condition_group_id", sa.UUID(), server_default=sa.text("uuidv7()"), nullable=False, comment="Immutable UUIDv7 identifier for one Boolean structured-product condition evaluated as a unit."),
        sa.Column("structured_product_instrument_node_id", sa.UUID(), nullable=False, comment="Parent structured-product instrument whose contractual terms contain this condition group."),
        sa.Column("group_code", sa.String(length=100), nullable=False, comment="Stable product-local business code for the contractual condition group."),
        sa.Column("observation_style", sa.String(length=30), nullable=False, comment="Observation convention: DISCRETE, CONTINUOUS, or FINAL_ONLY."),
        sa.Column("schedule_event_id", sa.UUID(), nullable=True, comment="Exact scheduled observation event; required for DISCRETE and FINAL_ONLY groups and absent for CONTINUOUS groups."),
        sa.Column("logical_operator", sa.String(length=20), nullable=False, comment="How atomic members aggregate: ALL, ANY, or NONE."),
        sa.Column("evaluation_sequence", sa.Integer(), server_default=sa.text("1"), nullable=False, comment="Deterministic group evaluation order for the parent and observation context; lower values are evaluated first."),
        sa.Column("status", sa.String(length=30), server_default=sa.text("'DRAFT'"), nullable=False, comment="Lifecycle status such as DRAFT, VALIDATED, ACTIVE, SUPERSEDED, or RETIRED."),
        sa.Column("source_payload_id", sa.UUID(), nullable=True, comment="Retained source payload evidencing this contractual condition group."),
        sa.ForeignKeyConstraint(["structured_product_instrument_node_id"], ["secm.structured_product_terms.instrument_node_id"], name="fk_sp_condition_group_terms"),
        sa.ForeignKeyConstraint(["schedule_event_id"], ["secm.schedule_event.schedule_event_id"], name="fk_sp_condition_group_event"),
        sa.ForeignKeyConstraint(["source_payload_id"], ["ing.source_payload.source_payload_id"], name="fk_sp_condition_group_source_payload"),
        sa.PrimaryKeyConstraint("condition_group_id"),
        sa.UniqueConstraint("structured_product_instrument_node_id", "group_code", name="uq_sp_condition_group_code"),
        sa.UniqueConstraint("structured_product_instrument_node_id", "schedule_event_id", "evaluation_sequence", name="uq_sp_condition_group_event_sequence"),
        sa.CheckConstraint("observation_style IN ('DISCRETE', 'CONTINUOUS', 'FINAL_ONLY')", name="ck_sp_condition_group_observation_style"),
        sa.CheckConstraint("logical_operator IN ('ALL', 'ANY', 'NONE')", name="ck_sp_condition_group_operator"),
        sa.CheckConstraint("(observation_style IN ('DISCRETE', 'FINAL_ONLY') AND schedule_event_id IS NOT NULL) OR (observation_style = 'CONTINUOUS' AND schedule_event_id IS NULL)", name="ck_sp_condition_group_observation"),
        sa.CheckConstraint("evaluation_sequence > 0", name="ck_sp_condition_group_evaluation_sequence"),
        schema="secm",
    )
    op.create_table(
        "barrier_rule",
        sa.Column("barrier_rule_id", sa.UUID(), server_default=sa.text("uuidv7()"), nullable=False, comment="Immutable UUIDv7 identifier for one atomic, underlying-specific contractual predicate."),
        sa.Column("condition_group_id", sa.UUID(), nullable=False, comment="Boolean condition group that aggregates this atomic predicate."),
        sa.Column("owner_reference_node_id", sa.UUID(), nullable=False, comment="Component or instrument that supplies the contractual context for this atomic predicate."),
        sa.Column("underlying_reference_node_id", sa.UUID(), nullable=False, comment="Specific underlying reference node tested by this atomic predicate."),
        sa.Column("condition_sequence", sa.Integer(), nullable=False, comment="Deterministic member sequence within the owning condition group."),
        sa.Column("comparison_operator", sa.String(length=20), nullable=False, comment="Comparison operator: GE, GT, LE, LT, BETWEEN, or OUTSIDE."),
        sa.Column("level_reference_type", sa.String(length=40), nullable=False, comment="Level basis such as PCT_OF_INITIAL, PCT_OF_STRIKE, ABSOLUTE_LEVEL, or PCT_OF_PAR."),
        sa.Column("lower_level_value", sa.Numeric(precision=30, scale=12), nullable=True, comment="Required threshold, or lower bound for BETWEEN and OUTSIDE, expressed using level_reference_type."),
        sa.Column("upper_level_value", sa.Numeric(precision=30, scale=12), nullable=True, comment="Upper bound for BETWEEN and OUTSIDE, expressed using level_reference_type."),
        sa.Column("underlying_measure", sa.String(length=40), nullable=False, comment="Measured metric such as OFFICIAL_CLOSE, FINAL_PERFORMANCE, INTRADAY_LOW, or AVERAGE_PERFORMANCE."),
        sa.Column("status", sa.String(length=30), server_default=sa.text("'DRAFT'"), nullable=False, comment="Lifecycle status such as DRAFT, VALIDATED, ACTIVE, SUPERSEDED, or RETIRED."),
        sa.Column("source_payload_id", sa.UUID(), nullable=True, comment="Retained source payload evidencing this atomic predicate."),
        sa.ForeignKeyConstraint(["condition_group_id"], ["secm.structured_product_condition_group.condition_group_id"], name="fk_barrier_rule_group"),
        sa.ForeignKeyConstraint(["owner_reference_node_id"], ["secm.financial_reference_node.reference_node_id"], name="fk_barrier_rule_owner"),
        sa.ForeignKeyConstraint(["underlying_reference_node_id"], ["secm.financial_reference_node.reference_node_id"], name="fk_barrier_rule_underlying"),
        sa.ForeignKeyConstraint(["source_payload_id"], ["ing.source_payload.source_payload_id"], name="fk_barrier_rule_source_payload"),
        sa.PrimaryKeyConstraint("barrier_rule_id"),
        sa.UniqueConstraint("condition_group_id", "condition_sequence", name="uq_barrier_rule_group_sequence"),
        sa.CheckConstraint("condition_sequence > 0", name="ck_barrier_rule_sequence"),
        sa.CheckConstraint("comparison_operator IN ('GE', 'GT', 'LE', 'LT', 'BETWEEN', 'OUTSIDE')", name="ck_barrier_rule_comparison"),
        sa.CheckConstraint("(comparison_operator IN ('GE', 'GT', 'LE', 'LT') AND lower_level_value IS NOT NULL AND upper_level_value IS NULL) OR (comparison_operator IN ('BETWEEN', 'OUTSIDE') AND lower_level_value IS NOT NULL AND upper_level_value IS NOT NULL AND upper_level_value >= lower_level_value)", name="ck_barrier_rule_levels"),
        schema="secm",
    )
    op.create_table(
        "condition_group_action",
        sa.Column("condition_group_action_id", sa.UUID(), server_default=sa.text("uuidv7()"), nullable=False, comment="Immutable UUIDv7 identifier for one ordered consequence of a satisfied condition group."),
        sa.Column("condition_group_id", sa.UUID(), nullable=False, comment="Satisfied Boolean condition group that causes this action."),
        sa.Column("action_type", sa.String(length=50), nullable=False, comment="Consequence: PAY_COMPONENT, REDEEM_PARENT, TERMINATE_PARENT, CANCEL_FUTURE_COMPONENTS, or ACTIVATE_CAPITAL_PROTECTION."),
        sa.Column("target_scope", sa.String(length=20), nullable=False, comment="Contractual target scope: COMPONENT or PARENT."),
        sa.Column("target_reference_node_id", sa.UUID(), nullable=False, comment="Specific component or parent reference node affected by this action."),
        sa.Column("execution_sequence", sa.Integer(), server_default=sa.text("1"), nullable=False, comment="Deterministic sequence in which satisfied-group actions execute; lower values execute first."),
        sa.Column("status", sa.String(length=30), server_default=sa.text("'DRAFT'"), nullable=False, comment="Lifecycle status such as DRAFT, VALIDATED, ACTIVE, SUPERSEDED, or RETIRED."),
        sa.Column("source_payload_id", sa.UUID(), nullable=True, comment="Retained source payload evidencing this group action."),
        sa.ForeignKeyConstraint(["condition_group_id"], ["secm.structured_product_condition_group.condition_group_id"], name="fk_condition_group_action_group"),
        sa.ForeignKeyConstraint(["target_reference_node_id"], ["secm.financial_reference_node.reference_node_id"], name="fk_condition_group_action_target"),
        sa.ForeignKeyConstraint(["source_payload_id"], ["ing.source_payload.source_payload_id"], name="fk_condition_group_action_source_payload"),
        sa.PrimaryKeyConstraint("condition_group_action_id"),
        sa.UniqueConstraint("condition_group_id", "execution_sequence", name="uq_condition_group_action_sequence"),
        sa.CheckConstraint("action_type IN ('PAY_COMPONENT', 'REDEEM_PARENT', 'TERMINATE_PARENT', 'CANCEL_FUTURE_COMPONENTS', 'ACTIVATE_CAPITAL_PROTECTION')", name="ck_condition_group_action_type"),
        sa.CheckConstraint("target_scope IN ('COMPONENT', 'PARENT')", name="ck_condition_group_action_target_scope"),
        sa.CheckConstraint("execution_sequence > 0", name="ck_condition_group_action_execution_sequence"),
        schema="secm",
    )


def downgrade() -> None:
    op.drop_table("condition_group_action", schema="secm")
    op.drop_table("barrier_rule", schema="secm")
    op.drop_table("structured_product_condition_group", schema="secm")

    op.create_table(
        "barrier_rule",
        sa.Column("barrier_rule_id", sa.UUID(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column("owner_reference_node_id", sa.UUID(), nullable=False),
        sa.Column("barrier_role", sa.String(length=40), nullable=False),
        sa.Column("condition_direction", sa.String(length=30), nullable=False),
        sa.Column("condition_effect", sa.String(length=30), nullable=False),
        sa.Column("level_reference_type", sa.String(length=40), nullable=False),
        sa.Column("level_value", sa.Numeric(precision=30, scale=12), nullable=True),
        sa.Column("observation_style", sa.String(length=30), nullable=False),
        sa.Column("schedule_id", sa.UUID(), nullable=True),
        sa.Column("underlying_scope", sa.String(length=30), nullable=False),
        sa.Column("underlying_measure", sa.String(length=40), nullable=False),
        sa.Column("priority", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.ForeignKeyConstraint(["owner_reference_node_id"], ["secm.financial_reference_node.reference_node_id"]),
        sa.ForeignKeyConstraint(["schedule_id"], ["secm.schedule.schedule_id"]),
        sa.PrimaryKeyConstraint("barrier_rule_id"),
        schema="secm",
    )
    op.create_table(
        "barrier_action",
        sa.Column("barrier_action_id", sa.UUID(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column("barrier_rule_id", sa.UUID(), nullable=False),
        sa.Column("action_type", sa.String(length=50), nullable=False),
        sa.Column("target_reference_node_id", sa.UUID(), nullable=True),
        sa.Column("evaluation_sequence", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.ForeignKeyConstraint(["barrier_rule_id"], ["secm.barrier_rule.barrier_rule_id"]),
        sa.ForeignKeyConstraint(["target_reference_node_id"], ["secm.financial_reference_node.reference_node_id"]),
        sa.PrimaryKeyConstraint("barrier_action_id"),
        sa.UniqueConstraint("barrier_rule_id", "evaluation_sequence", name="uq_barrier_action_sequence"),
        schema="secm",
    )
