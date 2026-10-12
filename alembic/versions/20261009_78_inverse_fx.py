"""Explicit reciprocal FX permission; no existing rule is broadened."""
from alembic import op
import sqlalchemy as sa

revision='20261009_78'
down_revision='20261009_77'
branch_labels=depends_on=None


def upgrade():
    op.add_column('valuation_policy_rule',sa.Column('allow_inverse_fx',sa.Boolean(),nullable=False,server_default=sa.text('false')),schema='ten')
    op.create_check_constraint('ck_policy_inverse_fx','valuation_policy_rule',
        "NOT allow_inverse_fx OR (series_type='FX_SPOT' AND pricing_convention IN ('EXPLICIT_TIME','NAMED_FIXING'))",schema='ten')


def downgrade():
    raise RuntimeError('Forward-only: preserve frozen FX conventions.')
