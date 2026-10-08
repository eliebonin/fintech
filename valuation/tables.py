"""Attribution storage registered in shared metadata without runtime reflection.

Tables live beside existing valuation evidence in nav. Financial payloads are
immutable; official selection belongs to review batches, not mutable results.
"""
from sqlalchemy import Table,Column,String,DateTime,Date,Integer,Numeric,ForeignKey,ForeignKeyConstraint,UniqueConstraint,CheckConstraint,Index,text
from sqlalchemy.dialects.postgresql import UUID,JSONB

def register_valuation_tables(metadata):
    global attempt, run_event, attribution, batch, item, review_event, lineage
    uid=UUID(as_uuid=True)
    # Wall-clock evidence time, not the start of a long financial transaction.
    now=text('clock_timestamp()')
    def key(name): return Column(name,uid,primary_key=True,server_default=text('uuidv7()'))
    def actor(name): return Column(name,uid,ForeignKey('secm.user_account.user_account_id'),nullable=False)
    def scope(): return [Column('tenant_id',uid,ForeignKey('ten.tenant.tenant_id'),nullable=False),Column('strategy_id',uid,ForeignKey('trd.strategy.strategy_id'),nullable=False)]
    attempt=Table('valuation_attempt',metadata,key('attempt_id'),*scope(),actor('initiated_by'),
        Column('request_key',String(255),nullable=False),Column('request_hash',String(64),nullable=False),
        Column('request_payload',JSONB,nullable=False),Column('correlation_id',String(100),nullable=False),
        Column('status',String(20),nullable=False),Column('error_code',String(80)),
        Column('started_at',DateTime(timezone=True),nullable=False,server_default=now),Column('completed_at',DateTime(timezone=True)),
        UniqueConstraint('tenant_id','request_key',name='uq_valuation_attempt_key'),UniqueConstraint('attempt_id','tenant_id',name='uq_valuation_attempt_scope'),
        CheckConstraint("status IN ('RUNNING','COMPLETED','FAILED')",name='ck_valuation_attempt_status'),schema='nav')
    run_event=Table('valuation_run_event',metadata,key('event_id'),Column('attempt_id',uid,ForeignKey('nav.valuation_attempt.attempt_id'),nullable=False),
        Column('event_code',String(40),nullable=False),Column('stage',String(40),nullable=False),Column('details',JSONB,nullable=False),
        Column('recorded_at',DateTime(timezone=True),nullable=False,server_default=now),schema='nav')
    attribution=Table('pnl_attribution',metadata,key('attribution_id'),*scope(),
        Column('attempt_id',uid,nullable=False),Column('trade_id',uid,ForeignKey('trd.trade.trade_id')),
        Column('position_key',String(64)),Column('subject_id',uid,ForeignKey('secm.financial_reference_node.reference_node_id')),
        Column('value_date',Date,nullable=False),Column('version',Integer,nullable=False),
        Column('supersedes_attribution_id',uid,ForeignKey('nav.pnl_attribution.attribution_id')),
        Column('method',String(80),nullable=False),Column('input_hash',String(64),nullable=False),
        Column('currency_id',uid,ForeignKey('secm.currency.currency_id'),nullable=False),
        Column('market_pnl',Numeric(30,12),nullable=False),Column('gross_pnl',Numeric(30,12),nullable=False),Column('net_pnl',Numeric(30,12),nullable=False),
        Column('components',JSONB,nullable=False),Column('evidence',JSONB,nullable=False),
        Column('created_at',DateTime(timezone=True),nullable=False,server_default=now),
        ForeignKeyConstraint(['attempt_id','tenant_id'],['nav.valuation_attempt.attempt_id','nav.valuation_attempt.tenant_id']),
        UniqueConstraint('tenant_id','strategy_id','value_date','trade_id','version',name='uq_pnl_attribution_version'),
        UniqueConstraint('tenant_id','strategy_id','value_date','position_key','version',name='uq_pnl_position_version'),
        CheckConstraint("(trade_id IS NOT NULL AND position_key IS NULL AND subject_id IS NULL) OR (trade_id IS NULL AND position_key IS NOT NULL AND subject_id IS NOT NULL)",name='ck_pnl_result_owner'),
        UniqueConstraint('attribution_id','tenant_id',name='uq_pnl_attribution_scope'),CheckConstraint('version > 0',name='ck_pnl_attribution_version'),schema='nav')
    batch=Table('pnl_review_batch',metadata,key('batch_id'),*scope(),actor('staged_by'),
        Column('attempt_id',uid,nullable=False),Column('value_date',Date,nullable=False),Column('status',String(20),nullable=False),
        Column('mode',String(20),nullable=False),Column('input_hash',String(64),nullable=False),Column('base_population_hash',String(64),nullable=False),
        Column('summary',JSONB,nullable=False),Column('created_at',DateTime(timezone=True),nullable=False,server_default=now),
        ForeignKeyConstraint(['attempt_id','tenant_id'],['nav.valuation_attempt.attempt_id','nav.valuation_attempt.tenant_id']),
        UniqueConstraint('tenant_id','strategy_id','value_date','input_hash','mode',name='uq_pnl_batch_idempotency'),
        UniqueConstraint('batch_id','tenant_id',name='uq_pnl_batch_scope'),
        CheckConstraint("status IN ('STAGED','PUBLISHED','CANCELLED','SUPERSEDED')",name='ck_pnl_batch_status'),
        CheckConstraint("mode IN ('AUTHORITATIVE','INCREMENTAL')",name='ck_pnl_batch_mode'),schema='nav')
    Index('uq_pnl_published_population',batch.c.tenant_id,batch.c.strategy_id,batch.c.value_date,unique=True,postgresql_where=text("status = 'PUBLISHED'"))
    item=Table('pnl_review_item',metadata,key('item_id'),Column('tenant_id',uid,nullable=False),Column('batch_id',uid,nullable=False),
        Column('attribution_id',uid,nullable=False),Column('trade_id',uid,ForeignKey('trd.trade.trade_id')),
        Column('position_key',String(64)),
        ForeignKeyConstraint(['batch_id','tenant_id'],['nav.pnl_review_batch.batch_id','nav.pnl_review_batch.tenant_id']),
        ForeignKeyConstraint(['attribution_id','tenant_id'],['nav.pnl_attribution.attribution_id','nav.pnl_attribution.tenant_id']),
        UniqueConstraint('batch_id','trade_id',name='uq_pnl_review_trade'),
        UniqueConstraint('batch_id','position_key',name='uq_pnl_review_position'),
        CheckConstraint('(trade_id IS NULL) <> (position_key IS NULL)',name='ck_pnl_item_owner'),schema='nav')
    lineage=Table('pnl_attribution_lineage',metadata,key('lineage_id'),
        Column('attribution_id',uid,ForeignKey('nav.pnl_attribution.attribution_id'),nullable=False),
        Column('trade_id',uid,ForeignKey('trd.trade.trade_id'),nullable=False),
        Column('event_id',uid,ForeignKey('trd.trade_lifecycle_event.trade_lifecycle_event_id'),nullable=False),
        Column('role',String(30),nullable=False),
        UniqueConstraint('attribution_id','event_id',name='uq_pnl_lineage_event'),
        CheckConstraint("role IN ('OPENING_EVIDENCE','PERIOD_EXECUTION','LIFECYCLE_EVIDENCE')",name='ck_pnl_lineage_role'),schema='nav')
    review_event=Table('pnl_review_event',metadata,key('review_event_id'),Column('batch_id',uid,ForeignKey('nav.pnl_review_batch.batch_id'),nullable=False),
        actor('actor_id'),Column('action',String(30),nullable=False),Column('comment',String(2000),nullable=False),
        Column('recorded_at',DateTime(timezone=True),nullable=False,server_default=now),schema='nav')
    documentation={
        'position_key':'Hash of compatible position conventions; null for historical trade-owned results.',
        'subject_id':'Actual listing/traded subject valued by this position-owned result.',
        'tenant_id':'Tenant owning this valuation, attribution or review record; enforced together with parent scope.',
        'strategy_id':'Tenant strategy whose booked economics are valued and reviewed.',
        'initiated_by':'Authenticated account requesting this calculation attempt.',
        'staged_by':'Authenticated account staging the candidate population; cannot independently publish its own batch.',
        'actor_id':'Authenticated account recording this explanation or review decision.',
        'request_key':'Tenant-scoped retry-stable key for an unchanged calculation request.',
        'request_hash':'SHA256 of exact request configuration and initiating identity, used to reject key reuse.',
        'request_payload':'Frozen cutoff, strategy, currency and policy configuration; contains no raw provider payload.',
        'correlation_id':'Identifier linking API requests, operational diagnostics and this calculation attempt.',
        'status':'Controlled operational or review lifecycle state, constrained by this table status check.',
        'error_code':'Safe bounded failure category; never a raw exception or database connection string.',
        'started_at':'UTC recording time of the independently committed calculation attempt.',
        'completed_at':'UTC time the attempt reached a terminal COMPLETED or FAILED state.',
        'event_code':'Controlled stage event identifying start, validation, completion or failure.',
        'stage':'Named processing stage responsible for this operational event.',
        'details':'Safe structured timings, counts, identifiers and error categories; not financial input payloads.',
        'recorded_at':'UTC recording time of this immutable operational or review event.',
        'trade_id':'Original execution owner for historical v1 attribution; null for position-owned v2 results.',
        'value_date':'UTC closing-cutoff business date of this period attribution or review population.',
        'version':'Positive monotonically increasing immutable attribution version within tenant/strategy/trade/date scope.',
        'supersedes_attribution_id':'Prior immutable attribution version replaced by changed financial inputs or method.',
        'method':'Versioned calculation methodology, separate from attribution storage version.',
        'input_hash':'Canonical SHA256 of the effective financial inputs defining this attribution or review population.',
        'currency_id':'Reporting currency of the stored monetary P&L components and totals.',
        'market_pnl':'Clean price, FX and price/FX-cross movement; excludes income, fees and adjustments.',
        'gross_pnl':'Market P&L plus separately attributed income flows; equals market P&L in the first market-only alpha.',
        'net_pnl':'Gross P&L plus separately attributed signed costs/adjustments; no manual edit is permitted.',
        'components':'Exact decimal-string component amounts, reconciled to monetary totals before storage and by database trigger.',
        'evidence':'Immutable booked facts, selected input identities, calculation method and resolution snapshot lineage.',
        'created_at':'UTC recording time of this immutable financial version or staged review population.',
        'mode':'Explicit AUTHORITATIVE replacement or INCREMENTAL supplementation semantics.',
        'base_population_hash':'Official attribution selection hash at staging, checked again atomically at publication.',
        'summary':'Frozen period bridge, currency, validation state and scope limitations presented to reviewers.',
        'action':'Recorded workflow action such as STAGED, EXPLANATION, PUBLISHED, CANCELLED or SUPERSEDED.',
        'comment':'Bounded human explanation or publication rationale, retained with actor and recording time.',
    }
    for table in (attempt,run_event,attribution,batch,item,review_event):
        table.comment='Valuation/P&L evidence and review domain; operational attempts remain distinct from official financial selection.'
        for column in table.columns:
            column.comment=documentation.get(column.name) or ('Immutable UUIDv7 identity of this record.' if column.primary_key else
                {'attempt_id':'Parent calculation attempt, retaining independently recorded operational lineage.',
                 'batch_id':'Parent tenant/strategy/date review batch selecting candidate or official attribution versions.',
                 'attribution_id':'Exact immutable attribution version selected by this review item.'}[column.name])
