"""Append-only tenant policy for lifecycle annotation inheritance."""
from sqlalchemy import Table,Column,Integer,String,DateTime,ForeignKey,CheckConstraint,text
from sqlalchemy.dialects.postgresql import UUID,JSONB

def register(metadata):
    return Table('lifecycle_allocation_policy',metadata,
        Column('tenant_id',UUID(as_uuid=True),ForeignKey('ten.tenant.tenant_id'),primary_key=True),
        Column('revision',Integer,primary_key=True),Column('fields',JSONB,nullable=False),
        Column('reason',String(2000),nullable=False),
        Column('actor_id',UUID(as_uuid=True),ForeignKey('secm.user_account.user_account_id'),nullable=False),
        Column('recorded_at',DateTime(timezone=True),nullable=False,server_default=text('now()')),
        CheckConstraint("revision>0 AND jsonb_typeof(fields)='array'",name='ck_lifecycle_allocation_policy'),schema='trd')
