"""Consolidate closing prices; preserve historical policies and evidence."""
from alembic import op
import sqlalchemy as sa

revision = '20261008_76'
down_revision = '20261008_75'
branch_labels = depends_on = None


def upgrade():
    op.add_column('market_data_series', sa.Column('closing_method', sa.String(30), nullable=False,
        server_default=sa.text("'UNKNOWN'"), comment='Closing methodology: EXCHANGE_OFFICIAL, LAST_TRADE, PROVIDER_DEFINED or UNKNOWN; separate from adjustment basis.'), schema='md')
    op.add_column('valuation_policy_rule', sa.Column('require_official_close', sa.Boolean(), nullable=False,
        server_default=sa.text('false'), comment='Require exchange-official closing designation for CLOSE; legacy OFFICIAL_CLOSE implies true without rewriting immutable rules.'), schema='ten')
    # Preserve the designation already asserted by the legacy series type, not
    # independently certify it. No prices, adjustments or permissions change.
    op.execute("UPDATE md.market_data_series SET series_type='CLOSE', closing_method='EXCHANGE_OFFICIAL' WHERE series_type='OFFICIAL_CLOSE'")
    op.create_check_constraint('ck_market_data_series_closing_method', 'market_data_series',
        "closing_method IN ('EXCHANGE_OFFICIAL','LAST_TRADE','PROVIDER_DEFINED','UNKNOWN') AND (series_type='CLOSE' OR closing_method='UNKNOWN')", schema='md')
    op.create_check_constraint('ck_policy_official_close', 'valuation_policy_rule',
        "NOT require_official_close OR series_type IN ('CLOSE','OFFICIAL_CLOSE')", schema='ten')
    # Older seeds/import clients use the legacy spelling. Normalize at the write
    # boundary so they cannot recreate a second closing-price family.
    op.execute("""
      CREATE FUNCTION md.normalize_closing_series() RETURNS trigger LANGUAGE plpgsql AS $$
      BEGIN
        IF NEW.series_type='OFFICIAL_CLOSE' THEN
          NEW.series_type := 'CLOSE'; NEW.closing_method := 'EXCHANGE_OFFICIAL';
        END IF;
        RETURN NEW;
      END $$;
      CREATE TRIGGER normalize_closing_series BEFORE INSERT OR UPDATE ON md.market_data_series
        FOR EACH ROW EXECUTE FUNCTION md.normalize_closing_series();
    """)


def downgrade():
    raise RuntimeError('Forward-only: closing methodology and frozen policy evidence must be retained.')
