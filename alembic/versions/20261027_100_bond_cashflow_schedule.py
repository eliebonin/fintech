"""Full retained bond schedules: typed coupons and principal, preserving evidence."""
from alembic import op

revision = '20261027_100'
down_revision = '20261024_99'
branch_labels = depends_on = None


def upgrade():
    op.execute('ALTER TABLE secm.bond_coupon_schedule RENAME TO bond_cashflow_schedule')
    op.execute('ALTER TABLE secm.bond_coupon_period RENAME TO bond_cashflow')
    op.execute('ALTER TABLE secm.bond_cashflow RENAME COLUMN period_id TO cashflow_id')
    op.execute('ALTER TABLE secm.bond_cashflow RENAME COLUMN coupon_key TO cashflow_key')
    op.execute('ALTER TABLE secm.bond_cashflow RENAME COLUMN rate_formula TO amount_formula')
    # A constant default assigns the existing immutable rows their original type
    # without rewriting their values, identities, hashes or payment foreign keys.
    op.execute("ALTER TABLE secm.bond_cashflow ADD COLUMN cashflow_type varchar(20) NOT NULL DEFAULT 'COUPON'")
    op.execute('ALTER TABLE secm.bond_cashflow ALTER COLUMN accrual_start DROP NOT NULL')
    op.execute('ALTER TABLE secm.bond_cashflow ALTER COLUMN accrual_end DROP NOT NULL')
    op.execute('ALTER TABLE secm.bond_cashflow DROP CONSTRAINT ck_bond_coupon_period_dates')
    op.execute('ALTER TABLE secm.bond_cashflow DROP CONSTRAINT ck_bond_coupon_period_economics')
    op.execute("ALTER TABLE secm.bond_cashflow ADD CONSTRAINT ck_bond_cashflow_type CHECK(cashflow_type IN ('COUPON','PRINCIPAL'))")
    op.execute("""ALTER TABLE secm.bond_cashflow ADD CONSTRAINT ck_bond_cashflow_dates CHECK(
      (cashflow_type='COUPON' AND accrual_start IS NOT NULL AND accrual_end IS NOT NULL AND accrual_end>accrual_start AND payment_date>=accrual_start)
      OR (cashflow_type='PRINCIPAL' AND accrual_start IS NULL AND accrual_end IS NULL AND coupon_rate IS NULL AND record_date IS NULL AND ex_date IS NULL))""")
    op.execute("""ALTER TABLE secm.bond_cashflow ADD CONSTRAINT ck_bond_cashflow_economics CHECK(
      (cashflow_type='COUPON' AND (coupon_rate IS NOT NULL OR amount_per_100 IS NOT NULL OR amount_formula IS NOT NULL))
      OR (cashflow_type='PRINCIPAL' AND ((amount_per_100 IS NOT NULL AND amount_per_100>0) OR (amount_per_100 IS NULL AND amount_formula IS NOT NULL))))""")
    # PL/pgSQL's SQL text must follow the renamed relations. Keep every prior
    # ownership, cash-account and correction-chain guard, adding coupon type.
    op.execute("""CREATE OR REPLACE FUNCTION trd.check_bond_coupon_payment_scope() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF NOT EXISTS(SELECT 1 FROM trd.strategy WHERE strategy_id=NEW.strategy_id AND tenant_id=NEW.tenant_id)
        OR NOT EXISTS(SELECT 1 FROM secm.bond_cashflow p JOIN secm.bond_cashflow_schedule s USING(schedule_id)
          WHERE p.cashflow_id=NEW.period_id AND s.tenant_id=NEW.tenant_id AND p.cashflow_type='COUPON')
        THEN RAISE EXCEPTION 'Coupon payment scope/type mismatch'; END IF;
      IF NEW.cash_account_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM trd.cash_account WHERE cash_account_id=NEW.cash_account_id AND strategy_id=NEW.strategy_id)
        THEN RAISE EXCEPTION 'Coupon payment account scope mismatch'; END IF;
      IF (NEW.revision=1 AND (NEW.supersedes_payment_id IS NOT NULL OR NEW.status<>'CONFIRMED'))
        OR (NEW.revision>1 AND NOT EXISTS(SELECT 1 FROM trd.bond_coupon_payment WHERE payment_id=NEW.supersedes_payment_id
          AND logical_payment_id=NEW.logical_payment_id AND tenant_id=NEW.tenant_id AND strategy_id=NEW.strategy_id
          AND period_id=NEW.period_id AND revision=NEW.revision-1))
        THEN RAISE EXCEPTION 'Coupon payment revision mismatch'; END IF;
      RETURN NEW;
    END $$""")
    for table in ('secm.bond_cashflow_schedule', 'secm.bond_cashflow', 'trd.bond_coupon_payment'):
        op.execute(f"COMMENT ON TABLE {table} IS 'Retained bond cashflow schedule/coupon payment facts. No automatic earnings, cash or trade posting.'")
    for column, comment in {
        'cashflow_id': 'Retained payment identity; existing coupon confirmations keep this identity.',
        'cashflow_key': 'Unique sourced human key within one schedule revision.',
        'cashflow_type': 'COUPON or PRINCIPAL. Expected contractual event, not confirmation of settlement.',
        'amount_per_100': 'Exact amount in schedule currency per 100 original nominal; null is unknown, never assumed zero.',
        'amount_formula': 'Sourced formula for a not-yet-fixed cashflow amount; never evaluated implicitly.',
    }.items():
        op.execute(f"COMMENT ON COLUMN secm.bond_cashflow.{column} IS '{comment}'")


def downgrade():
    raise RuntimeError('Forward-only: retain full bond schedules and coupon-payment history')
