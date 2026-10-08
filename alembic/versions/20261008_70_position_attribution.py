"""Explicit position ownership and immutable execution lineage; preserve v1 rows."""
from alembic import op
revision='20261008_70'
down_revision='20261007_69'
branch_labels=depends_on=None

def upgrade():
    op.execute("""
    ALTER TABLE nav.pnl_attribution ALTER COLUMN trade_id DROP NOT NULL;
    ALTER TABLE nav.pnl_attribution ADD COLUMN position_key varchar(64),
      ADD COLUMN subject_id uuid REFERENCES secm.financial_reference_node(reference_node_id),
      ADD CONSTRAINT ck_pnl_result_owner CHECK (
        (trade_id IS NOT NULL AND position_key IS NULL AND subject_id IS NULL) OR
        (trade_id IS NULL AND position_key IS NOT NULL AND subject_id IS NOT NULL)),
      ADD CONSTRAINT uq_pnl_position_version UNIQUE(tenant_id,strategy_id,value_date,position_key,version);
    ALTER TABLE nav.pnl_review_item ALTER COLUMN trade_id DROP NOT NULL;
    ALTER TABLE nav.pnl_review_item ADD COLUMN position_key varchar(64),
      ADD CONSTRAINT ck_pnl_item_owner CHECK ((trade_id IS NULL) <> (position_key IS NULL)),
      ADD CONSTRAINT uq_pnl_review_position UNIQUE(batch_id,position_key);
    CREATE TABLE nav.pnl_attribution_lineage (
      lineage_id uuid PRIMARY KEY DEFAULT uuidv7(),
      attribution_id uuid NOT NULL REFERENCES nav.pnl_attribution(attribution_id),
      trade_id uuid NOT NULL REFERENCES trd.trade(trade_id),
      event_id uuid NOT NULL REFERENCES trd.trade_lifecycle_event(trade_lifecycle_event_id),
      role varchar(30) NOT NULL CHECK(role IN ('OPENING_EVIDENCE','PERIOD_EXECUTION','LIFECYCLE_EVIDENCE')),
      CONSTRAINT uq_pnl_lineage_event UNIQUE(attribution_id,event_id));
    CREATE TRIGGER protect_pnl_lineage BEFORE UPDATE OR DELETE ON nav.pnl_attribution_lineage
      FOR EACH ROW EXECUTE FUNCTION nav.protect_pnl_evidence();
    CREATE OR REPLACE FUNCTION nav.check_valuation_scope() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE owner uuid; parent_strategy uuid; parent_date date; selected_trade uuid; selected_position text;
      market numeric; gross numeric; net numeric; component record;
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
        IF NEW.trade_id IS NOT NULL THEN
          SELECT strategy_id INTO parent_strategy FROM trd.trade WHERE trade_id=NEW.trade_id;
          IF parent_strategy IS DISTINCT FROM NEW.strategy_id THEN RAISE EXCEPTION 'attribution trade scope mismatch'; END IF;
        ELSE
          IF NEW.method <> 'listed-equity-position-market-pnl-v2' OR
             NEW.evidence->'identity'->'bucket'->'key'->>'subject_id' IS DISTINCT FROM NEW.subject_id::text OR
             NEW.evidence->'identity'->'bucket'->'key'->>'strategy_id' IS DISTINCT FROM NEW.strategy_id::text OR
             NEW.evidence->'identity'->'bucket'->'key'->>'tenant_id' IS DISTINCT FROM NEW.tenant_id::text THEN
            RAISE EXCEPTION 'position attribution scope mismatch';
          END IF;
        END IF;
        market:=0; gross:=0; net:=0;
        FOR component IN SELECT key,value FROM jsonb_each_text(NEW.components) LOOP
          IF component.key IN ('PRICE','FX','PRICE_FX_CROSS','MODEL_MARK_CHANGE') THEN market:=market+component.value::numeric;
          ELSIF component.key IN ('ACCRUAL','CARRY','COUPON','DIVIDEND','RESET','CASHFLOW') THEN gross:=gross+component.value::numeric;
          ELSIF component.key IN ('BROKER_FEE','CUSTODY_FEE','MANAGEMENT_FEE','PERFORMANCE_FEE','TAX','OTHER_COST','ADJUSTMENT') THEN net:=net+component.value::numeric;
          ELSE RAISE EXCEPTION 'unsupported attribution component'; END IF;
        END LOOP;
        gross:=gross+market; net:=net+gross;
        IF market<>NEW.market_pnl OR gross<>NEW.gross_pnl OR net<>NEW.net_pnl THEN RAISE EXCEPTION 'attribution components do not reconcile'; END IF;
      END IF;
      IF TG_TABLE_NAME='pnl_review_item' THEN
        SELECT strategy_id,value_date INTO parent_strategy,parent_date FROM nav.pnl_review_batch WHERE batch_id=NEW.batch_id AND tenant_id=NEW.tenant_id;
        SELECT trade_id,position_key INTO selected_trade,selected_position FROM nav.pnl_attribution
          WHERE attribution_id=NEW.attribution_id AND tenant_id=NEW.tenant_id AND strategy_id=parent_strategy AND value_date=parent_date;
        IF NOT FOUND OR selected_trade IS DISTINCT FROM NEW.trade_id OR selected_position IS DISTINCT FROM NEW.position_key THEN
          RAISE EXCEPTION 'review attribution scope mismatch';
        END IF;
      END IF;
      RETURN NEW;
    END $$;
    CREATE FUNCTION nav.check_pnl_lineage() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE strategy uuid; subject uuid; event_trade uuid; trade_strategy uuid; trade_subject uuid; state text;
    BEGIN
      SELECT strategy_id,subject_id INTO strategy,subject FROM nav.pnl_attribution WHERE attribution_id=NEW.attribution_id;
      SELECT a.status INTO state FROM nav.valuation_attempt a JOIN nav.pnl_attribution p ON p.attempt_id=a.attempt_id
        WHERE p.attribution_id=NEW.attribution_id FOR SHARE OF a;
      IF state IS DISTINCT FROM 'RUNNING' THEN RAISE EXCEPTION 'completed attribution lineage is immutable'; END IF;
      SELECT strategy_id,trade_subject_reference_node_id INTO trade_strategy,trade_subject FROM trd.trade WHERE trade_id=NEW.trade_id;
      SELECT trade_id INTO event_trade FROM trd.trade_lifecycle_event WHERE trade_lifecycle_event_id=NEW.event_id;
      IF strategy IS DISTINCT FROM trade_strategy OR subject IS DISTINCT FROM trade_subject OR event_trade IS DISTINCT FROM NEW.trade_id THEN
        RAISE EXCEPTION 'position lineage scope mismatch';
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER check_pnl_lineage BEFORE INSERT ON nav.pnl_attribution_lineage FOR EACH ROW EXECUTE FUNCTION nav.check_pnl_lineage();
    COMMENT ON COLUMN nav.pnl_attribution.position_key IS 'Hash of compatible position conventions; null for historical trade-owned attribution.';
    COMMENT ON COLUMN nav.pnl_attribution.subject_id IS 'Actual valued listing/traded subject; never a fabricated trade owner.';
    COMMENT ON TABLE nav.pnl_attribution_lineage IS 'Immutable original ledger event links supporting position-owned attribution.';
    """)

