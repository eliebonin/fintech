"""Transactional ledger-change evidence for valuation reassessment."""
from alembic import op
from valuation import tables as t
from security_master_schema import models as m

revision='20261014_92'
down_revision='20261014_91'
branch_labels=None
depends_on=None


def upgrade():
    t.ledger_revision.create(op.get_bind())
    t.ledger_change.create(op.get_bind())
    t.reassessment_request.create(op.get_bind())
    op.execute("""CREATE FUNCTION nav.capture_trade_valuation_change() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE tr trd.trade%ROWTYPE; owner uuid; rev integer; starting date; why text; actor uuid; identity text;
    BEGIN
      IF TG_TABLE_NAME='trade_lifecycle_event' THEN
        SELECT * INTO STRICT tr FROM trd.trade WHERE trade_id=NEW.trade_id;
        actor:=NEW.recorded_by_user_account_id; identity:='event:'||NEW.trade_lifecycle_event_id;
        why:=left(NEW.event_type||coalesce(': '||((NEW.event_payload::jsonb)->>'reason'),''),2000);
      ELSE
        tr:=NEW; actor:=NEW.booked_by_user_account_id;
        IF TG_OP='UPDATE' THEN
          IF OLD.strategy_id<>NEW.strategy_id THEN RAISE EXCEPTION 'Moving booked trades between strategies requires explicit replacement'; END IF;
          IF ROW(OLD.quantity,OLD.execution_price,OLD.price_currency_id,OLD.trade_datetime_utc,OLD.valuation_effective_date,OLD.trade_subject_reference_node_id,OLD.price_basis,OLD.quantity_unit)
            IS NOT DISTINCT FROM ROW(NEW.quantity,NEW.execution_price,NEW.price_currency_id,NEW.trade_datetime_utc,NEW.valuation_effective_date,NEW.trade_subject_reference_node_id,NEW.price_basis,NEW.quantity_unit) THEN RETURN NEW; END IF;
          why:='ECONOMICS_CHANGED'; identity:='update:'||uuidv7();
        ELSE why:='BOOKING_ADDED'; identity:='trade:'||NEW.trade_id; END IF;
      END IF;
      SELECT tenant_id INTO STRICT owner FROM trd.strategy WHERE strategy_id=tr.strategy_id FOR NO KEY UPDATE;
      starting:=coalesce(tr.valuation_effective_date,(tr.trade_datetime_utc AT TIME ZONE 'UTC')::date);
      IF TG_TABLE_NAME='trade' AND TG_OP='UPDATE' THEN
        starting:=least(starting,coalesce(OLD.valuation_effective_date,(OLD.trade_datetime_utc AT TIME ZONE 'UTC')::date));
      END IF;
      INSERT INTO nav.strategy_ledger_revision(tenant_id,strategy_id,revision) VALUES(owner,tr.strategy_id,1)
        ON CONFLICT(tenant_id,strategy_id) DO UPDATE SET revision=nav.strategy_ledger_revision.revision+1 RETURNING revision INTO rev;
      INSERT INTO nav.strategy_ledger_change(tenant_id,strategy_id,revision,change_key,trade_id,economic_from,reason,actor_id)
        VALUES(owner,tr.strategy_id,rev,identity,tr.trade_id,starting,why,actor);
      RETURN NEW;
    END $$""")
    op.execute('CREATE TRIGGER valuation_trade_change AFTER INSERT OR UPDATE ON trd.trade FOR EACH ROW EXECUTE FUNCTION nav.capture_trade_valuation_change()')
    op.execute('CREATE TRIGGER valuation_event_change AFTER INSERT ON trd.trade_lifecycle_event FOR EACH ROW EXECUTE FUNCTION nav.capture_trade_valuation_change()')
    op.execute("""CREATE FUNCTION nav.guard_ledger_change() RETURNS trigger LANGUAGE plpgsql AS $$
      BEGIN RAISE EXCEPTION 'Ledger change evidence is immutable'; END $$""")
    op.execute('CREATE TRIGGER immutable_ledger_change BEFORE UPDATE OR DELETE ON nav.strategy_ledger_change FOR EACH ROW EXECUTE FUNCTION nav.guard_ledger_change()')
    op.execute('CREATE TRIGGER immutable_reassessment_request BEFORE UPDATE OR DELETE ON nav.valuation_reassessment_request FOR EACH ROW EXECUTE FUNCTION nav.guard_ledger_change()')


def downgrade():
    raise RuntimeError('Forward-only: retain valuation ledger-change evidence')
