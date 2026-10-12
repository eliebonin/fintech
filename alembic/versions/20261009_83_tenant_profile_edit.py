"""Platform-managed operational contacts and optimistic tenant-profile version."""
from alembic import op

revision='20261009_83'
down_revision='20261009_82'
branch_labels=None
depends_on=None

def upgrade():
    # IF NOT EXISTS also supports local metadata-bootstrap databases.
    op.execute('ALTER TABLE ten.tenant ADD COLUMN IF NOT EXISTS operational_contact_name varchar(250)')
    op.execute('ALTER TABLE ten.tenant ADD COLUMN IF NOT EXISTS operational_contact_email varchar(254)')
    op.execute('ALTER TABLE ten.tenant ADD COLUMN IF NOT EXISTS profile_version integer NOT NULL DEFAULT 0')
    op.execute("COMMENT ON COLUMN ten.tenant.operational_contact_name IS 'Platform-managed operational contact; not a login identity or authority grant.'")
    op.execute("COMMENT ON COLUMN ten.tenant.operational_contact_email IS 'Operational contact email; no invitation or authentication is implied.'")
    op.execute("COMMENT ON COLUMN ten.tenant.profile_version IS 'Optimistic concurrency token for tenant profile and status edits.'")

def downgrade():
    raise RuntimeError('Forward-only: preserve tenant contacts and edit history.')
