"""Worklist reads and counts use the caller's strategy-scoped authority."""
from tests.test_access_api import client,headers
from tests.test_strategy_scopes_api import scoped_user
from security_master_schema.demo_data import DEMO_IDS as ids


def test_worklist_and_options_are_scoped_and_read_only(client):
 h,_=scoped_user(client,['LIFECYCLE_READ'],[ids['strategy']])
 result=client.get('/v1/lifecycle/worklist/options',headers=h)
 assert result.status_code==200,result.text
 assert result.json()['total']==1
 assert result.json()['items'][0]['strategyId']==str(ids['strategy'])
 params=dict(fromDate='2026-11-01',toDate='2026-11-30',limit=25,offset=0,status='ALL',attention='ALL',includeEarlierOverdue='true')
 result=client.get('/v1/lifecycle/worklist',headers=h,params=params)
 assert result.status_code==200,result.text
 assert result.json()['total']==0 and result.json()['unavailableReason']
 for event in ['ALL','BOND_MATURITY','FX_FORWARD_MATURITY','BOND_COUPON','FUTURE_EXPIRY','OPTION_EXPIRY','STRUCTURED_OBSERVATION']:
  filtered=client.get('/v1/lifecycle/worklist',headers=h,params=dict(params,eventType=event))
  assert filtered.status_code==200,filtered.text
  assert 'FX_FORWARD_MATURITY' in filtered.json()['discoveryEventTypes']
 assert client.get('/v1/lifecycle/worklist',headers=h,params=dict(params,eventType='UNSUPPORTED_EVENT')).status_code==422
 assert client.get('/v1/lifecycle/worklist',headers=h,params=dict(params,strategyId=str(ids['uk_fund_strategy']))).status_code==403
 assert client.get('/v1/lifecycle/worklist',headers=h,params=dict(params,fromDate='2026-12-01')).status_code==422
 assert client.post('/v1/lifecycle/worklist',headers=h,json=params).status_code in (403,405)
 assert client.get('/v1/lifecycle/worklist/options',headers=headers()|{'X-User-Account-Id':str(ids['platform_admin_user_account'])}).status_code==403


def test_coupon_inspection_is_strategy_scoped_and_has_no_write_route(client):
 from uuid import uuid4
 h,_=scoped_user(client,['LIFECYCLE_READ'],[ids['strategy']])
 params=dict(strategyId=str(ids['strategy']),periodId=str(uuid4()))
 assert client.get('/v1/lifecycle/worklist/coupon',headers=h,params=params).status_code==404
 assert client.get('/v1/lifecycle/worklist/coupon',headers=h,params=dict(params,strategyId=str(ids['uk_fund_strategy']))).status_code==403
 assert client.post('/v1/lifecycle/worklist/coupon',headers=h,json=params).status_code in (403,405)


def test_future_inspection_is_scoped_and_get_only(client):
 from uuid import uuid4
 h,_=scoped_user(client,['LIFECYCLE_READ'],[ids['strategy']])
 params=dict(strategyId=str(ids['strategy']),instrumentId=str(uuid4()),milestoneKind='LAST_TRADE')
 assert client.get('/v1/lifecycle/worklist/future',headers=h,params=params).status_code==404
 assert client.get('/v1/lifecycle/worklist/future',headers=h,params=params|dict(strategyId=str(ids['uk_fund_strategy']))).status_code==403
 assert client.post('/v1/lifecycle/worklist/future',headers=h,json=params).status_code in (403,405)


def test_option_inspection_is_strategy_scoped_and_has_no_financial_write_route(client):
 from uuid import uuid4
 h,_=scoped_user(client,['LIFECYCLE_READ'],[ids['strategy']])
 params=dict(strategyId=str(ids['strategy']),instrumentId=str(uuid4()),milestoneKind='EXPIRY')
 assert client.get('/v1/lifecycle/worklist/option',headers=h,params=params).status_code==404
 assert client.get('/v1/lifecycle/worklist/option',headers=h,params=params|dict(strategyId=str(ids['uk_fund_strategy']))).status_code==403
 assert client.post('/v1/lifecycle/worklist/option',headers=h,json=params).status_code in (403,405)


def test_structured_inspection_is_scoped_and_get_only(client):
 from uuid import uuid4
 h,_=scoped_user(client,['LIFECYCLE_READ'],[ids['strategy']])
 params=dict(strategyId=str(ids['strategy']),instrumentId=str(uuid4()),eventKey='notice')
 assert client.get('/v1/lifecycle/worklist/structured',headers=h,params=params).status_code==404
 assert client.get('/v1/lifecycle/worklist/structured',headers=h,params=params|dict(strategyId=str(ids['uk_fund_strategy']))).status_code==403
 assert client.post('/v1/lifecycle/worklist/structured',headers=h,json=params).status_code in (403,405)
