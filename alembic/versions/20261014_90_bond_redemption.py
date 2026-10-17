"""Append-only plain bond maturity preparation and posting evidence."""
from alembic import op
from security_master_schema import models as m
revision='20261014_90'
down_revision='20261014_89'
branch_labels=None
depends_on=None


def upgrade():
    for table in (m.bond_redemption_policy,m.bond_redemption_proposal,m.bond_redemption_posting): table.create(op.get_bind())
    op.execute('''CREATE FUNCTION trd.guard_bond_redemption_evidence() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN RAISE EXCEPTION 'Bond redemption evidence is immutable; append a new record'; END $$''')
    for name in ('bond_redemption_policy','bond_redemption_proposal','bond_redemption_posting'):
        op.execute(f'CREATE TRIGGER immutable_{name} BEFORE UPDATE OR DELETE ON trd.{name} FOR EACH ROW EXECUTE FUNCTION trd.guard_bond_redemption_evidence()')


def downgrade():
    raise RuntimeError('Forward-only: retain lifecycle authority and posting evidence')
