from uuid import uuid4
import pytest
from tests.test_access_api import headers
from tests.test_governed_trade_configuration import engine,connection
from tests.api_client import FixtureTestClient,ConnectionEngine
from apps.reference_api.main import create_app

@pytest.fixture
def client(connection):
    with FixtureTestClient(create_app(engine=ConnectionEngine(connection))) as result:yield result
from tests.test_strategy_scopes_api import scoped_user
from security_master_schema.demo_data import DEMO_IDS as ids


def test_profile_publish_does_not_adopt_until_reviewed_assignment(client):
    base='/v1/trade-profiles'
    data={'code':'API_'+uuid4().hex,'label':'API dealing','reason':'Synthetic test','expectedVersion':0,'fields':[{'standardFieldKey':'COUNTERPARTY','requirement':'OPTIONAL'}]}
    r=client.post(base,headers=headers(),json=data)
    assert r.status_code==201,r.text
    first=r.json(); identity=first['profileId'];version=first['versionId']
    assert client.get(base,headers=headers(),params={'q':data['code']}).json()['total']==1
    data.pop('code');data['expectedVersion']=1
    second=client.post(f'{base}/{identity}/versions',headers=headers(),json=data)
    assert second.status_code==201,second.text
    assert client.get(f'{base}/{identity}/versions',headers=headers()).json()['total']==2
    target=f'{base}/strategies/{ids["strategy"]}'
    preview=client.post(target+'/preview',headers=headers(),json={'profileVersionId':str(version)} )
    assert preview.status_code==200,preview.text
    proof=preview.json()
    r=client.post(target,headers=headers(),json={'profileVersionId':str(version),'expectedRevision':proof['assignmentRevision'],'inputHash':proof['inputHash'],'reason':'Reviewed adoption'})
    assert r.status_code==200,r.text
    assert client.get(target,headers=headers()).json()['profileVersionId']==version
    r=client.post(base+'/default',headers=headers(),json={'profileVersionId':str(version),'expectedRevision':client.get(base+'/default',headers=headers()).json()['revision'],'reason':'Default for new strategies'})
    assert r.status_code==200,r.text
    assert client.get(base+'/default',headers=headers()).json()['profileVersionId']==version


def test_strategy_context_is_readable_without_configure_but_adoption_is_not(client):
    h,_=scoped_user(client,['STRATEGY_READ'],[ids['strategy']])
    route=f'/v1/trade-profiles/strategies/{ids["strategy"]}'
    # A reader can inspect the actual pinned assignment, never borrow configurator authority.
    r=client.get(route,headers=h)
    assert r.status_code==200,r.text
    assert client.get('/v1/trade-profiles',headers=h).status_code==403
    assert client.get(f'/v1/trade-profiles/strategies/{ids["uk_fund_strategy"]}',headers=h).status_code==403
    assert client.post(route+'/preview',headers=h,json={'profileVersionId':str(uuid4())}).status_code==403


def test_profile_usage_catalogue_usage_and_history_filter_strategy_scope(client,connection):
    from uuid import UUID
    from tests.test_governed_trade_configuration import catalogue,entry,field,TENANT,ACTOR
    from tests.profile_fixtures import assign
    from trading.profiles.configuration import assign_profile,current_assignment
    cat=catalogue(connection);entry(connection,cat);prop=field(connection,cat)
    version,_=assign(connection,TENANT,ACTOR,ids['strategy'],[dict(propertyCode=prop['code'],propertyVersion=1)])
    before=current_assignment(connection,TENANT,ids['uk_fund_strategy'])
    assign_profile(connection,TENANT,ACTOR,ids['uk_fund_strategy'],version['versionId'],before['revision'],'Confidential other-strategy adoption')
    h,_=scoped_user(client,['TRADE_CONFIGURE','STRATEGY_READ'],[ids['strategy']])
    result=client.get(f"/v1/trade-profiles/{version['profileId']}/usage",headers=h)
    assert result.status_code==200,result.text
    assert [row['strategyId'] for row in result.json()['items']]==[str(ids['strategy'])]
    used=client.get(f'/v1/tenant-reference/sources/catalogue:{cat}/usage',headers=h)
    assert used.status_code==200,used.text
    scoped=[row for row in used.json()['items'] if row['kind']=='STRATEGY']
    assert [row['identity'] for row in scoped]==[str(ids['strategy'])]
    audit=client.get('/v1/trade-configuration/audit',headers=h)
    assert audit.status_code==200,audit.text
    assert 'Confidential other-strategy adoption' not in audit.text


def test_strategy_creation_materializes_the_explicit_current_default(client):
    base='/v1/trade-profiles'
    profile=client.post(base,headers=headers(),json={'code':'CREATE_'+uuid4().hex,'label':'New strategy default','reason':'Explicit test default','expectedVersion':0,'fields':[]})
    assert profile.status_code==201,profile.text
    default=client.get(base+'/default',headers=headers()).json()
    updated=client.post(base+'/default',headers=headers(),json={'profileVersionId':profile.json()['versionId'],'expectedRevision':default['revision'],'reason':'Use for newly created strategies'})
    assert updated.status_code==200,updated.text
    created=client.post('/v1/strategies',headers=headers(),json={'strategyCode':'PROFILE_'+uuid4().hex,'displayName':'Explicit default strategy','strategyType':'FUND','baseCurrencyCode':'GBP'})
    assert created.status_code==201,created.text
    selected=client.get(base+'/strategies/'+created.json()['data']['strategyId'],headers=headers())
    assert selected.status_code==200,selected.text
    assert selected.json()['profileVersionId']==profile.json()['versionId']
