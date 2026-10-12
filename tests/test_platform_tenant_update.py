"""Platform-only tenant edits, stale writes and reversible access suspension."""
from uuid import uuid4
from tests.test_access_api import client, headers
from security_master_schema.demo_data import DEMO_IDS

ROOT={'X-User-Account-Id':str(DEMO_IDS['platform_admin_user_account'])}
TENANT=str(DEMO_IDS['second_tenant'])

def current(client):
    return next(t for t in client.get('/v1/platform/tenants',headers=ROOT).json()['tenants'] if t['tenantId']==TENANT)

def payload(tenant,**changes):
    return dict(name=tenant['name'],status=tenant['status'],contactName=tenant.get('contactName'),
        contactEmail=tenant.get('contactEmail'),expectedVersion=tenant.get('profileVersion',0))|changes

def test_platform_edits_contact_and_name_with_audit_and_immutable_identity(client):
    before=current(client)
    response=client.put('/v1/platform/tenants/'+TENANT,headers=ROOT,json=payload(before,name=' Updated tenant ',contactName=' Operations ',contactEmail=' ops@example.org '))
    assert response.status_code==200,response.text
    after=current(client)
    assert after['name']=='Updated tenant' and after['contactName']=='Operations' and after['contactEmail']=='ops@example.org'
    assert after['code']==before['code'] and after['tenantId']==before['tenantId']
    assert after['moduleCodes']==before['moduleCodes'] and after['users']==before['users']
    assert after['profileVersion']==before.get('profileVersion',0)+1
    event=next(e for e in client.get('/v1/platform/audit',headers=ROOT).json()['events'] if e['action']=='TENANT_PROFILE_CHANGED' and str(e['tenant_id'])==TENANT)
    assert event['details']['before']['name']==before['name'] and event['details']['after']['contactEmail']=='ops@example.org'
    assert event['actor_id']==ROOT['X-User-Account-Id']

def test_tenant_administrator_cannot_edit_platform_registry(client):
    assert client.put('/v1/platform/tenants/'+TENANT,headers=headers(),json=payload(current(client))).status_code==403

def test_stale_profile_write_cannot_overwrite_a_saved_edit(client):
    before=current(client)
    body=payload(before,name='First edit')
    assert client.put('/v1/platform/tenants/'+TENANT,headers=ROOT,json=body).status_code==200
    conflict=client.put('/v1/platform/tenants/'+TENANT,headers=ROOT,json=body|{'name':'Stale overwrite'})
    assert conflict.status_code==409
    assert current(client)['name']=='First edit'

def test_invalid_fields_and_unknown_tenant_fail_without_changes(client):
    before=current(client)
    for changes in ({'name':'   '},{'contactEmail':'not-an-email'},{'tenantCode':'RENAME'},{'status':'RETIRED'}):
        assert client.put('/v1/platform/tenants/'+TENANT,headers=ROOT,json=payload(before,**changes)).status_code==422
    assert client.put('/v1/platform/tenants/'+str(uuid4()),headers=ROOT,json=payload(before)).status_code==404
    assert current(client)==before

def test_suspension_blocks_existing_tenant_session_and_reactivation_restores_access(client):
    token=client.post('/v1/local-session',headers=ROOT,json={'tenantId':TENANT,'userId':str(DEMO_IDS['demo_user_account'])}).json()['token']
    subject=headers(tenant='second_tenant')|{'X-Local-Access-Token':token}
    assert client.get('/v1/tenant-workspace',headers=subject).status_code==200
    before=current(client)
    assert client.put('/v1/platform/tenants/'+TENANT,headers=ROOT,json=payload(before,status='SUSPENDED')).status_code==422
    assert client.put('/v1/platform/tenants/'+TENANT,headers=ROOT,json=payload(before,status='SUSPENDED',confirmStatusChange=True)).status_code==200
    assert client.get('/v1/tenant-workspace',headers=subject).status_code==403
    assert client.put('/v1/platform/tenants/'+TENANT,headers=ROOT,json=payload(current(client),status='ACTIVE',confirmStatusChange=True)).status_code==200
    assert client.get('/v1/tenant-workspace',headers=subject).status_code==200
