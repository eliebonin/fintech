"""Preserve existing admin operational access explicitly before role separation."""
from datetime import date
from alembic import op
from sqlalchemy import select
from security_master_schema import models as m
from security_master_schema.access_bootstrap import bootstrap_admin_operations

revision='20261013_84'
down_revision='20261009_83'
branch_labels=None
depends_on=None


def upgrade():
    c=op.get_bind()
    today=date.today()
    rows=c.execute(select(m.tenant_user_account.c.tenant_id,m.tenant_user_account.c.user_account_id).where(
        m.tenant_user_account.c.membership_role=='TENANT_ADMIN',
        m.tenant_user_account.c.valid_from<=today,
        m.tenant_user_account.c.valid_to.is_(None)|(m.tenant_user_account.c.valid_to>=today))).all()
    for tenant,user in rows:
        bootstrap_admin_operations(c,tenant,user,user,as_of=today,include_creation=False)


def downgrade():
    raise RuntimeError('Forward-only: retain explicit access assignments and audit; role changes must not restore implicit financial authority.')
