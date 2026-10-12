"""Transactional tenant/module and tenant-local user/group administration."""
from datetime import date, datetime, timedelta, timezone
from uuid import uuid4
from sqlalchemy import select, update, delete
from . import models as m
from .access_control import ACTION_MODULES
from .tenant_workspace import resolve_platform_role, resolve_tenant_workspace, require_tenant_action, TenantActionForbidden


def audit(c, actor, tenant, action, details, subject=None):
    c.execute(m.access_audit_event.insert().values(actor_id=actor, subject_id=subject,
        tenant_id=tenant, action=action, details=details))


def require_platform(c, actor):
    if resolve_platform_role(c, actor, date.today()) != 'PLATFORM_ADMIN':
        raise TenantActionForbidden('Platform administration authority is required')


class TenantProfileConflict(ValueError):
    """A stale form must not overwrite a newer tenant profile."""


class TenantNotFound(ValueError):
    """The platform target does not exist."""


def update_tenant(c, tenant, actor, request):
    """Lock the registry row; persist the edit and before/after audit atomically.

    Suspension blocks workspace resolution without deleting subscriptions,
    memberships or financial records. Reactivation reuses those existing grants.
    """
    require_platform(c,actor)
    row=c.execute(select(m.tenant).where(m.tenant.c.tenant_id==tenant).with_for_update()).mappings().one_or_none()
    if row is None:
        raise TenantNotFound('Tenant was not found')
    if row['profile_version']!=request.expectedVersion:
        raise TenantProfileConflict('Tenant details changed. Refresh and reopen the editor before saving again.')
    if row['status'] not in {'ACTIVE','SUSPENDED'}:
        raise ValueError('Retired tenants cannot be edited or reactivated through this workflow')
    if row['status']!=request.status and not request.confirmStatusChange:
        raise ValueError('Confirm the tenant status change and its access impact')
    before=dict(name=row['display_name'],contactName=row['operational_contact_name'],
        contactEmail=row['operational_contact_email'],status=row['status'],profileVersion=row['profile_version'])
    after=dict(name=request.name,contactName=request.contactName,contactEmail=request.contactEmail,
        status=request.status,profileVersion=row['profile_version']+1)
    c.execute(update(m.tenant).where(m.tenant.c.tenant_id==tenant).values(display_name=request.name,
        operational_contact_name=request.contactName,operational_contact_email=request.contactEmail,
        status=request.status,profile_version=after['profileVersion']))
    audit(c,actor,tenant,'TENANT_PROFILE_CHANGED',dict(before=before,after=after))
    return dict(updated=True,profileVersion=after['profileVersion'])


def require_admin(c, tenant, actor):
    workspace = resolve_tenant_workspace(c, tenant, actor, date.today())
    require_tenant_action(workspace, 'ACCESS_MANAGE')
    return workspace


def lock_tenant(c, tenant):
    if c.scalar(select(m.tenant.c.tenant_id).where(m.tenant.c.tenant_id == tenant,
          m.tenant.c.status == 'ACTIVE').with_for_update()) is None:
        raise ValueError('Active tenant was not found')


