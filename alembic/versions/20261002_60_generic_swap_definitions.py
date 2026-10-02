"""Versioned generic swap economics; legacy swaps are not backfilled."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = '20261002_60'
down_revision = '20261002_59'
branch_labels = depends_on = None


def upgrade():
    op.create_table('swap_definition_version',
        sa.Column('instrument_definition_version_id', UUID(as_uuid=True), sa.ForeignKey('secm.instrument_definition_version.instrument_definition_version_id'), primary_key=True),
        sa.Column('schema_version', sa.Integer(), nullable=False),
        sa.Column('economics_payload', JSONB(), nullable=False),
        sa.CheckConstraint("schema_version = 1 AND jsonb_typeof(economics_payload) = 'object' AND economics_payload ? 'schemaVersion' AND economics_payload->>'schemaVersion' = schema_version::text", name='ck_swap_definition_version_payload'),
        schema='secm')


def downgrade():
    raise RuntimeError('Forward-only: approved swap definitions must not be discarded.')
