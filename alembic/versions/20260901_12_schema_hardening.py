"""Harden tenant ownership, effective definitions, observations, and audit links."""

from alembic import op
import sqlalchemy as sa


revision = "20260901_12"
down_revision = "20260901_11"
branch_labels = None
depends_on = None


ZERO_UUID = "00000000-0000-0000-0000-000000000000"


def upgrade() -> None:
    op.create_table(
        "tenant_user_account",
        sa.Column("tenant_user_account_id", sa.UUID(), primary_key=True, server_default=sa.text("uuidv7()"), comment="Immutable UUIDv7 identifier for one user's membership in a tenant."),
        sa.Column("tenant_id", sa.UUID(), sa.ForeignKey("ten.tenant.tenant_id"), nullable=False, comment="Tenant whose data and operations the user may access."),
        sa.Column("user_account_id", sa.UUID(), sa.ForeignKey("secm.user_account.user_account_id"), nullable=False, comment="Application user account granted access to the tenant."),
        sa.Column("membership_role", sa.String(length=40), nullable=False, comment="Tenant role such as ADMIN, OPERATIONS, VALUATION, or READ_ONLY."),
        sa.Column("status", sa.String(length=30), nullable=False, server_default=sa.text("'ACTIVE'"), comment="Membership lifecycle status such as ACTIVE, SUSPENDED, or REVOKED."),
        sa.Column("valid_from", sa.Date(), nullable=False, comment="First business date on which the membership is effective."),
        sa.Column("valid_to", sa.Date(), nullable=True, comment="Last business date on which the membership is effective."),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="UTC timestamp at which the membership was created."),
        sa.UniqueConstraint("tenant_id", "user_account_id", "valid_from", name="uq_tenant_user_account_membership"),
        sa.CheckConstraint("valid_to IS NULL OR valid_to >= valid_from", name="ck_tenant_user_account_valid_period"),
        schema="ten",
    )
    op.create_index("ix_tenant_user_account_lookup", "tenant_user_account", ["tenant_id", "user_account_id", "status", "valid_from", "valid_to"], schema="ten")

    op.add_column(
        "external_object_mapping",
        sa.Column("tenant_id", sa.UUID(), sa.ForeignKey("ten.tenant.tenant_id"), nullable=True, comment="Tenant owning this mapping when it is a tenant-local alias; null means the mapping is shared canonical data."),
        schema="ing",
    )
    op.execute(
        """
        UPDATE ing.external_object_mapping m
        SET tenant_id = s.tenant_id
        FROM ing.external_id_namespace n
        JOIN ing.integration_source_system s
          ON s.integration_source_system_id = n.integration_source_system_id
        WHERE m.external_id_namespace_id = n.external_id_namespace_id
          AND m.tenant_id IS NULL
          AND s.tenant_id IS NOT NULL
        """
    )
    op.drop_constraint("uq_external_object_mapping_business_key", "external_object_mapping", schema="ing", type_="unique")
    op.create_unique_constraint(
        "uq_external_object_mapping_business_key",
        "external_object_mapping",
        ["external_id_namespace_id", "external_object_type", "external_id_value", "context_market_venue_id", "tenant_id", "valid_from"],
        schema="ing",
    )
    op.execute("ALTER TABLE ing.external_object_mapping DROP CONSTRAINT IF EXISTS ex_external_object_mapping_effective_period")
    op.execute(
        f"""
        ALTER TABLE ing.external_object_mapping
        ADD CONSTRAINT ex_external_object_mapping_effective_period
        EXCLUDE USING gist (
            external_id_namespace_id WITH =,
            external_object_type WITH =,
            external_id_value WITH =,
            COALESCE(context_market_venue_id, '{ZERO_UUID}'::uuid) WITH =,
            COALESCE(tenant_id, '{ZERO_UUID}'::uuid) WITH =,
            daterange(valid_from, COALESCE(valid_to + 1, 'infinity'::date), '[)') WITH &&
        ) WHERE (status IN ('PROPOSED', 'VERIFIED'))
        """
    )
    op.create_index("ix_external_object_mapping_tenant_lookup", "external_object_mapping", ["tenant_id", "external_id_namespace_id", "external_id_value", "valid_from", "valid_to"], schema="ing")

    op.add_column(
        "market_data_observation",
        sa.Column("source_observation_key", sa.String(length=250), nullable=True, comment="Stable source-provided observation key used to make replayed ingestion idempotent within a series and dataset."),
        schema="md",
    )
    op.create_index(
        "uq_market_data_observation_source_key",
        "market_data_observation",
        ["market_data_series_id", "dataset_id", sa.text(f"COALESCE(market_data_vintage_id, '{ZERO_UUID}'::uuid)"), "source_observation_key"],
        unique=True,
        schema="md",
        postgresql_where=sa.text("source_observation_key IS NOT NULL"),
    )

    op.create_table(
        "market_data_series_dimension",
        sa.Column("market_data_series_dimension_id", sa.UUID(), primary_key=True, server_default=sa.text("uuidv7()"), comment="Immutable UUIDv7 identifier for one descriptive dimension of a market-data series."),
        sa.Column("market_data_series_id", sa.UUID(), sa.ForeignKey("md.market_data_series.market_data_series_id"), nullable=False, comment="Market-data series whose precise observable definition is being described."),
        sa.Column("dimension_code", sa.String(length=50), nullable=False, comment="Controlled dimension name such as TENOR, STRIKE, DELTA, QUOTE_SIDE, FIXING, SESSION, or SETTLEMENT."),
        sa.Column("dimension_value", sa.String(length=250), nullable=False, comment="Dimension value in canonical text form, for example 1M, ATM, BID, or LONDON_CLOSE."),
        sa.Column("numeric_value", sa.Numeric(30, 12), nullable=True, comment="Optional numeric representation of the dimension value when calculations need it."),
        sa.Column("unit_code", sa.String(length=30), nullable=True, comment="Optional unit for numeric_value, such as MONTHS, PERCENT, POINTS, or BASIS_POINTS."),
        sa.UniqueConstraint("market_data_series_id", "dimension_code", "dimension_value", name="uq_market_data_series_dimension"),
        schema="md",
    )
    op.create_index("ix_market_data_series_dimension_lookup", "market_data_series_dimension", ["dimension_code", "dimension_value", "market_data_series_id"], schema="md")

    op.add_column(
        "trade",
        sa.Column("locked_ytm", sa.Numeric(20, 12), nullable=True, comment="Yield-to-maturity locked at booking when supplied by the legacy trade workflow; scale is governed by the declared trade convention."),
        schema="trd",
    )
    op.create_index(
        "uq_trade_external_reference_source_value",
        "trade_external_reference",
        ["source_system_id", "reference_type", "reference_value"],
        unique=True,
        schema="trd",
        postgresql_where=sa.text("source_system_id IS NOT NULL"),
    )
    op.execute(
        f"""
        CREATE UNIQUE INDEX uq_cash_balance_snapshot_source
        ON trd.cash_balance (
            strategy_id,
            COALESCE(cash_account_id, '{ZERO_UUID}'::uuid),
            currency_id,
            balance_as_of_datetime_utc,
            balance_type,
            COALESCE(source_system_id, '')
        )
        """
    )

    op.add_column(
        "nav_valuation_line",
        sa.Column("price_input_snapshot_item_id", sa.UUID(), sa.ForeignKey("nav.nav_input_snapshot_item.nav_input_snapshot_item_id"), nullable=True, comment="Frozen NAV input item supplying the instrument or cash price used by this line."),
        schema="nav",
    )
    op.add_column(
        "nav_valuation_line",
        sa.Column("fx_input_snapshot_item_id", sa.UUID(), sa.ForeignKey("nav.nav_input_snapshot_item.nav_input_snapshot_item_id"), nullable=True, comment="Frozen NAV input item supplying the FX rate used by this line."),
        schema="nav",
    )

    op.create_check_constraint(
        "ck_instrument_definition_version_valid_period",
        "instrument_definition_version",
        "effective_to IS NULL OR effective_to >= effective_from",
        schema="secm",
    )
    op.create_check_constraint(
        "ck_listing_definition_version_valid_period",
        "listing_definition_version",
        "effective_to IS NULL OR effective_to >= effective_from",
        schema="secm",
    )
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    op.execute(
        """
        ALTER TABLE secm.instrument_definition_version
        ADD CONSTRAINT ex_instrument_definition_version_effective_period
        EXCLUDE USING gist (
            instrument_node_id WITH =,
            daterange(effective_from, COALESCE(effective_to + 1, 'infinity'::date), '[)') WITH &&
        ) WHERE (status = 'APPROVED')
        """
    )
    op.execute(
        """
        ALTER TABLE secm.listing_definition_version
        ADD CONSTRAINT ex_listing_definition_version_effective_period
        EXCLUDE USING gist (
            listing_node_id WITH =,
            daterange(effective_from, COALESCE(effective_to + 1, 'infinity'::date), '[)') WITH &&
        ) WHERE (status = 'APPROVED')
        """
    )

    # Legacy base rows predate version backfill. Use a conservative open-ended
    # compatibility start date; subsequent approved versions carry real dates.
    op.execute(
        """
        INSERT INTO secm.instrument_definition_version (
            instrument_node_id, sequence_no, instrument_type_id, asset_class,
            issuer_organisation_id, base_currency_id, effective_from,
            effective_to, is_current, status
        )
        SELECT i.instrument_node_id, i.sequence_no, i.instrument_type_id,
               i.asset_class, i.issuer_organisation_id, i.base_currency_id,
               COALESCE(i.effective_from, DATE '1900-01-01'), i.effective_to,
               TRUE, 'APPROVED'
        FROM secm.instrument i
        WHERE NOT EXISTS (
            SELECT 1 FROM secm.instrument_definition_version v
            WHERE v.instrument_node_id = i.instrument_node_id
        )
        """
    )
    op.execute(
        """
        INSERT INTO secm.listing_definition_version (
            listing_node_id, sequence_no, market_venue_id,
            trading_currency_id, trading_symbol, quote_factor, unit_multiplier,
            effective_from, effective_to, is_current, status
        )
        SELECT l.listing_node_id, 1, l.market_venue_id,
               l.trading_currency_id, l.trading_symbol, l.quote_factor,
               l.unit_multiplier, COALESCE(l.effective_from, DATE '1900-01-01'),
               l.effective_to, TRUE, 'APPROVED'
        FROM secm.listing l
        WHERE NOT EXISTS (
            SELECT 1 FROM secm.listing_definition_version v
            WHERE v.listing_node_id = l.listing_node_id
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS trd.uq_cash_balance_snapshot_source")
    op.drop_column("nav_valuation_line", "fx_input_snapshot_item_id", schema="nav")
    op.drop_column("nav_valuation_line", "price_input_snapshot_item_id", schema="nav")
    op.drop_index("uq_trade_external_reference_source_value", table_name="trade_external_reference", schema="trd")
    op.drop_column("trade", "locked_ytm", schema="trd")
    op.drop_index("ix_market_data_series_dimension_lookup", table_name="market_data_series_dimension", schema="md")
    op.drop_table("market_data_series_dimension", schema="md")
    op.drop_index("uq_market_data_observation_source_key", table_name="market_data_observation", schema="md")
    op.drop_column("market_data_observation", "source_observation_key", schema="md")
    op.drop_index("ix_external_object_mapping_tenant_lookup", table_name="external_object_mapping", schema="ing")
    op.execute("ALTER TABLE ing.external_object_mapping DROP CONSTRAINT IF EXISTS ex_external_object_mapping_effective_period")
    op.drop_constraint("uq_external_object_mapping_business_key", "external_object_mapping", schema="ing", type_="unique")
    op.create_unique_constraint(
        "uq_external_object_mapping_business_key",
        "external_object_mapping",
        ["external_id_namespace_id", "external_object_type", "external_id_value", "context_market_venue_id", "valid_from"],
        schema="ing",
    )
    op.execute(
        f"""
        ALTER TABLE ing.external_object_mapping
        ADD CONSTRAINT ex_external_object_mapping_effective_period
        EXCLUDE USING gist (
            external_id_namespace_id WITH =,
            external_object_type WITH =,
            external_id_value WITH =,
            COALESCE(context_market_venue_id, '{ZERO_UUID}'::uuid) WITH =,
            daterange(valid_from, COALESCE(valid_to + 1, 'infinity'::date), '[)') WITH &&
        ) WHERE (status IN ('PROPOSED', 'VERIFIED'))
        """
    )
    op.drop_column("external_object_mapping", "tenant_id", schema="ing")
    op.drop_index("ix_tenant_user_account_lookup", table_name="tenant_user_account", schema="ten")
    op.drop_table("tenant_user_account", schema="ten")
    op.execute("ALTER TABLE secm.instrument_definition_version DROP CONSTRAINT IF EXISTS ex_instrument_definition_version_effective_period")
    op.execute("ALTER TABLE secm.listing_definition_version DROP CONSTRAINT IF EXISTS ex_listing_definition_version_effective_period")
    op.drop_constraint("ck_instrument_definition_version_valid_period", "instrument_definition_version", schema="secm", type_="check")
    op.drop_constraint("ck_listing_definition_version_valid_period", "listing_definition_version", schema="secm", type_="check")
