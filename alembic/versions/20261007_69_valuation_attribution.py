"""Immutable financial evidence and separate valuation run/review records."""
from alembic import op
revision='20261007_69'
down_revision='20261007_68'
branch_labels=depends_on=None

NAMES=('valuation_attempt','valuation_run_event','pnl_attribution','pnl_review_batch','pnl_review_item','pnl_review_event')

# Frozen DDL: replaying revision 69 must not depend on later runtime models.
DDL = (
    "\nCREATE TABLE nav.valuation_attempt (\n\tattempt_id UUID DEFAULT uuidv7() NOT NULL, \n\ttenant_id UUID NOT NULL, \n\tstrategy_id UUID NOT NULL, \n\tinitiated_by UUID NOT NULL, \n\trequest_key VARCHAR(255) NOT NULL, \n\trequest_hash VARCHAR(64) NOT NULL, \n\trequest_payload JSONB NOT NULL, \n\tcorrelation_id VARCHAR(100) NOT NULL, \n\tstatus VARCHAR(20) NOT NULL, \n\terror_code VARCHAR(80), \n\tstarted_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp() NOT NULL, \n\tcompleted_at TIMESTAMP WITH TIME ZONE, \n\tPRIMARY KEY (attempt_id), \n\tCONSTRAINT uq_valuation_attempt_key UNIQUE (tenant_id, request_key), \n\tCONSTRAINT uq_valuation_attempt_scope UNIQUE (attempt_id, tenant_id), \n\tCONSTRAINT ck_valuation_attempt_status CHECK (status IN ('RUNNING','COMPLETED','FAILED')), \n\tFOREIGN KEY(tenant_id) REFERENCES ten.tenant (tenant_id), \n\tFOREIGN KEY(strategy_id) REFERENCES trd.strategy (strategy_id), \n\tFOREIGN KEY(initiated_by) REFERENCES secm.user_account (user_account_id)\n)\n\n",
    "COMMENT ON TABLE nav.valuation_attempt IS 'Valuation/P&L evidence and review domain; operational attempts remain distinct from official financial selection.'",
    "COMMENT ON COLUMN nav.valuation_attempt.attempt_id IS 'Immutable UUIDv7 identity of this record.'",
    "COMMENT ON COLUMN nav.valuation_attempt.tenant_id IS 'Tenant owning this valuation, attribution or review record; enforced together with parent scope.'",
    "COMMENT ON COLUMN nav.valuation_attempt.strategy_id IS 'Tenant strategy whose booked economics are valued and reviewed.'",
    "COMMENT ON COLUMN nav.valuation_attempt.initiated_by IS 'Authenticated account requesting this calculation attempt.'",
    "COMMENT ON COLUMN nav.valuation_attempt.request_key IS 'Tenant-scoped retry-stable key for an unchanged calculation request.'",
    "COMMENT ON COLUMN nav.valuation_attempt.request_hash IS 'SHA256 of exact request configuration and initiating identity, used to reject key reuse.'",
    "COMMENT ON COLUMN nav.valuation_attempt.request_payload IS 'Frozen cutoff, strategy, currency and policy configuration; contains no raw provider payload.'",
    "COMMENT ON COLUMN nav.valuation_attempt.correlation_id IS 'Identifier linking API requests, operational diagnostics and this calculation attempt.'",
    "COMMENT ON COLUMN nav.valuation_attempt.status IS 'Controlled operational or review lifecycle state, constrained by this table status check.'",
    "COMMENT ON COLUMN nav.valuation_attempt.error_code IS 'Safe bounded failure category; never a raw exception or database connection string.'",
    "COMMENT ON COLUMN nav.valuation_attempt.started_at IS 'UTC recording time of the independently committed calculation attempt.'",
    "COMMENT ON COLUMN nav.valuation_attempt.completed_at IS 'UTC time the attempt reached a terminal COMPLETED or FAILED state.'",
    "\nCREATE TABLE nav.valuation_run_event (\n\tevent_id UUID DEFAULT uuidv7() NOT NULL, \n\tattempt_id UUID NOT NULL, \n\tevent_code VARCHAR(40) NOT NULL, \n\tstage VARCHAR(40) NOT NULL, \n\tdetails JSONB NOT NULL, \n\trecorded_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp() NOT NULL, \n\tPRIMARY KEY (event_id), \n\tFOREIGN KEY(attempt_id) REFERENCES nav.valuation_attempt (attempt_id)\n)\n\n",
    "COMMENT ON TABLE nav.valuation_run_event IS 'Valuation/P&L evidence and review domain; operational attempts remain distinct from official financial selection.'",
    "COMMENT ON COLUMN nav.valuation_run_event.event_id IS 'Immutable UUIDv7 identity of this record.'",
    "COMMENT ON COLUMN nav.valuation_run_event.attempt_id IS 'Parent calculation attempt, retaining independently recorded operational lineage.'",
    "COMMENT ON COLUMN nav.valuation_run_event.event_code IS 'Controlled stage event identifying start, validation, completion or failure.'",
    "COMMENT ON COLUMN nav.valuation_run_event.stage IS 'Named processing stage responsible for this operational event.'",
    "COMMENT ON COLUMN nav.valuation_run_event.details IS 'Safe structured timings, counts, identifiers and error categories; not financial input payloads.'",
    "COMMENT ON COLUMN nav.valuation_run_event.recorded_at IS 'UTC recording time of this immutable operational or review event.'",
    "\nCREATE TABLE nav.pnl_attribution (\n\tattribution_id UUID DEFAULT uuidv7() NOT NULL, \n\ttenant_id UUID NOT NULL, \n\tstrategy_id UUID NOT NULL, \n\tattempt_id UUID NOT NULL, \n\ttrade_id UUID NOT NULL, \n\tvalue_date DATE NOT NULL, \n\tversion INTEGER NOT NULL, \n\tsupersedes_attribution_id UUID, \n\tmethod VARCHAR(80) NOT NULL, \n\tinput_hash VARCHAR(64) NOT NULL, \n\tcurrency_id UUID NOT NULL, \n\tmarket_pnl NUMERIC(30, 12) NOT NULL, \n\tgross_pnl NUMERIC(30, 12) NOT NULL, \n\tnet_pnl NUMERIC(30, 12) NOT NULL, \n\tcomponents JSONB NOT NULL, \n\tevidence JSONB NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp() NOT NULL, \n\tPRIMARY KEY (attribution_id), \n\tFOREIGN KEY(attempt_id, tenant_id) REFERENCES nav.valuation_attempt (attempt_id, tenant_id), \n\tCONSTRAINT uq_pnl_attribution_version UNIQUE (tenant_id, strategy_id, value_date, trade_id, version), \n\tCONSTRAINT uq_pnl_attribution_scope UNIQUE (attribution_id, tenant_id), \n\tCONSTRAINT ck_pnl_attribution_version CHECK (version > 0), \n\tFOREIGN KEY(tenant_id) REFERENCES ten.tenant (tenant_id), \n\tFOREIGN KEY(strategy_id) REFERENCES trd.strategy (strategy_id), \n\tFOREIGN KEY(trade_id) REFERENCES trd.trade (trade_id), \n\tFOREIGN KEY(supersedes_attribution_id) REFERENCES nav.pnl_attribution (attribution_id), \n\tFOREIGN KEY(currency_id) REFERENCES secm.currency (currency_id)\n)\n\n",
    "COMMENT ON TABLE nav.pnl_attribution IS 'Valuation/P&L evidence and review domain; operational attempts remain distinct from official financial selection.'",
    "COMMENT ON COLUMN nav.pnl_attribution.attribution_id IS 'Immutable UUIDv7 identity of this record.'",
    "COMMENT ON COLUMN nav.pnl_attribution.tenant_id IS 'Tenant owning this valuation, attribution or review record; enforced together with parent scope.'",
    "COMMENT ON COLUMN nav.pnl_attribution.strategy_id IS 'Tenant strategy whose booked economics are valued and reviewed.'",
    "COMMENT ON COLUMN nav.pnl_attribution.attempt_id IS 'Parent calculation attempt, retaining independently recorded operational lineage.'",
    "COMMENT ON COLUMN nav.pnl_attribution.trade_id IS 'Actual booked execution owning this first-alpha attribution; non-trade ownership is not yet implemented.'",
    "COMMENT ON COLUMN nav.pnl_attribution.value_date IS 'UTC closing-cutoff business date of this period attribution or review population.'",
    "COMMENT ON COLUMN nav.pnl_attribution.version IS 'Positive monotonically increasing immutable attribution version within tenant/strategy/trade/date scope.'",
    "COMMENT ON COLUMN nav.pnl_attribution.supersedes_attribution_id IS 'Prior immutable attribution version replaced by changed financial inputs or method.'",
    "COMMENT ON COLUMN nav.pnl_attribution.method IS 'Versioned calculation methodology, separate from attribution storage version.'",
    "COMMENT ON COLUMN nav.pnl_attribution.input_hash IS 'Canonical SHA256 of the effective financial inputs defining this attribution or review population.'",
    "COMMENT ON COLUMN nav.pnl_attribution.currency_id IS 'Reporting currency of the stored monetary P&L components and totals.'",
    "COMMENT ON COLUMN nav.pnl_attribution.market_pnl IS 'Clean price, FX and price/FX-cross movement; excludes income, fees and adjustments.'",
    "COMMENT ON COLUMN nav.pnl_attribution.gross_pnl IS 'Market P&L plus separately attributed income flows; equals market P&L in the first market-only alpha.'",
    "COMMENT ON COLUMN nav.pnl_attribution.net_pnl IS 'Gross P&L plus separately attributed signed costs/adjustments; no manual edit is permitted.'",
    "COMMENT ON COLUMN nav.pnl_attribution.components IS 'Exact decimal-string component amounts, reconciled to monetary totals before storage and by database trigger.'",
    "COMMENT ON COLUMN nav.pnl_attribution.evidence IS 'Immutable booked facts, selected input identities, calculation method and resolution snapshot lineage.'",
    "COMMENT ON COLUMN nav.pnl_attribution.created_at IS 'UTC recording time of this immutable financial version or staged review population.'",
    "\nCREATE TABLE nav.pnl_review_batch (\n\tbatch_id UUID DEFAULT uuidv7() NOT NULL, \n\ttenant_id UUID NOT NULL, \n\tstrategy_id UUID NOT NULL, \n\tstaged_by UUID NOT NULL, \n\tattempt_id UUID NOT NULL, \n\tvalue_date DATE NOT NULL, \n\tstatus VARCHAR(20) NOT NULL, \n\tmode VARCHAR(20) NOT NULL, \n\tinput_hash VARCHAR(64) NOT NULL, \n\tbase_population_hash VARCHAR(64) NOT NULL, \n\tsummary JSONB NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp() NOT NULL, \n\tPRIMARY KEY (batch_id), \n\tFOREIGN KEY(attempt_id, tenant_id) REFERENCES nav.valuation_attempt (attempt_id, tenant_id), \n\tCONSTRAINT uq_pnl_batch_idempotency UNIQUE (tenant_id, strategy_id, value_date, input_hash, mode), \n\tCONSTRAINT uq_pnl_batch_scope UNIQUE (batch_id, tenant_id), \n\tCONSTRAINT ck_pnl_batch_status CHECK (status IN ('STAGED','PUBLISHED','CANCELLED','SUPERSEDED')), \n\tCONSTRAINT ck_pnl_batch_mode CHECK (mode IN ('AUTHORITATIVE','INCREMENTAL')), \n\tFOREIGN KEY(tenant_id) REFERENCES ten.tenant (tenant_id), \n\tFOREIGN KEY(strategy_id) REFERENCES trd.strategy (strategy_id), \n\tFOREIGN KEY(staged_by) REFERENCES secm.user_account (user_account_id)\n)\n\n",
    "CREATE UNIQUE INDEX uq_pnl_published_population ON nav.pnl_review_batch (tenant_id, strategy_id, value_date) WHERE status = 'PUBLISHED'",
    "COMMENT ON TABLE nav.pnl_review_batch IS 'Valuation/P&L evidence and review domain; operational attempts remain distinct from official financial selection.'",
    "COMMENT ON COLUMN nav.pnl_review_batch.batch_id IS 'Immutable UUIDv7 identity of this record.'",
    "COMMENT ON COLUMN nav.pnl_review_batch.tenant_id IS 'Tenant owning this valuation, attribution or review record; enforced together with parent scope.'",
    "COMMENT ON COLUMN nav.pnl_review_batch.strategy_id IS 'Tenant strategy whose booked economics are valued and reviewed.'",
    "COMMENT ON COLUMN nav.pnl_review_batch.staged_by IS 'Authenticated account staging the candidate population; cannot independently publish its own batch.'",
    "COMMENT ON COLUMN nav.pnl_review_batch.attempt_id IS 'Parent calculation attempt, retaining independently recorded operational lineage.'",
    "COMMENT ON COLUMN nav.pnl_review_batch.value_date IS 'UTC closing-cutoff business date of this period attribution or review population.'",
    "COMMENT ON COLUMN nav.pnl_review_batch.status IS 'Controlled operational or review lifecycle state, constrained by this table status check.'",
    "COMMENT ON COLUMN nav.pnl_review_batch.mode IS 'Explicit AUTHORITATIVE replacement or INCREMENTAL supplementation semantics.'",
    "COMMENT ON COLUMN nav.pnl_review_batch.input_hash IS 'Canonical SHA256 of the effective financial inputs defining this attribution or review population.'",
    "COMMENT ON COLUMN nav.pnl_review_batch.base_population_hash IS 'Official attribution selection hash at staging, checked again atomically at publication.'",
    "COMMENT ON COLUMN nav.pnl_review_batch.summary IS 'Frozen period bridge, currency, validation state and scope limitations presented to reviewers.'",
    "COMMENT ON COLUMN nav.pnl_review_batch.created_at IS 'UTC recording time of this immutable financial version or staged review population.'",
    "\nCREATE TABLE nav.pnl_review_item (\n\titem_id UUID DEFAULT uuidv7() NOT NULL, \n\ttenant_id UUID NOT NULL, \n\tbatch_id UUID NOT NULL, \n\tattribution_id UUID NOT NULL, \n\ttrade_id UUID NOT NULL, \n\tPRIMARY KEY (item_id), \n\tFOREIGN KEY(batch_id, tenant_id) REFERENCES nav.pnl_review_batch (batch_id, tenant_id), \n\tFOREIGN KEY(attribution_id, tenant_id) REFERENCES nav.pnl_attribution (attribution_id, tenant_id), \n\tCONSTRAINT uq_pnl_review_trade UNIQUE (batch_id, trade_id), \n\tFOREIGN KEY(trade_id) REFERENCES trd.trade (trade_id)\n)\n\n",
    "COMMENT ON TABLE nav.pnl_review_item IS 'Valuation/P&L evidence and review domain; operational attempts remain distinct from official financial selection.'",
    "COMMENT ON COLUMN nav.pnl_review_item.item_id IS 'Immutable UUIDv7 identity of this record.'",
    "COMMENT ON COLUMN nav.pnl_review_item.tenant_id IS 'Tenant owning this valuation, attribution or review record; enforced together with parent scope.'",
    "COMMENT ON COLUMN nav.pnl_review_item.batch_id IS 'Parent tenant/strategy/date review batch selecting candidate or official attribution versions.'",
    "COMMENT ON COLUMN nav.pnl_review_item.attribution_id IS 'Exact immutable attribution version selected by this review item.'",
    "COMMENT ON COLUMN nav.pnl_review_item.trade_id IS 'Actual booked execution owning this first-alpha attribution; non-trade ownership is not yet implemented.'",
    "\nCREATE TABLE nav.pnl_review_event (\n\treview_event_id UUID DEFAULT uuidv7() NOT NULL, \n\tbatch_id UUID NOT NULL, \n\tactor_id UUID NOT NULL, \n\taction VARCHAR(30) NOT NULL, \n\tcomment VARCHAR(2000) NOT NULL, \n\trecorded_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp() NOT NULL, \n\tPRIMARY KEY (review_event_id), \n\tFOREIGN KEY(batch_id) REFERENCES nav.pnl_review_batch (batch_id), \n\tFOREIGN KEY(actor_id) REFERENCES secm.user_account (user_account_id)\n)\n\n",
    "COMMENT ON TABLE nav.pnl_review_event IS 'Valuation/P&L evidence and review domain; operational attempts remain distinct from official financial selection.'",
    "COMMENT ON COLUMN nav.pnl_review_event.review_event_id IS 'Immutable UUIDv7 identity of this record.'",
    "COMMENT ON COLUMN nav.pnl_review_event.batch_id IS 'Parent tenant/strategy/date review batch selecting candidate or official attribution versions.'",
    "COMMENT ON COLUMN nav.pnl_review_event.actor_id IS 'Authenticated account recording this explanation or review decision.'",
    "COMMENT ON COLUMN nav.pnl_review_event.action IS 'Recorded workflow action such as STAGED, EXPLANATION, PUBLISHED, CANCELLED or SUPERSEDED.'",
    "COMMENT ON COLUMN nav.pnl_review_event.comment IS 'Bounded human explanation or publication rationale, retained with actor and recording time.'",
    "COMMENT ON COLUMN nav.pnl_review_event.recorded_at IS 'UTC recording time of this immutable operational or review event.'",
)

