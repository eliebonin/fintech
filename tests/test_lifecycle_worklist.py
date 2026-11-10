"""Derived Ops events reuse existing native positions and never write on read."""
from datetime import date,timedelta
import pytest

@pytest.mark.parametrize('days,entries,known,posted,prepared,stale,blocked,status,attention',[
 (2,1,True,False,False,False,False,'UPCOMING','INFORMATION'),
 (0,1,True,False,False,False,False,'DUE','ACTIONABLE'),
 (-2,1,True,False,False,False,False,'OVERDUE','ACTIONABLE'),
 (-2,0,True,True,False,False,False,'BOOKED','INFORMATION'),
 (-2,0,True,True,False,False,True,'BOOKED','INFORMATION'),
 (-2,2,True,True,False,False,False,'REASSESSMENT','ACTIONABLE'),
 (-2,1,True,False,True,False,False,'PREPARED','ACTIONABLE'),
 (-2,1,True,False,True,True,False,'REASSESSMENT','ACTIONABLE'),
 (-2,0,False,False,False,False,False,'BLOCKED','ACTIONABLE'),
 (-2,2,True,False,False,False,True,'BLOCKED','ACTIONABLE'),
 (2,1,True,False,False,False,True,'BLOCKED','INFORMATION'),
])
def test_state_never_confuses_date_exposure_and_booking(days,entries,known,posted,prepared,stale,blocked,status,attention):
 from lifecycle.worklist import event_state
 today=date(2026,11,5)
 assert event_state(today+timedelta(days=days),today,entries,known=known,posted=posted,prepared=prepared,stale=stale,blocked=blocked)==(status,attention)


def test_query_rejects_inverted_dates_and_unbounded_page():
 from lifecycle.worklist_contracts import WorklistQuery
 from pydantic import ValidationError
 with pytest.raises(ValidationError):WorklistQuery(fromDate='2026-11-06',toDate='2026-11-05')
 with pytest.raises(ValidationError):WorklistQuery(fromDate='2026-11-05',toDate='2026-11-06',limit=1001)


from tests.test_valuation_service import valued
from tests.test_bond_redemption_service import setup as bond_setup
from security_master_schema.demo_data import DEMO_IDS as ids
from security_master_schema import models as m
from sqlalchemy import select,func
from datetime import datetime,timezone
from uuid import uuid4


def read(c,r,**changes):
 from lifecycle.worklist import list_worklist
 from lifecycle.worklist_contracts import WorklistQuery
 values=dict(fromDate=r.closing_cutoff.date()-timedelta(days=1),toDate=datetime.now(timezone.utc).date()+timedelta(days=30),strategyId=r.strategy_id,includeEarlierOverdue=False)
 values.update(changes)
 return list_worklist(c,r.tenant_id,ids['demo_user_account'],WorklistQuery(**values))


def test_read_only_due_discovery_retains_exact_exposure_and_scope(valued):
 from lifecycle.worklist import list_worklist
 from lifecycle.worklist_contracts import WorklistQuery,WorklistResponse
 c,r,trade=valued;bond_setup(c,r,trade)
 count=c.scalar(select(func.count()).select_from(m.trade))
 audit=c.scalar(select(func.count()).select_from(m.access_audit_event))
 first=WorklistResponse.model_validate(read(c,r));second=read(c,r)
 assert first.total==1 and first.items[0].eventKey==second['items'][0]['eventKey']
 row=first.items[0]
 assert row.status=='OVERDUE' and row.remainingEntries==1
 assert row.quantities[0].netQuantity=='100000.000000000000'
 assert row.attention=='ACTIONABLE' and str(r.strategy_id) in row.actionHref and str(ids['bond_instrument_node']) in row.actionHref
 assert c.scalar(select(func.count()).select_from(m.trade))==count
 assert c.scalar(select(func.count()).select_from(m.access_audit_event))==audit
 with pytest.raises(PermissionError):list_worklist(c,ids['second_tenant'],ids['demo_user_account'],WorklistQuery(fromDate=r.closing_cutoff.date(),toDate=r.closing_cutoff.date(),strategyId=r.strategy_id))


