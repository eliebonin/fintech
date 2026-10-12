"""Tenant access-management metadata, registered separately from security terms."""
from sqlalchemy import Column, Table, String, ForeignKey, ForeignKeyConstraint, UniqueConstraint, CheckConstraint, DateTime, Text, text
from sqlalchemy.dialects.postgresql import UUID, JSONB


def register_access_tables(metadata):
    uid = UUID(as_uuid=True)
    now = text('CURRENT_TIMESTAMP')
    group = Table('access_group', metadata,
        Column('group_id', uid, primary_key=True, server_default=text('uuidv7()')),
        Column('tenant_id', uid, ForeignKey('ten.tenant.tenant_id'), nullable=False),
        Column('code', String(100), nullable=False), Column('display_name', String(250), nullable=False),
        Column('description', Text), Column('status', String(20), nullable=False, server_default=text("'ACTIVE'")),
        Column('created_at_utc', DateTime(timezone=True), nullable=False, server_default=now),
        UniqueConstraint('tenant_id', 'code', name='uq_access_group_code'),
        UniqueConstraint('tenant_id', 'group_id', name='uq_access_group_scope'),
        CheckConstraint("status IN ('ACTIVE','SUSPENDED')", name='ck_access_group_status'), schema='ten')
    member = Table('access_group_member', metadata,
        Column('tenant_id', uid, nullable=False, primary_key=True),
        Column('group_id', uid, nullable=False, primary_key=True),
        Column('user_account_id', uid, ForeignKey('secm.user_account.user_account_id'), nullable=False, primary_key=True),
        ForeignKeyConstraint(['tenant_id','group_id'], ['ten.access_group.tenant_id','ten.access_group.group_id']),
        schema='ten')
    grant = Table('access_group_grant', metadata,
        Column('tenant_id', uid, nullable=False, primary_key=True),
        Column('group_id', uid, nullable=False, primary_key=True),
        Column('action_code', String(60), nullable=False, primary_key=True),
        ForeignKeyConstraint(['tenant_id','group_id'], ['ten.access_group.tenant_id','ten.access_group.group_id']), schema='ten')
    audit = Table('access_audit_event', metadata,
        Column('event_id', uid, primary_key=True, server_default=text('uuidv7()')),
        Column('tenant_id', uid, ForeignKey('ten.tenant.tenant_id')),
        Column('actor_id', uid, ForeignKey('secm.user_account.user_account_id'), nullable=False),
        Column('subject_id', uid, ForeignKey('secm.user_account.user_account_id')),
        Column('action', String(100), nullable=False), Column('details', JSONB, nullable=False),
        Column('recorded_at_utc', DateTime(timezone=True), nullable=False, server_default=now), schema='ten')
    session = Table('local_access_session', metadata,
        Column('session_id', uid, primary_key=True), Column('token_hash', String(64), nullable=False, unique=True),
        Column('actor_id', uid, ForeignKey('secm.user_account.user_account_id'), nullable=False),
        Column('subject_id', uid, ForeignKey('secm.user_account.user_account_id')),
        Column('tenant_id', uid, ForeignKey('ten.tenant.tenant_id')),
        Column('expires_at_utc', DateTime(timezone=True), nullable=False),
        Column('revoked_at_utc', DateTime(timezone=True)),
        Column('created_at_utc', DateTime(timezone=True), nullable=False, server_default=now),
        CheckConstraint('(tenant_id IS NULL) = (subject_id IS NULL)', name='ck_local_access_session_context'), schema='ten')
    documentation={
        'group_id':'Immutable tenant group identifier; paired with tenant scope on membership and grant references.',
        'tenant_id':'Tenant scope; null only for platform audit or platform-only local sessions.',
        'code':'Stable tenant-unique group code.',
        'display_name':'Human-readable name of the tenant permission group.',
        'description':'Optional operational purpose of this tenant group.',
        'status':'ACTIVE or SUSPENDED; suspended groups confer no permissions.',
        'created_at_utc':'UTC recording time of group or local session creation.',
        'user_account_id':'Account assigned to this tenant group; active tenant membership is checked separately.',
        'action_code':'Controlled action grant; effective access also requires the tenant module entitlement.',
        'event_id':'Immutable UUIDv7 audit event identity.',
        'actor_id':'Real authenticated operator, retained independently of a selected tenant user.',
        'subject_id':'Selected effective user; null for platform-only context.',
        'action':'Controlled access-management or context-switch audit action.',
        'details':'Structured identifiers and changes; never raw session tokens or provider data.',
        'recorded_at_utc':'UTC time at which this access audit event was recorded.',
        'session_id':'Opaque local session record identity; not the authentication token.',
        'token_hash':'SHA256 digest of the local token; the raw bearer token is never stored.',
        'expires_at_utc':'UTC expiry boundary after which this local session is invalid.',
        'revoked_at_utc':'UTC revocation time; null while not explicitly revoked.',
    }
    for table in (group,member,grant,audit,session):
        for column in table.c: column.comment=documentation[column.name]
    return group, member, grant, audit, session
