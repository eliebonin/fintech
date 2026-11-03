"""Retained source balances and independently maintained local balance history."""
from alembic import op
revision='20261031_108'
down_revision='20261031_107'
branch_labels=depends_on=None


def upgrade():
    from security_master_schema import models as m
    from valuation import balance_history_tables as t
    for table in (t.balance_input,t.history_build,t.history_day):table.create(op.get_bind(),checkfirst=False)
    op.execute("""CREATE FUNCTION nav.protect_balance_history() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'Accrued balance sources and history are immutable; append a revision'; END IF;
      IF NOT EXISTS(SELECT 1 FROM trd.strategy s WHERE s.strategy_id=NEW.strategy_id AND s.tenant_id=NEW.tenant_id)
        THEN RAISE EXCEPTION 'Accrued balance strategy scope mismatch'; END IF;
      IF TG_TABLE_NAME<>'accrued_balance_build' THEN
        IF NOT EXISTS(SELECT 1 FROM secm.instrument i JOIN secm.instrument_type t USING(instrument_type_id)
          WHERE i.instrument_node_id=NEW.instrument_id AND t.type_code='BOND')
          THEN RAISE EXCEPTION 'Maintained accrued balance requires a canonical bond'; END IF;
        IF EXISTS(SELECT 1 FROM ten.reference_node_scope s WHERE s.reference_node_id=NEW.instrument_id
          AND (s.status<>'ACTIVE' OR s.scope_type='TENANT_PRIVATE' AND s.owner_tenant_id<>NEW.tenant_id))
          THEN RAISE EXCEPTION 'Accrued balance instrument scope mismatch'; END IF;
      END IF;
      IF TG_TABLE_NAME='accrued_balance_input' THEN
        IF NOT EXISTS(SELECT 1 FROM secm.instrument i WHERE i.instrument_node_id=NEW.instrument_id AND i.base_currency_id=NEW.currency_id)
          THEN RAISE EXCEPTION 'Supplied accrued balance must use the canonical monetary currency'; END IF;
        IF (NEW.revision=1 AND NEW.supersedes_input_id IS NOT NULL) OR
          (NEW.revision>1 AND NOT EXISTS(SELECT 1 FROM nav.accrued_balance_input p WHERE p.input_id=NEW.supersedes_input_id
            AND p.tenant_id=NEW.tenant_id AND p.strategy_id=NEW.strategy_id AND p.instrument_id=NEW.instrument_id
            AND p.currency_id=NEW.currency_id AND p.value_date=NEW.value_date AND p.revision=NEW.revision-1))
          THEN RAISE EXCEPTION 'Accrued balance revision scope mismatch'; END IF;
      ELSIF TG_TABLE_NAME='accrued_balance_history' THEN
        IF NOT EXISTS(SELECT 1 FROM nav.accrued_balance_build b WHERE b.build_id=NEW.build_id AND b.tenant_id=NEW.tenant_id
          AND b.strategy_id=NEW.strategy_id AND NEW.value_date BETWEEN b.from_date AND b.to_date)
          THEN RAISE EXCEPTION 'Accrued history build/date scope mismatch'; END IF;
        IF NEW.basis='DERIVED' AND NEW.opening_balance IS NOT NULL AND NEW.daily_earned IS NOT NULL
          AND NEW.trade_movements IS NOT NULL AND NEW.coupon_paid IS NOT NULL
          AND NEW.closing_balance IS DISTINCT FROM NEW.opening_balance+NEW.daily_earned+NEW.trade_movements-NEW.coupon_paid
          THEN RAISE EXCEPTION 'Derived accrued balance bridge mismatch'; END IF;
      END IF;
      RETURN NEW;
    END $$;""")
    for table in (t.balance_input,t.history_build,t.history_day):
        op.execute(f'CREATE TRIGGER {table.name}_guard BEFORE INSERT OR UPDATE OR DELETE ON nav.{table.name} FOR EACH ROW EXECUTE FUNCTION nav.protect_balance_history()')


def downgrade():raise RuntimeError('Forward-only: retain supplied balances and materialized history')
