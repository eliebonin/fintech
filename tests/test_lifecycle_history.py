"""Scoped instrument history keeps cancellation evidence before count/page."""
from uuid import uuid4
import pytest
from sqlalchemy import select,func
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from tests.test_valuation_service import valued
from lifecycle.history import instrument_history_clause

@pytest.mark.parametrize('family',['bond_redemption','fx_maturity'])
def test_history_filter_keeps_only_the_instrument_and_its_own_cancellations(valued,family):
 c,r,_=valued;t=getattr(m,family+'_posting');p=getattr(m,family+'_proposal')
 own,other,foreign=uuid4(),uuid4(),uuid4();instrument=ids['bond_instrument_node']
 common=dict(tenant_id=r.tenant_id,strategy_id=r.strategy_id,request_hash='a'*64,trade_ids=[],actor_id=ids['demo_user_account'],real_operator_id=ids['demo_user_account'])
 def posting(identity,evidence,**changes):
  c.execute(t.insert().values(**(common|dict(posting_id=identity,request_key=str(identity),evidence=evidence)|changes)))
 posting(own,dict(instrumentId=str(instrument)))
 posting(other,dict(instrumentId=str(ids['hsbc_instrument_node'])))
 posting(foreign,dict(instrumentId=str(instrument)),strategy_id=ids['strategy'])
 cancellation=uuid4();posting(cancellation,dict(operation='CANCEL',originalPostingId=str(own)))
 posting(uuid4(),dict(operation='CANCEL',originalPostingId=str(other)))
 posting(uuid4(),dict(operation='CANCEL',originalPostingId=str(foreign)))
 where=(t.c.tenant_id==r.tenant_id)&(t.c.strategy_id==r.strategy_id)&instrument_history_clause(t,r.tenant_id,r.strategy_id,instrument)
 assert c.scalar(select(func.count()).select_from(t).where(where))==2
 assert set(c.scalars(select(t.c.posting_id).where(where)))=={own,cancellation}
 assert len(list(c.scalars(select(t.c.posting_id).where(where).order_by(t.c.posting_id).offset(1).limit(1))))==1
 for node in [ids['hsbc_instrument_node']]*26+[instrument]:
  c.execute(p.insert().values(tenant_id=r.tenant_id,strategy_id=r.strategy_id,instrument_id=node,input_hash='a'*64,inputs={},policy_revision=0,mode='REVIEW',prepared_by=ids['demo_user_account'],prepared_operator=ids['demo_user_account']))
 scope=(p.c.tenant_id==r.tenant_id)&(p.c.strategy_id==r.strategy_id)&instrument_history_clause(p,r.tenant_id,r.strategy_id,instrument,proposals=True)
 assert c.scalar(select(func.count()).select_from(p).where(scope))==1
 assert len(list(c.scalars(select(p.c.proposal_id).where(scope).offset(1).limit(25))))==0
