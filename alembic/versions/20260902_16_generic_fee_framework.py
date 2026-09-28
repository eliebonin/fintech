"""Add shared, effective-dated contractual fee rules and assignments."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260902_16"
down_revision = "20260901_15"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the fee vocabulary/rule boundary and link trade fees to rules."""

    op.execute('CREATE SCHEMA IF NOT EXISTS "fee"')

    op.create_table(
        "fee_type",
        sa.Column("fee_type_id", sa.UUID(), server_default=sa.text("uuidv7()"), nullable=False, comment="Immutable UUIDv7 identifier for a governed fee classification."),
        sa.Column("fee_type_code", sa.String(length=50), nullable=False, comment="Unique fee classification code such as MANAGEMENT, PERFORMANCE, ADMINISTRATION, DISTRIBUTION, BROKERAGE, or TAX."),
        sa.Column("display_name", sa.String(length=250), nullable=False, comment="Human-readable fee classification name."),
        sa.Column("description", sa.Text(), nullable=True, comment="Business definition and inclusion guidance for this fee classification."),
        sa.Column("status", sa.String(length=30), server_default=sa.text("'ACTIVE'"), nullable=False, comment="Lifecycle status of the governed fee classification."),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False, comment="Display ordering value for fee-type lists."),
        sa.PrimaryKeyConstraint("fee_type_id"),
        sa.UniqueConstraint("fee_type_code"),
        schema="fee",
    )

    op.create_table(
        "fee_rule",
        sa.Column("fee_rule_id", sa.UUID(), server_default=sa.text("uuidv7()"), nullable=False, comment="Immutable UUIDv7 identifier for one version of a contractual or operational fee rule."),
        sa.Column("fee_type_id", sa.UUID(), nullable=False, comment="Governed classification of the fee calculated by this rule."),
        sa.Column("rule_code", sa.String(length=100), nullable=False, comment="Stable business code for the fee rule across its immutable versions."),
        sa.Column("display_name", sa.String(length=250), nullable=False, comment="Human-readable name of this fee rule version."),
        sa.Column("calculation_method", sa.String(length=30), nullable=False, comment="Calculation model such as RATE, FIXED, TIERED, PERFORMANCE, WAIVER, or REIMBURSEMENT."),
        sa.Column("calculation_basis", sa.String(length=50), nullable=False, comment="Base to which the rule applies, such as NAV, AUM, NOTIONAL, PERFORMANCE, TRANSACTION_VALUE, or FIXED."),
        sa.Column("rate_value", sa.Numeric(30, 12), nullable=True, comment="Rate or amount parameter; when rate_unit is PCT, a stored value of 12 means 12 percent."),
        sa.Column("rate_unit", sa.String(length=20), nullable=True, comment="Unit of rate_value such as PCT, BPS, AMOUNT, or MULTIPLIER."),
        sa.Column("currency_id", sa.UUID(), nullable=True, comment="Currency of a fixed fee, cap, floor, or other monetary parameter when applicable."),
        sa.Column("accrual_frequency", sa.String(length=40), nullable=True, comment="Frequency at which the fee is accrued, such as DAILY, MONTHLY, QUARTERLY, or ANNUAL."),
        sa.Column("payment_frequency", sa.String(length=40), nullable=True, comment="Frequency at which the accrued fee is paid or transferred."),
        sa.Column("day_count_convention", sa.String(length=30), nullable=True, comment="Day-count convention used for prorating a time-based rate, such as ACT_365 or ACT_360."),
        sa.Column("minimum_amount", sa.Numeric(30, 12), nullable=True, comment="Optional minimum monetary amount for the fee calculation."),
        sa.Column("maximum_amount", sa.Numeric(30, 12), nullable=True, comment="Optional maximum monetary amount or cap for the fee calculation."),
        sa.Column("parameters_json", postgresql.JSONB(), nullable=True, comment="Versioned model-specific parameters, such as performance-fee hurdle or high-water-mark configuration; core identity and amount fields remain typed columns."),
        sa.Column("tenant_id", sa.UUID(), nullable=True, comment="Tenant owning a private fee rule; null identifies a shared canonical rule."),
        sa.Column("valid_from", sa.Date(), nullable=False, comment="First business date on which this fee rule version is valid."),
        sa.Column("valid_to", sa.Date(), nullable=True, comment="Last business date on which this fee rule version is valid."),
        sa.Column("version_no", sa.Integer(), server_default=sa.text("1"), nullable=False, comment="Monotonically increasing version number for the rule code."),
        sa.Column("is_current", sa.Boolean(), server_default=sa.text("true"), nullable=False, comment="Convenience indicator for the current rule projection; date validity and status remain authoritative."),
        sa.Column("supersedes_fee_rule_id", sa.UUID(), nullable=True, comment="Prior fee rule version superseded by this immutable version."),
        sa.Column("source_payload_id", sa.UUID(), nullable=True, comment="Retained source payload from which the rule terms were obtained or validated."),
        sa.Column("source_reference", sa.String(length=500), nullable=True, comment="Human-readable prospectus, agreement, schedule, or other source reference for the rule."),
        sa.Column("approved_by_user_account_id", sa.UUID(), nullable=True, comment="Internal account that approved the rule for operational use."),
        sa.Column("approved_at_utc", sa.DateTime(timezone=True), nullable=True, comment="UTC timestamp at which the rule version was approved."),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False, comment="UTC timestamp at which the immutable fee rule version was created."),
        sa.CheckConstraint("valid_to IS NULL OR valid_to >= valid_from", name="ck_fee_rule_valid_period"),
        sa.CheckConstraint("version_no > 0", name="ck_fee_rule_positive_version"),
        sa.PrimaryKeyConstraint("fee_rule_id"),
        sa.ForeignKeyConstraint(["fee_type_id"], ["fee.fee_type.fee_type_id"], name="fk_fee_rule_fee_type"),
        sa.ForeignKeyConstraint(["currency_id"], ["secm.currency.currency_id"], name="fk_fee_rule_currency"),
        sa.ForeignKeyConstraint(["tenant_id"], ["ten.tenant.tenant_id"], name="fk_fee_rule_tenant"),
        sa.ForeignKeyConstraint(["supersedes_fee_rule_id"], ["fee.fee_rule.fee_rule_id"], name="fk_fee_rule_supersedes"),
        sa.ForeignKeyConstraint(["source_payload_id"], ["ing.source_payload.source_payload_id"], name="fk_fee_rule_source_payload"),
        sa.ForeignKeyConstraint(["approved_by_user_account_id"], ["secm.user_account.user_account_id"], name="fk_fee_rule_approved_by"),
        sa.UniqueConstraint("rule_code", "version_no", name="uq_fee_rule_code_version"),
        schema="fee",
    )

    op.create_table(
        "fee_rule_target",
        sa.Column("fee_rule_target_id", sa.UUID(), server_default=sa.text("uuidv7()"), nullable=False, comment="Immutable UUIDv7 identifier for assigning a fee rule to one fee-bearing object."),
        sa.Column("fee_rule_id", sa.UUID(), nullable=False, comment="Fee rule version assigned by this row."),
        sa.Column("target_reference_node_id", sa.UUID(), nullable=True, comment="Canonical or private reference node targeted by the rule, such as a fund, share class, AMC, bond, or structured product."),
        sa.Column("target_strategy_id", sa.UUID(), nullable=True, comment="Portfolio, mandate, managed reference portfolio, or other strategy targeted by the rule."),
        sa.Column("application_mode", sa.String(length=20), server_default=sa.text("'ADDITIVE'"), nullable=False, comment="How the target rule combines with broader rules: ADDITIVE, REPLACE, DEFAULT, or WAIVE."),
        sa.Column("priority", sa.Integer(), server_default=sa.text("1"), nullable=False, comment="Deterministic evaluation priority when multiple applicable rules share a fee type."),
        sa.Column("payer_organisation_id", sa.UUID(), nullable=True, comment="Organisation contractually responsible for paying the fee when specified."),
        sa.Column("recipient_organisation_id", sa.UUID(), nullable=True, comment="Organisation entitled to receive the fee when specified."),
        sa.Column("effective_from", sa.Date(), nullable=True, comment="Optional first business date on which this assignment is effective; it cannot extend the fee rule validity."),
        sa.Column("effective_to", sa.Date(), nullable=True, comment="Optional last business date on which this assignment is effective."),
        sa.Column("status", sa.String(length=30), server_default=sa.text("'ACTIVE'"), nullable=False, comment="Assignment lifecycle status such as ACTIVE, RETIRED, or REJECTED."),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False, comment="UTC timestamp at which this fee-rule assignment was created."),
        sa.CheckConstraint("(target_reference_node_id IS NOT NULL) <> (target_strategy_id IS NOT NULL)", name="ck_fee_rule_target_exactly_one_target"),
        sa.CheckConstraint("effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from", name="ck_fee_rule_target_valid_period"),
        sa.CheckConstraint("priority > 0", name="ck_fee_rule_target_positive_priority"),
        sa.PrimaryKeyConstraint("fee_rule_target_id"),
        sa.ForeignKeyConstraint(["fee_rule_id"], ["fee.fee_rule.fee_rule_id"], name="fk_fee_rule_target_rule"),
        sa.ForeignKeyConstraint(["target_reference_node_id"], ["secm.financial_reference_node.reference_node_id"], name="fk_fee_rule_target_reference_node"),
        sa.ForeignKeyConstraint(["target_strategy_id"], ["trd.strategy.strategy_id"], name="fk_fee_rule_target_strategy"),
        sa.ForeignKeyConstraint(["payer_organisation_id"], ["secm.organisation.organisation_id"], name="fk_fee_rule_target_payer"),
        sa.ForeignKeyConstraint(["recipient_organisation_id"], ["secm.organisation.organisation_id"], name="fk_fee_rule_target_recipient"),
        schema="fee",
    )

    op.create_index(
        "ix_fee_rule_type_validity",
        "fee_rule",
        ["fee_type_id", "valid_from", "valid_to"],
        schema="fee",
    )
    op.create_index(
        "ix_fee_rule_target_reference_node",
        "fee_rule_target",
        ["target_reference_node_id", "effective_from", "effective_to"],
        schema="fee",
    )
    op.create_index(
        "ix_fee_rule_target_strategy",
        "fee_rule_target",
        ["target_strategy_id", "effective_from", "effective_to"],
        schema="fee",
    )

    op.add_column(
        "trade_fee",
        sa.Column("fee_rule_id", sa.UUID(), nullable=True, comment="Optional contractual fee rule used to calculate this realised trade fee."),
        schema="trd",
    )
    op.create_foreign_key(
        "fk_trade_fee_fee_rule",
        "trade_fee",
        "fee_rule",
        ["fee_rule_id"],
        ["fee_rule_id"],
        source_schema="trd",
        referent_schema="fee",
    )
    op.create_index("ix_trade_fee_rule", "trade_fee", ["fee_rule_id"], schema="trd")


def downgrade() -> None:
    """Remove the fee framework and its optional trade-fee lineage column."""

    op.drop_index("ix_trade_fee_rule", table_name="trade_fee", schema="trd")
    op.drop_constraint("fk_trade_fee_fee_rule", "trade_fee", schema="trd", type_="foreignkey")
    op.drop_column("trade_fee", "fee_rule_id", schema="trd")
    op.drop_index("ix_fee_rule_target_strategy", table_name="fee_rule_target", schema="fee")
    op.drop_index("ix_fee_rule_target_reference_node", table_name="fee_rule_target", schema="fee")
    op.drop_index("ix_fee_rule_type_validity", table_name="fee_rule", schema="fee")
    op.drop_table("fee_rule_target", schema="fee")
    op.drop_table("fee_rule", schema="fee")
    op.drop_table("fee_type", schema="fee")
    op.execute('DROP SCHEMA IF EXISTS "fee"')
