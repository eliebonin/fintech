"""Bridge structured-product drafts to an auditable canonical terms graph."""

from alembic import op
import sqlalchemy as sa


revision = "20260909_32"
down_revision = "20260909_31"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Consolation is a parent-level consequence, not a new instrument node.
    # Keep the vocabulary in the canonical action table so the API can persist
    # the UI's explicit range/pay-consolation semantics without overloading a
    # generic component payout.
    op.drop_constraint("ck_condition_group_action_type", "condition_group_action", schema="secm", type_="check")
    op.create_check_constraint(
        "ck_condition_group_action_type",
        "condition_group_action",
        "action_type IN ('PAY_COMPONENT', 'PAY_CONSOLATION', 'REDEEM_PARENT', 'TERMINATE_PARENT', 'CANCEL_FUTURE_COMPONENTS', 'ACTIVATE_CAPITAL_PROTECTION')",
        schema="secm",
    )
    op.drop_constraint("ck_condition_group_action_payment_basis", "condition_group_action", schema="secm", type_="check")
    op.create_check_constraint(
        "ck_condition_group_action_payment_basis",
        "condition_group_action",
        "payment_basis IS NULL OR payment_basis IN ('PER_UNIT', 'PCT_OF_NOTIONAL', 'PCT_OF_PAR', 'PCT_OF_MAX_PAYOFF', 'ABSOLUTE')",
        schema="secm",
    )

    op.create_table(
        "structured_product_initial_fixing",
        sa.Column("structured_product_initial_fixing_id", sa.UUID(), server_default=sa.text("uuidv7()"), nullable=False, comment="Immutable UUIDv7 identifier for one recorded initial fixing used by a structured-product terms version."),
        sa.Column("structured_product_terms_id", sa.UUID(), nullable=False, comment="Structured-product terms version for which the initial fixing is contractually relevant."),
        sa.Column("underlying_reference_node_id", sa.UUID(), nullable=False, comment="Exact underlying reference node whose initial level was fixed."),
        sa.Column("fixing_date", sa.Date(), nullable=False, comment="Business date on which the initial underlying fixing applies."),
        sa.Column("fixing_value", sa.Numeric(30, 12), nullable=False, comment="Initial underlying value used as the contractual reference level."),
        sa.Column("fixing_basis", sa.String(length=40), nullable=False, comment="Unit and meaning of fixing_value: LEVEL, INDEX_POINTS, FX_RATE, or PERCENT_OF_INITIAL."),
        sa.Column("fixing_source", sa.String(length=30), nullable=False, comment="Provenance class of the fixing: MANUAL, MARKET_DATA, PROVIDER, or DERIVED."),
        sa.Column("market_data_observation_id", sa.UUID(), nullable=True, comment="Immutable market-data observation supporting the fixing when the source is market data."),
        sa.Column("market_data_resolution_snapshot_id", sa.UUID(), nullable=True, comment="Resolution snapshot proving the entitled market-data inputs used for the fixing."),
        sa.Column("source_system_id", sa.UUID(), nullable=True, comment="Source system that supplied or recorded the fixing when an external system is involved."),
        sa.Column("source_payload_id", sa.UUID(), nullable=True, comment="Retained raw payload evidencing the fixing when available."),
        sa.Column("status", sa.String(length=30), server_default=sa.text("'ACCEPTED'"), nullable=False, comment="Fixing lifecycle state: ACCEPTED, SUPERSEDED, or REJECTED."),
        sa.Column("supersedes_fixing_id", sa.UUID(), nullable=True, comment="Prior fixing superseded by this corrected value without mutating the original record."),
        sa.Column("recorded_at_utc", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False, comment="UTC timestamp at which Fortem recorded this fixing record."),
        sa.ForeignKeyConstraint(["structured_product_terms_id"], ["secm.structured_product_terms.structured_product_terms_id"], name="fk_sp_initial_fixing_terms"),
        sa.ForeignKeyConstraint(["underlying_reference_node_id"], ["secm.financial_reference_node.reference_node_id"], name="fk_sp_initial_fixing_underlying"),
        sa.ForeignKeyConstraint(["market_data_observation_id"], ["md.market_data_observation.market_data_observation_id"], name="fk_sp_initial_fixing_observation"),
        sa.ForeignKeyConstraint(["market_data_resolution_snapshot_id"], ["md.market_data_resolution_snapshot.market_data_resolution_snapshot_id"], name="fk_sp_initial_fixing_resolution_snapshot"),
        sa.ForeignKeyConstraint(["source_system_id"], ["ing.integration_source_system.integration_source_system_id"], name="fk_sp_initial_fixing_source_system"),
        sa.ForeignKeyConstraint(["source_payload_id"], ["ing.source_payload.source_payload_id"], name="fk_sp_initial_fixing_source_payload"),
        sa.ForeignKeyConstraint(["supersedes_fixing_id"], ["secm.structured_product_initial_fixing.structured_product_initial_fixing_id"], name="fk_sp_initial_fixing_supersedes"),
        sa.PrimaryKeyConstraint("structured_product_initial_fixing_id"),
        sa.UniqueConstraint("structured_product_terms_id", "underlying_reference_node_id", "fixing_date", "fixing_source", name="uq_structured_product_initial_fixing_record"),
        sa.CheckConstraint("fixing_value > 0", name="ck_structured_product_initial_fixing_positive"),
        sa.CheckConstraint("fixing_basis IN ('LEVEL', 'INDEX_POINTS', 'FX_RATE', 'PERCENT_OF_INITIAL')", name="ck_structured_product_initial_fixing_basis"),
        sa.CheckConstraint("fixing_source IN ('MANUAL', 'MARKET_DATA', 'PROVIDER', 'DERIVED')", name="ck_structured_product_initial_fixing_source"),
        sa.CheckConstraint("status IN ('ACCEPTED', 'SUPERSEDED', 'REJECTED')", name="ck_structured_product_initial_fixing_status"),
        schema="secm",
    )
    op.create_index(
        "uq_structured_product_initial_fixing_current",
        "structured_product_initial_fixing",
        ["structured_product_terms_id", "underlying_reference_node_id", "fixing_date"],
        unique=True,
        schema="secm",
        postgresql_where=sa.text("status = 'ACCEPTED'"),
    )


def downgrade() -> None:
    op.drop_index("uq_structured_product_initial_fixing_current", table_name="structured_product_initial_fixing", schema="secm")
    op.drop_table("structured_product_initial_fixing", schema="secm")

    op.drop_constraint("ck_condition_group_action_payment_basis", "condition_group_action", schema="secm", type_="check")
    op.create_check_constraint(
        "ck_condition_group_action_payment_basis",
        "condition_group_action",
        "payment_basis IS NULL OR payment_basis IN ('PER_UNIT', 'PCT_OF_NOTIONAL', 'PCT_OF_PAR', 'ABSOLUTE')",
        schema="secm",
    )
    op.drop_constraint("ck_condition_group_action_type", "condition_group_action", schema="secm", type_="check")
    op.create_check_constraint(
        "ck_condition_group_action_type",
        "condition_group_action",
        "action_type IN ('PAY_COMPONENT', 'REDEEM_PARENT', 'TERMINATE_PARENT', 'CANCEL_FUTURE_COMPONENTS', 'ACTIVATE_CAPITAL_PROTECTION')",
        schema="secm",
    )
