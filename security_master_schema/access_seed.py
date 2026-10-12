"""Idempotent access-only local seed; never reruns trading/market-data fixtures."""
from datetime import date
from uuid import UUID, uuid5
from sqlalchemy import select, update
from . import models as m
from .demo_data import DEMO_IDS
from .access_control import ACTION_MODULES

NAMESPACE=UUID('2a927531-4153-4c9c-bb90-3d27fdf79fde')


def seed_id(key):
    return uuid5(NAMESPACE,key)


def once(c, table, pk, values):
    if c.scalar(select(table.c[pk]).where(table.c[pk]==values[pk])) is None:
        c.execute(table.insert().values(**values))


def seed_access(c):
    third=seed_id('third-tenant')
    once(c,m.tenant,'tenant_id',dict(tenant_id=third,owning_organisation_id=DEMO_IDS['fortem_organisation'],
        tenant_code='FORTEM_THIRD_TENANT',display_name='Fortem Third Tenant',status='ACTIVE'))
    specs=[(DEMO_IDS['tenant'],'Fortem Demo',None),
           (DEMO_IDS['second_tenant'],'Fortem Second',{'SECURITY_MASTER','TRADING','MARKET_DATA'}),
           (third,'Fortem Third',{'SECURITY_MASTER','TRADING'})]
    personas={'Traders':{'REFERENCE_READ','STRATEGY_READ','TRADE_READ','TRADE_WRITE'},
        'Operations':{'REFERENCE_READ','REFERENCE_PROPOSE','REFERENCE_APPROVE','STRATEGY_READ','TRADE_READ','TRADE_CORRECT',
                      'MARKET_DATA_READ','MARKET_DATA_MANAGE','VALUATION_READ','VALUATION_RUN','VALUATION_REVIEW','CALENDAR_READ'},
        'Read Only':{'REFERENCE_READ','STRATEGY_READ','TRADE_READ','MARKET_DATA_READ','VALUATION_READ','CALENDAR_READ'}}
    for tenant,label,modules in specs:
        if modules is not None:
            for code in sorted(modules):
                module=c.scalar(select(m.platform_module.c.platform_module_id).where(m.platform_module.c.module_code==code))
                existing=c.scalar(select(m.tenant_module_entitlement.c.tenant_module_entitlement_id).where(
                    m.tenant_module_entitlement.c.tenant_id==tenant,m.tenant_module_entitlement.c.platform_module_id==module))
                if existing is None:
                    c.execute(m.tenant_module_entitlement.insert().values(tenant_id=tenant,platform_module_id=module,
                        entitlement_state='GRANTED',entitlement_source='MIGRATION',valid_from=date(2026,1,1)))
        enabled=set(c.scalars(select(m.platform_module.c.module_code).join(m.tenant_module_entitlement,
            m.tenant_module_entitlement.c.platform_module_id==m.platform_module.c.platform_module_id)
            .where(m.tenant_module_entitlement.c.tenant_id==tenant,m.tenant_module_entitlement.c.entitlement_state=='GRANTED',
                m.tenant_module_entitlement.c.valid_from<=date.today(),m.tenant_module_entitlement.c.valid_to.is_(None)
                |(m.tenant_module_entitlement.c.valid_to>=date.today()))))
        for persona in ('Admin','Traders','Operations','Read Only'):
            key=f'{tenant}:{persona}'
            person=seed_id(key+':person')
            user=DEMO_IDS['demo_user_account'] if tenant==DEMO_IDS['tenant'] and persona=='Admin' else seed_id(key+':user')
            once(c,m.person,'person_id',dict(person_id=person,display_name=f'{label} — {persona}'))
            once(c,m.user_account,'user_account_id',dict(user_account_id=user,person_id=person,account_type='HUMAN',status='ACTIVE'))
            # Give the existing operating demo admin a readable label only if unnamed.
            c.execute(update(m.user_account).where(m.user_account.c.user_account_id==user,m.user_account.c.person_id.is_(None)).values(person_id=person))
            membership=c.scalar(select(m.tenant_user_account.c.tenant_user_account_id).where(
                m.tenant_user_account.c.tenant_id==tenant,m.tenant_user_account.c.user_account_id==user))
            if membership is None:
                c.execute(m.tenant_user_account.insert().values(tenant_id=tenant,user_account_id=user,
                    membership_role='TENANT_ADMIN' if persona=='Admin' else 'MEMBER',status='ACTIVE',valid_from=date(2026,1,1)))
            if persona=='Admin':
                continue
            group=seed_id(key+':group')
            once(c,m.access_group,'group_id',dict(group_id=group,tenant_id=tenant,code=persona.upper().replace(' ','_'),display_name=persona))
            # Seed only once: subsequent runs preserve administrator edits/revocations.
            if c.scalar(select(m.access_group_member.c.user_account_id).where(m.access_group_member.c.tenant_id==tenant,
                    m.access_group_member.c.group_id==group,m.access_group_member.c.user_account_id==user)) is None:
                # A seed marker in the audit log prevents re-grant after deliberate removal.
                marker=c.scalar(select(m.access_audit_event.c.event_id).where(m.access_audit_event.c.action=='ACCESS_SEEDED',
                    m.access_audit_event.c.tenant_id==tenant,m.access_audit_event.c.subject_id==user))
                if marker is None:
                    c.execute(m.access_group_member.insert().values(tenant_id=tenant,group_id=group,user_account_id=user))
                    for action in sorted(personas[persona]):
                        if ACTION_MODULES[action]&enabled:
                            c.execute(m.access_group_grant.insert().values(tenant_id=tenant,group_id=group,action_code=action))
                    c.execute(m.access_audit_event.insert().values(actor_id=DEMO_IDS['platform_admin_user_account'],subject_id=user,
                        tenant_id=tenant,action='ACCESS_SEEDED',details={'groupId':str(group)}))
    person=seed_id('platform-person')
    once(c,m.person,'person_id',dict(person_id=person,display_name='Platform Administrator'))
    c.execute(update(m.user_account).where(m.user_account.c.user_account_id==DEMO_IDS['platform_admin_user_account'],
        m.user_account.c.person_id.is_(None)).values(person_id=person))
