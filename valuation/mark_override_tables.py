"""Immutable, scoped manual-price requests and append-only review decisions."""
from sqlalchemy import Table,Column,String,Date,DateTime,Numeric,ForeignKey,ForeignKeyConstraint,UniqueConstraint,CheckConstraint,Index,text
from sqlalchemy.dialects.postgresql import UUID,JSONB


def register(metadata):
    global request,decision
    uid=UUID(as_uuid=True)
    request=Table('valuation_mark_override_request',metadata,
        Column('request_id',uid,primary_key=True,server_default=text('uuidv7()')),
        Column('tenant_id',uid,ForeignKey('ten.tenant.tenant_id'),nullable=False),
        Column('strategy_id',uid,ForeignKey('trd.strategy.strategy_id'),nullable=False),
        Column('base_batch_id',uid,nullable=False),Column('input_key',String(64),nullable=False),
        Column('series_id',uid,ForeignKey('md.market_data_series.market_data_series_id'),nullable=False),
        Column('currency_id',uid,ForeignKey('secm.currency.currency_id'),nullable=False),
        Column('value_date',Date,nullable=False),Column('value',Numeric(30,12),nullable=False),
        Column('quoted_accrual_per_100',Numeric(30,12)),Column('quote_settlement_date',Date),
        Column('reason',String(2000),nullable=False),Column('source_reference',String(1000),nullable=False),
        Column('requested_by',uid,ForeignKey('secm.user_account.user_account_id'),nullable=False),
        Column('real_operator_id',uid,ForeignKey('secm.user_account.user_account_id'),nullable=False),
        Column('request_context',JSONB,nullable=False),Column('request_hash',String(64),nullable=False),
        Column('submission_key',String(255),nullable=False),
        Column('recorded_at',DateTime(timezone=True),nullable=False,server_default=text('clock_timestamp()')),
        ForeignKeyConstraint(['base_batch_id','tenant_id'],['nav.pnl_review_batch.batch_id','nav.pnl_review_batch.tenant_id']),
        UniqueConstraint('request_id','tenant_id',name='uq_mark_override_scope'),
        UniqueConstraint('tenant_id','submission_key',name='uq_mark_override_key'),
        CheckConstraint("length(input_key)=64 AND length(request_hash)=64 AND length(trim(reason))>0 AND length(trim(source_reference))>0",name='ck_mark_override_content'),
        CheckConstraint('(quoted_accrual_per_100 IS NULL) = (quote_settlement_date IS NULL)',name='ck_mark_override_quote_pair'),schema='nav')
    decision=Table('valuation_mark_override_decision',metadata,
        Column('decision_id',uid,primary_key=True,server_default=text('uuidv7()')),
        Column('request_id',uid,nullable=False),Column('tenant_id',uid,nullable=False),
        Column('action',String(20),nullable=False),
        Column('reviewed_by',uid,ForeignKey('secm.user_account.user_account_id'),nullable=False),
        Column('real_operator_id',uid,ForeignKey('secm.user_account.user_account_id'),nullable=False),
        Column('comment',String(2000),nullable=False),
        Column('recorded_at',DateTime(timezone=True),nullable=False,server_default=text('clock_timestamp()')),
        ForeignKeyConstraint(['request_id','tenant_id'],['nav.valuation_mark_override_request.request_id','nav.valuation_mark_override_request.tenant_id']),
        UniqueConstraint('request_id','action',name='uq_mark_override_decision_action'),
        CheckConstraint("action IN ('APPROVED','REJECTED','WITHDRAWN') AND length(trim(comment))>0",name='ck_mark_override_decision'),schema='nav')
    Index('ix_mark_override_input',request.c.tenant_id,request.c.strategy_id,request.c.input_key,request.c.recorded_at)
    for table in (request,decision):
        table.comment='Append-only tenant-reviewed mark evidence; not a provider observation or permission to publish an incomplete result.'
        for col in table.columns:
            col.comment={
                'value':'Exact manual quote in the existing series currency and quotation, never a P&L adjustment.',
                'quoted_accrual_per_100':'Optional paired DIRTY-quote accrued component per 100, not daily interest or a strategy stock.',
                'request_context':'Frozen missing resolution, quote dimensions and source population scope.',
                'real_operator_id':'Verified real operator retained separately from the selected tenant account.',
                'input_key':'Hash binding the exact tenant, strategy, policy/rule, cut, economic price date and dimension filters.',
                'action':'Independent approval/rejection or later withdrawal; prior decisions remain immutable.',
            }.get(col.name,'Retained mark-request scope, authorship or review evidence; no in-place financial edits.')
    return request,decision
