from uuid import uuid4
from tests.test_access_api import client,headers
from tests.test_strategy_scopes_api import scoped_user
from security_master_schema.demo_data import DEMO_IDS as ids


def test_lifecycle_collections_and_commands_are_strategy_scoped(client):
    h,_=scoped_user(client,['LIFECYCLE_READ','LIFECYCLE_CONFIGURE'],[ids['strategy']])
    options=client.get('/v1/lifecycle/options',headers=h)
    assert options.status_code==200,options.text
    assert [s['id'] for s in options.json()['strategies']]==[str(ids['strategy'])]
    assert client.get(f"/v1/lifecycle/options?strategyId={ids['uk_fund_strategy']}",headers=h).status_code==403
    assert client.get(f"/v1/lifecycle/bond-redemptions?strategyId={ids['uk_fund_strategy']}",headers=h).status_code==403
    policy=client.get(f"/v1/lifecycle/options?strategyId={ids['strategy']}",headers=h).json()['policy']
    result=client.post('/v1/lifecycle/policy',headers=h,json=dict(strategyId=str(ids['strategy']),mode='REVIEW',expectedRevision=policy['revision'],reason='Synthetic policy',confirmChange=True))
    assert result.status_code==200,result.text
    assert result.json()['revision']==policy['revision']+1
    # A reader/configurator cannot borrow posting authority from admin role or UI.
    data=dict(strategyId=str(ids['strategy']),instrumentId=str(ids['bond_instrument_node']),expectedFingerprint='a'*64,confirmBooking=True)
    assert client.post('/v1/lifecycle/bond-redemptions/book',headers=h|{'Idempotency-Key':str(uuid4())},json=data).status_code==403


def test_prepare_and_book_routes_require_their_own_action(client):
    h,_=scoped_user(client,['LIFECYCLE_READ','LIFECYCLE_PREPARE'],[ids['strategy']])
    data=dict(strategyId=str(ids['uk_fund_strategy']),instrumentId=str(ids['bond_instrument_node']),expectedFingerprint='a'*64)
    assert client.post('/v1/lifecycle/bond-redemptions/prepare',headers=h,json=data).status_code==403
    data['strategyId']=str(ids['strategy'])
    # A scoped action alone cannot bypass the unconfigured assistance tier.
    # Native future-maturity rejection is exercised with enabled service fixtures.
    result=client.post('/v1/lifecycle/bond-redemptions/prepare',headers=h,json=data)
    assert result.status_code==403,result.text
    assert 'selected Tier2 or higher' in result.json()['detail']
