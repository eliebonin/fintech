"""Append-only governed structured-security and futures booking conventions."""
from alembic import op
from security_master_schema import models as m
revision = '20261001_56'
down_revision = '20261001_55'
branch_labels = depends_on = None


def upgrade():
    m.instrument_booking_convention.create(op.get_bind())
    op.execute("""CREATE FUNCTION secm.reject_booking_convention_mutation() RETURNS trigger
        LANGUAGE plpgsql AS $$ BEGIN
        RAISE EXCEPTION 'Approved booking conventions are immutable; append a version';
        END $$""")
    op.execute("""CREATE TRIGGER booking_convention_immutable BEFORE UPDATE OR DELETE
        ON secm.instrument_booking_convention FOR EACH ROW
        EXECUTE FUNCTION secm.reject_booking_convention_mutation()""")


def downgrade():
    op.drop_table('instrument_booking_convention', schema='secm')
    op.execute('DROP FUNCTION secm.reject_booking_convention_mutation()')
