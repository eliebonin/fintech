"""Normalized immutable profile versions, field rules and retained assignments."""
from sqlalchemy import Table,Column,String,Integer,Text,DateTime,ForeignKey,ForeignKeyConstraint,UniqueConstraint,CheckConstraint,Index,text
from sqlalchemy.dialects.postgresql import UUID


def register(metadata):
    def uid(name,**kw):return Column(name,UUID(as_uuid=True),**kw)
    def stamp():return Column('recorded_at',DateTime(timezone=True),nullable=False,server_default=text('now()'))
    profile=Table('trade_profile',metadata,
        uid('profile_id',primary_key=True),uid('tenant_id',nullable=False),Column('code',String(100),nullable=False),Column('status',String(20),nullable=False,server_default=text("'ACTIVE'")),
        uid('created_by',nullable=False),stamp(),ForeignKeyConstraint(['tenant_id'],['ten.tenant.tenant_id']),ForeignKeyConstraint(['created_by'],['secm.user_account.user_account_id']),
        UniqueConstraint('tenant_id','code',name='uq_trade_profile_code'),UniqueConstraint('tenant_id','profile_id',name='uq_trade_profile_owner'),CheckConstraint("status IN ('ACTIVE','RETIRED')",name='ck_trade_profile_status'),schema='trd')
    version=Table('trade_profile_version',metadata,
        uid('version_id',primary_key=True),uid('tenant_id',nullable=False),uid('profile_id',nullable=False),Column('version_no',Integer,nullable=False),Column('label',String(250),nullable=False),Column('description',Text),Column('reason',String(2000),nullable=False),Column('content_hash',String(64),nullable=False),Column('field_count',Integer,nullable=False,server_default=text('0')),uid('published_by',nullable=False),stamp(),
        ForeignKeyConstraint(['tenant_id','profile_id'],['trd.trade_profile.tenant_id','trd.trade_profile.profile_id']),ForeignKeyConstraint(['published_by'],['secm.user_account.user_account_id']),
        UniqueConstraint('tenant_id','version_id',name='uq_trade_profile_version_owner'),UniqueConstraint('tenant_id','profile_id','version_no',name='uq_trade_profile_version_number'),CheckConstraint("version_no>0 AND length(trim(label))>0 AND length(trim(reason))>0",name='ck_trade_profile_version'),schema='trd')
    rule=Table('trade_profile_field_rule',metadata,
        uid('rule_id',primary_key=True),uid('tenant_id',nullable=False),uid('profile_version_id',nullable=False),Column('standard_field_key',String(40)),Column('property_code',String(100)),Column('property_version',Integer),Column('requirement',String(20),nullable=False),Column('lifecycle_behavior',String(20),nullable=False),
        ForeignKeyConstraint(['tenant_id','profile_version_id'],['trd.trade_profile_version.tenant_id','trd.trade_profile_version.version_id']),
        ForeignKeyConstraint(['tenant_id','property_code','property_version'],['trd.trade_property_definition.tenant_id','trd.trade_property_definition.code','trd.trade_property_definition.version_no']),
        CheckConstraint("(standard_field_key IS NOT NULL AND property_code IS NULL AND property_version IS NULL) OR (standard_field_key IS NULL AND property_code IS NOT NULL AND property_version IS NOT NULL AND property_version>0)",name='ck_trade_profile_rule_source'),
        CheckConstraint("standard_field_key IS NULL OR standard_field_key IN ('COUNTERPARTY','EXECUTING_BROKER','TRADER','COMMENT')",name='ck_trade_profile_standard_key'),
        CheckConstraint("requirement IN ('REQUIRED','OPTIONAL','NOT_USED') AND lifecycle_behavior IN ('ALLOCATION','INHERIT','INPUT') AND (requirement<>'NOT_USED' OR lifecycle_behavior='INPUT') AND NOT (standard_field_key='COMMENT' AND lifecycle_behavior='ALLOCATION')",name='ck_trade_profile_rule_behavior'),schema='trd')
    Index('uq_profile_custom_field',rule.c.profile_version_id,rule.c.property_code,unique=True,postgresql_where=text('property_code IS NOT NULL'))
    Index('uq_profile_standard_field',rule.c.profile_version_id,rule.c.standard_field_key,unique=True,postgresql_where=text('standard_field_key IS NOT NULL'))
    Index('ix_profile_field_usage',rule.c.tenant_id,rule.c.property_code,rule.c.profile_version_id)
    assignment=Table('strategy_trade_profile_assignment',metadata,
        uid('tenant_id',nullable=False),uid('strategy_id',primary_key=True),Column('revision',Integer,primary_key=True),uid('profile_version_id',nullable=False),Column('previous_revision',Integer),uid('actor_id',nullable=False),Column('reason',String(2000),nullable=False),stamp(),
        ForeignKeyConstraint(['tenant_id','strategy_id'],['trd.strategy.tenant_id','trd.strategy.strategy_id']),ForeignKeyConstraint(['tenant_id','profile_version_id'],['trd.trade_profile_version.tenant_id','trd.trade_profile_version.version_id']),ForeignKeyConstraint(['actor_id'],['secm.user_account.user_account_id']),
        ForeignKeyConstraint(['strategy_id','previous_revision'],['ten.strategy_trade_profile_assignment.strategy_id','ten.strategy_trade_profile_assignment.revision']),
        UniqueConstraint('strategy_id','revision','profile_version_id',name='uq_strategy_profile_proof'),
        CheckConstraint("revision>0 AND length(trim(reason))>0 AND ((revision=1 AND previous_revision IS NULL) OR (previous_revision IS NOT NULL AND previous_revision=revision-1))",name='ck_strategy_profile_revision'),schema='ten')
    defaults=Table('tenant_trade_profile_default',metadata,
        uid('tenant_id',primary_key=True),Column('revision',Integer,primary_key=True),uid('profile_version_id',nullable=False),uid('actor_id',nullable=False),Column('reason',String(2000),nullable=False),stamp(),
        ForeignKeyConstraint(['tenant_id','profile_version_id'],['trd.trade_profile_version.tenant_id','trd.trade_profile_version.version_id']),ForeignKeyConstraint(['actor_id'],['secm.user_account.user_account_id']),CheckConstraint('revision>0 AND length(trim(reason))>0',name='ck_tenant_profile_default'),schema='ten')
    Index('ix_strategy_profile_current',assignment.c.tenant_id,assignment.c.strategy_id,assignment.c.revision.desc())
    Index('ix_profile_versions',version.c.tenant_id,version.c.profile_id,version.c.version_no.desc())
    Index('ix_profile_assignments',assignment.c.tenant_id,assignment.c.profile_version_id,assignment.c.strategy_id)
    return profile,version,rule,assignment,defaults
