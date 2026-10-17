"""Tenant-owned reference schedules and strategy payment evidence, not income."""
from sqlalchemy import Table,Column,String,Date,Integer,DateTime,Numeric,ForeignKey,UniqueConstraint,CheckConstraint,Index,text
from sqlalchemy.dialects.postgresql import UUID,JSONB


def register(metadata):
    global schedule,period,payment
    def uid(name,target=None,**kw): return Column(name,UUID(as_uuid=True),*([ForeignKey(target)] if target else []),**kw)
    def identity(name): return uid(name,primary_key=True,server_default=text('uuidv7()'))
    def audit(): return [uid('actor_id','secm.user_account.user_account_id',nullable=False),uid('real_operator_id','secm.user_account.user_account_id',nullable=False),Column('recorded_at',DateTime(timezone=True),nullable=False,server_default=text('clock_timestamp()'))]
    schedule=Table('bond_coupon_schedule',metadata,identity('schedule_id'),
        uid('tenant_id','ten.tenant.tenant_id',nullable=False),uid('instrument_id','secm.instrument.instrument_node_id',nullable=False),
        uid('bond_terms_id','secm.bond_terms.bond_terms_id',nullable=False),Column('terms_snapshot',JSONB,nullable=False),
        Column('revision',Integer,nullable=False),uid('supersedes_schedule_id','secm.bond_coupon_schedule.schedule_id'),
        uid('currency_id','secm.currency.currency_id',nullable=False),uid('calendar_id','cal.market_calendar.market_calendar_id'),
        uid('day_count_convention_id','secm.day_count_convention.day_count_convention_id'),Column('business_day_convention',String(40)),
        Column('source_reference',String(2000),nullable=False),Column('reason',String(2000),nullable=False),
        Column('request_key',String(255),nullable=False),Column('request_hash',String(64),nullable=False),*audit(),
        UniqueConstraint('tenant_id','instrument_id','revision',name='uq_bond_coupon_schedule_revision'),
        UniqueConstraint('tenant_id','request_key',name='uq_bond_coupon_schedule_request'),
        CheckConstraint('revision>0',name='ck_bond_coupon_schedule_revision'),schema='secm')
    period=Table('bond_coupon_period',metadata,identity('period_id'),uid('schedule_id','secm.bond_coupon_schedule.schedule_id',nullable=False),
        Column('coupon_key',String(100),nullable=False),Column('accrual_start',Date,nullable=False),Column('accrual_end',Date,nullable=False),
        Column('payment_date',Date,nullable=False),Column('record_date',Date),Column('ex_date',Date),
        Column('coupon_rate',Numeric(20,12)),Column('amount_per_100',Numeric(30,12)),Column('rate_formula',String(2000)),
        UniqueConstraint('schedule_id','coupon_key',name='uq_bond_coupon_period_key'),
        CheckConstraint('accrual_end>accrual_start AND payment_date>=accrual_start',name='ck_bond_coupon_period_dates'),
        CheckConstraint('coupon_rate IS NOT NULL OR amount_per_100 IS NOT NULL OR rate_formula IS NOT NULL',name='ck_bond_coupon_period_economics'),schema='secm')
    payment=Table('bond_coupon_payment',metadata,identity('payment_id'),uid('logical_payment_id',nullable=False),
        uid('tenant_id','ten.tenant.tenant_id',nullable=False),uid('strategy_id','trd.strategy.strategy_id',nullable=False),
        uid('period_id','secm.bond_coupon_period.period_id',nullable=False),Column('revision',Integer,nullable=False),
        uid('supersedes_payment_id','trd.bond_coupon_payment.payment_id'),Column('status',String(20),nullable=False),
        Column('payment_date',Date,nullable=False),Column('amount',Numeric(30,12),nullable=False),
        uid('currency_id','secm.currency.currency_id',nullable=False),uid('cash_account_id','trd.cash_account.cash_account_id'),
        Column('source_reference',String(2000),nullable=False),Column('note',String(2000),nullable=False),
        Column('request_key',String(255),nullable=False),Column('request_hash',String(64),nullable=False),*audit(),
        UniqueConstraint('logical_payment_id','revision',name='uq_bond_coupon_payment_revision'),
        UniqueConstraint('tenant_id','request_key',name='uq_bond_coupon_payment_request'),
        CheckConstraint("revision>0 AND status IN ('CONFIRMED','REVERSED')",name='ck_bond_coupon_payment_status'),
        CheckConstraint('amount<>0 AND amount>-1000000000000000000 AND amount<1000000000000000000',name='ck_bond_coupon_payment_amount'),schema='trd')
    Index('ix_bond_coupon_payment_report',payment.c.tenant_id,payment.c.strategy_id,payment.c.payment_date)
    for table in (schedule,period,payment):
        table.comment='Retained coupon schedule/payment facts. No automatic earnings, cash or trade posting.'
        for col in table.c: col.comment=col.comment or ('Exact decimal contractual/confirmed amount; not automatically P&L.' if isinstance(col.type,Numeric) else 'Coupon source, scope, date or immutable revision identity: '+col.name)