def set_module(c, tenant, actor, module_code, enabled):
    """Serialize toggles; same-day changes retain before/after in immutable audit.

    The existing entitlement schema has one version per business date. Repeated
    same-day toggles update that date's version, never insert overlapping grants.
    """
    require_platform(c, actor)
    lock_tenant(c, tenant)
    module = c.scalar(select(m.platform_module.c.platform_module_id).where(
        m.platform_module.c.module_code == module_code, m.platform_module.c.status == 'ACTIVE'))
    if module is None:
        raise ValueError('Unknown module')
    today = date.today()
    rows = c.execute(select(m.tenant_module_entitlement).where(
        m.tenant_module_entitlement.c.tenant_id == tenant,
        m.tenant_module_entitlement.c.platform_module_id == module,
        m.tenant_module_entitlement.c.valid_from <= today,
        (m.tenant_module_entitlement.c.valid_to.is_(None)) | (m.tenant_module_entitlement.c.valid_to >= today)
    ).with_for_update()).mappings().all()
    if len(rows) > 1:
        raise ValueError('Ambiguous entitlement history; repair before changing modules')
    state = 'GRANTED' if enabled else 'SUSPENDED'
    values = dict(entitlement_state=state, entitlement_source='MANUAL',
                  approved_by_user_account_id=actor, approved_at_utc=datetime.now(timezone.utc))
    prior = rows[0] if rows else None
    if prior and prior['valid_from'] == today:
        c.execute(update(m.tenant_module_entitlement).where(
            m.tenant_module_entitlement.c.tenant_module_entitlement_id == prior['tenant_module_entitlement_id']).values(**values))
    else:
        if prior:
            c.execute(update(m.tenant_module_entitlement).where(
                m.tenant_module_entitlement.c.tenant_module_entitlement_id == prior['tenant_module_entitlement_id'])
                .values(valid_to=today-timedelta(days=1)))
        c.execute(m.tenant_module_entitlement.insert().values(tenant_id=tenant, platform_module_id=module,
            valid_from=today, supersedes_entitlement_id=prior['tenant_module_entitlement_id'] if prior else None, **values))
    audit(c, actor, tenant, 'MODULE_CHANGED', {'moduleCode':module_code,
        'before':prior['entitlement_state'] if prior else None, 'after':state})


def save_group(c, tenant, actor, *, code, name, actions, group_id=None, status='ACTIVE', description=None):
    workspace = require_admin(c, tenant, actor)
    lock_tenant(c, tenant)
    code, name = code.strip().upper(), name.strip()
    if not code or not name or status not in {'ACTIVE','SUSPENDED'}:
        raise ValueError('Group code, name and valid status are required')
    if set(actions) - ACTION_MODULES.keys() or 'ACCESS_MANAGE' in actions:
        raise ValueError('Unknown or administrator-only group permission')
    for action in actions:
        if not ACTION_MODULES[action] & workspace.tenant_module_codes:
            # Existing grants remain visible while a subscription is disabled.
            existing = group_id and c.scalar(select(m.access_group_grant.c.action_code).where(
                m.access_group_grant.c.tenant_id==tenant, m.access_group_grant.c.group_id==group_id,
                m.access_group_grant.c.action_code==action))
            if not existing:
                raise ValueError('Groups can grant only modules enabled for this tenant')
    if group_id:
        if c.scalar(select(m.access_group.c.group_id).where(m.access_group.c.tenant_id==tenant,
                m.access_group.c.group_id==group_id)) is None:
            raise TenantActionForbidden('Group is outside this tenant')
        c.execute(update(m.access_group).where(m.access_group.c.tenant_id==tenant,
            m.access_group.c.group_id==group_id).values(code=code,display_name=name,description=description,status=status))
        c.execute(delete(m.access_group_grant).where(m.access_group_grant.c.tenant_id==tenant,m.access_group_grant.c.group_id==group_id))
    else:
        group_id = c.execute(m.access_group.insert().values(tenant_id=tenant,code=code,display_name=name,
            description=description,status=status).returning(m.access_group.c.group_id)).scalar_one()
    for action in sorted(set(actions)):
        c.execute(m.access_group_grant.insert().values(tenant_id=tenant,group_id=group_id,action_code=action))
    audit(c,actor,tenant,'GROUP_SAVED',{'groupId':str(group_id),'code':code,'status':status,'actions':sorted(set(actions))})
    return group_id


def add_user(c, tenant, actor, *, name, role='MEMBER'):
    require_admin(c,tenant,actor)
    lock_tenant(c,tenant)
    if not name.strip() or role not in {'MEMBER','TENANT_ADMIN'}:
        raise ValueError('User name and valid tenant role are required')
    person = c.execute(m.person.insert().values(display_name=name.strip()).returning(m.person.c.person_id)).scalar_one()
    user = c.execute(m.user_account.insert().values(person_id=person,account_type='HUMAN',status='ACTIVE')
                     .returning(m.user_account.c.user_account_id)).scalar_one()
    c.execute(m.tenant_user_account.insert().values(tenant_id=tenant,user_account_id=user,
        membership_role=role,status='ACTIVE',valid_from=date.today()))
    audit(c,actor,tenant,'USER_ADDED',{'name':name.strip(),'role':role},user)
    return user


