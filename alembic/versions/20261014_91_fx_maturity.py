"""Retained deliverable FX-forward maturity processing evidence."""
from alembic import op
from security_master_schema import models as m
revision='20261014_91'
down_revision='20261014_90'
branch_labels=None
depends_on=None


def upgrade():
    for table in (m.fx_maturity_policy,m.fx_maturity_proposal,m.fx_maturity_posting): table.create(op.get_bind())
    op.execute("""CREATE FUNCTION trd.guard_fx_maturity_evidence() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN RAISE EXCEPTION 'FX maturity evidence is immutable; append a new record'; END $$""")
    for name in ('fx_maturity_policy','fx_maturity_proposal','fx_maturity_posting'):
        op.execute(f'CREATE TRIGGER immutable_{name} BEFORE UPDATE OR DELETE ON trd.{name} FOR EACH ROW EXECUTE FUNCTION trd.guard_fx_maturity_evidence()')


def downgrade():
    raise RuntimeError('Forward-only: retain maturity policy and posting evidence')
