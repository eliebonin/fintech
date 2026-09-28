"""Add tenant-scoped generic valuation marks with immutable input lineage."""

from alembic import op
import sqlalchemy as sa


revision = "20260901_10"
down_revision = "20260901_09"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "valuation_mark",
        sa.Column("valuation_mark_id", sa.UUID(), primary_key=True, server_default=sa.text("uuidv7()"), comment="Immutable UUIDv7 identifier for one tenant-scoped valuation conclusion."),
        sa.Column("tenant_id", sa.UUID(), sa.ForeignKey("ten.tenant.tenant_id"), nullable=False, comment="Tenant owning the valuation mark and its confidential methodology/context."),
        sa.Column("subject_reference_node_id", sa.UUID(), sa.ForeignKey("secm.financial_reference_node.reference_node_id"), nullable=False, comment="Instrument, listing, fund, position subject or other reference node being marked."),
        sa.Column("strategy_id", sa.UUID(), sa.ForeignKey("trd.strategy.strategy_id"), nullable=True, comment="Optional strategy or portfolio context for the mark."),
        sa.Column("position_snapshot_line_id", sa.UUID(), sa.ForeignKey("trd.position_snapshot_line.position_snapshot_line_id"), nullable=True, comment="Optional frozen position line to which the mark applies."),
        sa.Column("trade_id", sa.UUID(), sa.ForeignKey("trd.trade.trade_id"), nullable=True, comment="Optional booked trade to which the mark applies."),
        sa.Column("valuation_date", sa.Date(), nullable=False, comment="Business valuation date of the mark."),
        sa.Column("valuation_cut_id", sa.UUID(), sa.ForeignKey("md.valuation_cut.valuation_cut_id"), nullable=False, comment="Named valuation cut used for the mark."),
        sa.Column("market_data_as_of_utc", sa.DateTime(timezone=True), nullable=False, comment="Historic information cut after which observations were ineligible for this mark."),
        sa.Column("mark_type", sa.String(length=50), nullable=False, comment="Mark classification such as FAIR_VALUE, MODEL_PRICE, ADMINISTRATOR_MARK, CLEAN_PRICE, DIRTY_PRICE, or YIELD."),
        sa.Column("valuation_method", sa.String(length=100), nullable=False, comment="Controlled or versioned method used to reach the mark."),
        sa.Column("value", sa.Numeric(30, 12), nullable=False, comment="Valuation result in the stated currency and price/value convention."),
        sa.Column("currency_id", sa.UUID(), sa.ForeignKey("secm.currency.currency_id"), nullable=False, comment="Currency of the valuation result."),
        sa.Column("market_data_resolution_snapshot_id", sa.UUID(), sa.ForeignKey("md.market_data_resolution_snapshot.market_data_resolution_snapshot_id"), nullable=True, comment="Immutable selected market-data input set supporting the mark when source data was used."),
        sa.Column("approved_override_id", sa.UUID(), nullable=True, comment="Tenant-approved override evidence identifier when the mark is not based on a market-data snapshot."),
        sa.Column("calculation_version", sa.String(length=100), nullable=False, comment="Version of the valuation implementation or model used to calculate the mark."),
        sa.Column("status", sa.String(length=30), nullable=False, server_default=sa.text("'DRAFT'"), comment="Review lifecycle such as DRAFT, REVIEWED, APPROVED, REJECTED, or SUPERSEDED."),
        sa.Column("created_by_user_account_id", sa.UUID(), sa.ForeignKey("secm.user_account.user_account_id"), nullable=False, comment="Authenticated account or service that created the mark."),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="UTC timestamp at which the mark was created."),
        schema="nav",
    )
    op.create_check_constraint("ck_valuation_mark_exactly_one_lineage", "valuation_mark", "(market_data_resolution_snapshot_id IS NOT NULL) <> (approved_override_id IS NOT NULL)", schema="nav")
    op.create_index("ix_valuation_mark_tenant_subject_date", "valuation_mark", ["tenant_id", "subject_reference_node_id", "valuation_date"], schema="nav")
    op.execute(
        """
        CREATE FUNCTION nav.prevent_valuation_mark_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'valuation marks are immutable; create a new mark instead';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_valuation_mark_immutable
        BEFORE UPDATE OR DELETE ON nav.valuation_mark
        FOR EACH ROW EXECUTE FUNCTION nav.prevent_valuation_mark_mutation()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_valuation_mark_immutable ON nav.valuation_mark")
    op.execute("DROP FUNCTION IF EXISTS nav.prevent_valuation_mark_mutation()")
    op.drop_index("ix_valuation_mark_tenant_subject_date", table_name="valuation_mark", schema="nav")
    op.drop_constraint("ck_valuation_mark_exactly_one_lineage", "valuation_mark", schema="nav", type_="check")
    op.drop_table("valuation_mark", schema="nav")
