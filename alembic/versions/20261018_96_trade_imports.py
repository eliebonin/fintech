"""Retained tenant trade-import artifacts, reviews and exact row identities."""
from alembic import op
from data_imports.tables import job,row

revision='20261018_96'
down_revision='20261017_95'
branch_labels=depends_on=None


def upgrade():
    job.create(op.get_bind());row.create(op.get_bind())


def downgrade():
    raise RuntimeError('Forward-only: preserve import evidence and financial row identities')
