"""Typed, append-only two-stage Ops interest review evidence."""
from alembic import op
revision='20261102_109'
down_revision='20261031_108'
branch_labels=depends_on=None


def upgrade():
    from security_master_schema import models
    from valuation import interest_review_tables as t
    for table in (t.review,t.item):table.create(op.get_bind(),checkfirst=False)
    op.execute("""CREATE FUNCTION nav.protect_interest_review() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'Interest review decisions are immutable'; END IF;
      IF NOT EXISTS(SELECT 1 FROM trd.strategy s WHERE s.strategy_id=NEW.strategy_id AND s.tenant_id=NEW.tenant_id)
        THEN RAISE EXCEPTION 'Interest review strategy scope mismatch'; END IF;
      IF TG_TABLE_NAME='interest_review' THEN
        IF (NEW.revision=1 AND NEW.supersedes_review_id IS NOT NULL) OR
          (NEW.revision>1 AND NOT EXISTS(SELECT 1 FROM nav.interest_review r WHERE r.review_id=NEW.supersedes_review_id
            AND r.tenant_id=NEW.tenant_id AND r.strategy_id=NEW.strategy_id AND r.value_date=NEW.value_date AND r.stage=NEW.stage AND r.revision=NEW.revision-1))
          THEN RAISE EXCEPTION 'Interest review revision mismatch'; END IF;
        IF NEW.stage='BALANCE' AND NOT EXISTS(SELECT 1 FROM nav.interest_review r WHERE r.review_id=NEW.daily_review_id
          AND r.tenant_id=NEW.tenant_id AND r.strategy_id=NEW.strategy_id AND r.value_date=NEW.value_date AND r.stage='DAILY' AND r.state='VALIDATED')
          THEN RAISE EXCEPTION 'Validated scoped daily review required'; END IF;
      ELSE
        IF NEW.source_input_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM nav.daily_accrual_input a WHERE a.input_id=NEW.source_input_id
          AND a.tenant_id=NEW.tenant_id AND a.strategy_id=NEW.strategy_id AND a.instrument_id=NEW.instrument_id AND a.currency_id=NEW.currency_id AND a.value_date=NEW.value_date)
          THEN RAISE EXCEPTION 'Daily source review scope mismatch'; END IF;
        IF NEW.balance_input_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM nav.accrued_balance_input a WHERE a.input_id=NEW.balance_input_id
          AND a.tenant_id=NEW.tenant_id AND a.strategy_id=NEW.strategy_id AND a.instrument_id=NEW.instrument_id AND a.currency_id=NEW.currency_id AND a.value_date=NEW.value_date)
          THEN RAISE EXCEPTION 'Balance source review scope mismatch'; END IF;
        IF NOT EXISTS(SELECT 1 FROM secm.instrument i JOIN secm.instrument_type it USING(instrument_type_id)
          WHERE i.instrument_node_id=NEW.instrument_id AND it.type_code='BOND' AND i.base_currency_id=NEW.currency_id)
          THEN RAISE EXCEPTION 'Interest review requires a local-currency canonical bond'; END IF;
        IF EXISTS(SELECT 1 FROM ten.reference_node_scope s WHERE s.reference_node_id=NEW.instrument_id
          AND (s.status<>'ACTIVE' OR s.scope_type='TENANT_PRIVATE' AND s.owner_tenant_id<>NEW.tenant_id))
          THEN RAISE EXCEPTION 'Interest review reference scope mismatch'; END IF;
        IF EXISTS(SELECT 1 FROM nav.interest_review r WHERE r.review_id=NEW.review_id AND r.state='VALIDATED') AND NEW.decision='ASSESSED' AND NEW.proposed_amount IS NULL
          THEN RAISE EXCEPTION 'Validated interest review needs an assessed amount'; END IF;
      END IF;
      RETURN NEW;
    END $$;""")
    for table in (t.review,t.item):
        op.execute(f'CREATE TRIGGER {table.name}_guard BEFORE INSERT OR UPDATE OR DELETE ON nav.{table.name} FOR EACH ROW EXECUTE FUNCTION nav.protect_interest_review()')
    op.execute("""CREATE FUNCTION nav.check_interest_review_population() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE expected integer; gaps integer;
    BEGIN
      SELECT row_count,gap_count INTO expected,gaps FROM nav.interest_review r WHERE r.review_id=NEW.review_id;
      IF (SELECT count(*) FROM nav.interest_review_item i WHERE i.review_id=NEW.review_id)<>expected
        THEN RAISE EXCEPTION 'Incomplete interest review population'; END IF;
      IF (SELECT count(*) FROM nav.interest_review_item i WHERE i.review_id=NEW.review_id AND i.decision='NOT_SUPPLIED')<>gaps
        THEN RAISE EXCEPTION 'Interest review gap count mismatch'; END IF;
      RETURN NULL;
    END $$;
    CREATE CONSTRAINT TRIGGER interest_review_population AFTER INSERT ON nav.interest_review
      DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION nav.check_interest_review_population();
    CREATE CONSTRAINT TRIGGER interest_review_item_population AFTER INSERT ON nav.interest_review_item
      DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION nav.check_interest_review_population();""")


def downgrade():raise RuntimeError('Forward-only: preserve interest review decisions')
