"""Read-only self/admin explanations enforce tenant isolation at the HTTP boundary."""
from uuid import uuid4
import pytest
from tests.test_access_api import client, headers


def member(client):
    result=client.post('/v1/access/users',headers=headers(),json={'name':'Explain '+uuid4().hex,'role':'MEMBER'})
    assert result.status_code==201
    return result.json()['userId']


def test_zero_grant_member_can_inspect_self_but_not_others(client):
    user=member(client)
    h=headers()|{'X-User-Account-Id':user}
    result=client.get('/v1/tenant-workspace/effective-access',headers=h)
    assert result.status_code==200,result.text
    assert result.headers['cache-control']=='no-store'
    assert result.json()['userId']==user
    assert not any(row['allowed'] for row in result.json()['actions'])
    assert client.get('/v1/tenant-workspace/effective-access?userId='+headers()['X-User-Account-Id'],headers=h).status_code==403
    assert client.get('/v1/tenant-workspace/unknown',headers=h).status_code==403
    assert client.post('/v1/tenant-workspace/effective-access',headers=h,json={}).status_code==403


def test_admin_can_explain_suspended_member_without_reviving_access(client):
    user=member(client)
    group=client.post('/v1/access/groups',headers=headers(),json={'code':'EXPLAIN_'+uuid4().hex,
        'name':'Trade readers','scopeMode':'ALL','actions':['TRADE_READ']}).json()['groupId']
    assert client.put('/v1/access/users/'+user+'/groups',headers=headers(),json={'groupIds':[group]}).status_code==200
    path='/v1/tenant-workspace/effective-access?userId='+user
    rows=client.get(path,headers=headers()).json()['actions']
    assert next(row for row in rows if row['code']=='TRADE_READ')['grantSources']==['Trade readers']
    assert client.put('/v1/access/users/'+user,headers=headers(),json={'status':'SUSPENDED'}).status_code==200
    result=client.get(path,headers=headers())
    assert result.status_code==200,result.text
    assert not any(row['allowed'] for row in result.json()['actions'])
    assert client.get(path,headers=headers()|{'X-User-Account-Id':user}).status_code==403


def test_foreign_or_unknown_targets_disclose_no_user_data(client):
    for user in [headers('platform_admin_user_account')['X-User-Account-Id'],str(uuid4())]:
        result=client.get('/v1/tenant-workspace/effective-access?userId='+user,headers=headers())
        assert result.status_code==403
        assert 'modules' not in result.json()


@pytest.mark.parametrize('method,path',[
    ('GET','/v1/trades'),('POST','/v1/trades'),
    ('POST','/v1/trades/'+str(uuid4())+'/cancel-booking'),
    ('GET','/v1/strategies'),('POST','/v1/strategies'),
    ('GET','/v1/instruments'),('POST','/v1/structured-product-proposals'),
    ('POST','/v1/structured-product-proposals/'+str(uuid4())+'/decision'),
    ('GET','/v1/market-data/policies'),('POST','/v1/market-data/policies'),
    ('GET','/v1/valuation/runs'),('POST','/v1/valuation/runs'),
    ('POST','/v1/valuation/runs/'+str(uuid4())+'/publish'),
    ('GET','/v1/access'),('POST','/v1/access/groups'),('GET','/v1/platform/tenants'),
])
def test_empty_grant_member_denied_at_each_module_boundary(client,method,path):
    user=member(client)
    result=client.request(method,path,headers=headers()|{'X-User-Account-Id':user})
    assert result.status_code==403,result.text
