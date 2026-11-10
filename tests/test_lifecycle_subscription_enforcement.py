"""Native bond/FX entry points enforce both selected and subscribed assistance."""
from uuid import uuid4
from sqlalchemy import select,func
import pytest
from tests.test_valuation_service import valued
from tests.test_bond_redemption_service import setup as bond_setup
from tests.test_fx_maturity_service import setup as fx_setup
from tests.test_lifecycle_entitlements import change
from tests.test_lifecycle_assistance import configure as select_assistance
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids


def setup(c,r,trade,product):
    if product=='BOND':
        from lifecycle import bond_service as svc
        bond_setup(c,r,trade,assistance=False)
        return svc,ids['bond_instrument_node'],'BOND_MATURITY',()
    from lifecycle import fx_service as svc
    instrument,_,cut,_=fx_setup(c,r,assistance=False)
    return svc,instrument,'FX_FORWARD_MATURITY',(r.policy_id,cut)


@pytest.mark.parametrize('product',['BOND','FX'])
def test_native_preview_requires_explicit_subscription_and_selection(valued,product):
    c,r,trade=valued;svc,instrument,event,args=setup(c,r,trade,product)
    with pytest.raises(PermissionError,match='assistance|Tier|subscription'):
        svc.candidate(c,r.tenant_id,r.strategy_id,instrument)


@pytest.mark.parametrize('product',['BOND','FX'])
def test_assisted_confirmation_is_retained_and_downgrade_preserves_receipt(valued,product):
    c,r,trade=valued;svc,instrument,event,args=setup(c,r,trade,product)
    change(c,3);select_assistance(c,3,event,strategy=r.strategy_id)
    svc.configure(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,'DIRECT',0,'Synthetic direct native policy',*args)
    select_assistance(c,2,event,strategy=r.strategy_id)
    data,fingerprint,_,_=svc.candidate(c,r.tenant_id,r.strategy_id,instrument)
    count=c.scalar(select(func.count()).select_from(m.trade))
    with pytest.raises(PermissionError):svc.post(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,instrument,fingerprint,str(uuid4()))
    assert c.scalar(select(func.count()).select_from(m.trade))==count
    prepared=svc.prepare(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,instrument,fingerprint)
    key=str(uuid4())
    posted=svc.post(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,instrument,fingerprint,key,proposal_id=prepared['proposalId'])
    assert posted['trade_ids']
    change(c,0)
    replay=svc.post(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,instrument,fingerprint,key,proposal_id=prepared['proposalId'])
    assert replay['trade_ids']==posted['trade_ids']
    assert c.scalar(select(func.count()).select_from(m.trade))==count+len(posted['trade_ids'])
    svc.cancel(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,posted['posting_id'],'Synthetic cancellation after downgrade',str(uuid4()))
