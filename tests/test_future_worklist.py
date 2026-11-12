"""Real approved futures and immutable ledger; notifications never post."""
from datetime import date,datetime,timezone
from decimal import Decimal
from uuid import UUID,uuid4
import pytest
from sqlalchemy import select,func
from tests.test_product_booking_api import future
from tests.test_future_measure_inputs import future_inputs
from tests.test_valuation_service import valued
from tests.test_lifecycle_worklist import read
from tests.test_lifecycle_assistance import configure
from tests.test_lifecycle_entitlements import change
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids


def enabled(future_inputs):
 c,r,_,_,execute=future_inputs
 change(c,3);configure(c,1,event='FUTURE_EXPIRY',strategy=r.strategy_id)
 node=c.scalar(select(m.future_terms.c.instrument_node_id).where(m.future_terms.c.instrument_node_id.in_(select(m.listing.c.instrument_node_id).where(m.listing.c.listing_node_id.in_(select(m.trade.c.trade_subject_reference_node_id).where(m.trade.c.strategy_id==r.strategy_id))))))
 return c,r,node,execute


def events(c,r,**kw):return read(c,r,eventType='FUTURE_EXPIRY',fromDate=date(2026,1,1),toDate=date(2028,12,31),**kw)


def test_future_selection_is_explicit_and_financial_processing_denied(future_inputs):
 from lifecycle.assistance import assistance_view,require_assistance,current_assistance_proof
 c,r,*_=future_inputs;change(c,3);configure(c,0,strategy=r.strategy_id)
 assert events(c,r)['total']==0
 view=configure(c,1,event='FUTURE_EXPIRY',strategy=r.strategy_id)
 assert view['availableTiers']==[0,1] and not view['handlerSupported'] and view['notificationDiscoveryAvailable']
 assert all(not op['allowed'] for op in view['operations'].values())
 with pytest.raises(ValueError,match='notifications-only'):configure(c,2,event='FUTURE_EXPIRY',strategy=r.strategy_id)
 with pytest.raises(PermissionError):require_assistance(c,r.tenant_id,ids['demo_user_account'],r.strategy_id,'FUTURE_EXPIRY','DIRECT')
 with pytest.raises(PermissionError):current_assistance_proof(c,r.tenant_id,r.strategy_id,'FUTURE_EXPIRY')


def test_sourced_events_and_inspection_do_not_change_financial_state(future_inputs):
 from lifecycle.worklist_futures import inspect_future
 from lifecycle.worklist_contracts import WorklistResponse,FutureInspection
 c,r,node,_=enabled(future_inputs)
 tables=[m.trade,m.cash_balance,m.bond_redemption_proposal,m.fx_maturity_posting,m.access_audit_event]
 counts=lambda:tuple(c.scalar(select(func.count()).select_from(t)) for t in tables)
 before=counts();result=WorklistResponse.model_validate(events(c,r))
 assert result.total>=2 and all(row.instrumentType=='FUTURE' for row in result.items)
 assert {'LAST_TRADE','FINAL_SETTLEMENT'}<={row.milestoneKind for row in result.items}
 assert all(Decimal(row.quantities[0].netQuantity)==10 for row in result.items)
 row=result.items[0]
 view=FutureInspection.model_validate(inspect_future(c,r.tenant_id,ids['demo_user_account'],r.strategy_id,node,row.milestoneKind))
 assert view.eventKey==row.eventKey and view.sourceFingerprint==row.sourceFingerprint
 assert view.quantityUnit=='CONTRACTS' and view.monetaryMultiplier=='5' and view.firstNoticeDate is None
 assert view.sourceReference=='Synthetic exchange specification' and view.financialTreatment=='NOT_ASSESSED'
 assert counts()==before
 assert events(c,r,q='no such future')['total']==0
 assert events(c,r,instrumentId=node)['total']==result.total
 assert events(c,r,q=str(node).upper())['total']==result.total
 assert events(c,r,q='%')['total']==0
 assert events(c,r,offset=25)['items']==[] and events(c,r,offset=25)['total']==result.total
 assert sum(result.statusCounts.values())==result.total


