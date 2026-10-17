from datetime import datetime,timedelta,timezone
from uuid import uuid4
from sqlalchemy import select
from tests.test_access_api import client,headers
from tests.test_strategy_scopes_api import scoped_user
from apps.reference_api.db import get_engine
from security_master_schema.demo_data import DEMO_IDS as ids
from valuation import tables as t

def test_policy_requires_admin_confirmation_and_revision_check(client):
    path='/v1/access/valuation-publication-policy'
    current=client.get(path,headers=headers());assert current.status_code==200,current.text
    h,_=scoped_user(client,['VALUATION_READ','MARKET_DATA_READ'],[ids['strategy']])
    assert client.get(path,headers=h).status_code==403
    command={'enabled':False,'validUntil':None,'expectedRevision':current.json()['revision'],'reason':'Synthetic policy review','confirmChange':True}
    assert client.put(path,headers=headers(),json=command|{'confirmChange':False}).status_code==422
    saved=client.put(path,headers=headers(),json=command);assert saved.status_code==200,saved.text
    assert saved.json()['revision']==command['expectedRevision']+1 and not saved.json()['active']
    assert client.put(path,headers=headers(),json=command).status_code==409
    expired=command|{'enabled':True,'expectedRevision':saved.json()['revision'],'validUntil':(datetime.now(timezone.utc)-timedelta(days=1)).isoformat()}
    assert client.put(path,headers=headers(),json=expired).status_code==422

def test_regular_review_cannot_invoke_exception_without_explicit_grant(client):
    h,_=scoped_user(client,['VALUATION_READ','VALUATION_REVIEW','MARKET_DATA_READ'],[ids['strategy']])
    response=client.post(f'/v1/valuation/batches/{uuid4()}/self-publish',headers=h,json={'comment':'Holiday cover','confirmSelfPublication':True})
    assert response.status_code==403

def test_exception_endpoint_requires_explicit_acknowledgement(client):
    h,_=scoped_user(client,['VALUATION_READ','VALUATION_REVIEW','VALUATION_SELF_PUBLISH','MARKET_DATA_READ'],[ids['strategy']])
    path=f'/v1/valuation/batches/{uuid4()}/self-publish'
    assert client.post(path,headers=h,json={'comment':'Holiday cover'}).status_code==422
    assert client.post(path,headers=h,json={'comment':'Holiday cover','confirmSelfPublication':False}).status_code==422
    assert client.post(path,headers=h,json={'comment':'   ','confirmSelfPublication':True}).status_code==422
    # Arbitrary override flags cannot be smuggled through the ordinary endpoint.
    assert client.post(path.replace('/self-publish','/publish'),headers=h,json={'comment':'Override','confirmSelfPublication':True}).status_code==422

def test_policy_revisions_cannot_be_rewritten(client):
    from sqlalchemy.exc import DBAPIError
    import pytest
    path='/v1/access/valuation-publication-policy'
    current=client.get(path,headers=headers()).json()
    saved=client.put(path,headers=headers(),json={'enabled':False,'expectedRevision':current['revision'],'reason':'Synthetic append-only review','confirmChange':True});assert saved.status_code==200
    with pytest.raises(DBAPIError,match='immutable'):
        with get_engine().begin() as c:
            c.execute(t.publication_policy.update().where(t.publication_policy.c.tenant_id==ids['tenant']).values(enabled=True))