def downgrade():
    # Refuse to discard position-owned financial history through a shape downgrade.
    op.execute("""DO $$ BEGIN
      IF EXISTS(SELECT 1 FROM nav.pnl_attribution WHERE position_key IS NOT NULL) THEN
        RAISE EXCEPTION 'Export/remove owned v2 evidence explicitly before downgrading position attribution';
      END IF;
    END $$;""")
    op.drop_table('pnl_attribution_lineage',schema='nav')
    op.execute('DROP FUNCTION nav.check_pnl_lineage()')
    # Restore the frozen revision-69 validator, not a mutable runtime function.
    from pathlib import Path
    path=Path(__file__).with_name('20261007_69_valuation_attribution.py')
    # The original validator is retained as frozen migration text in revision 69.
    source=path.read_text()
    start=source.index('    CREATE FUNCTION nav.check_valuation_scope()')
    end=source.index('    CREATE TRIGGER valuation_attempt_scope',start)
    op.execute(source[start:end].replace('CREATE FUNCTION','CREATE OR REPLACE FUNCTION',1))
    op.execute("""
    ALTER TABLE nav.pnl_review_item DROP CONSTRAINT uq_pnl_review_position, DROP CONSTRAINT ck_pnl_item_owner,
      DROP COLUMN position_key, ALTER COLUMN trade_id SET NOT NULL;
    ALTER TABLE nav.pnl_attribution DROP CONSTRAINT uq_pnl_position_version, DROP CONSTRAINT ck_pnl_result_owner,
      DROP COLUMN position_key, DROP COLUMN subject_id, ALTER COLUMN trade_id SET NOT NULL;
    """)
