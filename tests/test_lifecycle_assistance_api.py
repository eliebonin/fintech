"""Platform ceiling and tenant policy endpoints have separate authority."""
from tests.test_access_api import client,headers
from tests.test_strategy_scopes_api import scoped_user
from security_master_schema.demo_data import DEMO_IDS as ids


def test_platform_subscription_and_scoped_tenant_configuration(client):
    root={'X-User-Account-Id':str(ids['platform_admin_user_account'])}
    route=f"/v1/platform/tenants/{ids['tenant']}/lifecycle-subscription"
    current=client.get(route,headers=root)
    assert current.status_code==200,current.text
    rev=current.json()['revision']
    preview=client.post(route+'/preview',headers=root,json=dict(maximumTier=3,expectedRevision=rev))
    assert preview.status_code==200,preview.text
    saved=client.put(route,headers=root,json=dict(maximumTier=3,expectedRevision=rev,expectedImpactHash=preview.json()['inputHash'],reason='Synthetic API tier',confirmChange=True,confirmBlockedWorkflows=True))
    assert saved.status_code==200,saved.text
    h,first_group=scoped_user(client,['LIFECYCLE_READ','LIFECYCLE_CONFIGURE'],[ids['strategy']])
    query=dict(strategyId=str(ids['strategy']),eventType='BOND_MATURITY')
    view=client.get('/v1/lifecycle/assistance',params=query,headers=h)
    assert view.status_code==200,view.text
    result=client.post('/v1/lifecycle/assistance',headers=h,json=dict(**query,selectedTier=2,expectedRevision=view.json()['assistanceRevision'],expectedSubscriptionRevision=saved.json()['revision'],reason='Synthetic assisted strategy'))
    assert result.status_code==200,result.text
    assert result.json()['selectedTier']==2
    assert client.get('/v1/lifecycle/assistance',params=dict(query,strategyId=str(ids['uk_fund_strategy'])),headers=h).status_code==403
    assert client.get(route,headers=h).status_code==403
    options=client.get('/v1/lifecycle/assistance/options',headers=h)
    assert options.status_code==200 and options.json()['total']==1
    # A second configured strategy is deliberately outside this user's scope.
    import os
    from sqlalchemy import create_engine
    from tests.test_lifecycle_assistance import configure
    owner=create_engine(os.environ['DATABASE_URL'])
    with owner.begin() as c:configure(c,1,strategy=ids['uk_fund_strategy'])
    owner.dispose()
    transition=client.post('/v1/lifecycle/assistance/transitions/preview',headers=h,json=dict(proposedMaximumTier=1,expectedSubscriptionRevision=saved.json()['revision']))
    assert transition.status_code==403

    # Two SELECTED groups may jointly cover the current population without
    # requiring an ALL-scope grant or changing commercial authority.
    from uuid import uuid4
    result=client.post('/v1/access/groups',headers=headers(),json=dict(code='LIFE_'+uuid4().hex,name='Second scoped lifecycle group',actions=['LIFECYCLE_READ','LIFECYCLE_CONFIGURE'],scopeMode='SELECTED',strategyIds=[str(ids['uk_fund_strategy'])]))
    assert result.status_code==201,result.text
    user=h['X-User-Account-Id']
    assert client.put('/v1/access/users/'+user+'/groups',headers=headers(),json=dict(groupIds=[first_group,result.json()['groupId']])).status_code==200
    transition=client.post('/v1/lifecycle/assistance/transitions/preview',headers=h,json=dict(proposedMaximumTier=1,expectedSubscriptionRevision=saved.json()['revision']))
    assert transition.status_code==200,transition.text
    assert transition.json()['changedCount']==1
    assert len(transition.json()['items'])==2