def upgrade():
    for statement in DDL:
        op.execute(statement)
    op.execute("""
    CREATE FUNCTION nav.protect_pnl_evidence() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN RAISE EXCEPTION 'valuation financial and event evidence is immutable'; END $$;
    CREATE TRIGGER protect_pnl_attribution BEFORE UPDATE OR DELETE ON nav.pnl_attribution FOR EACH ROW EXECUTE FUNCTION nav.protect_pnl_evidence();
    CREATE TRIGGER protect_valuation_run_event BEFORE UPDATE OR DELETE ON nav.valuation_run_event FOR EACH ROW EXECUTE FUNCTION nav.protect_pnl_evidence();
    CREATE TRIGGER protect_pnl_review_event BEFORE UPDATE OR DELETE ON nav.pnl_review_event FOR EACH ROW EXECUTE FUNCTION nav.protect_pnl_evidence();
    CREATE FUNCTION nav.check_valuation_scope() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE owner uuid; parent_strategy uuid; parent_date date; selected_trade uuid; market numeric; gross numeric; net numeric; component record;
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
        SELECT strategy_id INTO parent_strategy FROM trd.trade WHERE trade_id=NEW.trade_id;
        IF parent_strategy IS DISTINCT FROM NEW.strategy_id THEN RAISE EXCEPTION 'attribution trade scope mismatch'; END IF;
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
        SELECT trade_id INTO selected_trade FROM nav.pnl_attribution WHERE attribution_id=NEW.attribution_id AND tenant_id=NEW.tenant_id AND strategy_id=parent_strategy AND value_date=parent_date;
        IF selected_trade IS DISTINCT FROM NEW.trade_id THEN RAISE EXCEPTION 'review attribution scope mismatch'; END IF;
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER valuation_attempt_scope BEFORE INSERT OR UPDATE ON nav.valuation_attempt FOR EACH ROW EXECUTE FUNCTION nav.check_valuation_scope();
    CREATE TRIGGER pnl_attribution_scope BEFORE INSERT ON nav.pnl_attribution FOR EACH ROW EXECUTE FUNCTION nav.check_valuation_scope();
    CREATE TRIGGER pnl_batch_scope BEFORE INSERT OR UPDATE ON nav.pnl_review_batch FOR EACH ROW EXECUTE FUNCTION nav.check_valuation_scope();
    CREATE TRIGGER pnl_item_scope BEFORE INSERT OR UPDATE ON nav.pnl_review_item FOR EACH ROW EXECUTE FUNCTION nav.check_valuation_scope();
    CREATE FUNCTION nav.protect_published_selection() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE state text;
    BEGIN
      IF TG_OP<>'INSERT' THEN
        SELECT status INTO state FROM nav.pnl_review_batch WHERE batch_id=OLD.batch_id FOR SHARE;
        IF state<>'STAGED' THEN RAISE EXCEPTION 'published review selection is immutable'; END IF;
      END IF;
      IF TG_OP<>'DELETE' THEN
        SELECT status INTO state FROM nav.pnl_review_batch WHERE batch_id=NEW.batch_id FOR SHARE;
        IF state<>'STAGED' THEN RAISE EXCEPTION 'published review selection is immutable'; END IF;
        RETURN NEW;
      END IF;
      RETURN OLD;
    END $$;
    CREATE TRIGGER protect_pnl_selection BEFORE INSERT OR UPDATE OR DELETE ON nav.pnl_review_item FOR EACH ROW EXECUTE FUNCTION nav.protect_published_selection();
    """)

def downgrade():
    # Explicit downgrade removes only this revision's valuation/review evidence.
    # Export that evidence first if it must be retained; no source trades/MD change.
    for name in reversed(NAMES): op.drop_table(name,schema='nav')
    for name in ('protect_published_selection','check_valuation_scope','protect_pnl_evidence'):
        op.execute('DROP FUNCTION nav.'+name+'()')
