"""Add immutable market-data source vintages and observation lineage."""

from alembic import op
import sqlalchemy as sa


revision = "20260901_11"
down_revision = "20260901_10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "market_data_vintage",
        sa.Column("market_data_vintage_id", sa.UUID(), primary_key=True, server_default=sa.text("uuidv7()"), comment="Immutable UUIDv7 identifier for one provider source vintage or extract version."),
        sa.Column("dataset_id", sa.UUID(), sa.ForeignKey("md.dataset.dataset_id"), nullable=False, comment="Governed dataset from which this source vintage was delivered."),
        sa.Column("data_provider_id", sa.UUID(), sa.ForeignKey("md.data_provider.data_provider_id"), nullable=False, comment="Provider responsible for publishing this source vintage."),
        sa.Column("source_vintage_key", sa.String(length=250), nullable=True, comment="Provider revision, file, batch, run, or other stable source-vintage identifier when supplied."),
        sa.Column("source_published_at_utc", sa.DateTime(timezone=True), nullable=True, comment="UTC time at which the provider published this vintage; null only when the provider supplies no publication timestamp."),
        sa.Column("received_at_utc", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="UTC time at which Fortem received or accepted this source vintage."),
        sa.Column("value_basis", sa.String(length=40), nullable=False, server_default=sa.text("'RAW'"), comment="Lineage basis of values in this vintage such as RAW, VENDOR_ADJUSTED, or RESTATED."),
        sa.Column("vintage_status", sa.String(length=30), nullable=False, server_default=sa.text("'CURRENT'"), comment="Lifecycle state such as CURRENT, CORRECTED, RESTATED, SUPERSEDED, or REJECTED."),
        sa.Column("content_hash", sa.String(length=128), nullable=True, comment="Hash of the retained source extract or normalized vintage content for duplicate and integrity detection."),
        sa.Column("source_payload_id", sa.UUID(), sa.ForeignKey("ing.source_payload.source_payload_id"), nullable=True, comment="Retained raw payload evidencing this source vintage when available."),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="UTC time at which the source vintage record was created."),
        sa.UniqueConstraint("dataset_id", "source_vintage_key", name="uq_market_data_vintage_dataset_key"),
        schema="md",
    )
    op.add_column(
        "market_data_observation",
        sa.Column("market_data_vintage_id", sa.UUID(), sa.ForeignKey("md.market_data_vintage.market_data_vintage_id"), nullable=True, comment="Provider source vintage containing this observation; nullable only for legacy rows pending lineage backfill."),
        schema="md",
    )
    op.add_column(
        "market_data_observation",
        sa.Column("source_published_at_utc", sa.DateTime(timezone=True), nullable=True, comment="UTC publication timestamp carried by the source for this observation or its vintage."),
        schema="md",
    )
    op.create_index(
        "ix_market_data_vintage_dataset_published",
        "market_data_vintage",
        ["dataset_id", "source_published_at_utc", "received_at_utc"],
        schema="md",
    )
    op.create_index(
        "ix_market_data_observation_vintage",
        "market_data_observation",
        ["market_data_vintage_id"],
        schema="md",
    )
    op.execute(
        """
        CREATE FUNCTION md.prevent_market_data_vintage_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'market-data vintages are immutable; ingest a new vintage instead';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_market_data_vintage_immutable
        BEFORE UPDATE OR DELETE ON md.market_data_vintage
        FOR EACH ROW EXECUTE FUNCTION md.prevent_market_data_vintage_mutation()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_market_data_vintage_immutable ON md.market_data_vintage")
    op.execute("DROP FUNCTION IF EXISTS md.prevent_market_data_vintage_mutation()")
    op.drop_index("ix_market_data_observation_vintage", table_name="market_data_observation", schema="md")
    op.drop_index("ix_market_data_vintage_dataset_published", table_name="market_data_vintage", schema="md")
    op.drop_column("market_data_observation", "source_published_at_utc", schema="md")
    op.drop_column("market_data_observation", "market_data_vintage_id", schema="md")
    op.drop_table("market_data_vintage", schema="md")
