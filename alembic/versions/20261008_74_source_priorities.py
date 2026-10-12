"""Immutable source preference versions, separate from licensing authority."""
from alembic import op
from sqlalchemy import text

revision = '20261008_74'
down_revision = '20261008_73'
branch_labels = depends_on = None


def upgrade():
    op.execute("""
      CREATE TABLE md.source_priority_version (
        source_priority_version_id uuid PRIMARY KEY DEFAULT uuidv7(),
        tenant_id uuid REFERENCES ten.tenant(tenant_id),
        instrument_type_id uuid NOT NULL REFERENCES secm.instrument_type(instrument_type_id),
        use_purpose varchar(40) NOT NULL DEFAULT 'VALUATION' CHECK (use_purpose='VALUATION'),
        mode varchar(20) NOT NULL CHECK (mode IN ('CUSTOM','INHERIT')),
        version_no integer NOT NULL CHECK (version_no > 0),
        created_by_user_account_id uuid NOT NULL REFERENCES secm.user_account(user_account_id),
        created_at_utc timestamptz NOT NULL DEFAULT clock_timestamp(),
        submission_key varchar(255) NOT NULL,
        submission_fingerprint varchar(64) NOT NULL,
        CHECK (tenant_id IS NOT NULL OR mode='CUSTOM'),
        UNIQUE NULLS NOT DISTINCT (tenant_id,instrument_type_id,use_purpose,version_no),
        UNIQUE NULLS NOT DISTINCT (tenant_id,submission_key)
      );
      CREATE INDEX ix_source_priority_asof ON md.source_priority_version
        (tenant_id,instrument_type_id,use_purpose,created_at_utc DESC);
      CREATE TABLE md.source_priority_entry (
        source_priority_version_id uuid NOT NULL REFERENCES md.source_priority_version(source_priority_version_id),
        dataset_id uuid NOT NULL REFERENCES md.dataset(dataset_id),
        priority integer NOT NULL CHECK (priority > 0),
        PRIMARY KEY (source_priority_version_id,dataset_id),
        UNIQUE(source_priority_version_id,priority)
      );
      CREATE FUNCTION md.prevent_source_priority_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN RAISE EXCEPTION 'Source priority versions are immutable'; END;
      $$;
      CREATE TRIGGER source_priority_version_immutable BEFORE UPDATE OR DELETE ON md.source_priority_version
        FOR EACH ROW EXECUTE FUNCTION md.prevent_source_priority_mutation();
      CREATE TRIGGER source_priority_entry_immutable BEFORE UPDATE OR DELETE ON md.source_priority_entry
        FOR EACH ROW EXECUTE FUNCTION md.prevent_source_priority_mutation();
    """)


def downgrade():
    if op.get_bind().scalar(text('SELECT EXISTS(SELECT 1 FROM md.source_priority_version)')):
        raise RuntimeError('Retained source priority evidence exists; downgrade would change selection authority')
    op.execute('DROP TABLE md.source_priority_entry; DROP TABLE md.source_priority_version; DROP FUNCTION md.prevent_source_priority_mutation()')
