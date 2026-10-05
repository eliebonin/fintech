"""Reject JSON-null swap schema versions without discarding approved evidence."""
from alembic import op

revision = '20261005_61'
down_revision = '20261002_60'
branch_labels = depends_on = None


def upgrade():
    op.drop_constraint('ck_swap_definition_version_payload', 'swap_definition_version', schema='secm', type_='check')
    op.create_check_constraint('ck_swap_definition_version_payload', 'swap_definition_version',
        "schema_version = 1 AND jsonb_typeof(economics_payload) = 'object' AND economics_payload ? 'schemaVersion' AND COALESCE(economics_payload->>'schemaVersion' = schema_version::text, false)", schema='secm')


def downgrade():
    raise RuntimeError('Forward-only: approved swap definitions must not be weakened.')
