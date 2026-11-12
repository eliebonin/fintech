"""FX discovery reuses native closure evidence without financial writes."""
import pytest
from decimal import Decimal
from uuid import UUID,uuid4
from sqlalchemy import select,func
from tests.test_valuation_service import valued
from tests.test_fx_maturity_service import setup
from tests.test_lifecycle_worklist import read
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids

def test_query_accepts_all_and_explicit_forward_maturity():
 from lifecycle.worklist_contracts import WorklistQuery
 for kind in ['ALL','BOND_MATURITY','FX_FORWARD_MATURITY']:
  assert WorklistQuery(fromDate='2026-10-01',toDate='2026-12-01',eventType=kind).eventType==kind
 assert WorklistQuery(fromDate='2026-10-01',toDate='2026-12-01').eventType=='ALL'

def test_due_forward_is_exact_and_read_only(valued):
 from lifecycle.worklist_contracts import WorklistResponse
 c,r,_=valued;instrument,_,_,_=setup(c,r)
 counts=lambda:tuple(c.scalar(select(func.count()).select_from(t)) for t in [m.trade,m.fx_maturity_proposal,m.fx_maturity_posting,m.access_audit_event])
 before=counts();result=WorklistResponse.model_validate(read(c,r,eventType='FX_FORWARD_MATURITY'))
 assert result.total==1
 row=result.items[0]
 assert row.eventType=='FX_FORWARD_MATURITY' and row.instrumentType=='FX_FORWARD'
 assert row.instrumentId==instrument and row.status=='BLOCKED'
 assert row.positionAssessed and row.quantities[0].currency=='GBP'
 assert Decimal(row.quantities[0].netQuantity)==1000000
 assert 'pricing policy' in ' '.join(row.reasons).lower()
 assert 'product=fx-forward' in row.actionHref
 assert read(c,r,eventType='BOND_MATURITY')['total']==0 and counts()==before

def test_forward_prepare_book_cancel_and_source_reassessment(valued):
 from lifecycle import fx_service as svc
 c,r,_=valued;instrument,_,cut,series=setup(c,r)
 svc.configure(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,'DIRECT',0,'Synthetic direct',r.policy_id,cut)
 assert read(c,r)['items'][0]['status']=='OVERDUE'
 override=dict(rate='1.125',sourceReference='Synthetic counterparty fixing',reason='Reviewed fixing')
 _,fingerprint,_,_=svc.candidate(c,r.tenant_id,r.strategy_id,instrument,rate_override=override)
 proposal=svc.prepare(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,instrument,fingerprint,rate_override=override)
 assert read(c,r)['items'][0]['status']=='PREPARED'
 c.execute(m.market_data_observation.update().where(m.market_data_observation.c.market_data_series_id==series).values(value=Decimal('1.13')))
 assert read(c,r)['items'][0]['status']=='REASSESSMENT'
 c.execute(m.market_data_observation.update().where(m.market_data_observation.c.market_data_series_id==series).values(value=Decimal('1.12')))
 post=svc.post(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,instrument,fingerprint,str(uuid4()),proposal_id=UUID(proposal['proposalId']))
 result=read(c,r);assert result['items'][0]['status']=='BOOKED' and result['items'][0]['remainingEntries']==0
 svc.cancel(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,UUID(post['posting_id']),'Synthetic undo',str(uuid4()))
 row=read(c,r)['items'][0];assert row['status']=='OVERDUE' and row['remainingEntries']==1

def test_missing_forward_evidence_is_not_zero(valued):
 c,r,_=valued;instrument,_,_,_=setup(c,r)
 original=dict(c.execute(select(m.trade).where(m.trade.c.strategy_id==r.strategy_id,m.trade.c.trade_subject_reference_node_id==instrument)).mappings().one())
 c.execute(m.trade.insert().values(**(original|dict(trade_id=uuid4()))))
 row=read(c,r)['items'][0]
 assert row['status']=='BLOCKED' and not row['positionAssessed'] and row['remainingEntries'] is None


def test_mixed_events_filter_before_counts_and_pagination(valued):
 from tests.test_bond_redemption_service import setup as bond_setup
 c,r,trade=valued;bond_setup(c,r,trade);instrument,_,_,_=setup(c,r)
 result=read(c,r)
 assert result['total']==2 and set(row['eventType'] for row in result['items'])=={'BOND_MATURITY','FX_FORWARD_MATURITY'}
 assert read(c,r,eventType='FX_FORWARD_MATURITY',offset=25)['total']==1
 assert read(c,r,eventType='FX_FORWARD_MATURITY',offset=25)['items']==[]
 assert read(c,r,instrumentId=instrument)['total']==1
 assert read(c,r,q='nonexistent instrument')['total']==0
 assert sum(result['statusCounts'].values())==2

def test_forward_notifications_tiers_and_tenant_scope(valued):
 import pytest
 from lifecycle.worklist import list_worklist
 from lifecycle.worklist_contracts import WorklistQuery
 from tests.test_lifecycle_assistance import configure
 c,r,_=valued;setup(c,r)
 configure(c,1,event='FX_FORWARD_MATURITY',strategy=r.strategy_id)
 row=read(c,r)['items'][0]
 assert row['status']=='OVERDUE' and row['selectedTier']==1 and row['actionLabel']=='Handle manually'
 configure(c,0,event='FX_FORWARD_MATURITY',strategy=r.strategy_id)
 assert read(c,r,eventType='FX_FORWARD_MATURITY')['total']==0
 with pytest.raises(PermissionError):
  list_worklist(c,ids['second_tenant'],ids['demo_user_account'],WorklistQuery(fromDate='2026-10-01',toDate='2026-12-01',eventType='FX_FORWARD_MATURITY',strategyId=r.strategy_id))

