"""Typed cash-owned P&L versions, retaining all prior review/scope safeguards."""
from alembic import op

revision='20261024_99'
down_revision='20261023_98'
branch_labels=depends_on=None


def upgrade():
    op.execute('ALTER TABLE trd.cash_account ADD CONSTRAINT uq_cash_account_strategy UNIQUE(cash_account_id,strategy_id)')
    op.execute('''ALTER TABLE nav.pnl_attribution
      ADD COLUMN cash_account_id uuid, ADD COLUMN cash_currency_id uuid REFERENCES secm.currency(currency_id),
      ADD CONSTRAINT fk_pnl_cash_strategy FOREIGN KEY(cash_account_id,strategy_id) REFERENCES trd.cash_account(cash_account_id,strategy_id),
      ADD CONSTRAINT uq_pnl_cash_version UNIQUE(tenant_id,strategy_id,value_date,cash_account_id,cash_currency_id,version),
      DROP CONSTRAINT ck_pnl_result_owner,
      ADD CONSTRAINT ck_pnl_result_owner CHECK (
        (((trade_id IS NOT NULL AND position_key IS NULL AND subject_id IS NULL) OR
          (trade_id IS NULL AND position_key IS NOT NULL AND subject_id IS NOT NULL)) AND cash_account_id IS NULL AND cash_currency_id IS NULL) OR
        (trade_id IS NULL AND position_key IS NULL AND subject_id IS NULL AND cash_account_id IS NOT NULL AND cash_currency_id IS NOT NULL))''')
    op.execute('''ALTER TABLE nav.pnl_review_item
      ADD COLUMN cash_account_id uuid REFERENCES trd.cash_account(cash_account_id),
      ADD COLUMN cash_currency_id uuid REFERENCES secm.currency(currency_id),
      ADD CONSTRAINT uq_pnl_review_cash UNIQUE(batch_id,cash_account_id,cash_currency_id),
      DROP CONSTRAINT ck_pnl_item_owner,
      ADD CONSTRAINT ck_pnl_item_owner CHECK (
        (((trade_id IS NULL) <> (position_key IS NULL)) AND cash_account_id IS NULL AND cash_currency_id IS NULL) OR
        (trade_id IS NULL AND position_key IS NULL AND cash_account_id IS NOT NULL AND cash_currency_id IS NOT NULL))''')
    op.execute('CREATE INDEX ix_cash_balance_pnl_inputs ON trd.cash_balance(strategy_id,balance_as_of_date,received_at_utc) WHERE source_system_id=\'TENANT_EOD\'')
    # API cash writers already lock this strategy. Cover direct native inserts
    # too: FK KEY SHARE alone is compatible with publication's NO KEY UPDATE.
    op.execute('''CREATE FUNCTION trd.serialize_cash_valuation_inputs() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF NEW.source_system_id='TENANT_EOD' THEN
        PERFORM 1 FROM trd.strategy WHERE strategy_id=NEW.strategy_id FOR NO KEY UPDATE;
        IF NOT EXISTS (SELECT 1 FROM trd.cash_account WHERE cash_account_id=NEW.cash_account_id AND strategy_id=NEW.strategy_id) THEN
          RAISE EXCEPTION 'cash snapshot strategy/account mismatch';
        END IF;
      END IF;
      RETURN NEW;
    END $$''')
    op.execute('''CREATE TRIGGER cash_valuation_inputs_lock BEFORE INSERT ON trd.cash_balance
      FOR EACH ROW EXECUTE FUNCTION trd.serialize_cash_valuation_inputs()''')
    # Restate the existing trigger, preserving tenant/attempt/date/item checks,
    # exact numeric reconciliation and immutable financial/audit triggers.
    op.execute('''CREATE OR REPLACE FUNCTION nav.check_valuation_scope() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE owner uuid; parent_strategy uuid; parent_date date; selected_trade uuid; selected_position text;
      selected_cash uuid; selected_currency uuid; market numeric; gross numeric; net numeric; component record;
    BEGIN
      IF TG_TABLE_NAME IN ('valuation_attempt','pnl_attribution','pnl_review_batch') THEN
        SELECT tenant_id INTO owner FROM trd.strategy WHERE strategy_id=NEW.strategy_id;
        IF owner IS DISTINCT FROM NEW.tenant_id THEN RAISE EXCEPTION 'valuation strategy tenant mismatch'; END IF;
      END IF;
      IF TG_TABLE_NAME IN ('pnl_attribution','pnl_review_batch') THEN
        SELECT strategy_id INTO parent_strategy FROM nav.valuation_attempt WHERE attempt_id=NEW.attempt_id AND tenant_id=NEW.tenant_id;
        IF parent_strategy IS DISTINCT FROM NEW.strategy_id THEN RAISE EXCEPTION 'valuation attempt scope mismatch'; END IF;
      END IF;
      IF TG_TABLE_NAME='pnl_attribution' THEN
        IF NEW.cash_account_id IS NOT NULL THEN
          IF NEW.method <> 'cash-fx-opening-balance-v1' OR
             NEW.evidence->'cashFx'->>'account_id' IS DISTINCT FROM NEW.cash_account_id::text OR
             NEW.evidence->'cashFx'->>'currency_id' IS DISTINCT FROM NEW.cash_currency_id::text OR
             NEW.evidence->'cashFx'->>'strategy_id' IS DISTINCT FROM NEW.strategy_id::text OR
             NEW.evidence->'cashFx'->>'tenant_id' IS DISTINCT FROM NEW.tenant_id::text OR NEW.market_pnl<>0 THEN
            RAISE EXCEPTION 'cash attribution scope mismatch';
          END IF;
        ELSIF NEW.trade_id IS NOT NULL THEN
          SELECT strategy_id INTO parent_strategy FROM trd.trade WHERE trade_id=NEW.trade_id;
          IF parent_strategy IS DISTINCT FROM NEW.strategy_id THEN RAISE EXCEPTION 'attribution trade scope mismatch'; END IF;
        ELSE
          IF NEW.method NOT IN ('listed-equity-position-market-pnl-v2','economic-position-pnl-v3') OR
             NEW.evidence->'identity'->'bucket'->'key'->>'subject_id' IS DISTINCT FROM NEW.subject_id::text OR
             NEW.evidence->'identity'->'bucket'->'key'->>'strategy_id' IS DISTINCT FROM NEW.strategy_id::text OR
             NEW.evidence->'identity'->'bucket'->'key'->>'tenant_id' IS DISTINCT FROM NEW.tenant_id::text THEN
            RAISE EXCEPTION 'position attribution scope mismatch';
          END IF;
        END IF;
        market:=0; gross:=0; net:=0;
        FOR component IN SELECT key,value FROM jsonb_each_text(NEW.components) LOOP
          IF component.key IN ('PRICE','FX','PRICE_FX_CROSS','MODEL_MARK_CHANGE') THEN market:=market+component.value::numeric;
          ELSIF component.key='CASH_FX' THEN
            IF NEW.cash_account_id IS NULL THEN RAISE EXCEPTION 'cash FX requires a cash owner'; END IF;
            gross:=gross+component.value::numeric;
          ELSIF component.key IN ('ACCRUAL','CARRY','COUPON','DIVIDEND','RESET','CASHFLOW') THEN gross:=gross+component.value::numeric;
          ELSIF component.key IN ('BROKER_FEE','CUSTODY_FEE','MANAGEMENT_FEE','PERFORMANCE_FEE','TAX','OTHER_COST','ADJUSTMENT') THEN net:=net+component.value::numeric;
          ELSE RAISE EXCEPTION 'unsupported attribution component'; END IF;
        END LOOP;
        gross:=gross+market; net:=net+gross;
        IF market<>NEW.market_pnl OR gross<>NEW.gross_pnl OR net<>NEW.net_pnl THEN RAISE EXCEPTION 'attribution components do not reconcile'; END IF;
      END IF;
      IF TG_TABLE_NAME='pnl_review_item' THEN
        SELECT strategy_id,value_date INTO parent_strategy,parent_date FROM nav.pnl_review_batch WHERE batch_id=NEW.batch_id AND tenant_id=NEW.tenant_id;
        SELECT trade_id,position_key,cash_account_id,cash_currency_id INTO selected_trade,selected_position,selected_cash,selected_currency FROM nav.pnl_attribution
          WHERE attribution_id=NEW.attribution_id AND tenant_id=NEW.tenant_id AND strategy_id=parent_strategy AND value_date=parent_date;
        IF NOT FOUND OR selected_trade IS DISTINCT FROM NEW.trade_id OR selected_position IS DISTINCT FROM NEW.position_key OR
          selected_cash IS DISTINCT FROM NEW.cash_account_id OR selected_currency IS DISTINCT FROM NEW.cash_currency_id THEN
          RAISE EXCEPTION 'review attribution scope mismatch';
        END IF;
      END IF;
      RETURN NEW;
    END $$''')
    for table in ('pnl_attribution','pnl_review_item'):
        op.execute(f"COMMENT ON COLUMN nav.{table}.cash_account_id IS 'Typed cash account attribution owner; no synthetic trade or instrument.'")
        op.execute(f"COMMENT ON COLUMN nav.{table}.cash_currency_id IS 'Native cash currency; distinct from attribution reporting currency.'")
    op.execute("COMMENT ON COLUMN nav.pnl_attribution.gross_pnl IS 'Investment market P&L plus separately attributed cash FX and recognized income, before costs.'")


def downgrade():
    raise RuntimeError('Forward-only: preserve cash P&L ownership and published evidence')
