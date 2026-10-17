"""Tenant administration is not operational authority; bootstrap is one-time."""
from datetime import date
from uuid import uuid4
from sqlalchemy import select
from tests.test_access_management import connection
from tests.test_access_api import client, headers
from security_master_schema import access_management as am, models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from security_master_schema.tenant_workspace import resolve_tenant_workspace


def test_new_admin_can_manage_access_but_cannot_operate_until_group_assigned(client):
    user=client.post('/v1/access/users',headers=headers(),json={'name':'Admin '+uuid4().hex,'role':'TENANT_ADMIN'}).json()['userId']
    h=headers()|{'X-User-Account-Id':user}
    assert client.get('/v1/access',headers=h).status_code==200
    assert client.get('/v1/trades',headers=h).status_code==403
    assert client.post('/v1/trades',headers=h,json={}).status_code==403
    assert client.post('/v1/structured-product-proposals',headers=h,json={}).status_code==403
    group=client.post('/v1/access/groups',headers=h,json={'code':'ADMIN_READ_'+uuid4().hex,
        'name':'Explicit readers','scopeMode':'ALL','actions':['TRADE_READ']}).json()['groupId']
    assert client.put('/v1/access/users/'+user+'/groups',headers=h,json={'groupIds':[group]}).status_code==200
    assert client.get('/v1/trades',headers=h).status_code==200
    assert client.post('/v1/trades',headers=h,json={}).status_code==403
    assert client.put('/v1/access/users/'+user+'/groups',headers=h,json={'groupIds':[]}).status_code==200
    assert client.get('/v1/trades',headers=h).status_code==403
    assert client.get('/v1/access',headers=h).status_code==200
    # HTTP fixtures commit; leave no extra active admin for later last-admin tests.
    assert client.put('/v1/access/users/'+user,headers=headers(),json={'status':'SUSPENDED'}).status_code==200


def test_bootstrap_preserves_existing_admin_access_but_never_regrants_removal(connection):
    from security_master_schema.access_bootstrap import bootstrap_admin_operations
    tenant,actor=ids['tenant'],ids['demo_user_account']
    user=am.add_user(connection,tenant,actor,name='Legacy admin',role='TENANT_ADMIN')
    assert bootstrap_admin_operations(connection,tenant,user,actor) is True
    workspace=resolve_tenant_workspace(connection,tenant,user,date.today())
    assert {'ACCESS_MANAGE','TRADE_WRITE','REFERENCE_APPROVE','VALUATION_REVIEW'}<=workspace.permission_codes
    am.set_user_groups(connection,tenant,actor,user,[])
    assert bootstrap_admin_operations(connection,tenant,user,actor) is False
    assert resolve_tenant_workspace(connection,tenant,user,date.today()).permission_codes=={'ACCESS_MANAGE'}
    assert connection.scalar(select(m.access_audit_event.c.event_id).where(
        m.access_audit_event.c.tenant_id==tenant,m.access_audit_event.c.subject_id==user,
        m.access_audit_event.c.action=='ADMIN_OPERATIONAL_ACCESS_BOOTSTRAPPED'))


def test_bootstrap_does_not_grant_members_or_foreign_users(connection):
    from security_master_schema.access_bootstrap import bootstrap_admin_operations
    tenant,actor=ids['tenant'],ids['demo_user_account']
    user=am.add_user(connection,tenant,actor,name='Member',role='MEMBER')
    assert bootstrap_admin_operations(connection,tenant,user,actor) is False
    assert bootstrap_admin_operations(connection,ids['second_tenant'],user,actor) is False


def test_later_module_activation_does_not_expand_bootstrap_grants(connection):
    from security_master_schema.access_bootstrap import bootstrap_admin_operations
    tenant,actor=ids['tenant'],ids['demo_user_account']
    am.set_module(connection,tenant,ids['platform_admin_user_account'],'VALUATION',False)
    user=am.add_user(connection,tenant,actor,name='Limited compatibility admin',role='TENANT_ADMIN')
    assert bootstrap_admin_operations(connection,tenant,user,actor)
    am.set_module(connection,tenant,ids['platform_admin_user_account'],'VALUATION',True)
    assert 'VALUATION_REVIEW' not in resolve_tenant_workspace(connection,tenant,user,date.today()).permission_codes
    assert not bootstrap_admin_operations(connection,tenant,user,actor)


def test_migration_assigns_explicit_existing_admin_operations(connection,monkeypatch):
    import importlib.util
    from pathlib import Path
    tenant,actor=ids['tenant'],ids['demo_user_account']
    user=am.add_user(connection,tenant,actor,name='Migration target',role='TENANT_ADMIN')
    assert resolve_tenant_workspace(connection,tenant,user,date.today()).permission_codes=={'ACCESS_MANAGE'}
    path=Path(__file__).resolve().parents[1]/'alembic/versions/20261013_84_admin_operational_groups.py'
    spec=importlib.util.spec_from_file_location('admin_transition_migration',path)
    migration=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    monkeypatch.setattr(migration.op,'get_bind',lambda:connection)
    migration.upgrade()
    migration.upgrade()
    assert 'TRADE_WRITE' in resolve_tenant_workspace(connection,tenant,user,date.today()).permission_codes
    assert len(connection.execute(select(m.access_group_member).where(
        m.access_group_member.c.tenant_id==tenant,m.access_group_member.c.user_account_id==user)).all())==1
    # Role downgrade removes administration only, not separately assigned operations.
    am.set_user_status(connection,tenant,actor,user,'ACTIVE','MEMBER')
    permissions=resolve_tenant_workspace(connection,tenant,user,date.today()).permission_codes
    assert 'TRADE_WRITE' in permissions
    assert 'ACCESS_MANAGE' not in permissions
