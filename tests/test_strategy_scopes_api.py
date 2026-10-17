"""HTTP scope enforcement, output filtering and no-preview side effects."""
import os
from uuid import uuid4
from sqlalchemy import create_engine,select,func
from tests.test_access_api import client,headers
from security_master_schema.demo_data import DEMO_IDS as ids
from security_master_schema import models as m


def scoped_user(client,actions,strategies):
    user=client.post('/v1/access/users',headers=headers(),json={'name':'Scope test '+uuid4().hex}).json()['userId']
    result=client.post('/v1/access/groups',headers=headers(),json={'code':'SCOPE_'+uuid4().hex,'name':'Scoped desk',
        'actions':actions,'scopeMode':'SELECTED','strategyIds':list(map(str,strategies))})
    assert result.status_code==201,result.text
    group=result.json()['groupId']
    assert client.put('/v1/access/users/'+user+'/groups',headers=headers(),json={'groupIds':[group]}).status_code==200
    return headers()|{'X-User-Account-Id':user},group


def test_strategy_lists_and_guessed_ids_are_scoped(client):
    from tests.test_cash_booking_integrity import payload
    for strategy in [ids['strategy'],ids['uk_fund_strategy']]:
        booking=payload().model_copy(update={'strategy_id':strategy})
        result=client.post('/v1/trades',headers=headers()|{'Idempotency-Key':str(uuid4())},json=booking.model_dump(mode='json',by_alias=True))
        assert result.status_code==201,result.text
    h,group=scoped_user(client,['STRATEGY_READ','TRADE_READ','TRADE_WRITE'],[ids['uk_fund_strategy']])
    result=client.get('/v1/strategies',headers=h)
    assert result.status_code==200,result.text
    assert [row['strategyId'] for row in result.json()['data']]==[str(ids['uk_fund_strategy'])]
    assert client.get('/v1/strategies/'+str(ids['strategy']),headers=h).status_code==403
    assert client.post('/v1/trades',headers=h,json={'strategyId':str(ids['strategy'])}).status_code==403
    all_trades=client.get('/v1/trades?fromDate=2026-01-01&toDate=2026-10-13&limit=100',headers=headers()).json()['data']
    denied=next(row for row in all_trades if row['strategyId']!=str(ids['uk_fund_strategy']))
    assert client.get('/v1/trades/'+denied['tradeId'],headers=h).status_code==403
    result=client.get('/v1/trades?limit=1&fromDate=2026-01-01&toDate=2026-10-13',headers=h)
    assert result.status_code==200,result.text
    assert all(row['strategyId']==str(ids['uk_fund_strategy']) for row in result.json()['data'])
    expected=len([row for row in all_trades if row['strategyId']==str(ids['uk_fund_strategy'])])
    assert result.json()['meta']['total']==expected


def test_preview_does_not_save_and_stale_group_save_is_rejected(client):
    h,group=scoped_user(client,['TRADE_READ'],[ids['strategy']])
    view=client.get('/v1/access',headers=headers()).json()
    original=next(g for g in view['groups'] if g['groupId']==group)
    proposal={'groupId':group,'code':original['code'],'name':original['name'],'actions':['TRADE_READ'],
        'scopeMode':'SELECTED','strategyIds':[],'expectedVersion':original['versionNo']}
    result=client.post('/v1/access/groups/preview',headers=headers(),json=proposal)
    assert result.status_code==200,result.text
    assert any(row['userId']==h['X-User-Account-Id'] and row['removed']==['TRADE_READ'] for row in result.json()['changes'])
    assert next(g for g in client.get('/v1/access',headers=headers()).json()['groups'] if g['groupId']==group)==original
    proposal.pop('groupId')
    assert client.put('/v1/access/groups/'+group,headers=headers(),json=proposal).status_code==200
    assert client.put('/v1/access/groups/'+group,headers=headers(),json=proposal).status_code==409
    assert client.get('/v1/trades',headers=h).json()['meta']['total']==0


def test_restricted_valuation_attempts_and_counts_do_not_leak(client):
    from valuation import tables as t
    h,_=scoped_user(client,['VALUATION_READ','VALUATION_RUN','MARKET_DATA_READ'],[ids['uk_fund_strategy']])
    attempt=uuid4()
    engine=create_engine(os.environ['DATABASE_URL'])
    with engine.begin() as c:
        c.execute(t.attempt.insert().values(attempt_id=attempt,tenant_id=ids['tenant'],strategy_id=ids['strategy'],
            initiated_by=ids['demo_user_account'],request_key='scope-'+uuid4().hex,request_hash='a'*64,
            request_payload={},correlation_id=str(uuid4()),status='FAILED'))
    engine.dispose()
    assert client.get('/v1/valuation/attempts/'+str(attempt),headers=h).status_code==403
    result=client.get('/v1/valuation/attempts',headers=h)
    assert result.status_code==200,result.text
    assert all(row['strategy_id']==str(ids['uk_fund_strategy']) for row in result.json()['items'])
    assert str(attempt) not in result.text


def test_create_permission_and_initial_group_scope_are_atomic(client):
    h,group=scoped_user(client,['STRATEGY_CREATE','STRATEGY_READ','TRADE_WRITE'],[])
    result=client.post('/v1/strategies',headers=h,json={'strategyCode':'SCOPED_'+uuid4().hex,'displayName':'New scoped fund',
        'strategyType':'FUND','baseCurrencyCode':'GBP','initialAccessGroupIds':[group]})
    assert result.status_code==201,result.text
    strategy=result.json()['data']['strategyId']
    assert [row['strategyId'] for row in client.get('/v1/strategies',headers=h).json()['data']]==[strategy]
    h2,other_group=scoped_user(client,['TRADE_WRITE'],[])
    body={'strategyCode':'DENIED_'+uuid4().hex,'displayName':'Denied initial access','strategyType':'FUND','initialAccessGroupIds':[other_group]}
    assert client.post('/v1/strategies',headers=h,json=body).status_code==403
    assert not any(row['strategyCode']==body['strategyCode'] for row in client.get('/v1/strategies',headers=headers()).json()['data'])


def test_preview_state_change_requires_new_confirmation(client):
    h,group=scoped_user(client,['TRADE_READ'],[ids['strategy']])
    original=next(g for g in client.get('/v1/access',headers=headers()).json()['groups'] if g['groupId']==group)
    body={'groupId':group,'code':original['code'],'name':original['name'],'actions':['TRADE_READ'],
        'scopeMode':'ALL','strategyIds':[],'expectedVersion':original['versionNo']}
    preview=client.post('/v1/access/groups/preview',headers=headers(),json=body)
    assert preview.status_code==200,preview.text
    client.put('/v1/access/users/'+h['X-User-Account-Id']+'/groups',headers=headers(),json={'groupIds':[]})
    body.pop('groupId');body['expectedImpactHash']=preview.json()['impactHash']
    assert client.put('/v1/access/groups/'+group,headers=headers(),json=body).status_code==409
