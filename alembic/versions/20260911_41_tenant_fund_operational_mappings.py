"""Add tenant-scoped fund administrator and custodian operational mappings.

Revision ID: 20260911_41
Revises: 20260910_40
"""

from alembic import op
import sqlalchemy as sa


revision = "20260911_41"
down_revision = "20260910_40"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create tenant feed profiles and effective-dated fund/share-class mappings."""

    op.execute('CREATE SCHEMA IF NOT EXISTS "cfg"')

    op.create_table(
        "external_data_mapping_profile",
        sa.Column("external_data_mapping_profile_id", sa.UUID(), server_default=sa.text("uuidv7()"), nullable=False, comment="Immutable UUIDv7 identifier for one tenant-owned external operational-data mapping profile."),
        sa.Column("tenant_id", sa.UUID(), nullable=False, comment="Tenant that owns the operational feed configuration and its mappings."),
        sa.Column("provider_organisation_id", sa.UUID(), nullable=False, comment="Canonical organisation acting as administrator, agent, custodian, bank, or other operational-data provider."),
        sa.Column("integration_source_system_id", sa.UUID(), nullable=False, comment="Integration source system or endpoint from which this profile's files or messages are received."),
        sa.Column("dataset_id", sa.UUID(), nullable=True, comment="Optional governed dataset representing the provider feed when it is catalogued as a dataset; null for operational feeds without a dataset contract."),
        sa.Column("profile_code", sa.String(length=100), nullable=False, comment="Stable tenant-local code for the feed interpretation, such as ABC_DAILY_VALUATION or ABC_DAILY_ACCOUNTING."),
        sa.Column("display_name", sa.String(length=250), nullable=False, comment="Human-readable name of the tenant operational-data mapping profile."),
        sa.Column("operational_context", sa.String(length=40), nullable=False, comment="Governed purpose of the external identifiers, initially VALUATION or ACCOUNTING."),
        sa.Column("allowed_source_scope", sa.String(length=40), nullable=False, comment="Source-record scope accepted by the profile: FUND, FUND_SHARE_CLASS, or BOTH."),
        sa.Column("normalization_mode", sa.String(length=40), server_default=sa.text("'EXACT'"), nullable=False, comment="Profile-controlled external-ID lookup normalisation: EXACT preserves value; TRIM_UPPER trims outer whitespace and uppercases it."),
        sa.Column("parser_contract_version", sa.String(length=100), nullable=True, comment="Version of the file, message, or parser contract interpreted by this profile."),
        sa.Column("status", sa.String(length=30), server_default=sa.text("'ACTIVE'"), nullable=False, comment="Lifecycle status of the profile: DRAFT, ACTIVE, SUSPENDED, RETIRED, or SUPERSEDED."),
        sa.Column("valid_from", sa.Date(), nullable=False, comment="First business date on which this profile may resolve operational source identifiers."),
        sa.Column("valid_to", sa.Date(), nullable=True, comment="Last business date on which this profile may resolve operational source identifiers; null means open-ended."),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False, comment="UTC timestamp at which this tenant operational-data mapping profile was created."),
        sa.Column("retired_at_utc", sa.DateTime(timezone=True), nullable=True, comment="UTC timestamp at which the profile was retired when no longer available for new processing."),
        sa.CheckConstraint("operational_context IN ('VALUATION', 'ACCOUNTING')", name="ck_cfg_mapping_profile_context"),
        sa.CheckConstraint("allowed_source_scope IN ('FUND', 'FUND_SHARE_CLASS', 'BOTH')", name="ck_cfg_mapping_profile_scope"),
        sa.CheckConstraint("normalization_mode IN ('EXACT', 'TRIM_UPPER')", name="ck_cfg_mapping_profile_normalization"),
        sa.CheckConstraint("valid_to IS NULL OR valid_to >= valid_from", name="ck_cfg_mapping_profile_valid_period"),
        sa.ForeignKeyConstraint(["tenant_id"], ["ten.tenant.tenant_id"]),
        sa.ForeignKeyConstraint(["provider_organisation_id"], ["secm.organisation.organisation_id"]),
        sa.ForeignKeyConstraint(["integration_source_system_id"], ["ing.integration_source_system.integration_source_system_id"]),
        sa.ForeignKeyConstraint(["dataset_id"], ["md.dataset.dataset_id"]),
        sa.PrimaryKeyConstraint("external_data_mapping_profile_id"),
        sa.UniqueConstraint("tenant_id", "profile_code", "valid_from", name="uq_cfg_external_data_mapping_profile_business_key"),
        schema="cfg",
    )
    op.create_table(
        "external_data_object_mapping",
        sa.Column("external_data_object_mapping_id", sa.UUID(), server_default=sa.text("uuidv7()"), nullable=False, comment="Immutable UUIDv7 identifier for one effective-dated tenant operational identifier mapping."),
        sa.Column("external_data_mapping_profile_id", sa.UUID(), nullable=False, comment="Tenant operational-data mapping profile that defines how this external identifier is interpreted."),
        sa.Column("source_object_scope", sa.String(length=40), nullable=False, comment="Scope represented by the external source record: FUND or FUND_SHARE_CLASS."),
        sa.Column("target_object_type", sa.String(length=40), nullable=False, comment="Canonical target type corresponding to target_object_id; must match source_object_scope in V1."),
        sa.Column("target_object_id", sa.UUID(), nullable=False, comment="Immutable UUID of the resolved canonical fund or fund share-class instrument; validated by a PostgreSQL trigger."),
        sa.Column("external_id_raw", sa.String(length=500), nullable=False, comment="External identifier exactly as received in the provider file, message, or report; immutable evidence and never normalised in place."),
        sa.Column("external_id_normalized", sa.String(length=500), nullable=False, comment="Profile-normalised lookup form of external_id_raw used for deterministic matching while raw evidence remains preserved."),
        sa.Column("mapping_role", sa.String(length=30), server_default=sa.text("'PRIMARY'"), nullable=False, comment="Business role of the identifier mapping, initially PRIMARY, ALIAS, LEGACY, or SOURCE_REFERENCE."),
        sa.Column("mapping_method", sa.String(length=30), nullable=False, comment="How the mapping was established, such as MANUAL, CLIENT_CONFIRMED, PROVIDER_MATCH, or RULE."),
        sa.Column("status", sa.String(length=30), server_default=sa.text("'PROPOSED'"), nullable=False, comment="Lifecycle and approval status: PROPOSED, APPROVED, REJECTED, RETIRED, or SUPERSEDED; only APPROVED mappings resolve production input."),
        sa.Column("confidence", sa.Numeric(precision=5, scale=4), nullable=True, comment="Optional confidence score from zero to one for a proposed or automatically matched mapping."),
        sa.Column("approved_by_user_account_id", sa.UUID(), nullable=True, comment="Authenticated internal user or service account that approved this mapping for operational resolution."),
        sa.Column("approved_at_utc", sa.DateTime(timezone=True), nullable=True, comment="UTC timestamp at which this mapping became approved for operational resolution."),
        sa.Column("valid_from", sa.Date(), nullable=False, comment="First report business date for which this identifier mapping is valid."),
        sa.Column("valid_to", sa.Date(), nullable=True, comment="Last report business date for which this identifier mapping is valid; null means open-ended."),
        sa.Column("recorded_at_utc", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False, comment="UTC timestamp at which this mapping version was recorded in tenant configuration."),
        sa.Column("source_payload_id", sa.UUID(), nullable=True, comment="Inbound source payload that evidenced or proposed the mapping when applicable."),
        sa.Column("supersedes_mapping_id", sa.UUID(), nullable=True, comment="Prior tenant operational mapping superseded by this version when an identifier is reassigned or corrected."),
        sa.CheckConstraint("source_object_scope IN ('FUND', 'FUND_SHARE_CLASS')", name="ck_cfg_external_data_mapping_scope"),
        sa.CheckConstraint("target_object_type = source_object_scope", name="ck_cfg_external_data_mapping_target_scope"),
        sa.CheckConstraint("mapping_role IN ('PRIMARY', 'ALIAS', 'LEGACY', 'SOURCE_REFERENCE')", name="ck_cfg_external_data_mapping_role"),
        sa.CheckConstraint("status IN ('PROPOSED', 'APPROVED', 'REJECTED', 'RETIRED', 'SUPERSEDED')", name="ck_cfg_external_data_mapping_status"),
        sa.CheckConstraint("confidence IS NULL OR (confidence >= 0 AND confidence <= 1)", name="ck_cfg_external_data_mapping_confidence"),
        sa.CheckConstraint("valid_to IS NULL OR valid_to >= valid_from", name="ck_cfg_external_data_mapping_valid_period"),
        sa.ForeignKeyConstraint(["external_data_mapping_profile_id"], ["cfg.external_data_mapping_profile.external_data_mapping_profile_id"]),
        sa.ForeignKeyConstraint(["approved_by_user_account_id"], ["secm.user_account.user_account_id"]),
        sa.ForeignKeyConstraint(["source_payload_id"], ["ing.source_payload.source_payload_id"]),
        sa.ForeignKeyConstraint(["supersedes_mapping_id"], ["cfg.external_data_object_mapping.external_data_object_mapping_id"]),
        sa.PrimaryKeyConstraint("external_data_object_mapping_id"),
        schema="cfg",
    )
    op.create_index("ix_cfg_external_data_mapping_profile_lookup", "external_data_mapping_profile", ["tenant_id", "provider_organisation_id", "operational_context", "valid_from", "valid_to"], schema="cfg")
    op.create_index("ix_cfg_external_data_object_mapping_resolve", "external_data_object_mapping", ["external_data_mapping_profile_id", "source_object_scope", "external_id_normalized", "valid_from", "valid_to"], schema="cfg")
    op.create_index("ix_cfg_external_data_object_mapping_target", "external_data_object_mapping", ["target_object_type", "target_object_id"], schema="cfg")

    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    op.execute(
        """
        ALTER TABLE cfg.external_data_object_mapping
        ADD CONSTRAINT ex_cfg_external_data_object_mapping_effective_period
        EXCLUDE USING gist (
            external_data_mapping_profile_id WITH =,
            source_object_scope WITH =,
            external_id_normalized WITH =,
            daterange(valid_from, COALESCE(valid_to + 1, 'infinity'::date), '[)') WITH &&
        ) WHERE (status = 'APPROVED')
        """
    )
    op.execute(
        """
        CREATE FUNCTION cfg.validate_external_data_mapping_target() RETURNS trigger AS $$
        BEGIN
            IF NEW.target_object_type = 'FUND' THEN
                IF NOT EXISTS (SELECT 1 FROM secm.fund WHERE fund_reference_node_id = NEW.target_object_id) THEN
                    RAISE EXCEPTION 'operational mapping target % is not a fund', NEW.target_object_id;
                END IF;
            ELSIF NEW.target_object_type = 'FUND_SHARE_CLASS' THEN
                IF NOT EXISTS (SELECT 1 FROM secm.instrument WHERE instrument_node_id = NEW.target_object_id) THEN
                    RAISE EXCEPTION 'operational mapping target % is not a fund share-class instrument', NEW.target_object_id;
                END IF;
            ELSE
                RAISE EXCEPTION 'unsupported operational mapping target type %', NEW.target_object_type;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_validate_external_data_mapping_target
        BEFORE INSERT OR UPDATE OF target_object_type, target_object_id
        ON cfg.external_data_object_mapping
        FOR EACH ROW EXECUTE FUNCTION cfg.validate_external_data_mapping_target()
        """
    )


def downgrade() -> None:
    """Remove tenant operational mapping configuration without touching shared mappings."""

    op.execute("DROP TRIGGER IF EXISTS trg_validate_external_data_mapping_target ON cfg.external_data_object_mapping")
    op.execute("DROP FUNCTION IF EXISTS cfg.validate_external_data_mapping_target()")
    op.drop_index("ix_cfg_external_data_object_mapping_target", table_name="external_data_object_mapping", schema="cfg")
    op.drop_index("ix_cfg_external_data_object_mapping_resolve", table_name="external_data_object_mapping", schema="cfg")
    op.drop_index("ix_cfg_external_data_mapping_profile_lookup", table_name="external_data_mapping_profile", schema="cfg")
    op.drop_table("external_data_object_mapping", schema="cfg")
    op.drop_table("external_data_mapping_profile", schema="cfg")
    op.execute('DROP SCHEMA IF EXISTS "cfg"')
