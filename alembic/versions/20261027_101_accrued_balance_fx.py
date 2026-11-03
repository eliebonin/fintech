"""Immutable derived accrued-interest balance dataset; no operating inputs seeded."""
from alembic import op

revision='20261027_101'
down_revision='20261027_100'
branch_labels=depends_on=None


def upgrade():
    op.execute('''CREATE TABLE nav.accrued_interest_balance (
      balance_id uuid PRIMARY KEY DEFAULT uuidv7(), attempt_id uuid NOT NULL, tenant_id uuid NOT NULL,
      strategy_id uuid NOT NULL REFERENCES trd.strategy(strategy_id),
      instrument_id uuid NOT NULL REFERENCES secm.instrument(instrument_node_id),
      currency_id uuid NOT NULL REFERENCES secm.currency(currency_id),
      reporting_currency_id uuid NOT NULL REFERENCES secm.currency(currency_id), value_date date NOT NULL,
      opening_balance numeric, daily_earned numeric, balance_movements numeric, coupon_paid numeric,
      closing_balance numeric, opening_fx numeric, closing_fx numeric, fx_pnl numeric,
      basis varchar(40) NOT NULL, fx_status varchar(30) NOT NULL, input_hash varchar(64) NOT NULL,
      evidence jsonb NOT NULL, recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      FOREIGN KEY(attempt_id,tenant_id) REFERENCES nav.valuation_attempt(attempt_id,tenant_id),
      CONSTRAINT uq_accrued_balance_attempt UNIQUE(attempt_id,instrument_id,currency_id,value_date),
      CONSTRAINT ck_accrued_balance_fx_status CHECK(fx_status IN ('CALCULATED','NOT_CALCULATED') AND
        ((fx_status='CALCULATED' AND fx_pnl IS NOT NULL) OR (fx_status='NOT_CALCULATED' AND fx_pnl IS NULL))))''')
    op.execute('CREATE INDEX ix_accrued_balance_strategy_date ON nav.accrued_interest_balance(tenant_id,strategy_id,value_date)')
    op.execute('''CREATE FUNCTION nav.protect_accrued_balance_snapshot() RETURNS trigger LANGUAGE plpgsql AS $$
      BEGIN
        IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'Accrued balance evidence is immutable'; END IF;
        IF NOT EXISTS(SELECT 1 FROM nav.valuation_attempt WHERE attempt_id=NEW.attempt_id AND tenant_id=NEW.tenant_id AND strategy_id=NEW.strategy_id)
          THEN RAISE EXCEPTION 'Accrued balance attempt scope mismatch'; END IF;
        IF NOT EXISTS(SELECT 1 FROM secm.instrument i JOIN secm.instrument_type t USING(instrument_type_id)
          WHERE i.instrument_node_id=NEW.instrument_id AND t.type_code='BOND')
          THEN RAISE EXCEPTION 'Accrued balance requires a canonical bond'; END IF;
        RETURN NEW;
      END $$''')
    op.execute('CREATE TRIGGER accrued_balance_evidence_guard BEFORE INSERT OR UPDATE OR DELETE ON nav.accrued_interest_balance FOR EACH ROW EXECUTE FUNCTION nav.protect_accrued_balance_snapshot()')
    op.execute("COMMENT ON TABLE nav.accrued_interest_balance IS 'Immutable per-attempt accrued stocks and FX attribution; derived output, never an implicitly trusted future input.'")
    columns=('balance_id','attempt_id','tenant_id','strategy_id','instrument_id','currency_id','reporting_currency_id','value_date',
             'opening_balance','daily_earned','balance_movements','coupon_paid','closing_balance','opening_fx','closing_fx','fx_pnl','basis','fx_status','input_hash','evidence','recorded_at')
    for name in columns:op.execute(f"COMMENT ON COLUMN nav.accrued_interest_balance.{name} IS 'Exact retained accrued-balance value or scoped source/attempt evidence: {name}'")
    # Insert one bounded owner branch without replacing any prior scope,
    # component-reconciliation or review-item guard. Fail atomically on drift.
    from sqlalchemy import text
    original=op.get_bind().scalar(text("SELECT pg_get_functiondef('nav.check_valuation_scope()'::regprocedure)"))
    anchor='ELSIF NEW.trade_id IS NOT NULL THEN'
    if original.count(anchor)!=1:raise RuntimeError('Unexpected valuation scope function; review before extending')
    branch='''ELSIF NEW.method='accrued-interest-receivable-fx-v1' THEN
          IF NEW.trade_id IS NOT NULL OR NEW.market_pnl<>0 OR
            NEW.evidence->>'resultFormat' IS DISTINCT FROM 'ACCRUED_RECEIVABLE_V1' OR
            NEW.evidence->'receivableScope'->>'tenantId' IS DISTINCT FROM NEW.tenant_id::text OR
            NEW.evidence->'receivableScope'->>'strategyId' IS DISTINCT FROM NEW.strategy_id::text OR
            NEW.evidence->'receivableScope'->>'instrumentId' IS DISTINCT FROM NEW.subject_id::text OR
            NEW.evidence->'identity'->'receivable'->>'instrumentId' IS DISTINCT FROM NEW.subject_id::text OR
            NEW.evidence->'identity'->'receivable'->>'currencyId' IS DISTINCT FROM NEW.evidence->'receivableScope'->>'currencyId' OR
            EXISTS(SELECT 1 FROM jsonb_object_keys(NEW.components) AS k WHERE k NOT IN
              ('CARRY','BROKER_FEE','CUSTODY_FEE','MANAGEMENT_FEE','PERFORMANCE_FEE','TAX','OTHER_COST','ADJUSTMENT')) OR
            NOT EXISTS(SELECT 1 FROM nav.accrued_interest_balance s WHERE
              s.attempt_id=(NEW.evidence->>'balanceSourceAttemptId')::uuid AND s.tenant_id=NEW.tenant_id AND
              s.strategy_id=NEW.strategy_id AND s.instrument_id=NEW.subject_id AND s.reporting_currency_id=NEW.currency_id AND
              s.currency_id=(NEW.evidence->'receivableScope'->>'currencyId')::uuid AND s.fx_pnl IS NOT NULL) THEN
            RAISE EXCEPTION 'accrued receivable scope/evidence mismatch';
          END IF;
          SELECT sum(s.fx_pnl) INTO market FROM nav.accrued_interest_balance s WHERE
            s.attempt_id=(NEW.evidence->>'balanceSourceAttemptId')::uuid AND s.tenant_id=NEW.tenant_id AND
            s.strategy_id=NEW.strategy_id AND s.instrument_id=NEW.subject_id AND
            s.currency_id=(NEW.evidence->'receivableScope'->>'currencyId')::uuid;
          IF market IS DISTINCT FROM (NEW.evidence->'storageRounding'->'exact'->'components'->>'CARRY')::numeric OR
             NEW.components->>'CARRY' IS NULL OR abs(market-(NEW.components->>'CARRY')::numeric)>0.0000000000005 THEN
            RAISE EXCEPTION 'accrued receivable amount differs from frozen balances';
          END IF;
        '''
    op.execute(original.replace(anchor,branch+anchor))


def downgrade():
    raise RuntimeError('Forward-only: retain accrued balance and FX evidence')
