"""Read-only full-series transport, date/instrument selection and scope."""
from datetime import date,timedelta
from uuid import uuid4
from tests.test_valuation_service import valued
from tests.api_client import ConnectionEngine,FixtureTestClient
from apps.reference_api.main import create_app
from security_master_schema.demo_data import DEMO_IDS as ids
from valuation.balance_history import record_balance_input,refresh_history
from valuation.balance_history_contracts import BalanceInputCreate,BalanceHistoryRefresh


def test_interest_bond_choices_do_not_include_unrelated_bonds_after_a_listing_trade(valued):
    c,r,_=valued  # This strategy owns one listed equity execution and no bonds.
    headers={'X-Tenant-Id':str(r.tenant_id),'X-User-Account-Id':str(ids['demo_user_account'])}
    with FixtureTestClient(create_app(engine=ConnectionEngine(c))) as client:
        response=client.get('/v1/valuation/interest-options',headers=headers,params=dict(strategyId=str(r.strategy_id)))
        assert response.status_code==200,response.text
        assert response.json()['bonds']==[]
        assert response.json()['strategyLabel']


def test_balance_series_contains_all_dates_not_only_the_first_history_page(valued):
    c,r,_=valued;first=date(2026,8,1);last=first+timedelta(days=34)
    for i in range(35):
        record_balance_input(c,r.tenant_id,ids['demo_user_account'],BalanceInputCreate(strategyId=r.strategy_id,
            instrumentId=ids['bond_instrument_node'],currencyId=ids['gbp_currency'],valueDate=first+timedelta(days=i),
            closingBalance=f'{1000+i}.123456789012',sourceReference='Synthetic series assessment',reason='Chart acceptance'),uuid4().hex)
    refresh_history(c,r.tenant_id,ids['demo_user_account'],BalanceHistoryRefresh(strategyId=r.strategy_id,fromDate=first,toDate=last),uuid4().hex)
    headers={'X-Tenant-Id':str(r.tenant_id),'X-User-Account-Id':str(ids['demo_user_account'])}
    params=dict(strategyId=str(r.strategy_id),instrumentId=str(ids['bond_instrument_node']),fromDate=str(first),toDate=str(last))
    with FixtureTestClient(create_app(engine=ConnectionEngine(c))) as client:
        paged=client.get('/v1/valuation/balance-history',headers=headers,params=params|dict(limit=1))
        assert paged.status_code==200 and len(paged.json()['items'])==1
        assert paged.json()['total']==35
        other_page=client.get('/v1/valuation/balance-history',headers=headers,params=params|dict(instrumentId=str(ids['hsbc_instrument_node']),limit=1))
        assert other_page.status_code==200 and other_page.json()['total']==0 and other_page.json()['items']==[]
        second_page=client.get('/v1/valuation/balance-history',headers=headers,params=params|dict(limit=1,offset=34))
        assert second_page.status_code==200 and second_page.json()['total']==35
        assert second_page.json()['items'][0]['closing_balance']=='1034.123456789012'
        full=client.get('/v1/valuation/balance-series',headers=headers,params=params)
        assert full.status_code==200,full.text
        data=full.json();assert data['total']==len(data['items'])==35
        assert data['items'][-1]['closing_balance']=='1034.123456789012'
        assert all('bondSources' not in row.get('source_proof',{}) for row in data['items'])
        filtered=client.get('/v1/valuation/balance-series',headers=headers,params=params|dict(fromDate=str(last),toDate=str(last)))
        assert filtered.status_code==200 and filtered.json()['total']==1
        other=client.get('/v1/valuation/balance-series',headers=headers,params=params|dict(instrumentId=str(ids['hsbc_instrument_node'])))
        assert other.status_code==200 and other.json()['items']==[]
        long_range=client.get('/v1/valuation/balance-series',headers=headers,params=params|dict(fromDate='2024-01-01'))
        assert long_range.status_code==200 and long_range.json()['total']==35
        reversed_dates=client.get('/v1/valuation/balance-series',headers=headers,params=params|dict(fromDate=str(last),toDate=str(first)))
        assert reversed_dates.status_code==422
        foreign=client.get('/v1/valuation/balance-series',headers=headers,params=params|dict(strategyId=str(uuid4())))
        assert foreign.status_code in (403,404)
        from tests.test_strategy_scopes_api import scoped_user
        reader,_=scoped_user(client,['VALUATION_READ','MARKET_DATA_READ'],[r.strategy_id])
        readable=client.get('/v1/valuation/balance-series',headers=reader,params=params)
        assert readable.status_code==200 and readable.json()['total']==35