def test_forward_partial_close_and_opposing_allocations(valued):
 from apps.reference_api.fx_forward_booking import book_fx_forward_trade,load_fx_forward_booking_terms
 from apps.reference_api.contracts import FxForwardBookingRequest
 from security_master_schema.fx_forward_booking import fx_forward_terms_fingerprint
 from tests.test_lifecycle_allocation_store import field
 from tests.profile_fixtures import configure_allocation,allocation_policy
 from datetime import date
 c,r,_=valued;instrument,_,_,_=setup(c,r)
 first=c.scalar(select(m.trade.c.trade_id).where(m.trade.c.strategy_id==r.strategy_id,m.trade.c.trade_subject_reference_node_id==instrument))
 terms=load_fx_forward_booking_terms(c,r.tenant_id,instrument,as_of=date(2026,9,30))
 request=FxForwardBookingRequest.model_validate(dict(instrumentId=str(instrument),strategyId=str(r.strategy_id),side='SELL',quantity='250000',tradeDatetime='2026-09-30T11:00:00Z',counterpartyOrganisationId=str(ids['bank_a_organisation']),expectedTermsFingerprint=fx_forward_terms_fingerprint(terms)))
 book_fx_forward_trade(c,r.tenant_id,ids['demo_user_account'],request,str(uuid4()),'Synthetic partial close')
 assert Decimal(read(c,r)['items'][0]['quantities'][0]['netQuantity'])==750000
 request=request.model_copy(update={'quantity':Decimal('750000')})
 book_fx_forward_trade(c,r.tenant_id,ids['demo_user_account'],request,str(uuid4()),'Synthetic opposing allocation')
 assert read(c,r)['total']==0
 dimension=field(c,r.tenant_id)
 trades=c.scalars(select(m.trade.c.trade_id).where(m.trade.c.strategy_id==r.strategy_id,m.trade.c.trade_subject_reference_node_id==instrument)).all()
 for identity in trades:c.execute(m.trade_property_value.insert().values(trade_id=identity,definition_id=dimension,tenant_id=r.tenant_id,value='first' if identity==first else 'second'))
 configure_allocation(c,r.tenant_id,ids['demo_user_account'],r.strategy_id,[dict(definitionId=str(dimension),behavior='ALLOCATION')],allocation_policy(c,r.tenant_id,r.strategy_id).revision,'Synthetic allocation preservation')
 row=read(c,r)['items'][0]
 assert row['remainingEntries']==2 and Decimal(row['quantities'][0]['netQuantity'])==0 and Decimal(row['quantities'][0]['grossQuantity'])==2000000


@pytest.mark.parametrize('family',['bond','fx'])
def test_prepared_standard_fields_survive_reassessment_and_confirmation(valued,family):
 from trading.profiles.contracts import standard_input_id
 c,r,trade=valued
 if family=='fx':
  from lifecycle import fx_service as svc
  instrument,_,cut,_=setup(c,r)
  svc.configure(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,'DIRECT',0,'Synthetic direct',r.policy_id,cut)
 else:
  from lifecycle import bond_service as svc
  from tests.test_bond_redemption_service import setup as bond_setup
  bond_setup(c,r,trade);instrument=ids['bond_instrument_node']
  svc.configure(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,'DIRECT',0,'Synthetic direct')
 data,_,_,_=svc.candidate(c,r.tenant_id,r.strategy_id,instrument)
 annotations={data['movements'][0]['movementKey']:[dict(definitionId=str(standard_input_id('COMMENT')),value='Ops retained maturity note')]}
 _,fp,_,_=svc.candidate(c,r.tenant_id,r.strategy_id,instrument,annotation_inputs=annotations)
 prepared=svc.prepare(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,instrument,fp,annotation_inputs=annotations)
 row=read(c,r)['items'][0]
 assert row['status']=='PREPARED',row['reasons']
 posted=svc.post(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,instrument,fp,str(uuid4()),proposal_id=UUID(prepared['proposalId']))
 assert c.scalar(select(m.trade.c.comment).where(m.trade.c.trade_id==UUID(posted['trade_ids'][0])))=='Ops retained maturity note'


def test_post_maturity_execution_is_explicitly_blocked(valued):
 from datetime import timedelta
 c,r,_=valued;instrument,_,_,_=setup(c,r)
 original=dict(c.execute(select(m.trade).where(m.trade.c.strategy_id==r.strategy_id,m.trade.c.trade_subject_reference_node_id==instrument)).mappings().one())
 c.execute(m.trade.insert().values(**(original|dict(trade_id=uuid4(),trade_datetime_utc=r.closing_cutoff+timedelta(days=1),valuation_effective_date=(r.closing_cutoff+timedelta(days=1)).date(),settlement_date=None))))
 row=read(c,r)['items'][0]
 assert row['status']=='BLOCKED' and not row['positionAssessed']
 assert 'after maturity' in ' '.join(row['reasons'])

def test_future_forward_is_information_without_selecting_a_rate(valued):
 from datetime import datetime,timezone,timedelta
 from dataclasses import replace
 from tests.test_lifecycle_assistance import configure
 c,r,_=valued;r=replace(r,closing_cutoff=datetime.now(timezone.utc)+timedelta(days=10))
 setup(c,r);configure(c,1,event='FX_FORWARD_MATURITY',strategy=r.strategy_id)
 row=read(c,r)['items'][0]
 assert row['status']=='UPCOMING' and row['attention']=='INFORMATION'
 assert read(c,r,attention='ACTIONABLE')['total']==0
