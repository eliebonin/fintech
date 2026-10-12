"""Operational catalogue must not load history or hide empty visible series."""
from contextlib import contextmanager
from uuid import uuid4
from datetime import date, datetime, timezone
from security_master_schema import models as m
from sqlalchemy import event, select
from apps.reference_api.db import get_engine
from security_master_schema.demo_data import DEMO_IDS as ids
from tests.test_api_reference_authority import request

@contextmanager
def connection():
    with get_engine().connect() as c:
        tx=c.begin()
        try: yield c
        finally: tx.rollback()

def test_catalogue_is_compact_searchable_and_retains_empty_paging_totals():
    with connection() as c:
        response=request(c,'GET','/v1/market-data/catalogue?q=HSBC&limit=1')
        assert response.status_code==200,response.text
        body=response.json()
        assert body['data'] and body['meta']['total']>=1
        row=body['data'][0]
        assert 'observations' not in row and 'observationTotal' not in row
        assert 'latestMarketDate' in row and 'latestValue' in row
        empty=request(c,'GET',f"/v1/market-data/catalogue?q=HSBC&limit=1&offset={body['meta']['total']}").json()
        assert empty['data']==[] and empty['meta']['total']==body['meta']['total']
        assert request(c,'GET','/v1/market-data/catalogue?q=not-a-real-reference').json()['meta']['total']==0

def test_catalogue_statement_count_does_not_grow_with_page_size():
    with connection() as c:
        counts=[]
        def record(*args): counts.append(args[2])
        event.listen(c,'before_cursor_execute',record)
        budgets=[]
        for size in (1,25,100):
            counts.clear()
            response=request(c,'GET',f'/v1/market-data/catalogue?limit={size}')
            assert response.status_code==200,response.text
            # Group-action resolution/RLS adds fixed queries, not per-series work.
            budgets.append(len(counts))
            assert len(counts)<=17,len(counts)
            assert not any('count(' in sql.lower() and 'market_data_observation' in sql.lower() for sql in counts)
        assert len(set(budgets))==1,budgets
        assert request(c,'GET','/v1/market-data/catalogue?limit=101').status_code==422

def test_catalogue_keeps_empty_series_and_bounds_values_by_market_date():
    with connection() as c:
        series=dict(c.execute(select(m.market_data_series).limit(1)).mappings().one())
        series['market_data_series_id']=uuid4()
        c.execute(m.market_data_series.insert().values(**series))
        body=request(c,'GET','/v1/market-data/catalogue?asOf=1900-01-01&limit=100').json()
        assert any(row['seriesId']==str(series['market_data_series_id']) for row in body['data'])
        assert all(row['latestValue'] is None and row['latestMarketDate'] is None for row in body['data'])

def test_catalogue_denies_inactive_membership_and_hides_private_nodes():
    with connection() as c:
        row=request(c,'GET','/v1/market-data/catalogue?limit=1').json()['data'][0]
        node=row['referenceNodeId']
        c.execute(m.reference_node_scope.delete().where(m.reference_node_scope.c.reference_node_id==node))
        c.execute(m.reference_node_scope.insert().values(reference_node_id=node,scope_type='TENANT_PRIVATE',owner_tenant_id=ids['second_tenant']))
        assert request(c,'GET',f'/v1/market-data/catalogue?q={node}').json()['data']==[]
        c.execute(m.tenant_user_account.update().where(m.tenant_user_account.c.tenant_id==ids['tenant'],m.tenant_user_account.c.user_account_id==ids['demo_user_account']).values(status='SUSPENDED'))
        assert request(c,'GET','/v1/market-data/catalogue').status_code==403

