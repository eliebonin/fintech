"""Durable ingestion jobs/attempts and evidence-based historical mapping reviews."""
from alembic import op

revision='20261007_64'
down_revision='20261007_63'
branch_labels=depends_on=None


def upgrade():
    op.execute("""
    CREATE TABLE md.market_data_ingestion_job (
      job_id UUID PRIMARY KEY DEFAULT uuidv7(), dataset_id UUID NOT NULL REFERENCES md.dataset(dataset_id),
      namespace_id UUID NOT NULL REFERENCES ing.external_id_namespace(external_id_namespace_id),
      tenant_id UUID NOT NULL REFERENCES ten.tenant(tenant_id), actor_id UUID NOT NULL REFERENCES secm.user_account(user_account_id),
      selection JSONB NOT NULL, request JSONB NOT NULL, status VARCHAR(20) NOT NULL DEFAULT 'RUNNING',
      started_at_utc TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP, finished_at_utc TIMESTAMPTZ,
      summary JSONB NOT NULL DEFAULT '{}',
      CONSTRAINT ck_md_job_status CHECK(status IN ('RUNNING','COMPLETE','PARTIAL','FAILED','BLOCKED','ABORTED')),
      CONSTRAINT ck_md_job_finished CHECK((status='RUNNING')=(finished_at_utc IS NULL))
    );
    CREATE TABLE md.market_data_ingestion_attempt (
      attempt_id UUID PRIMARY KEY DEFAULT uuidv7(), job_id UUID NOT NULL REFERENCES md.market_data_ingestion_job(job_id),
      symbol VARCHAR(100) NOT NULL, request JSONB NOT NULL, status VARCHAR(20) NOT NULL DEFAULT 'RUNNING',
      started_at_utc TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP, finished_at_utc TIMESTAMPTZ,
      delivery_run_id UUID REFERENCES md.market_data_ingestion_run(run_id), report JSONB NOT NULL DEFAULT '{}',
      CONSTRAINT ck_md_attempt_status CHECK(status IN ('RUNNING','COMPLETE','PARTIAL','FAILED','BLOCKED','ABORTED')),
      CONSTRAINT ck_md_attempt_finished CHECK((status='RUNNING')=(finished_at_utc IS NULL))
    );
    CREATE INDEX ix_md_attempt_job ON md.market_data_ingestion_attempt(job_id);
    CREATE TABLE md.market_data_mapping_history_review (
      review_id UUID PRIMARY KEY DEFAULT uuidv7(), mapping_id UUID NOT NULL REFERENCES ing.external_object_mapping(external_object_mapping_id),
      tenant_id UUID NOT NULL REFERENCES ten.tenant(tenant_id), actor_id UUID NOT NULL REFERENCES secm.user_account(user_account_id),
      market_from DATE NOT NULL, market_to DATE NOT NULL, decision VARCHAR(20) NOT NULL,
      evidence_reference TEXT NOT NULL, reviewed_at_utc TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
      supersedes_review_id UUID UNIQUE REFERENCES md.market_data_mapping_history_review(review_id),
      CONSTRAINT ck_md_history_review CHECK(decision IN ('APPROVED','REJECTED') AND market_to>=market_from AND length(trim(evidence_reference))>0)
    );
    CREATE FUNCTION md.protect_operational_terminal() RETURNS trigger AS $$
    BEGIN
      IF OLD.status<>'RUNNING' OR TG_OP='DELETE' THEN
        RAISE EXCEPTION 'terminal ingestion evidence cannot be changed or deleted';
      END IF;
      RETURN NEW;
    END; $$ LANGUAGE plpgsql;
    CREATE TRIGGER trg_md_job_terminal BEFORE UPDATE OR DELETE ON md.market_data_ingestion_job
      FOR EACH ROW EXECUTE FUNCTION md.protect_operational_terminal();
    CREATE TRIGGER trg_md_attempt_terminal BEFORE UPDATE OR DELETE ON md.market_data_ingestion_attempt
      FOR EACH ROW EXECUTE FUNCTION md.protect_operational_terminal();
    CREATE FUNCTION md.protect_history_review() RETURNS trigger AS $$
    BEGIN
      IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'historical review evidence is immutable'; END IF;
      PERFORM 1 FROM ing.external_object_mapping WHERE external_object_mapping_id=NEW.mapping_id FOR UPDATE;
      IF NEW.supersedes_review_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM md.market_data_mapping_history_review prior
        WHERE prior.review_id=NEW.supersedes_review_id AND prior.mapping_id=NEW.mapping_id
          AND prior.market_from=NEW.market_from AND prior.market_to=NEW.market_to
          AND NOT EXISTS(SELECT 1 FROM md.market_data_mapping_history_review newer WHERE newer.supersedes_review_id=prior.review_id)) THEN
        RAISE EXCEPTION 'historical review predecessor must be current and cover the same mapping/period';
      END IF;
      IF EXISTS(SELECT 1 FROM md.market_data_mapping_history_review WHERE mapping_id=NEW.mapping_id
        AND market_from<=NEW.market_to AND market_to>=NEW.market_from
        AND review_id IS DISTINCT FROM NEW.supersedes_review_id
        AND NOT EXISTS(SELECT 1 FROM md.market_data_mapping_history_review newer WHERE newer.supersedes_review_id=md.market_data_mapping_history_review.review_id)) THEN
        RAISE EXCEPTION 'historical review periods overlap';
      END IF;
      RETURN NEW;
    END; $$ LANGUAGE plpgsql;
    CREATE TRIGGER trg_md_history_review BEFORE INSERT OR UPDATE OR DELETE ON md.market_data_mapping_history_review
      FOR EACH ROW EXECUTE FUNCTION md.protect_history_review();
    COMMENT ON TABLE md.market_data_ingestion_job IS 'Operational lifecycle, separate from immutable deliveries and calendar completeness.';
    COMMENT ON TABLE md.market_data_ingestion_attempt IS 'Committed request attempts, including failures before a delivery can be published.';
    COMMENT ON TABLE md.market_data_mapping_history_review IS 'Attributed evidence for historical source-to-listing continuity, never inferred from current ticker.';
    """)


def downgrade():
    raise RuntimeError('Forward-only: operational and historical review evidence must not be discarded.')
