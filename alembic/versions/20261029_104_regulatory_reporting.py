"""Retained regulatory preparation; no tenant grants or regulator submissions."""
from alembic import op
revision='20261029_104'
down_revision='20261028_103'
branch_labels=None
depends_on=None

def upgrade():
    op.execute("""
    CREATE SCHEMA IF NOT EXISTS reg;
    INSERT INTO ten.platform_module(module_code,display_name,description,module_category,status,sort_order)
    VALUES('REGULATORY_REPORTING','Regulatory Reporting','Legal-entity assessment, transaction preparation and retained exports; no submission connectivity.','OPERATIONS','ACTIVE',110)
    ON CONFLICT(module_code) DO NOTHING;
    CREATE TABLE reg.reporting_profile(
      profile_id uuid PRIMARY KEY,tenant_id uuid NOT NULL REFERENCES ten.tenant,
      name varchar(250) NOT NULL,lei varchar(20) NOT NULL,firm_category varchar(40) NOT NULL,
      firm_scope varchar(20) NOT NULL CHECK(firm_scope IN ('IN_SCOPE','OUT_OF_SCOPE','UNASSESSED')),
      reason text NOT NULL CHECK(length(trim(reason))>=3),revision integer NOT NULL CHECK(revision>0),
      actor_id uuid NOT NULL REFERENCES secm.user_account,recorded_at timestamptz NOT NULL DEFAULT clock_timestamp());
    CREATE TABLE reg.profile_revision(
      profile_id uuid NOT NULL REFERENCES reg.reporting_profile,revision integer NOT NULL,
      tenant_id uuid NOT NULL REFERENCES ten.tenant,payload jsonb NOT NULL,
      actor_id uuid NOT NULL REFERENCES secm.user_account,recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      PRIMARY KEY(profile_id,revision));
    CREATE TABLE reg.transaction_candidate(
      candidate_id uuid PRIMARY KEY,tenant_id uuid NOT NULL REFERENCES ten.tenant,
      strategy_id uuid NOT NULL REFERENCES trd.strategy,trade_id uuid NOT NULL REFERENCES trd.trade,
      profile_id uuid NOT NULL REFERENCES reg.reporting_profile,execution_date date NOT NULL,
      revision integer NOT NULL CHECK(revision>0),source_hash varchar(64) NOT NULL,payload jsonb NOT NULL,
      reportability varchar(30) NOT NULL CHECK(reportability IN ('REPORTABLE','NOT_REPORTABLE','NEEDS_ASSESSMENT')),
      readiness varchar(20) NOT NULL CHECK(readiness IN ('READY','INCOMPLETE')),
      disposition varchar(10) NOT NULL CHECK(disposition IN ('AUTO','HOLD')),included boolean NOT NULL,
      actor_id uuid NOT NULL REFERENCES secm.user_account,recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      CONSTRAINT uq_reporting_candidate UNIQUE(tenant_id,profile_id,trade_id));
    CREATE INDEX ix_reporting_queue ON reg.transaction_candidate(tenant_id,strategy_id,profile_id,execution_date,candidate_id);
    CREATE TABLE reg.candidate_revision(
      candidate_id uuid NOT NULL REFERENCES reg.transaction_candidate,revision integer NOT NULL,
      tenant_id uuid NOT NULL REFERENCES ten.tenant,payload jsonb NOT NULL,
      actor_id uuid NOT NULL REFERENCES secm.user_account,recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      PRIMARY KEY(candidate_id,revision));
    CREATE TABLE reg.preparation_export(
      export_id uuid PRIMARY KEY,tenant_id uuid NOT NULL REFERENCES ten.tenant,
      profile_id uuid NOT NULL REFERENCES reg.reporting_profile,strategy_id uuid NOT NULL REFERENCES trd.strategy,
      request_key varchar(200) NOT NULL,request_hash varchar(64) NOT NULL,
      manifest jsonb NOT NULL,csv_content text NOT NULL,content_hash varchar(64) NOT NULL,
      actor_id uuid NOT NULL REFERENCES secm.user_account,recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      CONSTRAINT uq_reporting_export_request UNIQUE(tenant_id,request_key));
    CREATE FUNCTION reg.reject_retained_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN RAISE EXCEPTION 'Retained reporting evidence is immutable'; END; $$;
    CREATE TRIGGER profile_revision_immutable BEFORE UPDATE OR DELETE ON reg.profile_revision
      FOR EACH ROW EXECUTE FUNCTION reg.reject_retained_mutation();
    CREATE TRIGGER candidate_revision_immutable BEFORE UPDATE OR DELETE ON reg.candidate_revision
      FOR EACH ROW EXECUTE FUNCTION reg.reject_retained_mutation();
    CREATE TRIGGER preparation_export_immutable BEFORE UPDATE OR DELETE ON reg.preparation_export
      FOR EACH ROW EXECUTE FUNCTION reg.reject_retained_mutation();
    COMMENT ON SCHEMA reg IS 'Regulatory reporting preparation; exported does not mean submitted or accepted.';
    COMMENT ON TABLE reg.transaction_candidate IS 'Current review projection; immutable revisions preserve generated facts and reasoned human decisions.';
    COMMENT ON TABLE reg.preparation_export IS 'Frozen PREPARATION_ONLY CSV and manifest; not an FCA accepted submission format.';
    """)

def downgrade():
    raise RuntimeError('Retained reporting evidence cannot be safely downgraded')
