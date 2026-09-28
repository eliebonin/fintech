"""Add governed automation policies and evidence for reference-data proposals."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260902_17"
down_revision = "20260902_16"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the policy-bound, auditable automated onboarding boundary."""

    op.create_table(
        "reference_data_automation_policy",
        sa.Column("reference_data_automation_policy_id", sa.UUID(), server_default=sa.text("uuidv7()"), nullable=False, comment="Immutable UUIDv7 identifier for one version of a policy governing automated reference-data proposals."),
        sa.Column("policy_code", sa.String(length=100), nullable=False, comment="Stable business code for the automation policy across immutable versions."),
        sa.Column("display_name", sa.String(length=250), nullable=False, comment="Human-readable name of the automation policy version."),
        sa.Column("source_system_id", sa.UUID(), nullable=False, comment="Source system whose proposals may be evaluated by this policy."),
        sa.Column("target_object_type", sa.String(length=50), nullable=False, comment="Reference-data object type governed by the policy, such as EQUITY, LISTING, or IDENTIFIER_MAPPING."),
        sa.Column("operation_type", sa.String(length=30), nullable=False, comment="Permitted operation governed by the policy, such as CREATE, AMEND, or MAP."),
        sa.Column("min_confidence", sa.Numeric(5, 4), nullable=True, comment="Minimum normalized confidence score required for automatic approval, between zero and one."),
        sa.Column("required_identifier_schemes", postgresql.JSONB(), nullable=True, comment="JSON array of identifier schemes that must be present before this policy can approve automatically."),
        sa.Column("criteria_json", postgresql.JSONB(), nullable=True, comment="Versioned source-specific validation criteria evaluated by the automation service."),
        sa.Column("auto_approve", sa.Boolean(), server_default=sa.text("false"), nullable=False, comment="Whether a proposal satisfying this policy may receive an automated approval decision."),
        sa.Column("tenant_id", sa.UUID(), nullable=True, comment="Tenant owning a private policy; null identifies a shared canonical policy."),
        sa.Column("valid_from", sa.Date(), nullable=False, comment="First business date on which this policy version is effective."),
        sa.Column("valid_to", sa.Date(), nullable=True, comment="Last business date on which this policy version is effective."),
        sa.Column("version_no", sa.Integer(), server_default=sa.text("1"), nullable=False, comment="Monotonically increasing immutable version number for the policy code."),
        sa.Column("status", sa.String(length=30), server_default=sa.text("'ACTIVE'"), nullable=False, comment="Lifecycle status such as DRAFT, ACTIVE, RETIRED, or SUPERSEDED."),
        sa.Column("approved_by_user_account_id", sa.UUID(), nullable=True, comment="Steward account approving this policy version for operational use."),
        sa.Column("approved_at_utc", sa.DateTime(timezone=True), nullable=True, comment="UTC timestamp at which the automation policy version was approved."),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False, comment="UTC timestamp at which the automation policy version was created."),
        sa.CheckConstraint("min_confidence IS NULL OR (min_confidence >= 0 AND min_confidence <= 1)", name="ck_reference_data_automation_policy_confidence"),
        sa.CheckConstraint("valid_to IS NULL OR valid_to >= valid_from", name="ck_reference_data_automation_policy_valid_period"),
        sa.CheckConstraint("version_no > 0", name="ck_reference_data_automation_policy_positive_version"),
        sa.ForeignKeyConstraint(["source_system_id"], ["ing.integration_source_system.integration_source_system_id"], name="fk_reference_data_automation_policy_source_system"),
        sa.ForeignKeyConstraint(["tenant_id"], ["ten.tenant.tenant_id"], name="fk_reference_data_automation_policy_tenant"),
        sa.ForeignKeyConstraint(["approved_by_user_account_id"], ["secm.user_account.user_account_id"], name="fk_reference_data_automation_policy_approved_by"),
        sa.PrimaryKeyConstraint("reference_data_automation_policy_id"),
        sa.UniqueConstraint("policy_code", "version_no", "tenant_id", name="uq_reference_data_automation_policy_version"),
        schema="secm",
    )

    proposal_columns = [
        sa.Column("source_system_id", sa.UUID(), nullable=True, comment="Source system that submitted the proposal, retained explicitly for automation policy evaluation."),
        sa.Column("submission_mode", sa.String(length=20), server_default=sa.text("'MANUAL'"), nullable=False, comment="How the proposal entered the workflow: MANUAL or AUTOMATED."),
        sa.Column("automation_policy_id", sa.UUID(), nullable=True, comment="Automation policy evaluated for this proposal when submission_mode is AUTOMATED."),
        sa.Column("idempotency_key", sa.String(length=500), nullable=True, comment="Source-scoped idempotency key ensuring retries do not create duplicate proposals or instruments."),
        sa.Column("match_status", sa.String(length=30), server_default=sa.text("'NEW'"), nullable=False, comment="Result of duplicate and identity matching: NEW, EXACT_MATCH, POSSIBLE_MATCH, or CONFLICT."),
        sa.Column("confidence_score", sa.Numeric(5, 4), nullable=True, comment="Normalized confidence score assigned by matching or source validation, between zero and one."),
        sa.Column("payload_schema_version", sa.String(length=40), server_default=sa.text("'1'"), nullable=False, comment="Version of the structured proposal payload contract used by the producer."),
    ]
    for column in proposal_columns:
        op.add_column("reference_data_proposal", column, schema="secm")
    op.create_foreign_key(
        "fk_reference_data_proposal_source_system",
        "reference_data_proposal",
        "integration_source_system",
        ["source_system_id"],
        ["integration_source_system_id"],
        source_schema="secm",
        referent_schema="ing",
    )
    op.create_foreign_key(
        "fk_reference_data_proposal_automation_policy",
        "reference_data_proposal",
        "reference_data_automation_policy",
        ["automation_policy_id"],
        ["reference_data_automation_policy_id"],
        source_schema="secm",
        referent_schema="secm",
    )
    op.create_unique_constraint(
        "uq_reference_data_proposal_idempotency",
        "reference_data_proposal",
        ["source_system_id", "idempotency_key", "tenant_id"],
        schema="secm",
    )
    op.create_check_constraint(
        "ck_reference_data_proposal_submission_mode",
        "reference_data_proposal",
        "submission_mode IN ('MANUAL', 'AUTOMATED')",
        schema="secm",
    )
    op.create_check_constraint(
        "ck_reference_data_proposal_confidence",
        "reference_data_proposal",
        "confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)",
        schema="secm",
    )

    approval_columns = [
        sa.Column("decision_method", sa.String(length=20), server_default=sa.text("'MANUAL'"), nullable=False, comment="How the decision was made: MANUAL by a steward or AUTOMATED under a governed policy."),
        sa.Column("automation_policy_id", sa.UUID(), nullable=True, comment="Automation policy responsible for an automated decision, when decision_method is AUTOMATED."),
        sa.Column("decision_evidence_json", postgresql.JSONB(), nullable=True, comment="Structured matching, validation, and policy evidence retained with the decision."),
    ]
    for column in approval_columns:
        op.add_column("reference_data_approval", column, schema="secm")
    op.create_foreign_key(
        "fk_reference_data_approval_automation_policy",
        "reference_data_approval",
        "reference_data_automation_policy",
        ["automation_policy_id"],
        ["reference_data_automation_policy_id"],
        source_schema="secm",
        referent_schema="secm",
    )
    op.create_check_constraint(
        "ck_reference_data_approval_decision_method",
        "reference_data_approval",
        "decision_method IN ('MANUAL', 'AUTOMATED')",
        schema="secm",
    )

    op.create_index(
        "ix_reference_data_automation_policy_source_target",
        "reference_data_automation_policy",
        ["source_system_id", "target_object_type", "operation_type", "valid_from", "valid_to"],
        schema="secm",
    )
    op.create_index(
        "ix_reference_data_proposal_idempotency",
        "reference_data_proposal",
        ["source_system_id", "idempotency_key", "tenant_id"],
        schema="secm",
    )