def test_notifications_tier_does_not_use_paid_preparation_and_zero_selection_hides_event(valued):
 from tests.test_lifecycle_assistance import configure
 from tests.test_lifecycle_entitlements import change
 c,r,trade=valued;bond_setup(c,r,trade)
 configure(c,1,strategy=r.strategy_id)
 row=read(c,r)['items'][0]
 assert row['selectedTier']==1 and row['actionLabel']=='Handle manually'
 assert read(c,r,status='UPCOMING')['total']==0
 assert read(c,r,attention='INFORMATION')['total']==0
 configure(c,0,strategy=r.strategy_id)
 inactive=read(c,r)
 assert inactive['total']==0 and 'not enabled for this strategy' in inactive['unavailableReason']
 configure(c,3,strategy=r.strategy_id);change(c,1)
 assert read(c,r)['items'][0]['status']=='BLOCKED'
 change(c,0)
 result=read(c,r)
 assert result['total']==0 and 'subscription' in result['unavailableReason']


def test_prepared_posted_and_cancelled_history_is_reassessed_without_writes(valued):
 from lifecycle import bond_service as svc
 from tests.test_lifecycle_assistance import configure
 c,r,trade=valued;bond_setup(c,r,trade)
 svc.configure(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,'MANUAL',0,'Explicit confirmation path')
 data,fingerprint,_,_=svc.candidate(c,r.tenant_id,r.strategy_id,ids['bond_instrument_node'])
 proposal=svc.prepare(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,ids['bond_instrument_node'],fingerprint)
 assert read(c,r)['items'][0]['status']=='PREPARED'
 configure(c,2,strategy=r.strategy_id)
 assert read(c,r)['items'][0]['status']=='REASSESSMENT'
 data,fingerprint,_,_=svc.candidate(c,r.tenant_id,r.strategy_id,ids['bond_instrument_node'])
 proposal=svc.prepare(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,ids['bond_instrument_node'],fingerprint)
 posted=svc.post(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,ids['bond_instrument_node'],fingerprint,str(uuid4()),proposal_id=proposal['proposalId'])
 result=read(c,r)
 assert result['items'][0]['status']=='BOOKED' and result['items'][0]['remainingEntries']==0
 c.execute(m.bond_terms.update().where(m.bond_terms.c.instrument_node_id==ids['bond_instrument_node']).values(redemption_amount_per_par=101))
 assert read(c,r)['items'][0]['status']=='BOOKED'
 c.execute(m.bond_terms.update().where(m.bond_terms.c.instrument_node_id==ids['bond_instrument_node']).values(redemption_amount_per_par=100))
 svc.cancel(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,posted['posting_id'],'Synthetic closure correction',str(uuid4()))
 row=read(c,r)['items'][0]
 assert row['status']!='BOOKED' and row['remainingEntries']==1
 # Cancelling the old generated closure and later closing through an ordinary
 # execution must not resurrect the cancelled receipt as a completed event.
 original=dict(c.execute(select(m.trade).where(m.trade.c.trade_id==data['movements'][0]['tradeIds'][0])).mappings().one())
 sale=uuid4();c.execute(m.trade.insert().values(**(original|dict(trade_id=sale,quantity=-original['quantity']))))
 event=dict(c.execute(select(m.trade_lifecycle_event).where(m.trade_lifecycle_event.c.trade_id==original['trade_id'],m.trade_lifecycle_event.c.event_type=='BOOKED')).mappings().one())
 c.execute(m.trade_lifecycle_event.insert().values(**(event|dict(trade_id=sale,trade_lifecycle_event_id=uuid4()))))
 assert read(c,r)['total']==0



