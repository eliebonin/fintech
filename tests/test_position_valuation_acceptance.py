"""HTTP zero-result acceptance against the suite's owned disposable database."""
import asyncio
from dataclasses import replace
from datetime import timedelta
from uuid import uuid4
from httpx import AsyncClient,ASGITransport
from tests.test_valuation_service import valued
from apps.reference_api.main import create_app
from apps.reference_api.db import get_engine
from security_master_schema.demo_data import DEMO_IDS as ids

def test_http_empty_result_is_explicit_and_retry_stable(valued):
    c,r,_=valued
    assert get_engine().url.database.startswith('fortem_isolated_tests_')
    r=replace(r,opening_cutoff=r.opening_cutoff-timedelta(days=10),closing_cutoff=r.closing_cutoff-timedelta(days=10))
    c.commit()  # Synthetic fixture only; runner owns independent transactions.
    payload=dict(strategyId=str(r.strategy_id),policyId=str(r.policy_id),cutId=str(r.cut_id),
        reportingCurrencyId=str(r.reporting_currency_id),openingCutoff=r.opening_cutoff.isoformat(),
        closingCutoff=r.closing_cutoff.isoformat(),informationCutoff=r.information_cutoff.isoformat())
    headers={'X-Tenant-Id':str(r.tenant_id),'X-User-Account-Id':str(ids['demo_user_account']),'Idempotency-Key':str(uuid4())}
    async def exercise():
        async with AsyncClient(transport=ASGITransport(app=create_app(engine=get_engine())),base_url='http://test') as client:
            first=await client.post('/v1/valuation/attempts',json=payload,headers=headers)
            assert first.status_code==201,first.text
            result=first.json(); batch=result['batch']
            assert result['attempt']['status']=='COMPLETED'
            assert batch['items']==[] and batch['summary']['marketPnl']=='0'
            assert batch['summary']['resultFormat']=='POSITION_V2'
            assert batch['summary']['positionEvidence']['requiredMarkCount']==0
            again=await client.post('/v1/valuation/attempts',json=payload,headers=headers)
            assert again.status_code==201 and again.json()['batch']['batch_id']==batch['batch_id']
            detail=await client.get('/v1/valuation/attempts/'+result['attempt']['attempt_id'],headers=headers)
            assert detail.status_code==200 and detail.json()['batch']['summary']['marketPnl']=='0'
            rejected=await client.post('/v1/valuation/batches/'+batch['batch_id']+'/publish',json={'comment':'Self-review'},headers=headers)
            assert rejected.status_code==409 and 'independent' in rejected.text
    asyncio.run(exercise())
