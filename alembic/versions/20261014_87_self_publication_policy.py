"""Explicit tenant self-publication governance, default disabled; no grants seeded."""
from alembic import op
from security_master_schema import models as m
from valuation import tables as t
revision='20261014_87'
down_revision='20261013_86'
branch_labels=None
depends_on=None

def upgrade():
    t.publication_policy.create(op.get_bind(),checkfirst=True)
    op.execute("""CREATE FUNCTION nav.prevent_publication_policy_mutation() RETURNS trigger AS $$
        BEGIN RAISE EXCEPTION 'Publication policy revisions are immutable; append a revision'; END;
        $$ LANGUAGE plpgsql""")
    op.execute("""CREATE TRIGGER trg_publication_policy_immutable BEFORE UPDATE OR DELETE
        ON nav.valuation_publication_policy FOR EACH ROW EXECUTE FUNCTION nav.prevent_publication_policy_mutation()""")

def downgrade():
    op.execute('DROP TRIGGER IF EXISTS trg_publication_policy_immutable ON nav.valuation_publication_policy')
    t.publication_policy.drop(op.get_bind())
    op.execute('DROP FUNCTION IF EXISTS nav.prevent_publication_policy_mutation()')
