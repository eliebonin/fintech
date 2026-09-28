"""Add composable tenant operating profiles and module entitlements.

Revision ID: 20260911_42
Revises: 20260911_41
"""

from alembic import op
import sqlalchemy as sa


revision = "20260911_42"
down_revision = "20260911_41"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the tenant capability control-plane catalogue and assignments."""

    op.create_table(
        "operating_profile",
        sa.Column("operating_profile_id", sa.UUID(), server_default=sa.text("uuidv7()"), nullable=False, comment="Immutable UUIDv7 identifier for a governed composable tenant operating-profile definition."),
        sa.Column("profile_code", sa.String(length=100), nullable=False, comment="Stable unique operating-profile code such as FUND_MANAGER, AMC_MANAGER, or STRUCTURED_PRODUCT_DISTRIBUTOR."),
        sa.Column("display_name", sa.String(length=250), nullable=False, comment="Human-readable operating-profile name used in onboarding, administration, and reporting."),
        sa.Column("description", sa.Text(), nullable=True, comment="Business definition of the operating profile and the tenant activities it commonly represents."),
        sa.Column("status", sa.String(length=30), server_default=sa.text("'ACTIVE'"), nullable=False, comment="Lifecycle status of the governed operating profile, such as ACTIVE, RETIRED, or SUPERSEDED."),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False, comment="Display ordering for operational-profile catalogues and onboarding templates."),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False, comment="UTC timestamp at which this governed operating-profile definition was created."),
        sa.PrimaryKeyConstraint("operating_profile_id"),
        sa.UniqueConstraint("profile_code"),
        schema="ten",
    )
    op.create_table(
        "platform_module",
        sa.Column("platform_module_id", sa.UUID(), server_default=sa.text("uuidv7()"), nullable=False, comment="Immutable UUIDv7 identifier for a governed platform product capability."),
        sa.Column("module_code", sa.String(length=100), nullable=False, comment="Stable unique capability code such as TRADING, FUND_MANAGEMENT, UCITS_CONTROLS, or STRUCTURED_PRODUCTS."),
        sa.Column("display_name", sa.String(length=250), nullable=False, comment="Human-readable platform-module name used in administration and product packaging."),
        sa.Column("description", sa.Text(), nullable=True, comment="Business definition of the capability granted when this platform module is entitled to a tenant."),
        sa.Column("module_category", sa.String(length=40), nullable=False, comment="Broad module category such as CORE_REFERENCE, MARKET_DATA, TRADING, VALUATION, FUND, AMC, STRUCTURED_PRODUCT, or DISTRIBUTION."),
        sa.Column("status", sa.String(length=30), server_default=sa.text("'ACTIVE'"), nullable=False, comment="Lifecycle status of the governed platform module, such as ACTIVE, RETIRED, or SUPERSEDED."),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False, comment="Display ordering for module catalogues and tenant administration."),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False, comment="UTC timestamp at which this governed platform-module definition was created."),
        sa.PrimaryKeyConstraint("platform_module_id"),
        sa.UniqueConstraint("module_code"),
        schema="ten",
    )
    op.create_table(
        "tenant_operating_profile_assignment",
        sa.Column("tenant_operating_profile_assignment_id", sa.UUID(), server_default=sa.text("uuidv7()"), nullable=False, comment="Immutable UUIDv7 identifier for one effective-dated tenant operating-profile assignment."),
        sa.Column("tenant_id", sa.UUID(), nullable=False, comment="Tenant classified by this operating-profile assignment."),
        sa.Column("operating_profile_id", sa.UUID(), nullable=False, comment="Governed operating profile assigned to the tenant."),
        sa.Column("assignment_source", sa.String(length=30), nullable=False, comment="How the profile assignment was established, such as ONBOARDING, CONTRACT, MANUAL, or MIGRATION."),
        sa.Column("status", sa.String(length=30), server_default=sa.text("'ACTIVE'"), nullable=False, comment="Lifecycle status of the assignment, such as PROPOSED, ACTIVE, REJECTED, RETIRED, or SUPERSEDED."),
        sa.Column("approved_by_user_account_id", sa.UUID(), nullable=True, comment="Authenticated account that approved the operating-profile assignment for tenant use."),
        sa.Column("approved_at_utc", sa.DateTime(timezone=True), nullable=True, comment="UTC timestamp at which the tenant operating-profile assignment was approved."),
        sa.Column("valid_from", sa.Date(), nullable=False, comment="First business date on which this profile assignment is effective for the tenant."),
        sa.Column("valid_to", sa.Date(), nullable=True, comment="Last business date on which this profile assignment is effective; null means open-ended."),
        sa.Column("recorded_at_utc", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False, comment="UTC timestamp at which this assignment version was recorded."),
        sa.Column("supersedes_assignment_id", sa.UUID(), nullable=True, comment="Prior assignment version superseded by this row when profile classification is corrected or renewed."),
        sa.CheckConstraint("assignment_source IN ('ONBOARDING', 'CONTRACT', 'MANUAL', 'MIGRATION')", name="ck_tenant_profile_assignment_source"),
        sa.CheckConstraint("status IN ('PROPOSED', 'ACTIVE', 'REJECTED', 'RETIRED', 'SUPERSEDED')", name="ck_tenant_profile_assignment_status"),
        sa.CheckConstraint("valid_to IS NULL OR valid_to >= valid_from", name="ck_tenant_profile_assignment_valid_period"),
        sa.ForeignKeyConstraint(["tenant_id"], ["ten.tenant.tenant_id"]),
        sa.ForeignKeyConstraint(["operating_profile_id"], ["ten.operating_profile.operating_profile_id"]),
        sa.ForeignKeyConstraint(["approved_by_user_account_id"], ["secm.user_account.user_account_id"]),
        sa.ForeignKeyConstraint(["supersedes_assignment_id"], ["ten.tenant_operating_profile_assignment.tenant_operating_profile_assignment_id"]),
        sa.PrimaryKeyConstraint("tenant_operating_profile_assignment_id"),
        sa.UniqueConstraint("tenant_id", "operating_profile_id", "valid_from", name="uq_tenant_operating_profile_assignment_business_key"),
        schema="ten",
    )
    op.create_table(
        "operating_profile_module_recommendation",
        sa.Column("operating_profile_module_recommendation_id", sa.UUID(), server_default=sa.text("uuidv7()"), nullable=False, comment="Immutable UUIDv7 identifier for one profile-to-module onboarding recommendation."),
        sa.Column("operating_profile_id", sa.UUID(), nullable=False, comment="Operating profile for which this module is recommended during tenant onboarding."),
        sa.Column("platform_module_id", sa.UUID(), nullable=False, comment="Platform module recommended for the associated operating profile."),
        sa.Column("recommendation_strength", sa.String(length=30), server_default=sa.text("'STANDARD'"), nullable=False, comment="Onboarding recommendation strength: CORE, STANDARD, OPTIONAL, or NOT_APPLICABLE; it never grants access."),
        sa.Column("rationale", sa.Text(), nullable=True, comment="Business rationale explaining why the module is recommended for the operating profile."),
        sa.Column("status", sa.String(length=30), server_default=sa.text("'ACTIVE'"), nullable=False, comment="Lifecycle status of this profile-to-module onboarding recommendation."),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False, comment="UTC timestamp at which the onboarding recommendation was created."),
        sa.CheckConstraint("recommendation_strength IN ('CORE', 'STANDARD', 'OPTIONAL', 'NOT_APPLICABLE')", name="ck_profile_module_recommendation_strength"),
        sa.ForeignKeyConstraint(["operating_profile_id"], ["ten.operating_profile.operating_profile_id"]),
        sa.ForeignKeyConstraint(["platform_module_id"], ["ten.platform_module.platform_module_id"]),
        sa.PrimaryKeyConstraint("operating_profile_module_recommendation_id"),
        sa.UniqueConstraint("operating_profile_id", "platform_module_id", name="uq_operating_profile_module_recommendation"),
        schema="ten",
    )
    op.create_table(
        "tenant_module_entitlement",
        sa.Column("tenant_module_entitlement_id", sa.UUID(), server_default=sa.text("uuidv7()"), nullable=False, comment="Immutable UUIDv7 identifier for one effective-dated tenant platform-module entitlement version."),
        sa.Column("tenant_id", sa.UUID(), nullable=False, comment="Tenant receiving, suspending, or revoking access to the platform module."),
        sa.Column("platform_module_id", sa.UUID(), nullable=False, comment="Governed platform module to which this entitlement lifecycle record applies."),
        sa.Column("entitlement_state", sa.String(length=30), nullable=False, comment="Entitlement state: GRANTED permits capability resolution; SUSPENDED and REVOKED do not."),
        sa.Column("entitlement_source", sa.String(length=30), nullable=False, comment="Source of the entitlement decision, such as CONTRACT, TRIAL, MANUAL, or MIGRATION."),
        sa.Column("external_contract_reference", sa.String(length=250), nullable=True, comment="Optional commercial contract, order, or subscription reference evidencing the module entitlement decision."),
        sa.Column("approved_by_user_account_id", sa.UUID(), nullable=True, comment="Authenticated account that approved the entitlement lifecycle decision."),
        sa.Column("approved_at_utc", sa.DateTime(timezone=True), nullable=True, comment="UTC timestamp at which the module entitlement lifecycle decision was approved."),
        sa.Column("valid_from", sa.Date(), nullable=False, comment="First business date on which this entitlement state applies to the tenant."),
        sa.Column("valid_to", sa.Date(), nullable=True, comment="Last business date on which this entitlement state applies; null means open-ended."),
        sa.Column("recorded_at_utc", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False, comment="UTC timestamp at which this entitlement version was recorded."),
        sa.Column("supersedes_entitlement_id", sa.UUID(), nullable=True, comment="Prior module-entitlement version superseded by this lifecycle record."),
        sa.CheckConstraint("entitlement_state IN ('GRANTED', 'SUSPENDED', 'REVOKED')", name="ck_tenant_module_entitlement_state"),
        sa.CheckConstraint("entitlement_source IN ('CONTRACT', 'TRIAL', 'MANUAL', 'MIGRATION')", name="ck_tenant_module_entitlement_source"),
        sa.CheckConstraint("valid_to IS NULL OR valid_to >= valid_from", name="ck_tenant_module_entitlement_valid_period"),
        sa.ForeignKeyConstraint(["tenant_id"], ["ten.tenant.tenant_id"]),
        sa.ForeignKeyConstraint(["platform_module_id"], ["ten.platform_module.platform_module_id"]),
        sa.ForeignKeyConstraint(["approved_by_user_account_id"], ["secm.user_account.user_account_id"]),
        sa.ForeignKeyConstraint(["supersedes_entitlement_id"], ["ten.tenant_module_entitlement.tenant_module_entitlement_id"]),
        sa.PrimaryKeyConstraint("tenant_module_entitlement_id"),
        sa.UniqueConstraint("tenant_id", "platform_module_id", "valid_from", name="uq_tenant_module_entitlement_business_key"),
        schema="ten",
    )
    op.create_index("ix_tenant_operating_profile_assignment_lookup", "tenant_operating_profile_assignment", ["tenant_id", "operating_profile_id", "status", "valid_from", "valid_to"], schema="ten")
    op.create_index("ix_tenant_module_entitlement_resolve", "tenant_module_entitlement", ["tenant_id", "platform_module_id", "entitlement_state", "valid_from", "valid_to"], schema="ten")
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    op.execute("""
        ALTER TABLE ten.tenant_operating_profile_assignment
        ADD CONSTRAINT ex_tenant_operating_profile_assignment_effective_period
        EXCLUDE USING gist (
            tenant_id WITH =,
            operating_profile_id WITH =,
            daterange(valid_from, COALESCE(valid_to + 1, 'infinity'::date), '[)') WITH &&
        ) WHERE (status = 'ACTIVE')
    """)
    op.execute("""
        ALTER TABLE ten.tenant_module_entitlement
        ADD CONSTRAINT ex_tenant_module_entitlement_effective_period
        EXCLUDE USING gist (
            tenant_id WITH =,
            platform_module_id WITH =,
            daterange(valid_from, COALESCE(valid_to + 1, 'infinity'::date), '[)') WITH &&
        ) WHERE (entitlement_state IN ('GRANTED', 'SUSPENDED'))
    """)


def downgrade() -> None:
    """Remove tenant capability catalogues and assignments."""

    op.drop_index("ix_tenant_module_entitlement_resolve", table_name="tenant_module_entitlement", schema="ten")
    op.drop_index("ix_tenant_operating_profile_assignment_lookup", table_name="tenant_operating_profile_assignment", schema="ten")
    op.drop_table("tenant_module_entitlement", schema="ten")
    op.drop_table("operating_profile_module_recommendation", schema="ten")
    op.drop_table("tenant_operating_profile_assignment", schema="ten")
    op.drop_table("platform_module", schema="ten")
    op.drop_table("operating_profile", schema="ten")
