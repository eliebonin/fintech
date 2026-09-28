"""Add coverage and date-completeness semantics to market-data series."""

from alembic import op
import sqlalchemy as sa


revision = "20260901_15"
down_revision = "20260901_14"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Describe expected series coverage and reject undated daily observations."""

    op.add_column(
        "market_data_series",
        sa.Column(
            "expected_frequency_code",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'EVENT_DRIVEN'"),
            comment="Expected cadence such as BUSINESS_DAILY, CALENDAR_DAILY, INTRADAY, MONTHLY, QUARTERLY, or EVENT_DRIVEN; used for coverage and date validation.",
        ),
        schema="md",
    )
    op.add_column(
        "market_data_series",
        sa.Column(
            "expected_market_calendar_id",
            sa.UUID(),
            nullable=True,
            comment="Calendar expected to govern valid market dates for this series; nullable only when no calendar is meaningful or a resolver derives one from the listing venue.",
        ),
        schema="md",
    )
    op.add_column(
        "market_data_series",
        sa.Column(
            "coverage_start_date",
            sa.Date(),
            nullable=True,
            comment="First market date the source declares this series to cover; does not imply every expected session has been received.",
        ),
        schema="md",
    )
    op.add_column(
        "market_data_series",
        sa.Column(
            "coverage_end_date",
            sa.Date(),
            nullable=True,
            comment="Last market date the source declares this series to cover; null while the series remains open-ended.",
        ),
        schema="md",
    )
    op.create_foreign_key(
        "fk_market_data_series_expected_calendar",
        "market_data_series",
        "market_calendar",
        ["expected_market_calendar_id"],
        ["market_calendar_id"],
        source_schema="md",
        referent_schema="cal",
    )
    op.create_check_constraint(
        "ck_market_data_series_coverage_range",
        "market_data_series",
        "coverage_end_date IS NULL OR coverage_start_date IS NULL OR coverage_end_date >= coverage_start_date",
        schema="md",
    )
    op.create_index(
        "ix_market_data_series_calendar_frequency",
        "market_data_series",
        ["expected_market_calendar_id", "expected_frequency_code"],
        schema="md",
    )
    op.execute(
        """
        CREATE FUNCTION md.enforce_market_data_observation_market_date() RETURNS trigger AS $$
        DECLARE
            series_frequency text;
        BEGIN
            SELECT expected_frequency_code
              INTO series_frequency
              FROM md.market_data_series
             WHERE market_data_series_id = NEW.market_data_series_id;

            IF series_frequency IN ('BUSINESS_DAILY', 'CALENDAR_DAILY', 'MONTHLY', 'QUARTERLY')
               AND NEW.market_date IS NULL THEN
                RAISE EXCEPTION 'market_date is required for % series %', series_frequency, NEW.market_data_series_id;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_market_data_observation_requires_market_date
        BEFORE INSERT OR UPDATE OF market_date, market_data_series_id
        ON md.market_data_observation
        FOR EACH ROW EXECUTE FUNCTION md.enforce_market_data_observation_market_date()
        """
    )


def downgrade() -> None:
    """Remove coverage metadata and the date-required trigger."""

    op.execute("DROP TRIGGER IF EXISTS trg_market_data_observation_requires_market_date ON md.market_data_observation")
    op.execute("DROP FUNCTION IF EXISTS md.enforce_market_data_observation_market_date()")
    op.drop_index("ix_market_data_series_calendar_frequency", table_name="market_data_series", schema="md")
    op.drop_constraint("ck_market_data_series_coverage_range", "market_data_series", schema="md", type_="check")
    op.drop_constraint("fk_market_data_series_expected_calendar", "market_data_series", schema="md", type_="foreignkey")
    op.drop_column("market_data_series", "coverage_end_date", schema="md")
    op.drop_column("market_data_series", "coverage_start_date", schema="md")
    op.drop_column("market_data_series", "expected_market_calendar_id", schema="md")
    op.drop_column("market_data_series", "expected_frequency_code", schema="md")
