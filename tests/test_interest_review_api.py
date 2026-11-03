from datetime import date
from uuid import uuid4
from tests.api_client import ConnectionEngine,FixtureTestClient
from tests.test_valuation_service import valued
from tests.test_economic_pnl_acceptance import add_bond
from tests.test_accrued_balance_integration import daily
from tests.test_interest_review_integration import command
from apps.reference_api.main import create_app
from security_master_schema.demo_data import DEMO_IDS as ids


def test_api_two_stage_review_is_scoped_and_preserves_exact_receipts(valued):
    c,r,trade=valued;add_bond(c,r,trade);daily(c,r,date(2026,9,30));daily(c,r,date(2026,10,1))
    headers={'X-Tenant-Id':str(r.tenant_id),'X-User-Account-Id':str(ids['demo_user_account'])}
    params=dict(strategyId=str(r.strategy_id),valueDate='2026-10-01',stage='DAILY')
    with FixtureTestClient(create_app(engine=ConnectionEngine(c))) as client:
        result=client.get('/v1/valuation/interest-review',headers=headers,params=params)
        assert result.status_code==200,result.text
        view=result.json();assert view['canWrite'] and view['strategyLabel']
        payload=command(view,'DAILY').model_dump(mode='json',by_alias=True)
        key=str(uuid4());first=client.post('/v1/valuation/interest-review',headers=headers|{'Idempotency-Key':key},json=payload)
        assert first.status_code==201,first.text
        second=client.post('/v1/valuation/interest-review',headers=headers|{'Idempotency-Key':key},json=payload)
        assert second.json()['review_id']==first.json()['review_id']
        balance=client.get('/v1/valuation/interest-review',headers=headers,params=params|dict(stage='BALANCE'))
        assert balance.status_code==200,balance.text
        final=client.post('/v1/valuation/interest-review',headers=headers|{'Idempotency-Key':str(uuid4())},json=command(balance.json(),'BALANCE').model_dump(mode='json',by_alias=True))
        assert final.status_code==201,final.text
        from tests.test_strategy_scopes_api import scoped_user
        restricted,_=scoped_user(client,['VALUATION_READ','VALUATION_RUN','MARKET_DATA_READ'],[ids['uk_fund_strategy']])
        denied=client.get('/v1/valuation/interest-review',headers=restricted,params=params)
        assert denied.status_code in (403,404),denied.text
        reader,_=scoped_user(client,['VALUATION_READ','MARKET_DATA_READ'],[r.strategy_id])
        read=client.get('/v1/valuation/interest-review',headers=reader,params=params)
        assert read.status_code==200 and read.json()['canWrite'] is False
        assert client.post('/v1/valuation/interest-review',headers=reader|{'Idempotency-Key':str(uuid4())},json=payload).status_code==403
        reviewer,_=scoped_user(client,['VALUATION_READ','VALUATION_REVIEW','MARKET_DATA_READ'],[r.strategy_id])
        review=client.get('/v1/valuation/interest-review',headers=reviewer,params=params)
        assert review.status_code==200 and review.json()['canWrite']
        draft=command(review.json(),'DAILY').model_copy(update={'state':'DRAFT'}).model_dump(mode='json',by_alias=True)
        saved=client.post('/v1/valuation/interest-review',headers=reviewer|{'Idempotency-Key':str(uuid4())},json=draft)
        assert saved.status_code==201,saved.text