def membership_row(c, tenant, user):
    rows = c.execute(select(m.tenant_user_account).where(m.tenant_user_account.c.tenant_id==tenant,
        m.tenant_user_account.c.user_account_id==user, m.tenant_user_account.c.valid_from<=date.today(),
        m.tenant_user_account.c.valid_to.is_(None) | (m.tenant_user_account.c.valid_to>=date.today()))).mappings().all()
    if len(rows) != 1:
        raise TenantActionForbidden('User is outside this tenant or membership is ambiguous')
    return rows[0]


def set_user_groups(c, tenant, actor, user, groups):
    require_admin(c,tenant,actor)
    lock_tenant(c,tenant)
    membership_row(c,tenant,user)
    valid = set(c.scalars(select(m.access_group.c.group_id).where(m.access_group.c.tenant_id==tenant,
        m.access_group.c.status=='ACTIVE', m.access_group.c.group_id.in_(groups)))) if groups else set()
    if valid != set(groups):
        raise TenantActionForbidden('Group is inactive or outside this tenant')
    c.execute(delete(m.access_group_member).where(m.access_group_member.c.tenant_id==tenant,m.access_group_member.c.user_account_id==user))
    for group in sorted(valid,key=str):
        c.execute(m.access_group_member.insert().values(tenant_id=tenant,group_id=group,user_account_id=user))
    audit(c,actor,tenant,'USER_GROUPS_CHANGED',{'groupIds':sorted(map(str,valid))},user)


def set_user_status(c, tenant, actor, user, status, role=None):
    require_admin(c,tenant,actor)
    lock_tenant(c,tenant)
    row = membership_row(c,tenant,user)
    if status not in {'ACTIVE','SUSPENDED'} or (role and role not in {'MEMBER','TENANT_ADMIN'}):
        raise ValueError('Invalid membership status or role')
    if row['membership_role']=='TENANT_ADMIN' and row['status']=='ACTIVE' and (status!='ACTIVE' or role=='MEMBER'):
        admins = c.execute(select(m.tenant_user_account.c.user_account_id)
            .join(m.user_account,m.user_account.c.user_account_id==m.tenant_user_account.c.user_account_id)
            .where(m.tenant_user_account.c.tenant_id==tenant,m.tenant_user_account.c.membership_role=='TENANT_ADMIN',
                m.tenant_user_account.c.status=='ACTIVE',m.user_account.c.status=='ACTIVE',
                m.tenant_user_account.c.valid_from<=date.today(),
                m.tenant_user_account.c.valid_to.is_(None)|(m.tenant_user_account.c.valid_to>=date.today()))).all()
        if len(admins)<=1:
            raise ValueError('Cannot remove the last active tenant administrator')
    c.execute(update(m.tenant_user_account).where(m.tenant_user_account.c.tenant_user_account_id==row['tenant_user_account_id'])
        .values(status=status,membership_role=role or row['membership_role']))
    audit(c,actor,tenant,'USER_MEMBERSHIP_CHANGED',{'status':status,'role':role or row['membership_role']},user)


