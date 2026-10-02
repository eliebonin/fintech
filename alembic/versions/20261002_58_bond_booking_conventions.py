"""Allow approved bond conventions; no historical trade reinterpretation."""
from alembic import op

revision = '20261002_58'
down_revision = '20261002_57'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint('ck_instrument_booking_convention_kind', 'instrument_booking_convention', schema='secm')
    op.create_check_constraint('ck_instrument_booking_convention_kind', 'instrument_booking_convention',
        "version_no > 0 AND kind IN ('STRUCTURED_PRODUCT','FUTURE','BOND')", schema='secm')


def downgrade():
    raise RuntimeError('Forward-only: approved bond conventions must not be discarded.')
