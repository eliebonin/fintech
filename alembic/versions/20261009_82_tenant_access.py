"""Add tenant-local access groups and audited local test sessions."""
from alembic import op
from security_master_schema import models as m

revision = '20261009_82'
down_revision = '20261009_81'
branch_labels = None
depends_on = None


def upgrade():
    for table in (m.access_group, m.access_group_member, m.access_group_grant,
                  m.access_audit_event, m.local_access_session):
        table.create(op.get_bind(), checkfirst=True)


def downgrade():
    raise RuntimeError('Forward-only: retained access audit and authority records.')
