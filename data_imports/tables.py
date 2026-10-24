"""Private bounded artifacts and immutable row-to-booking identities."""
from sqlalchemy import Table,Column,String,DateTime,ForeignKey,UniqueConstraint,LargeBinary,Index,text
from sqlalchemy.dialects.postgresql import UUID,JSONB
from security_master_schema.models import metadata

job=Table('file_import_job',metadata,
    Column('job_id',UUID(as_uuid=True),primary_key=True),
    Column('tenant_id',UUID(as_uuid=True),ForeignKey('ten.tenant.tenant_id'),nullable=False),
    Column('strategy_id',UUID(as_uuid=True),ForeignKey('trd.strategy.strategy_id'),nullable=False),
    Column('actor_id',UUID(as_uuid=True),ForeignKey('secm.user_account.user_account_id'),nullable=False),
    Column('request_key',String(255),nullable=False),Column('request_hash',String(64),nullable=False),
    Column('source',String(100),nullable=False),Column('filename',String(200),nullable=False),
    Column('artifact',LargeBinary,nullable=False),Column('artifact_sha256',String(64),nullable=False),
    Column('status',String(30),nullable=False),Column('report',JSONB,nullable=False),
    Column('created_at',DateTime(timezone=True),nullable=False,server_default=text('clock_timestamp()')),
    UniqueConstraint('tenant_id','request_key',name='uq_import_job_request'),schema='trd')
Index('ix_import_job_scope',job.c.tenant_id,job.c.strategy_id,job.c.created_at)
row=Table('file_import_trade_identity',metadata,
    Column('tenant_id',UUID(as_uuid=True),ForeignKey('ten.tenant.tenant_id'),primary_key=True),
    Column('strategy_id',UUID(as_uuid=True),ForeignKey('trd.strategy.strategy_id'),primary_key=True),
    Column('source',String(100),primary_key=True),Column('source_trade_id',String(200),primary_key=True),
    Column('payload_hash',String(64),nullable=False),Column('trade_id',UUID(as_uuid=True),ForeignKey('trd.trade.trade_id'),nullable=False),
    Column('job_id',UUID(as_uuid=True),ForeignKey('trd.file_import_job.job_id'),nullable=False),schema='trd')

_comments={
    'job_id':'Retained import identity; links original artifact, review and committed receipt.',
    'tenant_id':'Owning tenant; resolved from current authenticated context, not workbook metadata.',
    'strategy_id':'Owning strategy; every read and command rechecks action-bound strategy access.',
    'actor_id':'Authenticated account that submitted the original file; later commands retain their own audit actor.',
    'request_key':'Tenant-scoped original upload retry key; conflicting reuse is rejected.',
    'request_hash':'Hash of original upload intent including actor, source, scope and exact encoded content.',
    'source':'Tenant/strategy-scoped stable external delivery namespace, not a permission or provider licence.',
    'filename':'Untrusted original display filename; never used as a filesystem path or download header.',
    'artifact':'Bounded original bytes retained privately; no public static access or formula execution.',
    'artifact_sha256':'SHA-256 of exact retained original bytes, separate from row deduplication identity.',
    'status':'Current intake/review/application state; READY is not booked and APPLIED has a durable receipt.',
    'report':'Retained validation rows, proposed facts, review hash and per-row application receipt; not a parallel ledger.',
    'created_at':'Actual server receipt time; never backdated to the execution date in the uploaded file.',
    'source_trade_id':'Stable external trade ID within tenant, strategy and source; different economics require explicit correction.',
    'payload_hash':'Hash of normalised booking request for immutable external row identity conflict checks.',
    'trade_id':'Actual booked ledger record, created through the existing authorised cash-booking service.',
}
for table in (job,row):
    for field in table.columns:field.comment=_comments[field.name]
