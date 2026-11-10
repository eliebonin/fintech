"""FX maturity uses the same pinned profile proof as its opening writer."""
from uuid import UUID,uuid4
from sqlalchemy import select
from tests.test_valuation_service import valued
from tests.test_fx_maturity_service import setup
from tests.profile_fixtures import assign
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from lifecycle import fx_service as svc


def test_fx_maturity_profile_post_and_retry(valued):
    c,r,_=valued
    version,_=assign(c,r.tenant_id,ids['demo_user_account'],r.strategy_id)
    instrument,_,cut,_=setup(c,r)
    svc.configure(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,'DIRECT',0,'Isolated profile closure',r.policy_id,cut)
    _,fingerprint,_,_=svc.candidate(c,r.tenant_id,r.strategy_id,instrument)
    key=str(uuid4())
    result=svc.post(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,instrument,fingerprint,key)
    assert svc.post(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,instrument,fingerprint,key)['trade_ids']==result['trade_ids']
    for identity in result['trade_ids']:
        assert c.scalar(select(m.trade.c.trade_profile_version_id).where(m.trade.c.trade_id==UUID(identity)))==version['versionId']
