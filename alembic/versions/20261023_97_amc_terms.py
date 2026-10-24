"""Native AMC terms and existing funded-security booking convention extension."""
from alembic import op
from security_master_schema.models import amc_terms

revision='20261023_97'
down_revision='20261018_96'
branch_labels=depends_on=None


def upgrade():
    amc_terms.create(op.get_bind())
    op.drop_constraint('ck_instrument_booking_convention_kind','instrument_booking_convention',schema='secm',type_='check')
    op.create_check_constraint('ck_instrument_booking_convention_kind','instrument_booking_convention',
        "version_no > 0 AND kind IN ('STRUCTURED_PRODUCT','FUTURE','BOND','SWAP','ACTIVELY_MANAGED_CERTIFICATE')",schema='secm')


def downgrade():
    raise RuntimeError('Forward-only: preserve approved AMC terms and booking evidence')
