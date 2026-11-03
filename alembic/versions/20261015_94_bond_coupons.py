"""Retained coupon schedule and payment facts; no financial postings."""
from alembic import op

revision='20261015_94'
down_revision='20261014_93'
branch_labels=depends_on=None


def upgrade():
    # Freeze this historical schema. Importing mutable application tables here
    # would make a fresh install skip the original schema before migration 100.
    op.execute('''CREATE TABLE secm.bond_coupon_schedule (
      schedule_id uuid PRIMARY KEY DEFAULT uuidv7(),
      tenant_id uuid NOT NULL REFERENCES ten.tenant(tenant_id),
      instrument_id uuid NOT NULL REFERENCES secm.instrument(instrument_node_id),
      bond_terms_id uuid NOT NULL REFERENCES secm.bond_terms(bond_terms_id),
      terms_snapshot jsonb NOT NULL, revision integer NOT NULL,
      supersedes_schedule_id uuid REFERENCES secm.bond_coupon_schedule(schedule_id),
      currency_id uuid NOT NULL REFERENCES secm.currency(currency_id),
      calendar_id uuid REFERENCES cal.market_calendar(market_calendar_id),
      day_count_convention_id uuid REFERENCES secm.day_count_convention(day_count_convention_id),
      business_day_convention varchar(40), source_reference varchar(2000) NOT NULL,
      reason varchar(2000) NOT NULL, request_key varchar(255) NOT NULL, request_hash varchar(64) NOT NULL,
      actor_id uuid NOT NULL REFERENCES secm.user_account(user_account_id),
      real_operator_id uuid NOT NULL REFERENCES secm.user_account(user_account_id),
      recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      CONSTRAINT uq_bond_coupon_schedule_revision UNIQUE(tenant_id,instrument_id,revision),
      CONSTRAINT uq_bond_coupon_schedule_request UNIQUE(tenant_id,request_key),
      CONSTRAINT ck_bond_coupon_schedule_revision CHECK(revision>0))''')
    op.execute('''CREATE TABLE secm.bond_coupon_period (
      period_id uuid PRIMARY KEY DEFAULT uuidv7(),
      schedule_id uuid NOT NULL REFERENCES secm.bond_coupon_schedule(schedule_id),
      coupon_key varchar(100) NOT NULL, accrual_start date NOT NULL, accrual_end date NOT NULL,
      payment_date date NOT NULL, record_date date, ex_date date,
      coupon_rate numeric(20,12), amount_per_100 numeric(30,12), rate_formula varchar(2000),
      CONSTRAINT uq_bond_coupon_period_key UNIQUE(schedule_id,coupon_key),
      CONSTRAINT ck_bond_coupon_period_dates CHECK(accrual_end>accrual_start AND payment_date>=accrual_start),
      CONSTRAINT ck_bond_coupon_period_economics CHECK(coupon_rate IS NOT NULL OR amount_per_100 IS NOT NULL OR rate_formula IS NOT NULL))''')
    op.execute('''CREATE TABLE trd.bond_coupon_payment (
      payment_id uuid PRIMARY KEY DEFAULT uuidv7(), logical_payment_id uuid NOT NULL,
      tenant_id uuid NOT NULL REFERENCES ten.tenant(tenant_id),
      strategy_id uuid NOT NULL REFERENCES trd.strategy(strategy_id),
      period_id uuid NOT NULL REFERENCES secm.bond_coupon_period(period_id), revision integer NOT NULL,
      supersedes_payment_id uuid REFERENCES trd.bond_coupon_payment(payment_id), status varchar(20) NOT NULL,
      payment_date date NOT NULL, amount numeric(30,12) NOT NULL,
      currency_id uuid NOT NULL REFERENCES secm.currency(currency_id),
      cash_account_id uuid REFERENCES trd.cash_account(cash_account_id),
      source_reference varchar(2000) NOT NULL, note varchar(2000) NOT NULL,
      request_key varchar(255) NOT NULL, request_hash varchar(64) NOT NULL,
      actor_id uuid NOT NULL REFERENCES secm.user_account(user_account_id),
      real_operator_id uuid NOT NULL REFERENCES secm.user_account(user_account_id),
      recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      CONSTRAINT uq_bond_coupon_payment_revision UNIQUE(logical_payment_id,revision),
      CONSTRAINT uq_bond_coupon_payment_request UNIQUE(tenant_id,request_key),
      CONSTRAINT ck_bond_coupon_payment_status CHECK(revision>0 AND status IN ('CONFIRMED','REVERSED')),
      CONSTRAINT ck_bond_coupon_payment_amount CHECK(amount<>0 AND amount>-1000000000000000000 AND amount<1000000000000000000))''')
    op.execute('CREATE INDEX ix_bond_coupon_payment_report ON trd.bond_coupon_payment(tenant_id,strategy_id,payment_date)')
    op.execute("""CREATE FUNCTION secm.protect_bond_coupon_evidence() RETURNS trigger LANGUAGE plpgsql AS $$
      BEGIN RAISE EXCEPTION 'Coupon evidence is immutable'; END $$""")
    for table in ('secm.bond_coupon_schedule','secm.bond_coupon_period','trd.bond_coupon_payment'):
        op.execute(f'CREATE TRIGGER immutable_{table.split(".")[1]} BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION secm.protect_bond_coupon_evidence()')
        op.execute(f"COMMENT ON TABLE {table} IS 'Retained coupon schedule/payment facts. No automatic earnings, cash or trade posting.'")
        columns=op.get_bind().exec_driver_sql("SELECT column_name FROM information_schema.columns WHERE table_schema=%s AND table_name=%s",tuple(table.split('.'))).scalars()
        for column in columns:
            op.execute(f"COMMENT ON COLUMN {table}.{column} IS 'Coupon source, scope, date or immutable revision identity: {column}'")
    op.execute("""CREATE FUNCTION trd.check_bond_coupon_payment_scope() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF NOT EXISTS(SELECT 1 FROM trd.strategy WHERE strategy_id=NEW.strategy_id AND tenant_id=NEW.tenant_id)
        OR NOT EXISTS(SELECT 1 FROM secm.bond_coupon_period p JOIN secm.bond_coupon_schedule s USING(schedule_id)
          WHERE p.period_id=NEW.period_id AND s.tenant_id=NEW.tenant_id)
        THEN RAISE EXCEPTION 'Coupon payment scope mismatch'; END IF;
      IF NEW.cash_account_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM trd.cash_account WHERE cash_account_id=NEW.cash_account_id AND strategy_id=NEW.strategy_id)
        THEN RAISE EXCEPTION 'Coupon payment account scope mismatch'; END IF;
      IF (NEW.revision=1 AND (NEW.supersedes_payment_id IS NOT NULL OR NEW.status<>'CONFIRMED'))
        OR (NEW.revision>1 AND NOT EXISTS(SELECT 1 FROM trd.bond_coupon_payment WHERE payment_id=NEW.supersedes_payment_id
          AND logical_payment_id=NEW.logical_payment_id AND tenant_id=NEW.tenant_id AND strategy_id=NEW.strategy_id
          AND period_id=NEW.period_id AND revision=NEW.revision-1))
        THEN RAISE EXCEPTION 'Coupon payment revision mismatch'; END IF;
      RETURN NEW;
    END $$""")
    op.execute('CREATE TRIGGER coupon_payment_scope BEFORE INSERT ON trd.bond_coupon_payment FOR EACH ROW EXECUTE FUNCTION trd.check_bond_coupon_payment_scope()')


def downgrade():
    raise RuntimeError('Forward-only: retain coupon schedule and payment audit')
