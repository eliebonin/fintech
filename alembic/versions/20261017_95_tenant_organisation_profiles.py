"""Tenant-private organisation metadata; existing eligibility is unchanged."""
from alembic import op
from security_master_schema import models as m

revision = '20261017_95'
down_revision = '20261015_94'
branch_labels = depends_on = None

def upgrade():
    m.tenant_organisation_profile.create(op.get_bind())

def downgrade():
    raise RuntimeError('Forward-only: retain tenant organisation configuration')
