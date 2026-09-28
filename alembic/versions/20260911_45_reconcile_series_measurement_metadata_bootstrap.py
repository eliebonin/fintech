"""Reconcile series-measurement controls for metadata-bootstrapped local databases.

Revision ID: 20260911_45
Revises: 20260911_44
"""

from alembic import op


revision = "20260911_45"
down_revision = "20260911_44"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add the series FK and backfill when metadata created the catalogue first."""

    op.execute(
        """
        ALTER TABLE md.market_data_series
        ADD COLUMN IF NOT EXISTS measure_definition_id uuid
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'fk_market_data_series_measure_definition'
                  AND conrelid = 'md.market_data_series'::regclass
            ) THEN
                ALTER TABLE md.market_data_series
                ADD CONSTRAINT fk_market_data_series_measure_definition
                FOREIGN KEY (measure_definition_id)
                REFERENCES md.series_measure_definition(series_measure_definition_id);
            END IF;
        END $$;
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_market_data_series_measure_definition
        ON md.market_data_series (measure_definition_id)
        """
    )
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
    """Remove only the reconciliation controls created by this revision."""

    op.execute("DROP INDEX IF EXISTS md.ix_market_data_series_measure_definition")
    op.execute("ALTER TABLE md.market_data_series DROP CONSTRAINT IF EXISTS fk_market_data_series_measure_definition")
    op.execute("ALTER TABLE md.market_data_series DROP COLUMN IF EXISTS measure_definition_id")
