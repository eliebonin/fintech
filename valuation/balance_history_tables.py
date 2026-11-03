"""Supplied stocks are sources; maintained local history is distinct from run output."""
from sqlalchemy import Table,Column,Date,DateTime,String,Integer,Numeric,ForeignKey,ForeignKeyConstraint,UniqueConstraint,CheckConstraint,Index,text
from sqlalchemy.dialects.postgresql import UUID,JSONB


def register(metadata):
    global balance_input,history_build,history_day
    uid=UUID(as_uuid=True)
    def identity(name):return Column(name,uid,primary_key=True,server_default=text('uuidv7()'))
    def scope():return [Column('tenant_id',uid,ForeignKey('ten.tenant.tenant_id'),nullable=False),Column('strategy_id',uid,ForeignKey('trd.strategy.strategy_id'),nullable=False)]
    def stamp():return Column('recorded_at',DateTime(timezone=True),nullable=False,server_default=text('clock_timestamp()'))
    balance_input=Table('accrued_balance_input',metadata,identity('input_id'),*scope(),
        Column('instrument_id',uid,ForeignKey('secm.instrument.instrument_node_id'),nullable=False),
        Column('currency_id',uid,ForeignKey('secm.currency.currency_id'),nullable=False),Column('value_date',Date,nullable=False),
        Column('closing_balance',Numeric(30,12)),Column('status',String(20),nullable=False),
        Column('revision',Integer,nullable=False),Column('supersedes_input_id',uid,ForeignKey('nav.accrued_balance_input.input_id')),
        Column('source_reference',String(2000),nullable=False),Column('reason',String(2000),nullable=False),
        Column('recorded_by',uid,ForeignKey('secm.user_account.user_account_id'),nullable=False),stamp(),
        Column('submission_key',String(255),nullable=False),Column('request_hash',String(64),nullable=False),
        UniqueConstraint('tenant_id','submission_key',name='uq_balance_input_key'),
        UniqueConstraint('tenant_id','strategy_id','instrument_id','currency_id','value_date','revision',name='uq_balance_input_revision'),
        CheckConstraint("revision>0 AND ((status='ACTIVE' AND closing_balance IS NOT NULL) OR (status='WITHDRAWN' AND closing_balance IS NULL AND supersedes_input_id IS NOT NULL))",name='ck_balance_input_status'),schema='nav')
    history_build=Table('accrued_balance_build',metadata,identity('build_id'),*scope(),
        Column('from_date',Date,nullable=False),Column('to_date',Date,nullable=False),
        Column('information_cutoff',DateTime(timezone=True),nullable=False),Column('source_proof',JSONB,nullable=False),
        Column('method',String(60),nullable=False),Column('recorded_by',uid,ForeignKey('secm.user_account.user_account_id'),nullable=False),stamp(),
        Column('submission_key',String(255),nullable=False),Column('request_hash',String(64),nullable=False),
        UniqueConstraint('tenant_id','submission_key',name='uq_balance_build_key'),
        UniqueConstraint('build_id','tenant_id','strategy_id',name='uq_balance_build_scope'),
        CheckConstraint('to_date>=from_date',name='ck_balance_build_dates'),schema='nav')
    history_day=Table('accrued_balance_history',metadata,identity('history_id'),
        Column('build_id',uid,nullable=False),Column('tenant_id',uid,nullable=False),Column('strategy_id',uid,nullable=False),
        Column('instrument_id',uid,ForeignKey('secm.instrument.instrument_node_id'),nullable=False),
        Column('currency_id',uid,ForeignKey('secm.currency.currency_id'),nullable=False),Column('value_date',Date,nullable=False),
        *[Column(name,Numeric()) for name in ('opening_balance','daily_earned','trade_movements','coupon_paid','closing_balance')],
        Column('basis',String(40),nullable=False),Column('evidence',JSONB,nullable=False),
        ForeignKeyConstraint(['build_id','tenant_id','strategy_id'],['nav.accrued_balance_build.build_id','nav.accrued_balance_build.tenant_id','nav.accrued_balance_build.strategy_id']),
        UniqueConstraint('build_id','instrument_id','currency_id','value_date',name='uq_balance_history_day'),schema='nav')
    Index('ix_balance_input_scope_date',balance_input.c.tenant_id,balance_input.c.strategy_id,balance_input.c.value_date)
    Index('ix_balance_history_scope_date',history_day.c.tenant_id,history_day.c.strategy_id,history_day.c.value_date)
    Index('ix_balance_build_strategy_time',history_build.c.tenant_id,history_build.c.strategy_id,history_build.c.recorded_at)
    for table in (balance_input,history_build,history_day):
        table.comment='Retained local accrued-interest balance source or maintained history; distinct from per-valuation FX output.'
        for column in table.c:column.comment='Exact scoped balance/history fact or immutable source revision: '+column.name
