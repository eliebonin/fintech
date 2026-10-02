"""Explicit option premium conventions and shared execution position effect."""
from alembic import op
import sqlalchemy as sa
revision='20261001_55'
down_revision='20261001_54'
branch_labels=depends_on=None


def upgrade():
    op.add_column('trade',sa.Column('position_effect',sa.String(10),nullable=True,comment='Recorded execution intent OPEN or CLOSE; unspecified for legacy trades, not settlement or position verification.'),schema='trd')
    op.create_check_constraint('ck_trade_position_effect','trade',"position_effect IS NULL OR position_effect IN ('OPEN','CLOSE')",schema='trd')
    op.add_column('option_terms',sa.Column('premium_multiplier',sa.Numeric(30,12),nullable=True,comment='Currency premium per quoted economic unit; distinct from exercise deliverable. No implicit default.'),schema='secm')
    op.add_column('option_terms',sa.Column('premium_style',sa.String(30),nullable=True,comment='Premium payment convention such as UPFRONT or FUTURES_STYLE; must be sourced.'),schema='secm')
    op.add_column('option_terms',sa.Column('last_trading_at_utc',sa.DateTime(timezone=True),nullable=True,comment='Explicit authoritative last trading instant, including timezone; not guessed from expiry date.'),schema='secm')
    op.create_check_constraint('ck_option_premium_multiplier','option_terms','premium_multiplier IS NULL OR premium_multiplier > 0',schema='secm')
    op.create_check_constraint('ck_option_premium_style','option_terms',"premium_style IS NULL OR premium_style IN ('UPFRONT','FUTURES_STYLE')",schema='secm')


def downgrade():
    op.drop_constraint('ck_option_premium_style','option_terms',schema='secm',type_='check')
    op.drop_constraint('ck_option_premium_multiplier','option_terms',schema='secm',type_='check')
    for column in ('last_trading_at_utc','premium_style','premium_multiplier'): op.drop_column('option_terms',column,schema='secm')
    op.drop_constraint('ck_trade_position_effect','trade',schema='trd',type_='check')
    op.drop_column('trade','position_effect',schema='trd')
