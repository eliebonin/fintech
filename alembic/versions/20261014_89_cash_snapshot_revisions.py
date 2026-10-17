"""Dated tenant cash input revisions, preserving existing balance records."""
from alembic import op

revision='20261014_89'
down_revision='20261014_88'
branch_labels=None
depends_on=None


def upgrade():
    op.execute('ALTER TABLE trd.cash_account ADD COLUMN display_label varchar(100)')
    op.execute('CREATE UNIQUE INDEX uq_cash_account_label ON trd.cash_account(strategy_id,display_label)')
    op.execute('''ALTER TABLE trd.cash_balance
        ADD COLUMN revision integer NOT NULL DEFAULT 1 CHECK (revision>0),
        ADD COLUMN supersedes_balance_id uuid REFERENCES trd.cash_balance(cash_balance_id),
        ADD COLUMN note varchar(2000), ADD COLUMN correction_reason varchar(2000),
        ADD COLUMN submission_key varchar(255), ADD COLUMN request_hash varchar(64)''')
    op.execute('DROP INDEX trd.uq_cash_balance_snapshot_source')
    op.execute('''CREATE UNIQUE INDEX uq_cash_balance_snapshot_source ON trd.cash_balance
        (strategy_id,COALESCE(cash_account_id,'00000000-0000-0000-0000-000000000000'::uuid),
        currency_id,balance_as_of_datetime_utc,balance_type,COALESCE(source_system_id,''),revision)''')
    op.execute('''CREATE UNIQUE INDEX uq_cash_balance_submission ON trd.cash_balance(strategy_id,submission_key)
        WHERE submission_key IS NOT NULL''')
    op.execute('''CREATE FUNCTION trd.guard_eod_cash_snapshot() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN IF OLD.source_system_id='TENANT_EOD' THEN
            RAISE EXCEPTION 'EoD cash snapshots are immutable; append a correction';
        END IF; IF TG_OP='DELETE' THEN RETURN OLD; END IF; RETURN NEW; END $$''')
    op.execute('''CREATE TRIGGER immutable_eod_cash_snapshot BEFORE UPDATE OR DELETE ON trd.cash_balance
        FOR EACH ROW EXECUTE FUNCTION trd.guard_eod_cash_snapshot()''')


def downgrade():
    raise RuntimeError('Forward-only: preserve dated cash input revision evidence')