def test_missing_evidence_is_visible_as_unassessed_not_zero(valued):
 c,r,trade=valued;_,booked,_=bond_setup(c,r,trade)
 broken=dict(c.execute(select(m.trade).where(m.trade.c.trade_id==booked)).mappings().one())
 c.execute(m.trade.insert().values(**(broken|dict(trade_id=uuid4()))))
 row=read(c,r)['items'][0]
 assert row['status']=='BLOCKED' and row['remainingEntries'] is None and row['quantities']==[]
 assert not row['positionAssessed'] and any('Position could not be assessed' in s for s in row['reasons'])


def test_changed_redemption_terms_invalidate_prepared_event(valued):
 from lifecycle import bond_service as svc
 c,r,trade=valued;bond_setup(c,r,trade)
 data,fp,_,_=svc.candidate(c,r.tenant_id,r.strategy_id,ids['bond_instrument_node'])
 svc.prepare(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,ids['bond_instrument_node'],fp)
 c.execute(m.bond_terms.update().where(m.bond_terms.c.instrument_node_id==ids['bond_instrument_node']).values(redemption_amount_per_par=101))
 assert read(c,r)['items'][0]['status']=='REASSESSMENT'


def test_future_information_and_explicit_earlier_overdue_filter(valued):
 from dataclasses import replace
 c,r,trade=valued
 future=datetime.now(timezone.utc)+timedelta(days=10)
 r=replace(r,closing_cutoff=future)
 bond_setup(c,r,trade)
 assert read(c,r)['items'][0]['status']=='UPCOMING'
 assert read(c,r,attention='ACTIONABLE')['total']==0
 assert read(c,r,fromDate=future.date()+timedelta(days=2),toDate=future.date()+timedelta(days=5),includeEarlierOverdue=True)['total']==0


def test_opposing_nonzero_allocations_do_not_disappear_at_zero_net(valued):
 import json
 from tests.test_lifecycle_allocation_store import field
 from tests.profile_fixtures import configure_allocation,allocation_policy
 c,r,trade=valued;_,booked,_=bond_setup(c,r,trade)
 original=dict(c.execute(select(m.trade).where(m.trade.c.trade_id==booked)).mappings().one())
 second=uuid4();c.execute(m.trade.insert().values(**(original|dict(trade_id=second,quantity=-original['quantity']))))
 event=dict(c.execute(select(m.trade_lifecycle_event).where(m.trade_lifecycle_event.c.trade_id==booked)).mappings().one())
 c.execute(m.trade_lifecycle_event.insert().values(**(event|dict(trade_id=second,trade_lifecycle_event_id=uuid4()))))
 dimension=field(c,r.tenant_id)
 for identity,value in [(booked,'alpha'),(second,'beta')]:c.execute(m.trade_property_value.insert().values(trade_id=identity,definition_id=dimension,tenant_id=r.tenant_id,value=value))
 configure_allocation(c,r.tenant_id,ids['demo_user_account'],r.strategy_id,[dict(definitionId=str(dimension),behavior='ALLOCATION')],allocation_policy(c,r.tenant_id,r.strategy_id).revision,'Preserve joint allocations')
 row=read(c,r)['items'][0]
 assert row['remainingEntries']==2 and row['attention']=='ACTIONABLE'
 assert __import__('decimal').Decimal(row['quantities'][0]['netQuantity'])==0
 assert __import__('decimal').Decimal(row['quantities'][0]['grossQuantity'])==200000


