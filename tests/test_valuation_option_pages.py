"""501 eligible strategies remain discoverable without widening read/run scope."""
import asyncio
from uuid import uuid4
from sqlalchemy import select
from httpx import AsyncClient
from tests.api_client import FixtureASGITransport as ASGITransport
from tests.test_access_management import connection
from tests.test_api_reference_authority import BoundEngine
from apps.reference_api.main import create_app
from security_master_schema import access_management as am, models as m
from security_master_schema.demo_data import DEMO_IDS as ids


def get(c,user,path):
    async def run():
        async with AsyncClient(transport=ASGITransport(app=create_app(engine=BoundEngine(c))),base_url='http://test') as client:
            return await client.get(path,headers={'X-Tenant-Id':str(ids['tenant']),'X-User-Account-Id':str(user)})
    return asyncio.run(run())


def population(c):
    token=uuid4().hex[:10];identities=[uuid4() for _ in range(501)]
    original=dict(c.execute(select(m.strategy).where(m.strategy.c.strategy_id==ids['strategy'])).mappings().one())
    c.execute(m.strategy.insert(),[original|dict(strategy_id=identity,strategy_code=f'PAGE_{token}_{n:03}',
        display_name=f'Paging {token} {n:03}') for n,identity in enumerate(identities)])
    return token,identities


def reader(c,mode='ALL',strategies=()):
    user=am.add_user(c,ids['tenant'],ids['demo_user_account'],name='Option reader')
    group=am.save_group(c,ids['tenant'],ids['demo_user_account'],code='OPTIONS_'+uuid4().hex,name='Option read scope',
        actions=['VALUATION_READ','MARKET_DATA_READ'],scope_mode=mode,strategy_ids=list(strategies))
    am.set_user_groups(c,ids['tenant'],ids['demo_user_account'],user,[group])
    return user


def test_pages_search_selected_id_and_legacy_completeness(connection):
    token,identities=population(connection);user=reader(connection)
    result=get(connection,user,f'/v1/valuation/option-choices?kind=strategies&q={token}&limit=1&offset=500')
    assert result.status_code==200,result.text
    page=result.json()
    assert page['total']==501 and page['limit']==1 and page['offset']==500
    assert [row['id'] for row in page['items']]==[str(identities[-1])]
    assert page['items'][0]['canCalculate'] is False
    selected=get(connection,user,f'/v1/valuation/option-choices?kind=strategies&q=no-match&selected_id={identities[-1]}').json()
    assert selected['items']==[] and selected['selected']['id']==str(identities[-1])
    legacy=get(connection,user,'/v1/valuation/options')
    assert len([s for s in legacy.json()['strategies'] if token in s['label']])==501


def test_scope_and_calculation_filter_apply_before_count_and_selected_lookup(connection):
    token,identities=population(connection);user=reader(connection,'SELECTED',[identities[0]])
    result=get(connection,user,f'/v1/valuation/option-choices?kind=strategies&q={token}&selected_id={identities[-1]}')
    assert result.status_code==200,result.text
    assert result.json()['total']==1 and result.json()['selected'] is None
    assert [row['id'] for row in result.json()['items']]==[str(identities[0])]
    blocked=get(connection,user,f'/v1/valuation/option-choices?kind=strategies&q={token}&for_calculation=true')
    assert blocked.json()['total']==0 and blocked.json()['items']==[]