def test_fully_closed_future_disappears_and_short_remains(future_inputs):
 c,r,node,execute=enabled(future_inputs)
 execute('SELL','10');assert events(c,r)['total']==0
 execute('SELL','3');rows=events(c,r)['items']
 assert rows and all(Decimal(row['quantities'][0]['netQuantity'])==-3 for row in rows)


def test_unknown_booking_evidence_is_blocked_not_zero(future_inputs):
 c,r,node,_=enabled(future_inputs)
 original=dict(c.execute(select(m.trade).where(m.trade.c.strategy_id==r.strategy_id,m.trade.c.quantity_unit=='CONTRACTS')).mappings().one())
 c.execute(m.trade.insert().values(**(original|dict(trade_id=uuid4()))))
 rows=events(c,r)['items'];assert rows and all(row['status']=='BLOCKED' and not row['positionAssessed'] and row['remainingEntries'] is None for row in rows)


def test_subscription_downgrade_does_not_offer_future_preparation(future_inputs):
 from lifecycle.assistance_transitions import preview_assistance_transition
 from lifecycle.entitlements import lifecycle_subscription_view
 c,r,node,_=enabled(future_inputs)
 request=dict(proposedMaximumTier=2,expectedSubscriptionRevision=lifecycle_subscription_view(c,r.tenant_id)['revision'],scope='SELECTED',targets=[(r.strategy_id,'FUTURE_EXPIRY')],replacement='HIGHEST_AVAILABLE')
 view=preview_assistance_transition(c,r.tenant_id,ids['demo_user_account'],request)
 assert view['items'][0]['afterTier']==1 and view['changedCount']==0
 with pytest.raises(ValueError,match='support level'):preview_assistance_transition(c,r.tenant_id,ids['demo_user_account'],request|dict(scope='ALL_CONFIGURED',targets=[],replacement='EXPLICIT',targetTier=2))


def test_inspection_rechecks_scope_and_notification_selection(future_inputs):
 from lifecycle.worklist_futures import inspect_future
 c,r,node,_=enabled(future_inputs)
 with pytest.raises(PermissionError):inspect_future(c,ids['second_tenant'],ids['demo_user_account'],r.strategy_id,node,'LAST_TRADE')
 configure(c,0,event='FUTURE_EXPIRY',strategy=r.strategy_id)
 assert events(c,r)['total']==0
 with pytest.raises(LookupError):inspect_future(c,r.tenant_id,ids['demo_user_account'],r.strategy_id,node,'LAST_TRADE')


def test_distinct_allocations_survive_aggregate_zero(future_inputs):
 from tests.test_lifecycle_allocation_store import field
 from tests.profile_fixtures import configure_allocation,allocation_policy
 c,r,node,_=enabled(future_inputs)
 original=dict(c.execute(select(m.trade).where(m.trade.c.strategy_id==r.strategy_id,m.trade.c.quantity_unit=='CONTRACTS')).mappings().one())
 second=uuid4();c.execute(m.trade.insert().values(**(original|dict(trade_id=second,quantity=-original['quantity']))))
 event=dict(c.execute(select(m.trade_lifecycle_event).where(m.trade_lifecycle_event.c.trade_id==original['trade_id'])).mappings().one())
 c.execute(m.trade_lifecycle_event.insert().values(**(event|dict(trade_id=second,trade_lifecycle_event_id=uuid4()))))
 dimension=field(c,r.tenant_id)
 for identity,value in [(original['trade_id'],'alpha'),(second,'beta')]:c.execute(m.trade_property_value.insert().values(trade_id=identity,definition_id=dimension,tenant_id=r.tenant_id,value=value))
 configure_allocation(c,r.tenant_id,ids['demo_user_account'],r.strategy_id,[dict(definitionId=str(dimension),behavior='ALLOCATION')],allocation_policy(c,r.tenant_id,r.strategy_id).revision,'Retain opposing contract allocations')
 rows=events(c,r)['items'];assert rows and all(row['remainingEntries']==2 for row in rows)
 assert all(Decimal(row['quantities'][0]['netQuantity'])==0 and Decimal(row['quantities'][0]['grossQuantity'])==20 for row in rows)


