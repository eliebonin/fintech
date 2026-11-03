"""Dataset 3: exact derived local stocks and frozen FX, owned by one attempt."""
from sqlalchemy import Table,Column,Date,DateTime,String,Numeric,ForeignKey,ForeignKeyConstraint,UniqueConstraint,CheckConstraint,Index,text
from sqlalchemy.dialects.postgresql import UUID,JSONB


def register(metadata):
    global balance_snapshot
    uid=UUID(as_uuid=True)
    balance_snapshot=Table('accrued_interest_balance',metadata,
        Column('balance_id',uid,primary_key=True,server_default=text('uuidv7()')),
        Column('attempt_id',uid,nullable=False),Column('tenant_id',uid,nullable=False),
        Column('strategy_id',uid,ForeignKey('trd.strategy.strategy_id'),nullable=False),
        Column('instrument_id',uid,ForeignKey('secm.instrument.instrument_node_id'),nullable=False),
        Column('currency_id',uid,ForeignKey('secm.currency.currency_id'),nullable=False),
        Column('reporting_currency_id',uid,ForeignKey('secm.currency.currency_id'),nullable=False),
        Column('value_date',Date,nullable=False),
        *[Column(name,Numeric()) for name in ('opening_balance','daily_earned','balance_movements','coupon_paid','closing_balance','opening_fx','closing_fx','fx_pnl')],
        Column('basis',String(40),nullable=False),Column('fx_status',String(30),nullable=False),
        Column('input_hash',String(64),nullable=False),Column('evidence',JSONB,nullable=False),
        Column('recorded_at',DateTime(timezone=True),nullable=False,server_default=text('clock_timestamp()')),
        ForeignKeyConstraint(['attempt_id','tenant_id'],['nav.valuation_attempt.attempt_id','nav.valuation_attempt.tenant_id']),
        UniqueConstraint('attempt_id','instrument_id','currency_id','value_date',name='uq_accrued_balance_attempt'),
        CheckConstraint("fx_status IN ('CALCULATED','NOT_CALCULATED') AND ((fx_status='CALCULATED' AND fx_pnl IS NOT NULL) OR (fx_status='NOT_CALCULATED' AND fx_pnl IS NULL))",name='ck_accrued_balance_fx_status'),schema='nav',
        comment='Immutable per-attempt accrued stocks and FX attribution; derived output, never an implicitly trusted future input.')
    Index('ix_accrued_balance_strategy_date',balance_snapshot.c.tenant_id,balance_snapshot.c.strategy_id,balance_snapshot.c.value_date)
    for col in balance_snapshot.c:col.comment='Exact retained accrued-balance value or scoped source/attempt evidence: '+col.name
