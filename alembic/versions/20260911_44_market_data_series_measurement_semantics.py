"""Add governed semantic definitions for market-data series measurements.

Revision ID: 20260911_44
Revises: 20260911_43
"""

from alembic import op
import sqlalchemy as sa


revision = "20260911_44"
down_revision = "20260911_43"
branch_labels = None
depends_on = None


_MEASURE_ROWS = (
    ("PRICE", "Price", "Tradable or evaluated unit price; period performance is normally a relative return.", "CURRENCY_PRICE", "RELATIVE_RETURN", "PERCENT", 4, 4, 10),
    ("FX_RATE", "FX rate", "Quote-currency amount per base-currency unit; movement is normally a relative return.", "CURRENCY_PRICE", "RELATIVE_RETURN", "PERCENT", 6, 4, 20),
    ("INDEX_LEVEL", "Index level", "Published index level; movement is normally a relative return.", "INDEX_POINTS", "RELATIVE_RETURN", "PERCENT", 4, 4, 30),
    ("NAV", "Net asset value", "Fund or share-class net asset value per unit; movement is normally a relative return.", "CURRENCY_PRICE", "RELATIVE_RETURN", "PERCENT", 6, 4, 40),
    ("IMPLIED_VOLATILITY", "Implied volatility", "Percent implied-volatility quote; movement is normally in volatility points.", "PERCENT", "ABSOLUTE_CHANGE", "VOLATILITY_POINTS", 4, 4, 50),
    ("YIELD", "Yield", "Percent yield quote; movement is normally in basis points.", "PERCENT", "BASIS_POINT_CHANGE", "BASIS_POINTS", 6, 2, 60),
    ("RATE", "Rate", "Percent interest or zero rate; movement is normally in basis points unless it is an FX rate.", "PERCENT", "BASIS_POINT_CHANGE", "BASIS_POINTS", 6, 2, 70),
    ("CREDIT_SPREAD", "Credit spread", "Credit, OAS, or related spread; movement is normally in basis points.", "BASIS_POINTS", "BASIS_POINT_CHANGE", "BASIS_POINTS", 2, 2, 80),
    ("VOLUME", "Volume", "Trading volume or turnover quantity; movement is normally an absolute unit change.", "QUANTITY", "ABSOLUTE_CHANGE", "UNITS", 0, 0, 90),
    ("OPEN_INTEREST", "Open interest", "Open derivative-contract count; movement is normally an absolute unit change.", "QUANTITY", "ABSOLUTE_CHANGE", "UNITS", 0, 0, 100),
    ("MONETARY_VALUE", "Monetary value", "Trade-specific or position-specific monetary value or MTM; movement is a monetary amount.", "CURRENCY_AMOUNT", "MONETARY_CHANGE", "CURRENCY_AMOUNT", 2, 2, 110),
)