def test_earlier_open_deadlines_are_opt_in_and_filters_precede_counts(future_inputs):
 from lifecycle.worklist import list_worklist
 from lifecycle.worklist_contracts import WorklistQuery
 c,r,node,_=enabled(future_inputs)
 now=datetime(2027,3,20,tzinfo=timezone.utc)
 query=WorklistQuery(fromDate='2027-03-21',toDate='2027-03-23',strategyId=r.strategy_id,eventType='FUTURE_EXPIRY',includeEarlierOverdue=False)
 assert list_worklist(c,r.tenant_id,ids['demo_user_account'],query,now=now)['total']==0
 result=list_worklist(c,r.tenant_id,ids['demo_user_account'],query.model_copy(update={'includeEarlierOverdue':True}),now=now)
 assert result['total']>=2 and all(row['status']=='OVERDUE' for row in result['items'])
 assert list_worklist(c,r.tenant_id,ids['demo_user_account'],query.model_copy(update={'includeEarlierOverdue':True,'attention':'INFORMATION'}),now=now)['total']==0


def test_reference_source_changes_are_identified_and_conflicts_block(future_inputs):
 from lifecycle.worklist_futures import inspect_future
 c,r,node,_=enabled(future_inputs)
 row=events(c,r)['items'][0]
 c.execute(m.instrument_dates.update().where(m.instrument_dates.c.instrument_node_id==node).values(expiry_date=date(2027,3,20)))
 view=inspect_future(c,r.tenant_id,ids['demo_user_account'],r.strategy_id,node,row['milestoneKind'])
 assert view['sourceFingerprint']!=row['sourceFingerprint']
 c.execute(m.instrument_dates.update().where(m.instrument_dates.c.instrument_node_id==node).values(last_trading_date=date(2027,3,18)))
 assert all(row['status']=='BLOCKED' and row['positionAssessed'] for row in events(c,r)['items'])


from tests.test_linear_futures_api import linear_future
from tests.test_linear_futures_pnl_integration import linear_inputs


def test_cash_and_physical_crypto_milestones_preserve_contract_units(linear_inputs):
 from lifecycle.worklist_futures import inspect_future
 c,r,f,_,_,_=linear_inputs
 change(c,3);configure(c,1,event='FUTURE_EXPIRY',strategy=r.strategy_id)
 rows=events(c,r)['items'];assert rows and all(Decimal(row['quantities'][0]['netQuantity'])==2 for row in rows)
 kinds={row['milestoneKind'] for row in rows}
 assert ('DELIVERY_START' in kinds)==(f['settlement']=='PHYSICAL')
 view=inspect_future(c,r.tenant_id,ids['demo_user_account'],r.strategy_id,UUID(f['node']),'LAST_TRADE')
 assert view['settlementMethod']==f['settlement'] and Decimal(view['monetaryMultiplier'])==Decimal(f['size'])


def test_cancelled_future_booking_is_not_rediscovered(future_inputs):
 c,r,node,_=enabled(future_inputs)
 original=dict(c.execute(select(m.trade_lifecycle_event).where(m.trade_lifecycle_event.c.trade_id.in_(select(m.trade.c.trade_id).where(m.trade.c.strategy_id==r.strategy_id,m.trade.c.quantity_unit=='CONTRACTS')))).mappings().one())
 c.execute(m.trade_lifecycle_event.insert().values(**(original|dict(trade_lifecycle_event_id=uuid4(),sequence_no=2,event_type='CANCELLED',event_payload='{}'))))
 assert events(c,r)['total']==0


