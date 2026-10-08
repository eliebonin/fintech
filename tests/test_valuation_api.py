"""New valuation API transport, authority and safe failed-run evidence."""
import asyncio
import pytest
from sqlalchemy import select
from security_master_schema import models as m
from uuid import uuid4
from datetime import datetime,timezone
from httpx import ASGITransport,AsyncClient
from apps.reference_api.main import create_app
from apps.reference_api.db import get_engine
from security_master_schema.demo_data import DEMO_IDS as ids

def call(method,path,body=None,tenant=None,headers=None):
    async def run():
        async with AsyncClient(transport=ASGITransport(app=create_app(engine=get_engine())),base_url='http://test') as client:
            return await client.request(method,path,json=body,headers={'X-Tenant-Id':str(tenant or ids['tenant']),
                'X-User-Account-Id':str(ids['demo_user_account']),'Idempotency-Key':str(uuid4())}|(headers or {}))
    return asyncio.run(run())

def test_list_is_live_tenant_scoped_not_demo():
    response=call('GET','/v1/valuation/attempts')
    assert response.status_code==200,response.text
    assert isinstance(response.json()['items'],list)
    assert response.json()['scope']=='MARKET_ONLY'


def test_market_data_alone_does_not_grant_valuation_access():
    engine=get_engine()
    assert engine.url.database.startswith('fortem_isolated_tests_')
    entitlement=m.tenant_module_entitlement
    with engine.begin() as c:
        row=c.execute(select(entitlement).where(entitlement.c.tenant_module_entitlement_id==ids['valuation_module_entitlement'])).mappings().one()
        original=row['entitlement_state']
        c.execute(entitlement.update().where(entitlement.c.tenant_module_entitlement_id==ids['valuation_module_entitlement']).values(entitlement_state='SUSPENDED'))
    try:
        response=call('GET','/v1/valuation/attempts')
        assert response.status_code==403,response.text
        assert 'VALUATION' in response.text
    finally:
        with engine.begin() as c:
            c.execute(entitlement.update().where(entitlement.c.tenant_module_entitlement_id==ids['valuation_module_entitlement']).values(entitlement_state=original))


def test_independent_transactions_receive_configured_budgets():
    from sqlalchemy import text
    from apps.reference_api.config import Settings
    from apps.reference_api.resource_limits import configure_transaction_budget
    from valuation.runner import execute
    from valuation.service import ValuationRequest,ValuationBlocked
    engine=get_engine();seen=[]
    settings=Settings.from_environment()
    def budget(c):
        configure_transaction_budget(c,settings)
        seen.append((c.scalar(text("SHOW statement_timeout")),c.scalar(text("SHOW lock_timeout"))))
    # Empty strategies are now valid zero results; use a missing policy to test
    # the failed-attempt transaction path deliberately, not accidentally.
    request=ValuationRequest(ids['tenant'],ids['strategy'],uuid4(),ids['valuation_cut'],ids['gbp_currency'],
        datetime(2026,9,29,22,tzinfo=timezone.utc),datetime(2026,10,1,22,tzinfo=timezone.utc),datetime.now(timezone.utc))
    with pytest.raises(ValuationBlocked):
        execute(engine,request,ids['demo_user_account'],str(uuid4()),'budget-test',configure_transaction=budget)
    assert seen==[('30s','10s')]*3

def test_write_denied_without_market_data_admin_authority():
    response=call('POST','/v1/valuation/attempts',dict(strategyId=str(ids['strategy']),policyId=str(ids['valuation_policy']),
        cutId=str(ids['valuation_cut']),reportingCurrencyId=str(ids['gbp_currency']),openingCutoff='2026-09-29T22:00:00Z',
        closingCutoff='2026-10-01T22:00:00Z',informationCutoff=datetime.now(timezone.utc).isoformat()),tenant=ids['second_tenant'])
    assert response.status_code==403,response.text

def test_unknown_attempt_is_opaque():
    response=call('GET','/v1/valuation/attempts/'+str(uuid4()))
    assert response.status_code==404,response.text

def test_naive_cutoffs_and_extra_inputs_are_rejected():
    response=call('POST','/v1/valuation/attempts',dict(strategyId=str(ids['strategy']),policyId=str(ids['valuation_policy']),
        cutId=str(ids['valuation_cut']),reportingCurrencyId=str(ids['gbp_currency']),openingCutoff='2026-09-29T22:00:00',
        closingCutoff='2026-10-01T22:00:00Z',informationCutoff=datetime.now(timezone.utc).isoformat(),inventedPrice='100'))
    assert response.status_code==422,response.text

def test_failed_calculation_has_durable_safe_attempt_and_no_financial_total():
    key=str(uuid4())
    payload=dict(strategyId=str(ids['strategy']),policyId=str(uuid4()),cutId=str(ids['valuation_cut']),
        reportingCurrencyId=str(ids['gbp_currency']),openingCutoff='2026-09-29T22:00:00Z',closingCutoff='2026-10-01T22:00:00Z',
        informationCutoff=datetime.now(timezone.utc).isoformat())
    response=call('POST','/v1/valuation/attempts',payload,headers={'Idempotency-Key':key})
    assert response.status_code==422,response.text
    assert 'marketPnl' not in response.json()
    listing=call('GET','/v1/valuation/attempts').json()['items']
    row=next(item for item in listing if item['request_key']==key)
    detail=call('GET','/v1/valuation/attempts/'+row['attempt_id']).json()
    assert detail['attempt']['status']=='FAILED'
    assert detail['batch'] is None
    assert detail['events'][-1]['event_code']=='FAILED'
    assert detail['events'][-1]['details']['reason']
    assert 'postgresql' not in str(detail).lower()
