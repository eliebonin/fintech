"""Controlled amendment requests preserve immutable financial versions."""
from alembic import op
revision='20261009_80'
down_revision='20261009_79'
branch_labels=depends_on=None


def upgrade():
    op.execute("""
    CREATE TABLE nav.pnl_amendment_request (
      request_id uuid PRIMARY KEY DEFAULT uuidv7(), tenant_id uuid NOT NULL REFERENCES ten.tenant,
      strategy_id uuid NOT NULL REFERENCES trd.strategy, requested_by uuid NOT NULL REFERENCES secm.user_account,
      base_batch_id uuid NOT NULL, base_attribution_id uuid NOT NULL, population_hash varchar(64) NOT NULL,
      submission_key varchar(255) NOT NULL, request_hash varchar(64) NOT NULL, component varchar(40) NOT NULL,
      amount numeric(30,12) NOT NULL, reason varchar(2000) NOT NULL, source_reference varchar(500) NOT NULL,
      status varchar(20) NOT NULL, reviewed_by uuid REFERENCES secm.user_account, review_comment varchar(2000),
      applied_batch_id uuid REFERENCES nav.pnl_review_batch, created_at timestamptz NOT NULL DEFAULT clock_timestamp(), reviewed_at timestamptz,
      CONSTRAINT uq_pnl_amendment_key UNIQUE(tenant_id,submission_key),
      FOREIGN KEY(base_batch_id,tenant_id) REFERENCES nav.pnl_review_batch(batch_id,tenant_id),
      FOREIGN KEY(base_attribution_id,tenant_id) REFERENCES nav.pnl_attribution(attribution_id,tenant_id),
      CONSTRAINT ck_pnl_amendment_status CHECK(status IN ('PENDING','APPLIED','REJECTED','STALE')));
    CREATE INDEX ix_pnl_amendment_batch ON nav.pnl_amendment_request(base_batch_id,status);
    CREATE FUNCTION nav.protect_pnl_amendment() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_OP='DELETE' THEN RAISE EXCEPTION 'amendment audit is immutable'; END IF;
      IF TG_OP='INSERT' THEN
        IF NEW.status<>'PENDING' OR NOT EXISTS(
          SELECT 1 FROM nav.pnl_review_batch b JOIN nav.pnl_review_item i ON i.batch_id=b.batch_id
          WHERE b.batch_id=NEW.base_batch_id AND b.tenant_id=NEW.tenant_id AND b.strategy_id=NEW.strategy_id
          AND b.status='STAGED' AND i.attribution_id=NEW.base_attribution_id)
          THEN RAISE EXCEPTION 'amendment base scope/state mismatch'; END IF;
      ELSE
        IF OLD.status<>'PENDING' OR NEW.status='PENDING' OR
          (to_jsonb(NEW)-ARRAY['status','reviewed_by','review_comment','applied_batch_id','reviewed_at']) IS DISTINCT FROM
          (to_jsonb(OLD)-ARRAY['status','reviewed_by','review_comment','applied_batch_id','reviewed_at'])
          THEN RAISE EXCEPTION 'amendment request evidence is immutable'; END IF;
        IF NEW.status='APPLIED' AND (NEW.reviewed_by=NEW.requested_by OR NEW.reviewed_by IS NULL OR NEW.applied_batch_id IS NULL)
          THEN RAISE EXCEPTION 'independent amendment approval required'; END IF;
        IF NEW.status='APPLIED' AND NOT EXISTS(SELECT 1 FROM nav.pnl_review_batch
          WHERE batch_id=NEW.applied_batch_id AND tenant_id=NEW.tenant_id AND strategy_id=NEW.strategy_id AND status='STAGED')
          THEN RAISE EXCEPTION 'amended candidate scope/state mismatch'; END IF;
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER protect_pnl_amendment BEFORE INSERT OR UPDATE OR DELETE ON nav.pnl_amendment_request
      FOR EACH ROW EXECUTE FUNCTION nav.protect_pnl_amendment();
    """)


def downgrade():
    raise RuntimeError('Forward-only: amendment requests and retained financial history.')
