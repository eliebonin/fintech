"""Add optional approved futures-family specifications without changing legacy families."""
from alembic import op
import sqlalchemy as sa

revision = '20261002_57'
down_revision = '20261001_56'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('future_family', sa.Column('specification_payload', sa.Text(), nullable=True,
        comment='Approved typed family specification; null preserves legacy per-expiry configuration.'), schema='secm')


def downgrade():
    raise RuntimeError('Forward-only migration: approved family specifications must not be discarded.')
