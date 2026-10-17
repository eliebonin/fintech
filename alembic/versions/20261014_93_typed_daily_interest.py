"""Promote daily earned interest and its currency without rewriting source evidence."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision='20261014_93'
down_revision='20261014_92'
branch_labels=depends_on=None


def upgrade():
    op.add_column('daily_accrual_input',sa.Column('daily_earned_interest',sa.Numeric(30,12),comment='Interest earned on value_date in currency_id; not accumulated balance.'),schema='nav')
    op.add_column('daily_accrual_input',sa.Column('currency_id',UUID(as_uuid=True),comment='Currency of daily_earned_interest.'),schema='nav')
    # ADD COLUMN holds an exclusive table lock until transaction commit. No
    # external writer can exploit this narrowly scoped immutable-trigger pause.
    op.execute("""DO $$ BEGIN
      IF EXISTS(SELECT 1 FROM nav.daily_accrual_input WHERE
        payload#>>'{amounts,dailyLocal}' IS NULL OR payload->>'currencyId' IS NULL OR
        (payload#>>'{amounts,dailyLocal}')::numeric IS DISTINCT FROM (payload#>>'{inputs,dailyEarned}')::numeric OR
        (payload#>>'{amounts,dailyLocal}')::numeric IS DISTINCT FROM round((payload#>>'{amounts,dailyLocal}')::numeric,12) OR
        abs((payload#>>'{amounts,dailyLocal}')::numeric)>=1000000000000000000)
      THEN RAISE EXCEPTION 'Legacy daily interest cannot be backfilled exactly; review source evidence'; END IF;
    END $$""")
    op.execute('ALTER TABLE nav.daily_accrual_input DISABLE TRIGGER daily_accrual_immutable')
    op.execute("UPDATE nav.daily_accrual_input SET daily_earned_interest=(payload#>>'{amounts,dailyLocal}')::numeric,currency_id=(payload->>'currencyId')::uuid")
    op.execute('ALTER TABLE nav.daily_accrual_input ENABLE TRIGGER daily_accrual_immutable')
    op.alter_column('daily_accrual_input','daily_earned_interest',nullable=False,schema='nav')
    op.alter_column('daily_accrual_input','currency_id',nullable=False,schema='nav')
    op.create_foreign_key('fk_accrual_currency','daily_accrual_input','currency',['currency_id'],['currency_id'],source_schema='nav',referent_schema='secm')
    op.create_check_constraint('ck_accrual_daily_finite','daily_accrual_input','daily_earned_interest > -1000000000000000000 AND daily_earned_interest < 1000000000000000000',schema='nav')
    op.create_check_constraint('ck_accrual_core_payload','daily_accrual_input',"(payload->>'currencyId')::uuid IS NOT DISTINCT FROM currency_id AND (coalesce(payload->>'dailyEarned',payload#>>'{amounts,dailyLocal}'))::numeric IS NOT DISTINCT FROM daily_earned_interest",schema='nav')


def downgrade():
    raise RuntimeError('Forward-only: retain typed daily interest and immutable revision evidence')
