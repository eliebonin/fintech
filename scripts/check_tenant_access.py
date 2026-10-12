"""Read-only business-data acceptance through the real local Next BFF.

Creates/revokes local sessions only. Does not book trades or edit access grants.
Run after migration 82 and seed_tenant_access.py; app on localhost:3000.
"""
import httpx

BASE='http://localhost:3000'


def expect(response, status=200):
    assert response.status_code==status,(response.request.url,response.status_code,response.text[:500])
    return response.json()


def main():
    with httpx.Client(base_url=BASE,headers={'Origin':BASE},timeout=60) as client:
        registry=expect(client.get('/api/session/context'))
        assert len(registry['tenants'])==3
        expect(client.post('/api/session/context',json={}))
        expect(client.get('/api/platform/tenants'))
        token=client.cookies.get('local_access_session')
        expect(client.post('/api/session/context',headers={'Origin':'https://untrusted.invalid'},json={}),403)
        expect(client.post('/api/session/context',json={'tenantId':registry['tenants'][0]['tenantId'],
            'userId':registry['tenants'][2]['users'][0]['userId']}),403)
        assert client.cookies.get('local_access_session')==token
        first_trade=None
        for tenant in registry['tenants']:
            seed_users=[u for u in tenant['users'] if ' — ' in u['name'] or u['role']=='TENANT_ADMIN']
            assert len(seed_users)>=4
            for user in seed_users:
                selected=expect(client.post('/api/session/context',json={'tenantId':tenant['tenantId'],'userId':user['userId']}))['context']
                assert selected['userId']==user['userId'] and selected['tenantId']==tenant['tenantId']
                assert selected['platformRole'] is None
                expect(client.get('/api/platform/tenants'),403)
                access=client.get('/api/access')
                expect(access,200 if user['role']=='TENANT_ADMIN' else 403)
                workspace=expect(client.get('/api/session/active-tenant'))
                assert workspace['permissionCodes']==selected['permissionCodes']
                api_headers={'X-Tenant-Id':tenant['tenantId'],'X-User-Account-Id':user['userId'],
                    'X-Local-Access-Token':client.cookies.get('local_access_session')}
                if 'TRADE_READ' in selected['permissionCodes']:
                    trades=expect(httpx.get('http://localhost:8000/v1/trades',headers=api_headers,timeout=30))
                    if tenant['code']=='FORTEM_DEMO_TENANT' and trades.get('data'):
                        first_trade=trades['data'][0]['tradeId']
                    elif first_trade and tenant['code']!='FORTEM_DEMO_TENANT':
                        expect(httpx.get('http://localhost:8000/v1/trades/'+first_trade,headers=api_headers,timeout=30),404)
                if 'TRADE_WRITE' not in selected['permissionCodes']:
                    # The API rejects this before business payload validation.
                    expect(client.post('/api/trades',headers={'Idempotency-Key':'access-denial-check',
                        'X-Expected-Tenant-Id':tenant['tenantId']},json={}),403)
                if user['role']!='TENANT_ADMIN':
                    expect(client.post('/api/access/groups',headers={'X-Expected-Tenant-Id':tenant['tenantId'],
                        'X-Expected-User-Id':user['userId']},json={'code':'FORBIDDEN','name':'Forbidden','actions':[]}),403)
                page=client.get('/tenant-profile')
                assert page.status_code==200 and user['name'] in page.text
                print(tenant['name'],user['name'],': context, permissions and server page PASS')
        # Forged cross-tab identity is rejected before a user-management write.
        assert first_trade is not None,'No trade was available to exercise cross-tenant object isolation'
        expect(client.post('/api/access/users',headers={'X-Expected-Tenant-Id':'wrong','X-Expected-User-Id':'wrong'},json={}),409)
        expect(client.delete('/api/session/context'))
        expect(client.post('/api/session/context',json={}))
        expect(client.get('/api/platform/tenants'))
        expect(client.delete('/api/session/context'))
    print('Tenant access HTTP acceptance complete; business data untouched.')


if __name__=='__main__':main()
