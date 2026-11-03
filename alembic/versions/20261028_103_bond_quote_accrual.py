"""Retain typed observation-paired bond quotation accrual without price rewrites."""
from alembic import op

revision='20261028_103'
down_revision='20261028_102'
branch_labels=None
depends_on=None


def upgrade():
    op.execute("""CREATE TABLE md.bond_quote_accrual (
      observation_id uuid PRIMARY KEY REFERENCES md.market_data_observation(market_data_observation_id),
      accrued_interest_per_100 numeric(30,12) NOT NULL,
      quote_settlement_date date NOT NULL,
      source_reference text NOT NULL,
      recorded_at_utc timestamptz NOT NULL DEFAULT timezone('UTC',now()),
      component_hash varchar(64) NOT NULL,
      CONSTRAINT ck_bond_quote_accrual_content CHECK(length(trim(source_reference))>0 AND length(source_reference)<=1000
        AND length(component_hash)=64 AND accrued_interest_per_100 > -1000000000000000000
        AND accrued_interest_per_100 < 1000000000000000000));
      COMMENT ON TABLE md.bond_quote_accrual IS 'Immutable per-100 accrued component paired with one DIRTY source price; not position interest or balance.';
      COMMENT ON COLUMN md.bond_quote_accrual.observation_id IS 'Exact source price observation; corrections create a new observation and paired component.';
      COMMENT ON COLUMN md.bond_quote_accrual.accrued_interest_per_100 IS 'Signed quoted accrued interest per 100 nominal, in the same currency/convention as the DIRTY price.';
      COMMENT ON COLUMN md.bond_quote_accrual.quote_settlement_date IS 'Provider quote settlement date shared by the DIRTY price and accrued component.';
      COMMENT ON COLUMN md.bond_quote_accrual.source_reference IS 'Explicit source evidence; subject, date, currency, dataset/licence and raw payload inherit from the price observation.';
      COMMENT ON COLUMN md.bond_quote_accrual.recorded_at_utc IS 'Time the paired source component became known, constrained by the valuation information cutoff.';
      COMMENT ON COLUMN md.bond_quote_accrual.component_hash IS 'SHA256 of canonical quoted amount, settlement date and source reference.';
      CREATE FUNCTION md.reject_bond_quote_accrual_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
      BEGIN RAISE EXCEPTION 'Bond quote accrual evidence is immutable; correct the source observation'; END; $$;
      CREATE TRIGGER bond_quote_accrual_immutable BEFORE UPDATE OR DELETE ON md.bond_quote_accrual
        FOR EACH ROW EXECUTE FUNCTION md.reject_bond_quote_accrual_mutation();""")


def downgrade():
    raise RuntimeError('Retained quote evidence cannot be downgraded safely')
