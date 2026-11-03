"""Retain tenant manual-mark requests and independent decisions without source rewrites."""
from alembic import op

revision='20261031_107'
down_revision='20261030_106'
branch_labels=None
depends_on=None


def upgrade():
    from security_master_schema import models as m
    from valuation import mark_override_tables as t
    for table in (t.request,t.decision):table.create(op.get_bind(),checkfirst=False)
    op.execute("""CREATE FUNCTION nav.reject_mark_override_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
      BEGIN RAISE EXCEPTION 'Manual mark requests and decisions are immutable; append a reviewed correction or withdrawal'; END; $$;
      CREATE TRIGGER mark_override_request_immutable BEFORE UPDATE OR DELETE ON nav.valuation_mark_override_request
        FOR EACH ROW EXECUTE FUNCTION nav.reject_mark_override_mutation();
      CREATE TRIGGER mark_override_decision_immutable BEFORE UPDATE OR DELETE ON nav.valuation_mark_override_decision
        FOR EACH ROW EXECUTE FUNCTION nav.reject_mark_override_mutation();""")


def downgrade():
    raise RuntimeError('Reviewed manual-mark evidence cannot be discarded by downgrade')
