"""Reporting across pages and read/run isolation, on an owned disposable DB."""
from datetime import date,datetime,timezone,timedelta
from uuid import uuid4
import pytest
from sqlalchemy import select
from tests.test_access_api import client,headers
from tests.test_strategy_scopes_api import scoped_user
from apps.reference_api.db import get_engine
from security_master_schema.demo_data import DEMO_IDS as ids
from valuation import tables as t

@pytest.fixture
def population():
    engine=get_engine();assert engine.url.database.startswith('platform_isolated_tests_')
    attempts=[uuid4() for _ in range(29)];batch=uuid4()
    with engine.begin() as c:
        for index,attempt in enumerate(attempts):
            day='2024-02-10' if index<26 else '2024-01-10'
            c.execute(t.attempt.insert().values(attempt_id=attempt,tenant_id=ids['tenant'],strategy_id=ids['strategy'],
                initiated_by=ids['demo_user_account'],request_key=uuid4().hex,request_hash='a'*64,
                request_payload={'strategy_id':str(ids['strategy']),'closing_cutoff':day+'T23:59:59Z'},
                correlation_id=uuid4().hex,status='COMPLETED' if index==28 else 'FAILED',
                started_at=datetime(2026,10,1,tzinfo=timezone.utc)+timedelta(seconds=index)))
        c.execute(t.batch.insert().values(batch_id=batch,tenant_id=ids['tenant'],strategy_id=ids['strategy'],
            attempt_id=attempts[28],staged_by=ids['demo_user_account'],value_date=date(2024,1,10),status='STAGED',
            mode='AUTHORITATIVE',input_hash='b'*64,base_population_hash='c'*64,
            summary={'netPnl':'999999','reportingCurrencyId':str(ids['gbp_currency'])}))
    yield attempts,batch
    with engine.begin() as c:
        c.execute(t.batch.delete().where(t.batch.c.batch_id==batch))
        c.execute(t.attempt.delete().where(t.attempt.c.attempt_id.in_(attempts)))

def test_full_history_filter_and_count_precede_pagination(client,population):
    attempts,_=population
    path=f'/v1/valuation/attempts?strategy_id={ids["strategy"]}&from_date=2024-02-01&to_date=2024-02-29&limit=25'
    first=client.get(path,headers=headers());assert first.status_code==200,first.text
    assert first.json()['total']==26 and len(first.json()['items'])==25
    second=client.get(path+'&offset=25',headers=headers());assert second.status_code==200,second.text
    assert second.json()['total']==26
    assert [row['attempt_id'] for row in second.json()['items']]==[str(attempts[0])]
    assert client.get(path+'&calculation_status=COMPLETED',headers=headers()).json()['total']==0

def test_actual_publication_state_is_reported_but_unguarded_financials_are_not(client,population):
    _,batch=population
    path=f'/v1/valuation/attempts?strategy_id={ids["strategy"]}&from_date=2024-01-10&to_date=2024-01-10&results_only=true&publication_status=STAGED'
    response=client.get(path,headers=headers());assert response.status_code==200,response.text
    body=response.json();assert body['total']==1
    row=body['items'][0];assert row['status']=='COMPLETED' and row['batch_status']=='STAGED'
    assert row['batch_id']==str(batch) and row['evidence_access']=='DENIED'
    assert 'financial_summary' not in row and '999999' not in response.text
    assert client.get(path.replace('STAGED','PUBLISHED'),headers=headers()).json()['total']==0

def test_read_only_strategy_is_available_without_run_authority(client,population):
    h,_=scoped_user(client,['VALUATION_READ','MARKET_DATA_READ'],[ids['strategy']])
    response=client.get('/v1/valuation/options',headers=h);assert response.status_code==200,response.text
    strategies=response.json()['strategies'];assert len(strategies)==1
    assert strategies[0]['id']==str(ids['strategy']) and strategies[0]['canCalculate'] is False
    rows=client.get('/v1/valuation/attempts?from_date=2024-02-01&to_date=2024-02-29',headers=h)
    assert rows.status_code==200 and rows.json()['total']==26
    denied=client.get(f'/v1/valuation/attempts?strategy_id={ids["uk_fund_strategy"]}',headers=h)
    # Explicitly guessed strategy IDs hit the existing authorization guard first.
    assert denied.status_code==403 and 'items' not in denied.json()

@pytest.mark.parametrize('query,status',[('from_date=2024-02-01&to_date=2024-01-01',422),('from_date=not-a-date',422),('publication_status=FINAL',422),('strategy_id=not-a-uuid',403)])
def test_invalid_report_filters_are_rejected(client,query,status):
    assert client.get('/v1/valuation/attempts?'+query,headers=headers()).status_code==status