def test_catalogue_selects_only_current_accepted_permitted_dated_values():
    with connection() as c:
        sample=c.execute(select(m.market_data_observation).limit(1)).mappings().one()
        common=dict(market_data_series_id=sample['market_data_series_id'],dataset_id=sample['dataset_id'],
            observed_at_utc=datetime(2026,10,8,16,tzinfo=timezone.utc),received_at_utc=datetime(2026,10,9,tzinfo=timezone.utc),
            market_date=date(2026,10,8),value_basis='RAW')
        previous=uuid4()
        c.execute(m.market_data_observation.insert().values(**common,market_data_observation_id=previous,value='11',quality_status='ACCEPTED'))
        c.execute(m.market_data_observation.insert().values(**common,market_data_observation_id=uuid4(),supersedes_observation_id=previous,value='12',quality_status='ACCEPTED'))
        c.execute(m.market_data_observation.insert().values(**common,market_data_observation_id=uuid4(),value='999',quality_status='REJECTED'))
        future={**common,'market_date':date(2099,1,1)}
        c.execute(m.market_data_observation.insert().values(**future,market_data_observation_id=uuid4(),value='888',quality_status='ACCEPTED'))
        rows=request(c,'GET','/v1/market-data/catalogue?asOf=2026-10-09&limit=100').json()['data']
        row=next(row for row in rows if row['seriesId']==str(sample['market_data_series_id']))
        assert float(row['latestValue'])==12,row
        c.execute(m.tenant_dataset_entitlement.update().where(m.tenant_dataset_entitlement.c.tenant_id==ids['tenant'],m.tenant_dataset_entitlement.c.dataset_id==sample['dataset_id']).values(status='SUSPENDED'))
        assert not any(row['seriesId']==str(sample['market_data_series_id']) for row in request(c,'GET','/v1/market-data/catalogue?limit=100').json()['data'])


def test_history_filters_exact_series_before_pagination():
    with connection() as c:
        sample=c.execute(select(m.market_data_observation).limit(1)).mappings().one()
        original=dict(c.execute(select(m.market_data_series).where(m.market_data_series.c.market_data_series_id==sample['market_data_series_id'])).mappings().one())
        other={**original,'market_data_series_id':uuid4()}
        c.execute(m.market_data_series.insert().values(**other))
        node=original['reference_node_id']
        selected=original['market_data_series_id']
        response=request(c,'GET',f'/v1/market-data/series?referenceNodeId={node}&seriesId={selected}&limit=1')
        assert response.status_code==200,response.text
        body=response.json()
        assert body['meta']['total']==1
        assert [row['seriesId'] for row in body['data']]==[str(selected)]
        assert request(c,'GET',f'/v1/market-data/series?referenceNodeId={node}&seriesId={uuid4()}').json()['data']==[]
        assert request(c,'GET','/v1/market-data/series?seriesId=invalid').status_code==422


def test_full_period_chart_is_independent_of_price_pages_and_rights():
    from datetime import timedelta
    with connection() as c:
        sample=dict(c.execute(select(m.market_data_observation).limit(1)).mappings().one())
        selected=sample['market_data_series_id']
        prices=[]
        for i in range(1010):
            prices.append({**sample,'market_data_observation_id':uuid4(),'market_date':date(2030,1,1)+timedelta(days=i),'value':str(i+1),'source_observation_key':f'chart-test-{i}','observed_at_utc':datetime(2030,1,1,tzinfo=timezone.utc)+timedelta(days=i),'supersedes_observation_id':None})
        c.execute(m.market_data_observation.insert(),prices)
        path=f'/v1/market-data/series?seriesId={selected}&fromDate=2030-01-01&toDate=2032-12-31&includeChart=true&observationLimit=25'
        first=request(c,'GET',path).json()['data'][0]
        later=request(c,'GET',path+'&observationOffset=25').json()['data'][0]
        assert len(first['observations'])==25
        assert first['observationTotal']==1010
        assert len(first['chartPoints'])==1010
        assert first['chartPoints']==later['chartPoints']
        for size in (50,100):
            page=request(c,'GET',path.replace('observationLimit=25',f'observationLimit={size}')+'&observationOffset=100').json()['data'][0]
            assert len(page['observations'])==size
            assert page['chartPoints']==first['chartPoints']
        assert first['observations'][0]['value']!=later['observations'][0]['value']
        assert set(first['chartPoints'][0])=={'marketDate','value'}
        assert float(first['chartPoints'][-1]['value'])==1010
        assert request(c,'GET','/v1/market-data/series?includeChart=true').status_code==400
        c.execute(m.tenant_dataset_entitlement.update().where(m.tenant_dataset_entitlement.c.tenant_id==ids['tenant'],m.tenant_dataset_entitlement.c.dataset_id==sample['dataset_id']).values(status='SUSPENDED'))
        assert request(c,'GET',path).json()['data']==[]
