"""Immutable position-level daily accrued-interest inputs and revisions."""
from alembic import op

revision='20261009_79'
down_revision='20261009_78'
branch_labels=depends_on=None


def upgrade():
    op.execute("""
    CREATE TABLE nav.daily_accrual_input (
      input_id uuid PRIMARY KEY DEFAULT uuidv7(), tenant_id uuid NOT NULL REFERENCES ten.tenant,
      strategy_id uuid NOT NULL REFERENCES trd.strategy, recorded_by uuid NOT NULL REFERENCES secm.user_account,
      instrument_id uuid NOT NULL REFERENCES secm.instrument, value_date date NOT NULL,
      input_type varchar(30) NOT NULL, revision integer NOT NULL,
      supersedes_input_id uuid REFERENCES nav.daily_accrual_input,
      submission_key varchar(255) NOT NULL, input_hash varchar(64) NOT NULL, request_hash varchar(64) NOT NULL,
      payload jsonb NOT NULL, recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      CONSTRAINT uq_accrual_submission UNIQUE(tenant_id,submission_key),
      CONSTRAINT uq_accrual_revision UNIQUE(tenant_id,strategy_id,instrument_id,value_date,input_type,revision),
      CONSTRAINT ck_accrual_type_revision CHECK(input_type='DAILY_INTEREST' AND revision>0));
    CREATE INDEX ix_accrual_asof ON nav.daily_accrual_input(tenant_id,strategy_id,value_date,recorded_at);
    CREATE TRIGGER daily_accrual_immutable BEFORE UPDATE OR DELETE ON nav.daily_accrual_input
      FOR EACH ROW EXECUTE FUNCTION nav.protect_pnl_evidence();
    CREATE FUNCTION nav.check_accrual_scope() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF NOT EXISTS(SELECT 1 FROM trd.strategy WHERE strategy_id=NEW.strategy_id AND tenant_id=NEW.tenant_id)
        THEN RAISE EXCEPTION 'accrual strategy tenant mismatch'; END IF;
      IF NEW.supersedes_input_id IS NOT NULL AND NOT EXISTS(
        SELECT 1 FROM nav.daily_accrual_input WHERE input_id=NEW.supersedes_input_id AND tenant_id=NEW.tenant_id
          AND strategy_id=NEW.strategy_id AND instrument_id=NEW.instrument_id AND value_date=NEW.value_date
          AND input_type=NEW.input_type AND revision=NEW.revision-1 AND recorded_at<=NEW.recorded_at)
        THEN RAISE EXCEPTION 'accrual revision scope mismatch'; END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER check_accrual_scope BEFORE INSERT ON nav.daily_accrual_input
      FOR EACH ROW EXECUTE FUNCTION nav.check_accrual_scope();
    """)


def downgrade():
    raise RuntimeError('Forward-only: retained daily accrual audit evidence.')
