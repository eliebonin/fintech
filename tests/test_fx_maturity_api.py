from uuid import uuid4
from sqlalchemy import select
from tests.test_access_api import client,headers
from tests.test_valuation_service import valued
from tests.test_fx_maturity_service import setup
from tests.test_strategy_scopes_api import scoped_user
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids


def test_mock_forward_http_closure_and_scope(client,valued):
    c,r,_=valued
    original_dates=dict(c.execute(select(m.instrument_dates).where(m.instrument_dates.c.instrument_node_id==ids['fx_forward_instrument_node'])).mappings().one())
    original_terms=dict(c.execute(select(m.fx_forward_terms).where(m.fx_forward_terms.c.instrument_node_id==ids['fx_forward_instrument_node'])).mappings().one())
    instrument,group,cut,series=setup(c,r);c.commit()
    base='/v1/lifecycle/fx-forward';h=headers();target=dict(strategyId=str(r.strategy_id),instrumentId=str(instrument))
    def ok(response,status=200):
        assert response.status_code==status,response.text
        return response.json()
    try:
        opts=ok(client.get(base+'/options',headers=h,params={'strategyId':str(r.strategy_id)}))
        assert str(instrument) in [row['id'] for row in opts['instruments']]
        ok(client.post(base+'/policy',headers=h,json=dict(strategyId=str(r.strategy_id),mode='DIRECT',expectedRevision=0,
            reason='Mock maturity API',confirmChange=True,pricingPolicyId=str(r.policy_id),pricingCutId=str(cut))))
        preview=ok(client.post(base+'/closures/preview',headers=h,json=target))
        assert preview['inputs']['suggestedPrice']=='1.12'
        override=dict(rate='1.125',sourceReference='Mock confirmed closing rate',reason='Counterparty confirmation')
        preview=ok(client.post(base+'/closures/preview',headers=h,json=target|dict(rateOverride=override)))
        payload=target|dict(expectedFingerprint=preview['inputHash'],confirmBooking=True,rateOverride=override)
        key=str(uuid4());booked=ok(client.post(base+'/closures/book',headers=h|{'Idempotency-Key':key},json=payload),201)
        assert booked['evidence']['price']=='1.125' and booked['evidence']['suggestedPrice']=='1.12'
        assert ok(client.post(base+'/closures/book',headers=h|{'Idempotency-Key':key},json=payload),201)['trade_ids']==booked['trade_ids']
        assert client.post(base+'/closures/preview',headers=h,json=target).status_code==409
        assert ok(client.get(base+'/closures/postings',headers=h,params={'strategyId':str(r.strategy_id)}))['total']==1
        denied,_=scoped_user(client,['LIFECYCLE_READ','MARKET_DATA_READ'],[ids['uk_fund_strategy']])
        assert client.get(base+'/closures/postings',headers=denied,params={'strategyId':str(r.strategy_id)}).status_code==403
        assert client.post(base+'/closures/book',headers=denied|{'Idempotency-Key':str(uuid4())},json=payload).status_code==403
    finally:
        c.rollback()
        with c.begin():
            c.execute(m.valuation_policy_rule.delete().where(m.valuation_policy_rule.c.market_data_series_id==series))
            c.execute(m.instrument_dates.update().where(m.instrument_dates.c.instrument_node_id==instrument).values(**original_dates))
            c.execute(m.fx_forward_terms.update().where(m.fx_forward_terms.c.instrument_node_id==instrument).values(**original_terms))
