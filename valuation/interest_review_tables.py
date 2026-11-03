"""Append-only typed Ops decisions, separate from financial source records."""
from sqlalchemy import Table,Column,Date,DateTime,String,Integer,Numeric,ForeignKey,ForeignKeyConstraint,UniqueConstraint,CheckConstraint,Index,text
from sqlalchemy.dialects.postgresql import UUID,JSONB


def register(metadata):
    global review,item
    uid=UUID(as_uuid=True)
    review=Table('interest_review',metadata,
        Column('review_id',uid,primary_key=True,server_default=text('uuidv7()')),
        Column('tenant_id',uid,ForeignKey('ten.tenant.tenant_id'),nullable=False),
        Column('strategy_id',uid,ForeignKey('trd.strategy.strategy_id'),nullable=False),
        Column('value_date',Date,nullable=False),Column('stage',String(20),nullable=False),Column('state',String(20),nullable=False),
        Column('revision',Integer,nullable=False),Column('row_count',Integer,nullable=False),Column('gap_count',Integer,nullable=False),Column('supersedes_review_id',uid,ForeignKey('nav.interest_review.review_id')),
        Column('daily_review_id',uid,ForeignKey('nav.interest_review.review_id')),
        Column('source_hash',String(64),nullable=False),Column('source_proof',JSONB,nullable=False),
        Column('actor_id',uid,ForeignKey('secm.user_account.user_account_id'),nullable=False),
        Column('real_operator_id',uid,ForeignKey('secm.user_account.user_account_id'),nullable=False),
        Column('recorded_at',DateTime(timezone=True),nullable=False,server_default=text('clock_timestamp()')),
        Column('request_key',String(255),nullable=False),Column('request_hash',String(64),nullable=False),
        UniqueConstraint('tenant_id','request_key',name='uq_interest_review_key'),
        UniqueConstraint('tenant_id','strategy_id','value_date','stage','revision',name='uq_interest_review_revision'),
        UniqueConstraint('review_id','tenant_id','strategy_id','value_date',name='uq_interest_review_scope'),
        CheckConstraint("stage IN ('DAILY','BALANCE') AND state IN ('DRAFT','VALIDATED') AND revision>0 AND row_count>0 AND gap_count BETWEEN 0 AND row_count AND (stage='BALANCE' OR daily_review_id IS NULL)",name='ck_interest_review_state'),schema='nav')
    item=Table('interest_review_item',metadata,
        Column('review_item_id',uid,primary_key=True,server_default=text('uuidv7()')),
        Column('review_id',uid,nullable=False),Column('tenant_id',uid,nullable=False),Column('strategy_id',uid,nullable=False),Column('value_date',Date,nullable=False),
        Column('instrument_id',uid,ForeignKey('secm.instrument.instrument_node_id'),nullable=False),
        Column('currency_id',uid,ForeignKey('secm.currency.currency_id'),nullable=False),
        *[Column(name,Numeric()) for name in ('source_amount','opening_balance','daily_increment')],Column('proposed_amount',Numeric(30,12)),
        Column('benchmark_daily',Numeric()),Column('covered_days',Integer,nullable=False),
        Column('decision',String(20),nullable=False),
        Column('source_input_id',uid,ForeignKey('nav.daily_accrual_input.input_id')),
        Column('balance_input_id',uid,ForeignKey('nav.accrued_balance_input.input_id')),
        Column('source_reference',String(2000),nullable=False),Column('reason',String(2000),nullable=False),Column('evidence',JSONB,nullable=False),
        ForeignKeyConstraint(['review_id','tenant_id','strategy_id','value_date'],['nav.interest_review.review_id','nav.interest_review.tenant_id','nav.interest_review.strategy_id','nav.interest_review.value_date']),
        UniqueConstraint('review_id','instrument_id','currency_id',name='uq_interest_review_item'),
        CheckConstraint("covered_days BETWEEN 1 AND 31 AND decision IN ('ASSESSED','NOT_SUPPLIED') AND (decision<>'NOT_SUPPLIED' OR proposed_amount IS NULL AND length(trim(reason))>0)",name='ck_interest_review_coverage'),schema='nav')
    Index('ix_interest_review_scope',review.c.tenant_id,review.c.strategy_id,review.c.value_date,review.c.stage,review.c.revision)
    for table in (review,item):
        table.comment='Immutable Ops daily interest/balance review decisions; not publication or accounting.'
        for column in table.c:column.comment='Typed review source, exact amount, scope or immutable decision evidence: '+column.name