def downgrade() -> None:
    """Remove automation policy metadata while preserving the original proposal boundary."""

    op.drop_index("ix_reference_data_proposal_idempotency", table_name="reference_data_proposal", schema="secm")
    op.drop_index("ix_reference_data_automation_policy_source_target", table_name="reference_data_automation_policy", schema="secm")
    op.drop_constraint("ck_reference_data_approval_decision_method", "reference_data_approval", schema="secm", type_="check")
    op.drop_constraint("fk_reference_data_approval_automation_policy", "reference_data_approval", schema="secm", type_="foreignkey")
    op.drop_column("reference_data_approval", "decision_evidence_json", schema="secm")
    op.drop_column("reference_data_approval", "automation_policy_id", schema="secm")
    op.drop_column("reference_data_approval", "decision_method", schema="secm")
    op.drop_constraint("ck_reference_data_proposal_confidence", "reference_data_proposal", schema="secm", type_="check")
    op.drop_constraint("ck_reference_data_proposal_submission_mode", "reference_data_proposal", schema="secm", type_="check")
    op.drop_constraint("uq_reference_data_proposal_idempotency", "reference_data_proposal", schema="secm", type_="unique")
    op.drop_constraint("fk_reference_data_proposal_automation_policy", "reference_data_proposal", schema="secm", type_="foreignkey")
    op.drop_constraint("fk_reference_data_proposal_source_system", "reference_data_proposal", schema="secm", type_="foreignkey")
    op.drop_column("reference_data_proposal", "payload_schema_version", schema="secm")
    op.drop_column("reference_data_proposal", "confidence_score", schema="secm")
    op.drop_column("reference_data_proposal", "match_status", schema="secm")
    op.drop_column("reference_data_proposal", "idempotency_key", schema="secm")
    op.drop_column("reference_data_proposal", "automation_policy_id", schema="secm")
    op.drop_column("reference_data_proposal", "submission_mode", schema="secm")
    op.drop_column("reference_data_proposal", "source_system_id", schema="secm")
    op.drop_table("reference_data_automation_policy", schema="secm")
