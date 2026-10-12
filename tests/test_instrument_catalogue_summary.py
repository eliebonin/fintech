"""Compact catalogue must stay bounded and retain tenant visibility."""
from contextlib import contextmanager
from sqlalchemy import event, select
from apps.reference_api.db import get_engine
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from tests.test_api_reference_authority import request

@contextmanager
def connection():
    with get_engine().connect() as c:
        tx=c.begin()
        try: yield c
        finally: tx.rollback()


def test_catalogue_summary_returns_table_fields_and_matching_listing_count():
    with connection() as c:
        response=request(c,'GET','/v1/instruments/catalogue?q=HSBC&limit=25')
        assert response.status_code==200,response.text
        data=response.json()['data']
        row=next(r for r in data if r['instrumentId']==str(ids['hsbc_instrument_node']))
        assert set(row)=={'instrumentId','canonicalName','instrumentType','assetClass','status','baseCurrency','listingCount'}
        detail=request(c,'GET',f"/v1/instruments/{row['instrumentId']}").json()['data']
        assert row['listingCount']==len(detail['listings'])
        assert detail['listings'][0]['marketData']
        assert next(r for r in request(c,'GET','/v1/instruments/search?q=HSBC').json()['data'] if r['instrumentId']==row['instrumentId'])['listings']


def test_catalogue_queries_stay_bounded_as_page_size_grows():
    with connection() as c:
        statements=[]
        def record(conn,cursor,sql,params,context,many): statements.append(sql)
        event.listen(c,'before_cursor_execute',record)
        budgets=[]
        for size in (1,25,100):
            statements.clear()
            response=request(c,'GET',f'/v1/instruments/catalogue?limit={size}&status=ACTIVE')
            assert response.status_code==200,response.text
            assert response.json()['data']
            # The action boundary adds fixed membership/RLS queries. Catalogue
            # cost must remain constant, never become one query per instrument.
            budgets.append(len(statements))
            assert len(statements)<=12,len(statements)
            assert not any('md.market_data_observation' in sql or 'licence_activity_grant' in sql for sql in statements)
        assert len(set(budgets))==1,budgets


def test_catalogue_summary_retains_filters_pages_and_empty_totals():
    with connection() as c:
        first=request(c,'GET','/v1/instruments/catalogue?instrument_type=BOND&asset_class=FIXED_INCOME&status=ACTIVE&limit=1').json()
        assert first['data'][0]['instrumentType']=='BOND'
        assert first['data'][0]['listingCount']==0
        empty=request(c,'GET',f"/v1/instruments/catalogue?instrument_type=BOND&asset_class=FIXED_INCOME&status=ACTIVE&limit=1&offset={first['meta']['total']}").json()
        assert empty['data']==[] and empty['meta']['total']==first['meta']['total']
        assert request(c,'GET','/v1/instruments/catalogue?q=BOND_DEMO_2031').json()['data']
        assert request(c,'GET','/v1/instruments/catalogue?q=ABC').json()['data']


def test_catalogue_summary_denies_inactive_membership_and_hides_private_instruments_and_listings():
    with connection() as c:
        c.execute(m.reference_node_scope.delete().where(m.reference_node_scope.c.reference_node_id==ids['hsbc_xlon_listing_node']))
        c.execute(m.reference_node_scope.insert().values(reference_node_id=ids['hsbc_xlon_listing_node'],scope_type='TENANT_PRIVATE',owner_tenant_id=ids['second_tenant']))
        row=next(r for r in request(c,'GET','/v1/instruments/catalogue?q=HSBC').json()['data'] if r['instrumentId']==str(ids['hsbc_instrument_node']))
        assert row['listingCount']==0
        c.execute(m.reference_node_scope.delete().where(m.reference_node_scope.c.reference_node_id==ids['hsbc_instrument_node']))
        c.execute(m.reference_node_scope.insert().values(reference_node_id=ids['hsbc_instrument_node'],scope_type='TENANT_PRIVATE',owner_tenant_id=ids['second_tenant']))
        assert not request(c,'GET',f"/v1/instruments/catalogue?q={ids['hsbc_instrument_node']}").json()['data']
        c.execute(m.tenant_user_account.update().where(m.tenant_user_account.c.tenant_id==ids['tenant'],m.tenant_user_account.c.user_account_id==ids['demo_user_account']).values(status='SUSPENDED'))
        assert request(c,'GET','/v1/instruments/catalogue').status_code==403


def test_listing_external_code_search_is_correlated_to_its_instrument():
    with connection() as c:
        mapping=c.execute(select(m.external_object_mapping).where(m.external_object_mapping.c.target_object_id==ids['hsbc_xlon_listing_node'])).mappings().first()
        assert mapping is not None
        code='AMZN_SEARCH_CORRELATION_REGRESSION'
        c.execute(m.external_object_mapping.update().where(m.external_object_mapping.c.external_object_mapping_id==mapping['external_object_mapping_id']).values(external_id_value=code))
        for endpoint in ('catalogue','search'):
            body=request(c,'GET',f'/v1/instruments/{endpoint}?q={code}').json()
            assert [row['instrumentId'] for row in body['data']]==[str(ids['hsbc_instrument_node'])]
            assert body['meta']['total']==1
        assert request(c,'GET','/v1/instruments/catalogue?q=NO_MATCH_SEARCH_CORRELATION').json()['data']==[]
