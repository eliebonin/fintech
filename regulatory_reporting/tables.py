"""Reporting records share model metadata; immutable revisions own evidence."""
from sqlalchemy import Table,Column,String,Text,Integer,Date,DateTime,ForeignKey,UniqueConstraint,Boolean,text
from sqlalchemy.dialects.postgresql import UUID,JSONB

def register(metadata):
    global profile,profile_revision,candidate,candidate_revision,export
    uid=UUID(as_uuid=True)
    def key(name):return Column(name,uid,primary_key=True)
    def tenant():return Column('tenant_id',uid,ForeignKey('ten.tenant.tenant_id'),nullable=False)
    def actor():return Column('actor_id',uid,ForeignKey('secm.user_account.user_account_id'),nullable=False)
    def stamp():return Column('recorded_at',DateTime(timezone=True),nullable=False,server_default=text('clock_timestamp()'))
    profile=Table('reporting_profile',metadata,key('profile_id'),tenant(),
        Column('name',String(250),nullable=False),Column('lei',String(20),nullable=False),
        Column('firm_category',String(40),nullable=False),Column('firm_scope',String(20),nullable=False),
        Column('reason',Text,nullable=False),Column('revision',Integer,nullable=False),actor(),stamp(),schema='reg')
    profile_revision=Table('profile_revision',metadata,
        Column('profile_id',uid,ForeignKey('reg.reporting_profile.profile_id'),primary_key=True),
        Column('revision',Integer,primary_key=True),tenant(),Column('payload',JSONB,nullable=False),actor(),stamp(),schema='reg')
    candidate=Table('transaction_candidate',metadata,key('candidate_id'),tenant(),
        Column('strategy_id',uid,ForeignKey('trd.strategy.strategy_id'),nullable=False),
        Column('trade_id',uid,ForeignKey('trd.trade.trade_id'),nullable=False),
        Column('profile_id',uid,ForeignKey('reg.reporting_profile.profile_id'),nullable=False),
        Column('execution_date',Date,nullable=False),Column('revision',Integer,nullable=False),
        Column('source_hash',String(64),nullable=False),Column('payload',JSONB,nullable=False),
        Column('reportability',String(30),nullable=False),Column('readiness',String(20),nullable=False),
        Column('disposition',String(10),nullable=False),Column('included',Boolean,nullable=False),actor(),stamp(),
        UniqueConstraint('tenant_id','profile_id','trade_id',name='uq_reporting_candidate'),schema='reg')
    candidate_revision=Table('candidate_revision',metadata,
        Column('candidate_id',uid,ForeignKey('reg.transaction_candidate.candidate_id'),primary_key=True),
        Column('revision',Integer,primary_key=True),tenant(),Column('payload',JSONB,nullable=False),actor(),stamp(),schema='reg')
    export=Table('preparation_export',metadata,key('export_id'),tenant(),
        Column('profile_id',uid,ForeignKey('reg.reporting_profile.profile_id'),nullable=False),
        Column('strategy_id',uid,ForeignKey('trd.strategy.strategy_id'),nullable=False),
        Column('request_key',String(200),nullable=False),Column('request_hash',String(64),nullable=False),
        Column('manifest',JSONB,nullable=False),Column('csv_content',Text,nullable=False),
        Column('content_hash',String(64),nullable=False),actor(),stamp(),
        UniqueConstraint('tenant_id','request_key',name='uq_reporting_export_request'),schema='reg')
    descriptions={
        'profile_id':'Stable tenant-owned reporting legal-entity profile, distinct from a strategy or fund.',
        'tenant_id':'Authoritative owner tenant; never accepted from browser request data.',
        'name':'Assessed reporting legal entity name.', 'lei':'Reporting entity LEI with local format/checksum validation; not registration-status proof.',
        'firm_category':'Declared regulatory category; does not itself establish reporting liability.',
        'firm_scope':'Explicitly assessed UK MiFIR firm scope; unknown remains UNASSESSED.',
        'reason':'Retained rationale for the profile assessment or change.',
        'revision':'Optimistic review version; immutable histories retain preceding versions.',
        'actor_id':'Selected authenticated actor; real operator ancestry is also retained by request audit.',
        'recorded_at':'UTC wall-clock time of the retained change/export.',
        'payload':'Versioned preparation evidence, exact decimal strings and reasoned review decisions; no final schema assertion.',
        'candidate_id':'Stable execution/profile preparation identity; distinct from a regulatory transaction reference.',
        'strategy_id':'Strategy owning the execution evidence; current action-bound access is required.',
        'trade_id':'Original booked execution/event; review does not alter its economics.',
        'execution_date':'UTC execution date, not valuation recognition or settlement date.',
        'source_hash':'SHA256 of execution/lifecycle evidence, current visibility/classification and profile revision.',
        'reportability':'Reasoned REPORTABLE, NOT_REPORTABLE or NEEDS_ASSESSMENT decision, separate from readiness.',
        'readiness':'Local preparation readiness only; not complete RTS 22 or FCA XSD validation.',
        'disposition':'AUTO inclusion when ready, or reasoned HOLD; neither changes regulatory scope.',
        'included':'Current reportable, ready and non-held preparation-export eligibility.',
        'export_id':'Stable immutable preparation artifact identity; not a regulator acknowledgement.',
        'request_key':'Tenant-scoped retry identity for one complete frozen export request.',
        'request_hash':'Canonical request hash; key reuse with a changed request is rejected.',
        'manifest':'Frozen complete population, included revisions, entity snapshot and outstanding reconciliation counts.',
        'csv_content':'Exact UTF-8 preparation CSV with spreadsheet formula protection; not a submission-format claim.',
        'content_hash':'SHA256 of the retained CSV bytes, rechecked on download.',
    }
    for table in (profile,profile_revision,candidate,candidate_revision,export):
        for column in table.c:column.comment=descriptions[column.name]
