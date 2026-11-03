"""Make access evidence append-only, including against accidental owner DML."""
from alembic import op

revision='20261030_105'
down_revision='20261029_104'
branch_labels=None
depends_on=None


def upgrade():
    op.execute("""
    CREATE FUNCTION ten.reject_access_audit_mutation() RETURNS trigger
    LANGUAGE plpgsql AS $$
    BEGIN
      RAISE EXCEPTION 'Access audit evidence is append-only' USING ERRCODE='23514';
    END;
    $$;
    CREATE TRIGGER access_audit_no_mutation BEFORE UPDATE OR DELETE
    ON ten.access_audit_event FOR EACH ROW EXECUTE FUNCTION ten.reject_access_audit_mutation();
    CREATE TRIGGER access_audit_no_truncate BEFORE TRUNCATE
    ON ten.access_audit_event FOR EACH STATEMENT EXECUTE FUNCTION ten.reject_access_audit_mutation();
    """)


def downgrade():
    op.execute('DROP TRIGGER access_audit_no_truncate ON ten.access_audit_event')
    op.execute('DROP TRIGGER access_audit_no_mutation ON ten.access_audit_event')
    op.execute('DROP FUNCTION ten.reject_access_audit_mutation()')
