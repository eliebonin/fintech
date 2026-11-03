import os
from contextlib import contextmanager
from uuid import uuid4
from sqlalchemy import create_engine,select
from tests.api_client import FixtureTestClient
from apps.reference_api.main import create_app
from apps.reference_api.workload_admission import AdmissionController,WorkloadBusy,WorkloadUnavailable
from security_master_schema.demo_data import DEMO_IDS as ids
from valuation import tables as t
import pytest


@pytest.mark.parametrize('failure,status',[(WorkloadBusy,429),(WorkloadUnavailable,503)])
def test_rejected_valuation_creates_no_attempt_and_retains_safe_retry_contract(failure,status):
    @contextmanager
    def unavailable(tenant):
        raise failure()
        yield
    engine=create_engine(os.environ['DATABASE_URL']);key='busy-'+uuid4().hex
    try:
        with FixtureTestClient(create_app(engine=engine,workload_controller=AdmissionController(unavailable))) as client:
            response=client.post('/v1/valuation/attempts',headers={'X-Tenant-Id':str(ids['tenant']),
                'X-User-Account-Id':str(ids['demo_user_account']),'Idempotency-Key':key},json={
                    'strategyId':str(ids['strategy']),'policyId':str(ids['valuation_policy']),
                    'cutId':str(ids['valuation_cut']),'reportingCurrencyId':str(ids['gbp_currency']),
                    'openingDate':'2026-09-29','closingDate':'2026-10-01'})
            assert response.status_code==status,response.text
            assert response.headers['Retry-After']=='5'
            body=response.json();assert body['notStarted'] is True and body['retryable'] is True
            assert body['code']==('workload.busy' if status==429 else 'workload.unavailable')
            status_read=client.get('/v1/valuation/attempts',headers={'X-Tenant-Id':str(ids['tenant']),'X-User-Account-Id':str(ids['demo_user_account'])})
            assert status_read.status_code==200,status_read.text
        with engine.connect() as c:assert c.scalar(select(t.attempt.c.attempt_id).where(t.attempt.c.request_key==key)) is None
    finally:engine.dispose()
