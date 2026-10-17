"""Retained coupon schedule and payment facts; no financial postings."""
from alembic import op
from lifecycle import coupon_tables as t
from security_master_schema import models as m

revision='20261015_94'
down_revision='20261014_93'
branch_labels=depends_on=None


def upgrade():
    for table in (t.schedule,t.period,t.payment): table.create(op.get_bind())
    op.execute("""CREATE FUNCTION secm.protect_bond_coupon_evidence() RETURNS trigger LANGUAGE plpgsql AS $$
      BEGIN RAISE EXCEPTION 'Coupon evidence is immutable'; END $$""")
    for table in (t.schedule,t.period,t.payment):
        op.execute(f'CREATE TRIGGER immutable_{table.name} BEFORE UPDATE OR DELETE ON {table.schema}.{table.name} FOR EACH ROW EXECUTE FUNCTION secm.protect_bond_coupon_evidence()')
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
