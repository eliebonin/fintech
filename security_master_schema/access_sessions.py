"""Opaque, expiring local test sessions; never a production authentication seam."""
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from secrets import token_urlsafe
from uuid import uuid4
from sqlalchemy import select, update
from . import models as m
from .access_management import require_platform, audit
from .tenant_workspace import resolve_tenant_workspace


def local_only(environment):
    if environment not in {'local','test','development'}:
        raise PermissionError('Local context switching is disabled outside development')


def start(c, actor, tenant, subject, *, environment):
    local_only(environment)
    require_platform(c,actor)
    if (tenant is None)!=(subject is None):
        raise ValueError('Select both tenant and user, or platform mode')
    if tenant:
        resolve_tenant_workspace(c,tenant,subject,datetime.now(timezone.utc).date())
    token=token_urlsafe(48)
    c.execute(m.local_access_session.insert().values(session_id=uuid4(),token_hash=sha256(token.encode()).hexdigest(),
        actor_id=actor,tenant_id=tenant,subject_id=subject,expires_at_utc=datetime.now(timezone.utc)+timedelta(hours=4)))
    audit(c,actor,tenant,'CONTEXT_STARTED',{'mode':'TENANT' if tenant else 'PLATFORM'},subject)
    return token


def resolve(c, token, *, environment):
    local_only(environment)
    row=c.execute(select(m.local_access_session).where(m.local_access_session.c.token_hash==sha256(token.encode()).hexdigest(),
        m.local_access_session.c.revoked_at_utc.is_(None),m.local_access_session.c.expires_at_utc>datetime.now(timezone.utc))).mappings().one_or_none()
    if row is None:
        raise PermissionError('Testing session expired, revoked or invalid; select a context again')
    require_platform(c,row['actor_id'])
    user=row['subject_id'] or row['actor_id']
    name=c.scalar(select(m.person.c.display_name).join(m.user_account,m.user_account.c.person_id==m.person.c.person_id)
        .where(m.user_account.c.user_account_id==user)) or str(user)
    result=dict(actorId=str(row['actor_id']),userId=str(user),userName=name,
        tenantId=str(row['tenant_id']) if row['tenant_id'] else None,
        platformRole='PLATFORM_ADMIN' if row['tenant_id'] is None else None,expiresAt=row['expires_at_utc'].isoformat())
    if row['tenant_id']:
        workspace=resolve_tenant_workspace(c,row['tenant_id'],user,datetime.now(timezone.utc).date())
        result.update(tenantName=workspace.tenant_name,tenantCode=workspace.tenant_code,
            membershipRole=workspace.membership_role,moduleCodes=sorted(workspace.module_codes),
            tenantModuleCodes=sorted(workspace.tenant_module_codes),permissionCodes=sorted(workspace.permission_codes))
    return result


def revoke(c, token, *, environment):
    result=resolve(c,token,environment=environment)
    c.execute(update(m.local_access_session).where(m.local_access_session.c.token_hash==sha256(token.encode()).hexdigest())
        .values(revoked_at_utc=datetime.now(timezone.utc)))
    from uuid import UUID
    audit(c,UUID(result['actorId']),UUID(result['tenantId']) if result['tenantId'] else None,'CONTEXT_ENDED',{},UUID(result['userId']))


def end(c, actor, token, *, environment):
    """Allow the trusted local operator to end even an expired session."""
    local_only(environment)
    require_platform(c, actor)
    if not token:
        return
    row=c.execute(select(m.local_access_session).where(
        m.local_access_session.c.token_hash==sha256(token.encode()).hexdigest())).mappings().one_or_none()
    if row is None:
        return  # Clearing an unknown stale browser cookie is idempotent.
    if row['actor_id'] != actor:
        raise PermissionError('Only the real operator can end this testing session')
    if row['revoked_at_utc'] is None:
        c.execute(update(m.local_access_session).where(m.local_access_session.c.session_id==row['session_id'])
            .values(revoked_at_utc=datetime.now(timezone.utc)))
        audit(c, actor, row['tenant_id'], 'CONTEXT_ENDED', {}, row['subject_id'])
