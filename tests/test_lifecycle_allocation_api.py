"""Allocation settings and picker visibility do not borrow configuration rights."""
from uuid import uuid4
from tests.test_access_api import client,headers
from tests.test_strategy_scopes_api import scoped_user
from security_master_schema.demo_data import DEMO_IDS as ids


def test_allocation_settings_require_configuration_authority(client):
    h,_=scoped_user(client,['LIFECYCLE_READ'],[ids['strategy']])
    assert client.get('/v1/trade-configuration/lifecycle-allocations',headers=h).status_code==403
    admin=headers()
    current=client.get('/v1/trade-configuration/lifecycle-allocations',headers=admin)
    assert current.status_code==200,current.text
    rev=current.json()['data']['revision']
    body=dict(fields=[],expectedRevision=rev,reason='Synthetic empty allocation configuration',confirmImpact=True)
    assert client.post('/v1/trade-configuration/lifecycle-allocations',headers=h,json=body).status_code==403
    result=client.post('/v1/trade-configuration/lifecycle-allocations',headers=admin,json=body)
    assert result.status_code==200,result.text
    assert result.json()['data']['revision']==rev+1


def test_lifecycle_picker_checks_strategy_and_catalogue_scope(client):
    h,_=scoped_user(client,['LIFECYCLE_READ'],[ids['strategy']])
    query=f"/v1/lifecycle/annotation-options?strategyId={ids['uk_fund_strategy']}&catalogueId={uuid4()}"
    assert client.get(query,headers=h).status_code==403
    query=f"/v1/lifecycle/annotation-options?strategyId={ids['strategy']}&catalogueId={uuid4()}"
    assert client.get(query,headers=h).status_code==404


def test_ops_reads_bound_published_values_without_configuration_rights(client):
    admin=headers();code='ALLOC_'+uuid4().hex
    response=client.post('/v1/trade-configuration/catalogues',headers=admin,json=dict(code=code,label='Synthetic lifecycle values',reason='Synthetic picker source'))
    assert response.status_code==201,response.text
    catalogue=response.json()['data']['catalogueId']
    published=client.post(f'/v1/trade-configuration/catalogues/{catalogue}/publish',headers=admin,json=dict(reason='Synthetic published source'))
    assert published.status_code==200,published.text
    record=client.post(f'/v1/trade-configuration/catalogues/{catalogue}/records',headers=admin,json=dict(code='CORE',label='Core allocation',reason='Synthetic value'))
    assert record.status_code==201,record.text
    definition=client.post('/v1/trade-configuration/properties',headers=admin,json=dict(code=code,label='Synthetic allocation',valueType='REFERENCE',catalogueId=catalogue))
    assert definition.status_code==201,definition.text
    h,_=scoped_user(client,['LIFECYCLE_READ'],[ids['strategy']])
    assert client.get(f'/v1/trade-configuration/catalogues/{catalogue}/records',headers=h).status_code==403
    result=client.get(f"/v1/lifecycle/annotation-options?strategyId={ids['strategy']}&catalogueId={catalogue}&q=Core",headers=h)
    assert result.status_code==200,result.text
    assert result.json()['items'][0]['label']=='Core allocation'