def test_full_scoped_population_is_filtered_before_pagination(valued):
 from security_master_schema import access_management as am
 from lifecycle.assistance import append_selection
 from tests.profile_fixtures import assign
 c,r,trade=valued;_,booked,_=bond_setup(c,r,trade)
 actor=ids['demo_user_account']
 group=am.save_group(c,r.tenant_id,actor,code='READ_'+uuid4().hex,name='Whole worklist test',actions=['LIFECYCLE_READ'],scope_mode='ALL')
 c.execute(m.access_group_member.insert().values(tenant_id=r.tenant_id,group_id=group,user_account_id=actor))
 strategy=dict(c.execute(select(m.strategy).where(m.strategy.c.strategy_id==r.strategy_id)).mappings().one())
 booking=dict(c.execute(select(m.trade).where(m.trade.c.trade_id==booked)).mappings().one())
 event=dict(c.execute(select(m.trade_lifecycle_event).where(m.trade_lifecycle_event.c.trade_id==booked)).mappings().one())
 for number in range(30):
  target,execution=uuid4(),uuid4()
  c.execute(m.strategy.insert().values(**(strategy|dict(strategy_id=target,strategy_code='WORK_'+target.hex,display_name=f'Worklist population {number:02d}'))))
  c.execute(m.trade.insert().values(**(booking|dict(trade_id=execution,strategy_id=target))))
  c.execute(m.trade_lifecycle_event.insert().values(**(event|dict(trade_id=execution,trade_lifecycle_event_id=uuid4()))))
  assign(c,r.tenant_id,actor,target)
  append_selection(c,r.tenant_id,actor,actor,target,'BOND_MATURITY',1,0,'Synthetic notifications')
 first=read(c,r,strategyId=None,limit=25)
 second=read(c,r,strategyId=None,limit=25,offset=25)
 assert first['total']==31 and len(first['items'])==25 and len(second['items'])==6
 assert first['statusCounts']['OVERDUE']==31
 assert not set(r['eventKey'] for r in first['items'])&set(r['eventKey'] for r in second['items'])
 assert read(c,r,strategyId=None,status='UPCOMING')['total']==0


def test_retired_but_owned_reference_remains_a_blocked_operational_event(valued):
 c,r,trade=valued;bond_setup(c,r,trade)
 c.execute(m.financial_reference_node.update().where(m.financial_reference_node.c.reference_node_id==ids['bond_instrument_node']).values(status='RETIRED'))
 result=read(c,r)
 assert result['total']==1 and result['items'][0]['status']=='BLOCKED'
 assert result['items'][0]['remainingEntries']==1


def test_closed_ordinary_position_is_not_an_outstanding_maturity_event(valued):
 c,r,trade=valued;_,booked,_=bond_setup(c,r,trade)
 original=dict(c.execute(select(m.trade).where(m.trade.c.trade_id==booked)).mappings().one())
 second=uuid4();c.execute(m.trade.insert().values(**(original|dict(trade_id=second,quantity=-original['quantity']))))
 event=dict(c.execute(select(m.trade_lifecycle_event).where(m.trade_lifecycle_event.c.trade_id==booked)).mappings().one())
 c.execute(m.trade_lifecycle_event.insert().values(**(event|dict(trade_id=second,trade_lifecycle_event_id=uuid4()))))
 assert read(c,r)['total']==0


def test_instrument_search_uses_names_and_identifiers_before_counts_and_page(valued):
 c,r,trade=valued;bond_setup(c,r,trade)
 node=ids['bond_instrument_node']
 c.execute(m.financial_reference_node.update().where(m.financial_reference_node.c.reference_node_id==node).values(canonical_name='Maturity search target'))
 assert read(c,r,q='search TARGET')['total']==1
 assert read(c,r,q='no matching instrument')['total']==0
 assert read(c,r,q='%')['total']==0
 identifier='GBSEARCH0001'
 scheme=c.scalar(select(m.identifier_scheme.c.identifier_scheme_id).where(m.identifier_scheme.c.scheme_code=='ISIN'))
 c.execute(m.financial_reference_identifier.insert().values(reference_node_id=node,identifier_scheme_id=scheme,identifier_value=identifier,is_primary=True))
 listing=c.scalar(select(m.listing.c.listing_node_id).where(m.listing.c.instrument_node_id==node))
 c.execute(m.financial_reference_identifier.insert().values(reference_node_id=listing,identifier_scheme_id=scheme,identifier_value='SEARCH_LISTING',is_primary=False))
 assert read(c,r,q='SEARCH_LISTING')['total']==1
 result=read(c,r,q=identifier,offset=25)
 assert result['total']==1 and result['items']==[] and result['statusCounts']['OVERDUE']==1
 assert read(c,r,q=str(node))['total']==1