def test_read_only_actor_sees_only_its_selected_strategy(future_inputs):
 from security_master_schema import access_management as am
 from lifecycle.worklist import list_worklist
 from lifecycle.worklist_contracts import WorklistQuery
 from lifecycle.worklist_futures import inspect_future
 c,r,node,_=enabled(future_inputs)
 actor=am.add_user(c,r.tenant_id,ids['demo_user_account'],name='Synthetic future notification reader')
 group=am.save_group(c,r.tenant_id,ids['demo_user_account'],code='FUT_READ_'+uuid4().hex,name='Selected strategy only',actions=['LIFECYCLE_READ'],scope_mode='SELECTED',strategy_ids=[r.strategy_id])
 am.set_user_groups(c,r.tenant_id,ids['demo_user_account'],actor,[group])
 query=WorklistQuery(fromDate='2026-01-01',toDate='2028-12-31',eventType='FUTURE_EXPIRY')
 rows=list_worklist(c,r.tenant_id,actor,query)['items'];assert rows and all(row['strategyId']==r.strategy_id for row in rows)
 assert inspect_future(c,r.tenant_id,actor,r.strategy_id,node,'LAST_TRADE')['positionAssessed']
 with pytest.raises(PermissionError):list_worklist(c,r.tenant_id,actor,query.model_copy(update={'strategyId':ids['uk_fund_strategy']}))


def test_futures_database_constraint_cannot_store_unsupported_preparation_tier(future_inputs):
 from sqlalchemy.exc import IntegrityError
 c,r,node,_=enabled(future_inputs)
 source=dict(c.execute(select(m.strategy_lifecycle_assistance).where(m.strategy_lifecycle_assistance.c.strategy_id==r.strategy_id,m.strategy_lifecycle_assistance.c.event_type=='FUTURE_EXPIRY')).mappings().one())
 with pytest.raises(IntegrityError),c.begin_nested():
  c.execute(m.strategy_lifecycle_assistance.insert().values(**(source|dict(selected_tier=2,revision=2,previous_revision=1))))


def test_full_future_population_is_paged_after_relevance_and_status(future_inputs):
 from tests.profile_fixtures import assign
 from lifecycle.assistance import append_selection
 c,r,node,_=enabled(future_inputs)
 strategy=dict(c.execute(select(m.strategy).where(m.strategy.c.strategy_id==r.strategy_id)).mappings().one())
 booking=dict(c.execute(select(m.trade).where(m.trade.c.strategy_id==r.strategy_id,m.trade.c.quantity_unit=='CONTRACTS')).mappings().one())
 for number in range(26):
  target=uuid4()
  c.execute(m.strategy.insert().values(**(strategy|dict(strategy_id=target,strategy_code='FUT_PAGE_'+target.hex,display_name=f'Future page {number:02d}'))))
  assign(c,r.tenant_id,ids['demo_user_account'],target)
  # Use the native writer so every synthetic strategy retains its own
  # correct profile assignment and immutable BOOKED proof.
  from apps.reference_api.product_booking import load_context,book
  from apps.reference_api.product_booking_contracts import ProductBookingRequest
  context=load_context(c,r.tenant_id,node,booking['trade_subject_reference_node_id'],date(2026,10,1))
  request=ProductBookingRequest.model_validate(dict(instrumentId=str(node),listingId=str(booking['trade_subject_reference_node_id']),strategyId=str(target),executionRoute='LISTED',side='BUY',quantity='10',executionPrice='6000',tradeDatetime='2026-10-01T10:00:00Z',positionEffect='OPEN',expectedTermsFingerprint=context.terms_fingerprint))
  book(c,r.tenant_id,ids['demo_user_account'],request,str(uuid4()),'FUTURE','future-pagination')
  append_selection(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],target,'FUTURE_EXPIRY',1,0,'Synthetic full-history page')
 from lifecycle.worklist import list_worklist
 from lifecycle.worklist_contracts import WorklistQuery
 query=WorklistQuery(fromDate='2027-03-19',toDate='2027-03-19',eventType='FUTURE_EXPIRY',limit=25)
 result=list_worklist(c,r.tenant_id,ids['demo_user_account'],query)
 assert result['total']>=54 and len(result['items'])==25 and sum(result['statusCounts'].values())==result['total']
 later=list_worklist(c,r.tenant_id,ids['demo_user_account'],query.model_copy(update={'offset':25}))
 assert later['total']==result['total'] and len(later['items'])==25
 assert not {r['eventKey'] for r in later['items']} & {r['eventKey'] for r in result['items']}
 assert list_worklist(c,r.tenant_id,ids['demo_user_account'],query.model_copy(update={'attention':'ACTIONABLE'}))['total']==0
