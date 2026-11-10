"""HTTP identities and scoped option access remain distinct from configuration."""
from tests.test_access_api import client,headers
from tests.test_strategy_scopes_api import scoped_user
from security_master_schema.demo_data import DEMO_IDS as ids


def test_reference_registry_is_configurator_only(client):
    assert client.get('/v1/tenant-reference/sources',headers=headers()).status_code==200
    h,_=scoped_user(client,['TRADE_READ'],[ids['strategy']])
    assert client.get('/v1/tenant-reference/sources',headers=h).status_code==403


def test_scoped_trader_lookup_does_not_require_configuration_permissions(client):
    h,_=scoped_user(client,['TRADE_WRITE'],[ids['strategy']])
    route='/v1/tenant-reference/options'
    r=client.get(route,headers=h,params={'sourceKey':'standard:TRADER','strategyId':str(ids['strategy']),'consumer':'booking'})
    assert r.status_code==200,r.text
    assert r.json()['limit']==25
    assert client.get(route,headers=h,params={'sourceKey':'standard:TRADER'}).status_code==403
    assert client.get(route,headers=h,params={'sourceKey':'standard:TRADER','strategyId':str(ids['uk_fund_strategy']),'consumer':'booking'}).status_code==403
