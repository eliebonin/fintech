"""Permit versioned economic position results, preserving all scope validators."""
from pathlib import Path
from alembic import op
revision='20261009_81'
down_revision='20261009_80'
branch_labels=depends_on=None


def upgrade():
    # Frozen migration text, never mutable application SQL. Keep the existing
    # numeric reconciliation and ownership checks byte-for-byte except methods.
    source=Path(__file__).with_name('20261008_70_position_attribution.py').read_text()
    start=source.index('    CREATE OR REPLACE FUNCTION nav.check_valuation_scope()')
    end=source.index('    CREATE FUNCTION nav.check_pnl_lineage()',start)
    original="NEW.method <> 'listed-equity-position-market-pnl-v2'"
    assert source[start:end].count(original)==1
    op.execute(source[start:end].replace(original,"NEW.method NOT IN ('listed-equity-position-market-pnl-v2','economic-position-pnl-v3')"))


def downgrade():
    raise RuntimeError('Forward-only: retained economic position financial versions.')
