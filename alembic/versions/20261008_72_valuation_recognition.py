"""Built-in immutable recognition dates; legacy trades remain unchanged."""
from alembic import op
revision='20261008_72'
down_revision='20261008_71'
branch_labels=depends_on=None

def upgrade():
    op.execute("""
    ALTER TABLE trd.trade ADD COLUMN valuation_effective_date date,
      ADD COLUMN valuation_date_basis varchar(30), ADD COLUMN valuation_override_reason varchar(1000),
      ADD CONSTRAINT ck_trade_valuation_recognition CHECK (
        (valuation_effective_date IS NULL AND valuation_date_basis IS NULL AND valuation_override_reason IS NULL) OR
        (valuation_effective_date IS NOT NULL AND valuation_date_basis IS NOT NULL AND
         valuation_effective_date >= (trade_datetime_utc AT TIME ZONE 'UTC')::date AND
         ((valuation_date_basis='UTC_TRADE_DATE' AND valuation_effective_date=(trade_datetime_utc AT TIME ZONE 'UTC')::date) OR
          (valuation_date_basis='EXPLICIT_OVERRIDE' AND valuation_effective_date>(trade_datetime_utc AT TIME ZONE 'UTC')::date
           AND valuation_override_reason IS NOT NULL AND length(btrim(valuation_override_reason))>0))));
    CREATE INDEX ix_trade_strategy_valuation_date ON trd.trade(strategy_id,valuation_effective_date,trade_id);
    CREATE FUNCTION trd.protect_valuation_recognition() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF (OLD.valuation_effective_date,OLD.valuation_date_basis,OLD.valuation_override_reason)
         IS DISTINCT FROM (NEW.valuation_effective_date,NEW.valuation_date_basis,NEW.valuation_override_reason) THEN
        RAISE EXCEPTION 'Valuation recognition is immutable; cancel and rebook the record';
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER protect_valuation_recognition BEFORE UPDATE ON trd.trade
      FOR EACH ROW EXECUTE FUNCTION trd.protect_valuation_recognition();
    COMMENT ON COLUMN trd.trade.valuation_effective_date IS 'Built-in daily valuation recognition date; null legacy records derive UTC execution date. Not settlement.';
    COMMENT ON COLUMN trd.trade.valuation_date_basis IS 'Frozen UTC_TRADE_DATE or EXPLICIT_OVERRIDE recognition convention.';
    COMMENT ON COLUMN trd.trade.valuation_override_reason IS 'Reason for later recognition; correction requires cancel and rebook.';
    """)

def downgrade():
    op.execute("""DO $$ BEGIN
      IF EXISTS(SELECT 1 FROM trd.trade WHERE valuation_effective_date IS NOT NULL) THEN
        RAISE EXCEPTION 'Recognition evidence exists; do not discard it by downgrading';
      END IF;
    END $$;
    DROP TRIGGER protect_valuation_recognition ON trd.trade;
    DROP FUNCTION trd.protect_valuation_recognition();
    DROP INDEX trd.ix_trade_strategy_valuation_date;
    ALTER TABLE trd.trade DROP CONSTRAINT ck_trade_valuation_recognition,
      DROP COLUMN valuation_effective_date, DROP COLUMN valuation_date_basis, DROP COLUMN valuation_override_reason;
    """)
