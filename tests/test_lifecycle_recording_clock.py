"""Current lifecycle reads must agree with persisted ledger recording time."""
from datetime import datetime,timedelta,timezone
from uuid import uuid4,UUID
import pytest
from sqlalchemy import select,func
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from tests.test_valuation_service import valued

@pytest.mark.parametrize('family',['bond','fx'])
def test_post_sees_own_writes_when_application_clock_is_behind_database(valued,monkeypatch,family):
 c,r,trade=valued
 if family=='bond':
  from lifecycle import bond_service as svc
  from tests.test_bond_redemption_service import setup
  setup(c,r,trade);instrument=ids['bond_instrument_node']
  svc.configure(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,'DIRECT',0,'Clock regression')
 else:
  from lifecycle import fx_service as svc
  from tests.test_fx_maturity_service import setup
  instrument,_,cut,_=setup(c,r)
  svc.configure(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,'DIRECT',0,'Clock regression',r.policy_id,cut)
 class Behind(datetime):
  @classmethod
  def now(cls,tz=None):return datetime.now(tz)-timedelta(seconds=5)
 monkeypatch.setattr(svc,'datetime',Behind)
 _,fingerprint,_,_=svc.candidate(c,r.tenant_id,r.strategy_id,instrument)
 key=str(uuid4());before=c.scalar(select(func.count()).select_from(m.trade))
 posted=svc.post(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,instrument,fingerprint,key)
 assert len(posted['trade_ids'])==1 and c.scalar(select(func.count()).select_from(m.trade))==before+1
 assert svc.post(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,instrument,fingerprint,key)['trade_ids']==posted['trade_ids']
 with pytest.raises(svc.RedemptionConflict):svc.candidate(c,r.tenant_id,r.strategy_id,instrument)
 if family=='bond':
  from lifecycle import worklist
  from lifecycle.worklist_contracts import WorklistQuery
  monkeypatch.setattr(worklist,'datetime',Behind)
  result=worklist.list_worklist(c,r.tenant_id,ids['demo_user_account'],WorklistQuery(fromDate=r.closing_cutoff.date(),toDate=datetime.now(timezone.utc).date(),strategyId=r.strategy_id))
  assert result['items'][0]['status']=='BOOKED' and result['items'][0]['quantities']==[]
