"""Add immutable effective-dated canonical instrument and listing definitions."""

from alembic import op
import sqlalchemy as sa


revision = "20260901_07"
down_revision = "20260901_06"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "instrument_definition_version",
        sa.Column("instrument_definition_version_id", sa.UUID(), primary_key=True, server_default=sa.text("uuidv7()"), comment="Immutable UUIDv7 identifier for one approved effective-dated canonical instrument definition version."),
        sa.Column("instrument_node_id", sa.UUID(), sa.ForeignKey("secm.instrument.instrument_node_id"), nullable=False, comment="Stable economic instrument identity whose canonical definition is versioned."),
        sa.Column("sequence_no", sa.Integer(), nullable=False, comment="Monotonically increasing definition version sequence for the instrument identity."),
        sa.Column("instrument_type_id", sa.UUID(), sa.ForeignKey("secm.instrument_type.instrument_type_id"), nullable=False, comment="Governed economic type in force for this instrument definition version."),
        sa.Column("asset_class", sa.String(length=40), nullable=False, comment="High-level asset class in force for this definition version."),
        sa.Column("issuer_organisation_id", sa.UUID(), sa.ForeignKey("secm.organisation.organisation_id"), nullable=True, comment="Issuer organisation in force for this definition version when applicable."),
        sa.Column("base_currency_id", sa.UUID(), sa.ForeignKey("secm.currency.currency_id"), nullable=True, comment="Base or denomination currency in force for this definition version."),
        sa.Column("effective_from", sa.Date(), nullable=False, comment="First business date on which this canonical definition version applies."),
        sa.Column("effective_to", sa.Date(), nullable=True, comment="Last business date on which this canonical definition version applies."),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.text("true"), comment="Whether this is the current approved operational definition version for the instrument identity."),
        sa.Column("status", sa.String(length=30), nullable=False, server_default=sa.text("'DRAFT'"), comment="Version approval status such as DRAFT, APPROVED, SUPERSEDED, or RETIRED."),
        sa.Column("source_payload_id", sa.UUID(), sa.ForeignKey("ing.source_payload.source_payload_id"), nullable=True, comment="Source evidence supporting this canonical definition version."),
        sa.Column("approved_by_user_account_id", sa.UUID(), sa.ForeignKey("secm.user_account.user_account_id"), nullable=True, comment="Steward account approving this definition version."),
        sa.Column("approved_at_utc", sa.DateTime(timezone=True), nullable=True, comment="UTC timestamp at which this definition version was approved."),
        sa.UniqueConstraint("instrument_node_id", "sequence_no", name="uq_instrument_definition_version_sequence"),
        schema="secm",
    )
    op.create_table(
        "listing_definition_version",
        sa.Column("listing_definition_version_id", sa.UUID(), primary_key=True, server_default=sa.text("uuidv7()"), comment="Immutable UUIDv7 identifier for one approved effective-dated canonical listing definition version."),
        sa.Column("listing_node_id", sa.UUID(), sa.ForeignKey("secm.listing.listing_node_id"), nullable=False, comment="Stable venue-listing identity whose canonical definition is versioned."),
        sa.Column("sequence_no", sa.Integer(), nullable=False, comment="Monotonically increasing definition version sequence for the listing identity."),
        sa.Column("market_venue_id", sa.UUID(), sa.ForeignKey("secm.market_venue.market_venue_id"), nullable=False, comment="Venue in force for this listing definition version."),
        sa.Column("trading_currency_id", sa.UUID(), sa.ForeignKey("secm.currency.currency_id"), nullable=False, comment="Trading currency in force for this listing definition version."),
        sa.Column("trading_symbol", sa.String(length=100), nullable=True, comment="Venue symbol in force for this listing definition version."),
        sa.Column("quote_factor", sa.Numeric(20, 8), nullable=False, server_default=sa.text("1"), comment="Quotation convention factor in force for this listing definition version."),
        sa.Column("unit_multiplier", sa.Numeric(20, 8), nullable=False, server_default=sa.text("1"), comment="Economic units represented by one traded unit in this listing definition version."),
        sa.Column("effective_from", sa.Date(), nullable=False, comment="First business date on which this canonical listing definition version applies."),
        sa.Column("effective_to", sa.Date(), nullable=True, comment="Last business date on which this canonical listing definition version applies."),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.text("true"), comment="Whether this is the current approved operational definition version for the listing identity."),
        sa.Column("status", sa.String(length=30), nullable=False, server_default=sa.text("'DRAFT'"), comment="Version approval status such as DRAFT, APPROVED, SUPERSEDED, or RETIRED."),
        sa.Column("source_payload_id", sa.UUID(), sa.ForeignKey("ing.source_payload.source_payload_id"), nullable=True, comment="Source evidence supporting this canonical listing definition version."),
        sa.Column("approved_by_user_account_id", sa.UUID(), sa.ForeignKey("secm.user_account.user_account_id"), nullable=True, comment="Steward account approving this listing definition version."),
        sa.Column("approved_at_utc", sa.DateTime(timezone=True), nullable=True, comment="UTC timestamp at which this listing definition version was approved."),
        sa.UniqueConstraint("listing_node_id", "sequence_no", name="uq_listing_definition_version_sequence"),
        schema="secm",
    )
    op.create_index("uq_instrument_definition_version_current", "instrument_definition_version", ["instrument_node_id"], unique=True, schema="secm", postgresql_where=sa.text("status = 'APPROVED' AND is_current"))
    op.create_index("uq_listing_definition_version_current", "listing_definition_version", ["listing_node_id"], unique=True, schema="secm", postgresql_where=sa.text("status = 'APPROVED' AND is_current"))
    op.execute(
        """
        CREATE FUNCTION secm.prevent_definition_version_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'canonical definition versions are immutable; append a new version instead';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_instrument_definition_version_immutable
        BEFORE UPDATE OR DELETE ON secm.instrument_definition_version
        FOR EACH ROW EXECUTE FUNCTION secm.prevent_definition_version_mutation()
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_listing_definition_version_immutable
        BEFORE UPDATE OR DELETE ON secm.listing_definition_version
        FOR EACH ROW EXECUTE FUNCTION secm.prevent_definition_version_mutation()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_listing_definition_version_immutable ON secm.listing_definition_version")
    op.execute("DROP TRIGGER IF EXISTS trg_instrument_definition_version_immutable ON secm.instrument_definition_version")
    op.execute("DROP FUNCTION IF EXISTS secm.prevent_definition_version_mutation()")
    op.drop_index("uq_listing_definition_version_current", table_name="listing_definition_version", schema="secm")
    op.drop_index("uq_instrument_definition_version_current", table_name="instrument_definition_version", schema="secm")
    op.drop_table("listing_definition_version", schema="secm")
    op.drop_table("instrument_definition_version", schema="secm")
