"""Verified tenant transport and exact local interest-history commands."""
from uuid import uuid4
from tests.api_client import ConnectionEngine,FixtureTestClient
from tests.test_valuation_service import valued
from tests.test_economic_pnl_acceptance import add_bond
from apps.reference_api.main import create_app
from security_master_schema.demo_data import DEMO_IDS as ids


def test_history_routes_keep_daily_income_and_assessed_stocks_separate(valued):
    c,r,trade=valued;add_bond(c,r,trade)
    headers={'X-Tenant-Id':str(r.tenant_id),'X-User-Account-Id':str(ids['demo_user_account']),'Idempotency-Key':str(uuid4())}
    with FixtureTestClient(create_app(engine=ConnectionEngine(c))) as client:
        response=client.post('/v1/valuation/balance-inputs',headers=headers,json={'strategyId':str(r.strategy_id),
            'instrumentId':str(ids['bond_instrument_node']),'currencyId':str(ids['gbp_currency']),'valueDate':'2026-09-30',
            'closingBalance':'5000.123456789012','sourceReference':'Synthetic assessed statement','reason':'Opening anchor'})
        assert response.status_code==201,response.text
        assert response.json()['closing_balance']=='5000.123456789012'
        response=client.post('/v1/valuation/balance-history-refresh',headers=headers|{'Idempotency-Key':str(uuid4())},
            json={'strategyId':str(r.strategy_id),'fromDate':'2026-09-30','toDate':'2026-10-01'})
        assert response.status_code==201,response.text
        response=client.get('/v1/valuation/balance-history',headers=headers,params={'strategyId':str(r.strategy_id),'fromDate':'2026-09-30','toDate':'2026-10-01'})
        assert response.status_code==200,response.text
        assert response.json()['total']==2
        assert response.json()['items'][1]['opening_balance']=='5000.123456789012'
        response=client.get('/v1/valuation/interest-options',headers=headers,params={'strategyId':str(r.strategy_id)})
        assert response.status_code==200,response.text
        assert any(x['id']==str(ids['bond_instrument_node']) for x in response.json()['bonds'])
        response=client.get('/v1/valuation/balance-history',headers=headers,params={'strategyId':str(uuid4()),'fromDate':'2026-09-30','toDate':'2026-10-01'})
        assert response.status_code in (403,404),response.text


def test_daily_and_balance_routes_require_scope_on_the_selected_strategy(valued):
    from tests.test_strategy_scopes_api import scoped_user
    c,r,_=valued
    with FixtureTestClient(create_app(engine=ConnectionEngine(c))) as client:
        restricted,_=scoped_user(client,['VALUATION_READ','VALUATION_RUN','MARKET_DATA_READ'],[ids['uk_fund_strategy']])
        params={'strategyId':str(r.strategy_id),'instrumentId':str(ids['bond_instrument_node']),'fromDate':'2026-09-30','toDate':'2026-10-01'}
        for route in ['accrual-inputs','balance-inputs','balance-history','balance-series','interest-options']:
            response=client.get('/v1/valuation/'+route,headers=restricted,params=params)
            assert response.status_code in (403,404),(route,response.text)


def test_ops_maintenance_retains_daily_corrections_and_separate_stock_withdrawals(valued):
    c,r,trade=valued;add_bond(c,r,trade)
    headers={'X-Tenant-Id':str(r.tenant_id),'X-User-Account-Id':str(ids['demo_user_account'])}
    scope=dict(strategyId=str(r.strategy_id),instrumentId=str(ids['bond_instrument_node']),currencyId=str(ids['gbp_currency']),valueDate='2026-10-01')
    with FixtureTestClient(create_app(engine=ConnectionEngine(c))) as client:
        key=str(uuid4());daily=scope|dict(dailyEarned='12.123456789012',sourceReference='Synthetic Ops daily source')
        recorded=client.post('/v1/valuation/accrual-inputs',headers=headers|{'Idempotency-Key':key},json=daily)
        assert recorded.status_code==201,recorded.text
        first=recorded.json();assert first['daily_earned_interest']=='12.123456789012'
        assert first['strategy_id']==scope['strategyId'] and first['instrument_id']==scope['instrumentId']
        assert client.post('/v1/valuation/accrual-inputs',headers=headers|{'Idempotency-Key':key},json=daily).json()['input_id']==first['input_id']
        revised=client.post('/v1/valuation/accrual-inputs',headers=headers|{'Idempotency-Key':str(uuid4())},json=daily|dict(supersedesInputId=first['input_id'],dailyEarned='13.123456789012'))
        assert revised.status_code==201,revised.text
        assert revised.json()['revision']==2 and revised.json()['daily_earned_interest']=='13.123456789012'
        anchor=client.post('/v1/valuation/balance-inputs',headers=headers|{'Idempotency-Key':str(uuid4())},json=scope|dict(closingBalance='1000.123456789012',sourceReference='Synthetic Ops statement',reason='Independent closing stock'))
        assert anchor.status_code==201,anchor.text
        withdrawn=client.post('/v1/valuation/balance-inputs',headers=headers|{'Idempotency-Key':str(uuid4())},json=scope|dict(closingBalance=None,status='WITHDRAWN',supersedesInputId=anchor.json()['input_id'],sourceReference='Synthetic Ops statement',reason='Duplicate statement entry'))
        assert withdrawn.status_code==201,withdrawn.text
        assert withdrawn.json()['closing_balance'] is None and withdrawn.json()['revision']==2
        params=dict(strategyId=str(r.strategy_id),fromDate='2026-10-01',toDate='2026-10-01')
        assert client.get('/v1/valuation/accrual-inputs',headers=headers,params=params).json()['items'][0]['input_id']==revised.json()['input_id']
        assert client.get('/v1/valuation/balance-inputs',headers=headers,params=params).json()['items'][0]['status']=='WITHDRAWN'
        build=client.post('/v1/valuation/balance-history-refresh',headers=headers|{'Idempotency-Key':str(uuid4())},json=params)
        assert build.status_code==201,build.text
        assert build.json()['strategy_id']==scope['strategyId'] and build.json()['from_date']=='2026-10-01'