def tenant_access_view(c, tenant, actor):
    workspace = require_admin(c,tenant,actor)
    groups=[]
    for row in c.execute(select(m.access_group).where(m.access_group.c.tenant_id==tenant).order_by(m.access_group.c.display_name)).mappings():
        actions=list(c.scalars(select(m.access_group_grant.c.action_code).where(m.access_group_grant.c.tenant_id==tenant,
            m.access_group_grant.c.group_id==row['group_id']).order_by(m.access_group_grant.c.action_code)))
        groups.append(dict(groupId=str(row['group_id']),code=row['code'],name=row['display_name'],description=row['description'],status=row['status'],actions=actions))
    users=[]
    rows=c.execute(select(m.tenant_user_account,m.person.c.display_name,m.user_account.c.status.label('account_status'))
        .join(m.user_account,m.user_account.c.user_account_id==m.tenant_user_account.c.user_account_id)
        .outerjoin(m.person,m.person.c.person_id==m.user_account.c.person_id)
        .where(m.tenant_user_account.c.tenant_id==tenant,m.tenant_user_account.c.valid_from<=date.today(),
            m.tenant_user_account.c.valid_to.is_(None)|(m.tenant_user_account.c.valid_to>=date.today()))).mappings()
    for row in rows:
        ids=list(c.scalars(select(m.access_group_member.c.group_id).where(m.access_group_member.c.tenant_id==tenant,
            m.access_group_member.c.user_account_id==row['user_account_id'])))
        permissions=[]
        if row['status']=='ACTIVE' and row['account_status']=='ACTIVE':
            permissions=sorted(resolve_tenant_workspace(c,tenant,row['user_account_id'],date.today()).permission_codes)
        users.append(dict(userId=str(row['user_account_id']),name=row['display_name'] or str(row['user_account_id']),
            role=row['membership_role'],status=row['status'],accountStatus=row['account_status'],groupIds=list(map(str,ids)),permissions=permissions))
    return dict(tenantId=str(tenant),userId=str(actor),users=users,groups=groups,tenantModuleCodes=sorted(workspace.tenant_module_codes),
        actions=[dict(code=code,moduleCodes=sorted(modules)) for code,modules in ACTION_MODULES.items() if code!='ACCESS_MANAGE'])


def platform_view(c, actor):
    require_platform(c,actor)
    modules=[dict(code=r.module_code,name=r.display_name) for r in c.execute(select(m.platform_module)
        .where(m.platform_module.c.status=='ACTIVE').order_by(m.platform_module.c.module_code))]
    tenants=[]
    from .tenancy import ModuleEntitlementRecord, resolve_effective_module_codes
    for tenant in c.execute(select(m.tenant).order_by(m.tenant.c.tenant_code)).mappings():
        rows=c.execute(select(m.tenant_module_entitlement,m.platform_module.c.module_code).join(m.platform_module,
            m.platform_module.c.platform_module_id==m.tenant_module_entitlement.c.platform_module_id)
            .where(m.tenant_module_entitlement.c.tenant_id==tenant['tenant_id'])).mappings()
        codes=resolve_effective_module_codes(tuple(ModuleEntitlementRecord(r['tenant_module_entitlement_id'],r['module_code'],
            r['valid_from'],r['valid_to'],r['entitlement_state']) for r in rows),date.today())
        users=c.execute(select(m.tenant_user_account.c.user_account_id,m.tenant_user_account.c.membership_role,m.person.c.display_name)
            .join(m.user_account,m.user_account.c.user_account_id==m.tenant_user_account.c.user_account_id)
            .outerjoin(m.person,m.person.c.person_id==m.user_account.c.person_id)
            .where(m.tenant_user_account.c.tenant_id==tenant['tenant_id'],m.tenant_user_account.c.status=='ACTIVE',
                m.user_account.c.status=='ACTIVE',m.tenant_user_account.c.valid_from<=date.today(),
                m.tenant_user_account.c.valid_to.is_(None)|(m.tenant_user_account.c.valid_to>=date.today()))).all()
        tenants.append(dict(tenantId=str(tenant['tenant_id']),code=tenant['tenant_code'],name=tenant['display_name'],status=tenant['status'],
            contactName=tenant['operational_contact_name'],contactEmail=tenant['operational_contact_email'],profileVersion=tenant['profile_version'],
            moduleCodes=sorted(codes),users=[dict(userId=str(r.user_account_id),name=r.display_name or str(r.user_account_id),role=r.membership_role) for r in users]))
    return dict(tenants=tenants,modules=modules)
