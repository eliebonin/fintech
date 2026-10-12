"""Visible default rules without changing existing strict policy semantics."""
from alembic import op
import sqlalchemy as sa

revision = '20261008_75'
down_revision = '20261008_74'
branch_labels = depends_on = None


def upgrade():
    op.add_column('valuation_policy', sa.Column('selection_mode', sa.String(20), nullable=False,
        server_default=sa.text("'STRICT'"), comment='STRICT explicit rules only; FLEXIBLE permits configured defaults for unmatched subjects.'), schema='ten')
    op.create_check_constraint('ck_valuation_policy_selection_mode', 'valuation_policy',
        "selection_mode IN ('STRICT','FLEXIBLE')", schema='ten')
    op.add_column('valuation_policy_rule', sa.Column('is_default', sa.Boolean(), nullable=False,
        server_default=sa.text('false'), comment='Default rule considered only in flexible policies after all matching explicit rules.'), schema='ten')


def downgrade():
    raise RuntimeError('Forward-only: retain frozen pricing policy authority.')
