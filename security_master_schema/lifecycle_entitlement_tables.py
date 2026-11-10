"""Typed assistance subscription/selection history; no financial or user grants."""
from sqlalchemy import Table,Column,Integer,String,DateTime,ForeignKey,ForeignKeyConstraint,CheckConstraint,Index,text
from sqlalchemy.dialects.postgresql import UUID


def register(metadata):
    def identity(name,**kw):return Column(name,UUID(as_uuid=True),**kw)
    def revision_columns():return [Column('revision',Integer,primary_key=True),Column('previous_revision',Integer),Column('reason',String(2000),nullable=False),identity('actor_id',nullable=False),identity('real_operator_id',nullable=False),Column('recorded_at',DateTime(timezone=True),nullable=False,server_default=text('now()'))]
    subscription=Table('tenant_lifecycle_subscription',metadata,identity('tenant_id',primary_key=True),*revision_columns(),
        Column('maximum_tier',Integer,nullable=False),Column('source',String(20),nullable=False),
        ForeignKeyConstraint(['tenant_id'],['ten.tenant.tenant_id']),ForeignKeyConstraint(['actor_id'],['secm.user_account.user_account_id']),ForeignKeyConstraint(['real_operator_id'],['secm.user_account.user_account_id']),
        ForeignKeyConstraint(['tenant_id','previous_revision'],['ten.tenant_lifecycle_subscription.tenant_id','ten.tenant_lifecycle_subscription.revision']),
        CheckConstraint("maximum_tier BETWEEN 0 AND 3 AND source IN ('MANUAL','TRIAL','CONTRACT','MIGRATION')",name='ck_lifecycle_subscription_tier'),
        CheckConstraint("revision>0 AND length(trim(reason))>0 AND ((revision=1 AND previous_revision IS NULL) OR (previous_revision IS NOT NULL AND previous_revision=revision-1))",name='ck_lifecycle_subscription_revision'),schema='ten')
    assistance=Table('strategy_lifecycle_assistance',metadata,identity('tenant_id',primary_key=True),identity('strategy_id',primary_key=True),Column('event_type',String(40),primary_key=True),*revision_columns(),Column('selected_tier',Integer,nullable=False),
        ForeignKeyConstraint(['tenant_id','strategy_id'],['trd.strategy.tenant_id','trd.strategy.strategy_id']),ForeignKeyConstraint(['actor_id'],['secm.user_account.user_account_id']),ForeignKeyConstraint(['real_operator_id'],['secm.user_account.user_account_id']),
        ForeignKeyConstraint(['tenant_id','strategy_id','event_type','previous_revision'],['ten.strategy_lifecycle_assistance.tenant_id','ten.strategy_lifecycle_assistance.strategy_id','ten.strategy_lifecycle_assistance.event_type','ten.strategy_lifecycle_assistance.revision']),
        CheckConstraint("selected_tier BETWEEN 0 AND 3 AND event_type IN ('BOND_MATURITY','FX_FORWARD_MATURITY')",name='ck_lifecycle_assistance_tier'),
        CheckConstraint("revision>0 AND length(trim(reason))>0 AND ((revision=1 AND previous_revision IS NULL) OR (previous_revision IS NOT NULL AND previous_revision=revision-1))",name='ck_lifecycle_assistance_revision'),schema='ten')
    Index('ix_lifecycle_subscription_current',subscription.c.tenant_id,subscription.c.revision.desc())
    Index('ix_lifecycle_assistance_current',assistance.c.tenant_id,assistance.c.strategy_id,assistance.c.event_type,assistance.c.revision.desc())
    for table in (subscription,assistance):
        for column in table.c:column.comment={'tenant_id':'Tenant owning this immutable lifecycle configuration revision.','strategy_id':'Tenant-owned strategy; never a global configuration override.','maximum_tier':'Commercial assistance ceiling0–3; never a user permission.','selected_tier':'Explicit assistance choice0–3 for one supported strategy/event.','event_type':'Supported event identity, independently of instrument reference IDs.','revision':'Monotonic immutable revision in this owner/event scope.','previous_revision':'Immediately preceding revision; null only for revision1.','reason':'Retained human explanation of the reviewed configuration change.','actor_id':'Verified selected actor authorising the configuration change.','real_operator_id':'Verified operator behind the selected context.','recorded_at':'UTC recording time; financial value dates are independent.','source':'Recorded provisioning provenance; does not establish payment.'}.get(column.name)
    return subscription,assistance