def upgrade() -> None:
    """Create semantic catalogue and backfill unambiguous existing series."""

    op.create_table(
        "series_measure_definition",
        sa.Column("series_measure_definition_id", sa.UUID(), server_default=sa.text("uuidv7()"), nullable=False, comment="Immutable UUIDv7 identifier for a governed definition of the economic meaning of a market-data series observation."),
        sa.Column("measure_code", sa.String(length=50), nullable=False, comment="Stable unique semantic code such as PRICE, FX_RATE, IMPLIED_VOLATILITY, YIELD, RATE, CREDIT_SPREAD, or VOLUME."),
        sa.Column("display_name", sa.String(length=250), nullable=False, comment="Human-readable name of the market-data measurement definition."),
        sa.Column("description", sa.Text(), nullable=True, comment="Business definition of the observed value and its intended analytical interpretation."),
        sa.Column("unit_type", sa.String(length=40), nullable=False, comment="Governed unit category such as CURRENCY_PRICE, PERCENT, BASIS_POINTS, INDEX_POINTS, QUANTITY, or CURRENCY_AMOUNT."),
        sa.Column("default_change_method", sa.String(length=40), nullable=False, comment="Default period-on-period analytical convention: RELATIVE_RETURN, ABSOLUTE_CHANGE, BASIS_POINT_CHANGE, or MONETARY_CHANGE; policies may explicitly override it."),
        sa.Column("change_display_unit", sa.String(length=40), nullable=False, comment="Display unit for the default change, such as PERCENT, VOLATILITY_POINTS, BASIS_POINTS, PIPS, UNITS, or CURRENCY_AMOUNT."),
        sa.Column("display_decimal_places", sa.Integer(), server_default=sa.text("4"), nullable=False, comment="Default number of decimal places when presenting a raw observation; this does not limit stored precision."),
        sa.Column("change_decimal_places", sa.Integer(), server_default=sa.text("4"), nullable=False, comment="Default number of decimal places when presenting a period-on-period change; this does not limit calculated precision."),
        sa.Column("status", sa.String(length=30), server_default=sa.text("'ACTIVE'"), nullable=False, comment="Lifecycle status of the governed definition, such as ACTIVE, RETIRED, or SUPERSEDED."),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False, comment="Display ordering for governed measurement-definition catalogues."),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False, comment="UTC timestamp at which the governed measurement definition was created."),
        sa.CheckConstraint("unit_type IN ('CURRENCY_PRICE', 'PERCENT', 'BASIS_POINTS', 'INDEX_POINTS', 'QUANTITY', 'CURRENCY_AMOUNT')", name="ck_series_measure_definition_unit_type"),
        sa.CheckConstraint("default_change_method IN ('RELATIVE_RETURN', 'ABSOLUTE_CHANGE', 'BASIS_POINT_CHANGE', 'MONETARY_CHANGE')", name="ck_series_measure_definition_change_method"),
        sa.CheckConstraint("display_decimal_places >= 0 AND change_decimal_places >= 0", name="ck_series_measure_definition_nonnegative_precision"),
        sa.PrimaryKeyConstraint("series_measure_definition_id"),
        sa.UniqueConstraint("measure_code"),
        schema="md",
    )
    measure_table = sa.table(
        "series_measure_definition",
        sa.column("measure_code", sa.String()), sa.column("display_name", sa.String()), sa.column("description", sa.Text()),
        sa.column("unit_type", sa.String()), sa.column("default_change_method", sa.String()), sa.column("change_display_unit", sa.String()),
        sa.column("display_decimal_places", sa.Integer()), sa.column("change_decimal_places", sa.Integer()), sa.column("status", sa.String()), sa.column("sort_order", sa.Integer()),
        schema="md",
    )
    op.bulk_insert(
        measure_table,
        [
            {"measure_code": code, "display_name": name, "description": description, "unit_type": unit_type, "default_change_method": method, "change_display_unit": display_unit, "display_decimal_places": display_precision, "change_decimal_places": change_precision, "status": "ACTIVE", "sort_order": sort_order}
            for code, name, description, unit_type, method, display_unit, display_precision, change_precision, sort_order in _MEASURE_ROWS
        ],
    )
    op.add_column(
        "market_data_series",
        sa.Column("measure_definition_id", sa.UUID(), nullable=True, comment="Governed semantic definition of what one observation measures and how a normal period-on-period movement is expressed; nullable only during legacy-series backfill."),
        schema="md",
    )
    op.create_foreign_key(
        "fk_market_data_series_measure_definition",
        "market_data_series",
        "series_measure_definition",
        ["measure_definition_id"],
        ["series_measure_definition_id"],
        source_schema="md",
        referent_schema="md",
    )
    op.create_index("ix_market_data_series_measure_definition", "market_data_series", ["measure_definition_id"], schema="md")
    op.execute(
        """
        UPDATE md.market_data_series AS series
        SET measure_definition_id = definition.series_measure_definition_id
        FROM md.series_measure_definition AS definition
        WHERE series.measure_definition_id IS NULL
          AND definition.measure_code = CASE
              WHEN series.value_type = 'RATE' AND series.series_type = 'FX_SPOT' THEN 'FX_RATE'
              WHEN series.value_type = 'PRICE' AND series.series_type = 'OFFICIAL_NAV' THEN 'NAV'
              WHEN series.value_type = 'SPREAD' THEN 'CREDIT_SPREAD'
              WHEN series.value_type IN ('PRICE', 'INDEX_LEVEL', 'YIELD', 'RATE', 'VOLUME') THEN series.value_type
              ELSE NULL
          END
        """
    )


def downgrade() -> None:
    """Remove the additive semantic catalogue and series link."""

    op.drop_index("ix_market_data_series_measure_definition", table_name="market_data_series", schema="md")
    op.drop_constraint("fk_market_data_series_measure_definition", "market_data_series", schema="md", type_="foreignkey")
    op.drop_column("market_data_series", "measure_definition_id", schema="md")
    op.drop_table("series_measure_definition", schema="md")
