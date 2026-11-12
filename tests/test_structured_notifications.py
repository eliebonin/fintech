"""Sourced structured schedules are information, never outcome or booking tasks."""
from datetime import date,datetime,timezone
from decimal import Decimal
from uuid import UUID,uuid4
import pytest
from sqlalchemy import select,func
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from tests.test_product_booking_api import structured
from tests.test_valuation_service import valued
from tests.test_lifecycle_assistance import configure
from tests.test_lifecycle_entitlements import change
from tests.test_generic_swap_booking_api import create_swap


@pytest.fixture(scope='module')
def note_swap(structured):return UUID(create_swap(reference=UUID(structured),maturityDate='2029-08-28'))


@pytest.fixture
def notes(structured,note_swap,valued):
 from apps.reference_api.product_booking import book,load_context
 from apps.reference_api.product_booking_contracts import ProductBookingRequest
 c,r,_=valued;node=UUID(structured);actor=ids['demo_user_account']
 terms=c.scalar(select(m.structured_product_terms.c.structured_product_terms_id).where(m.structured_product_terms.c.instrument_node_id==node,m.structured_product_terms.c.is_current))
 c.execute(m.structured_product_terms.update().where(m.structured_product_terms.c.structured_product_terms_id==terms).values(first_autocall_observation_date=date(2026,10,2)))
 created=[]
 for number,(purpose,day) in enumerate([('COUPON_OBSERVATION',date(2026,10,1)),('AUTOCALL_OBSERVATION',date(2026,10,2)),('FINAL_VALUATION',date(2029,8,24))],1):
  schedule,event,group=uuid4(),uuid4(),uuid4()
  c.execute(m.schedule.insert().values(schedule_id=schedule,owner_reference_node_id=node,schedule_type=purpose,status='ACTIVE'))
  c.execute(m.schedule_event.insert().values(schedule_event_id=event,schedule_id=schedule,event_sequence=1,event_type='OBSERVATION',event_date=day,payment_date=date(2026,10,5) if number<3 else date(2029,8,28),status='SCHEDULED'))
  c.execute(m.structured_product_condition_group.insert().values(condition_group_id=group,structured_product_terms_id=terms,group_code='TEST_'+str(number),observation_style='DISCRETE',schedule_event_id=event,logical_operator='ALL',underlying_aggregation='SINGLE',underlying_scope='SINGLE',evaluation_sequence=1,status='VALIDATED'))
  c.execute(m.barrier_rule.insert().values(condition_group_id=group,owner_reference_node_id=node,underlying_reference_node_id=ids['hsbc_instrument_node'],condition_sequence=1,comparison_operator='GE',level_reference_type='ABSOLUTE',lower_level_value=Decimal('100'),underlying_measure='LEVEL',status='VALIDATED'))
  if number==2:c.execute(m.condition_group_action.insert().values(condition_group_id=group,action_type='REDEEM_PARENT',target_scope='PARENT',target_reference_node_id=node,execution_sequence=1,status='VALIDATED'))
  created.append(event)
 def execute(root=node,side='BUY',quantity='100000',day='2026-09-30',strategy=None):
  context=load_context(c,r.tenant_id,root,None,date.fromisoformat(day))
  kind='STRUCTURED_PRODUCT' if root==node else 'SWAP'
  payload=ProductBookingRequest.model_validate(dict(instrumentId=str(root),strategyId=str(strategy or r.strategy_id),executionRoute='OTC',side=side,quantity=quantity,executionPrice='98' if kind=='STRUCTURED_PRODUCT' else '0',tradeDatetime=day+'T10:00:00Z',settlementDate='2026-10-05' if kind=='STRUCTURED_PRODUCT' else None,counterpartyOrganisationId=str(ids['bank_a_organisation']),expectedTermsFingerprint=context.terms_fingerprint))
  return book(c,r.tenant_id,actor,payload,str(uuid4()),kind,'structured-notification-test').data.trade.trade_id
 trade=execute();change(c,3);configure(c,1,event='STRUCTURED_OBSERVATION',strategy=r.strategy_id)
 return c,r,node,note_swap,trade,created,execute


def read(c,r,**kw):
 from lifecycle.worklist import list_worklist
 from lifecycle.worklist_contracts import WorklistQuery
 return list_worklist(c,r.tenant_id,ids['demo_user_account'],WorklistQuery(**(dict(fromDate='2026-09-01',toDate='2030-01-01',strategyId=r.strategy_id,eventType='STRUCTURED_OBSERVATION')|kw)))


def test_direct_schedule_is_informational_and_financially_inert(notes):
 from lifecycle.worklist_structured import inspect_structured
 from lifecycle.worklist_contracts import StructuredInspection,WorklistResponse
 c,r,node,swap,trade,events,execute=notes
 counts=lambda:tuple(c.scalar(select(func.count()).select_from(t)) for t in [m.trade,m.cash_balance,m.schedule_event,m.condition_group_action,m.bond_redemption_proposal,m.fx_maturity_posting,m.access_audit_event])
 before=counts();result=WorklistResponse.model_validate(read(c,r))
 assert result.total==4 and all(x.attention=='INFORMATION' for x in result.items)
 assert {x.milestoneKind for x in result.items}=={'COUPON_OBSERVATION','AUTOCALL_OBSERVATION','FINAL_VALUATION','MATURITY'}
 assert all(x.status in ('DATE_PASSED','SCHEDULED_TODAY','UPCOMING') for x in result.items)
 row=next(x for x in result.items if x.milestoneKind=='AUTOCALL_OBSERVATION')
 view=StructuredInspection.model_validate(inspect_structured(c,r.tenant_id,ids['demo_user_account'],r.strategy_id,node,row.eventKey))
 assert view.autocallEligibility=='ELIGIBLE_DATE' and view.outcomeStatus=='NOT_ASSESSED'
 assert view.positionAssessed and view.quantities  # Missing quantities must not pass a vacuous all().
 assert view.conditionalPaymentDate==date(2026,10,5) and view.conditions[0].barriers[0].lowerLevel=='100.000000000000'
 assert any(a.startswith('REDEEM_PARENT') for a in view.conditions[0].actions)
 assert all(Decimal(q.netQuantity)==100000 for q in view.quantities) and counts()==before
 assert read(c,r,attention='ACTIONABLE')['total']==0
 assert read(c,r,fromDate='2026-11-01',toDate='2026-11-30',includeEarlierOverdue=True)['total']==0


def test_swap_notices_distinguish_held_and_observed_contract(notes):
 from lifecycle.worklist_structured import inspect_structured
 c,r,node,swap,trade,events,execute=notes;execute(swap)
 result=read(c,r,instrumentId=swap)
 assert result['total']==4 and all(x['instrumentType']=='SWAP' and x['relatedInstrumentId']==node for x in result['items'])
 row=result['items'][0];view=inspect_structured(c,r.tenant_id,ids['demo_user_account'],r.strategy_id,swap,row['eventKey'])
 assert view['observedInstrumentId']==node and view['instrumentId']==swap and 'performance' in view['relation'].lower()
 assert read(c,r)['total']==8
 observed_name=c.scalar(select(m.financial_reference_node.c.canonical_name).where(m.financial_reference_node.c.reference_node_id==node))
 assert read(c,r,q=observed_name)['total']==8


def test_no_preholding_dates_or_current_future_notices_for_flat_holding(notes):
 c,r,node,swap,trade,events,execute=notes
 # An explicit current linked observation before the strategy acquired the note.
 source=dict(c.execute(select(m.schedule_event).where(m.schedule_event.c.schedule_event_id==events[0])).mappings().one())
 old=uuid4();c.execute(m.schedule_event.insert().values(**(source|dict(schedule_event_id=old,event_sequence=2,event_date=date(2026,9,1)))))
 group=dict(c.execute(select(m.structured_product_condition_group).where(m.structured_product_condition_group.c.schedule_event_id==events[0])).mappings().one())
 c.execute(m.structured_product_condition_group.insert().values(**(group|dict(condition_group_id=uuid4(),group_code='BEFORE_HOLDING',schedule_event_id=old))))
 assert read(c,r)['total']==4
 execute(side='SELL',day='2026-10-03')
 rows=read(c,r)['items'];assert rows and all(x['eventDate']<date(2026,10,3) for x in rows)
 assert read(c,r,fromDate='2026-11-01')['total']==0


def test_notification_caps_scope_and_cancellation(notes):
 from lifecycle.assistance import assistance_view,require_assistance
 from lifecycle.worklist_structured import inspect_structured
 from sqlalchemy.exc import IntegrityError
 c,r,node,swap,trade,events,execute=notes
 row=read(c,r)['items'][0];view=assistance_view(c,r.tenant_id,ids['demo_user_account'],r.strategy_id,'STRUCTURED_OBSERVATION')
 assert view['availableTiers']==[0,1] and not view['handlerSupported']
 with pytest.raises(ValueError):configure(c,2,event='STRUCTURED_OBSERVATION',strategy=r.strategy_id)
 with pytest.raises(PermissionError):require_assistance(c,r.tenant_id,ids['demo_user_account'],r.strategy_id,'STRUCTURED_OBSERVATION','DIRECT')
 with pytest.raises(PermissionError):inspect_structured(c,ids['second_tenant'],ids['demo_user_account'],r.strategy_id,node,row['eventKey'])
 configure(c,0,event='STRUCTURED_OBSERVATION',strategy=r.strategy_id)
 assert read(c,r)['total']==0
 with pytest.raises(LookupError):inspect_structured(c,r.tenant_id,ids['demo_user_account'],r.strategy_id,node,row['eventKey'])
 configure(c,1,event='STRUCTURED_OBSERVATION',strategy=r.strategy_id)
 event=dict(c.execute(select(m.trade_lifecycle_event).where(m.trade_lifecycle_event.c.trade_id==trade)).mappings().one())
 c.execute(m.trade_lifecycle_event.insert().values(**(event|dict(trade_lifecycle_event_id=uuid4(),sequence_no=2,event_type='CANCELLED',event_payload='{}'))))
 assert read(c,r)['total']==0


def test_old_unlinked_owner_schedule_is_not_current_evidence(notes):
 c,r,node,swap,trade,events,execute=notes
 schedule=uuid4();c.execute(m.schedule.insert().values(schedule_id=schedule,owner_reference_node_id=node,schedule_type='AUTOCALL_OBSERVATION',status='ACTIVE'))
 c.execute(m.schedule_event.insert().values(schedule_id=schedule,event_sequence=1,event_type='OBSERVATION',event_date=date(2026,10,4),status='SCHEDULED'))
 assert read(c,r)['total']==4


def test_private_dependencies_are_never_disclosed(notes):
 from lifecycle.worklist_structured import inspect_structured
 c,r,node,swap,trade,events,execute=notes
 scope=m.reference_node_scope
 c.execute(scope.update().where(scope.c.reference_node_id==ids['hsbc_instrument_node']).values(scope_type='TENANT_PRIVATE',owner_tenant_id=ids['second_tenant']))
 rows=read(c,r)['items'];assert len(rows)==1 and rows[0]['status']=='SOURCE_UNAVAILABLE' and rows[0]['attention']=='INFORMATION'
 view=inspect_structured(c,r.tenant_id,ids['demo_user_account'],r.strategy_id,node,rows[0]['eventKey'])
 assert view['observedInstrumentId'] is None and view['conditions']==[]
 assert str(ids['hsbc_instrument_node']) not in str(view)


def test_unknown_holdings_stay_unknown_without_financial_blockers(notes):
 c,r,node,swap,trade,events,execute=notes
 source=dict(c.execute(select(m.trade).where(m.trade.c.trade_id==trade)).mappings().one())
 c.execute(m.trade.insert().values(**(source|dict(trade_id=uuid4()))))
 rows=read(c,r)['items'];assert rows and all(x['status']=='SOURCE_UNAVAILABLE' and x['attention']=='INFORMATION' and not x['positionAssessed'] and x['quantities']==[] for x in rows)


def test_current_source_changes_and_retired_schedules_are_visible(notes):
 from lifecycle.worklist_structured import inspect_structured
 c,r,node,swap,trade,events,execute=notes
 row=next(x for x in read(c,r)['items'] if x['milestoneKind']=='AUTOCALL_OBSERVATION')
 c.execute(m.schedule_event.update().where(m.schedule_event.c.schedule_event_id==events[1]).values(payment_date=date(2026,10,6)))
 changed=inspect_structured(c,r.tenant_id,ids['demo_user_account'],r.strategy_id,node,row['eventKey'])
 assert changed['sourceFingerprint']!=row['sourceFingerprint']
 schedule=c.scalar(select(m.schedule_event.c.schedule_id).where(m.schedule_event.c.schedule_event_id==events[1]))
 c.execute(m.schedule.update().where(m.schedule.c.schedule_id==schedule).values(status='RETIRED'))
 assert all(x['milestoneKind']!='AUTOCALL_OBSERVATION' for x in read(c,r)['items'])


def test_read_only_scoped_user_can_inspect_and_zero_net_allocations_are_preserved(notes):
 from lifecycle.worklist_structured import inspect_structured
 from security_master_schema import access_management as am
 from tests.test_lifecycle_allocation_store import field
 from tests.profile_fixtures import configure_allocation,allocation_policy
 c,r,node,swap,trade,events,execute=notes
 sale=execute(side='SELL')
 dimension=field(c,r.tenant_id)
 for identity,value in [(trade,'alpha'),(sale,'beta')]:c.execute(m.trade_property_value.insert().values(trade_id=identity,definition_id=dimension,tenant_id=r.tenant_id,value=value))
 configure_allocation(c,r.tenant_id,ids['demo_user_account'],r.strategy_id,[dict(definitionId=str(dimension),behavior='ALLOCATION')],allocation_policy(c,r.tenant_id,r.strategy_id).revision,'Retain structured allocations')
 rows=read(c,r)['items'];assert len(rows)==4 and all(Decimal(x['quantities'][0]['netQuantity'])==0 and Decimal(x['quantities'][0]['grossQuantity'])==200000 for x in rows)
 actor=am.add_user(c,r.tenant_id,ids['demo_user_account'],name='Information-only structured reader')
 group=am.save_group(c,r.tenant_id,ids['demo_user_account'],code='SP_READ_'+uuid4().hex,name='Selected information',actions=['LIFECYCLE_READ'],scope_mode='SELECTED',strategy_ids=[r.strategy_id])
 am.set_user_groups(c,r.tenant_id,ids['demo_user_account'],actor,[group])
 assert inspect_structured(c,r.tenant_id,actor,r.strategy_id,node,rows[0]['eventKey'])['positionAssessed']
 with pytest.raises(PermissionError):inspect_structured(c,r.tenant_id,actor,ids['uk_fund_strategy'],node,rows[0]['eventKey'])


def test_full_population_filters_counts_and_inspection_do_not_depend_on_loaded_page(notes):
 from tests.profile_fixtures import assign
 from lifecycle.assistance import append_selection
 from lifecycle.worklist_structured import inspect_structured
 c,r,node,swap,trade,events,execute=notes
 source=dict(c.execute(select(m.strategy).where(m.strategy.c.strategy_id==r.strategy_id)).mappings().one())
 for n in range(26):
  target=uuid4();c.execute(m.strategy.insert().values(**(source|dict(strategy_id=target,strategy_code='SP_PAGE_'+target.hex,display_name=f'Schedule page {n:02d}'))))
  assign(c,r.tenant_id,ids['demo_user_account'],target);execute(strategy=target)
  append_selection(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],target,'STRUCTURED_OBSERVATION',1,0,'Synthetic full history')
 first=read(c,r,strategyId=None,limit=25);second=read(c,r,strategyId=None,limit=25,offset=25)
 assert first['total']==second['total']==108 and len(first['items'])==len(second['items'])==25
 assert sum(first['statusCounts'].values())==108
 assert not {x['eventKey'] for x in first['items']} & {x['eventKey'] for x in second['items']}
 row=second['items'][0]
 assert inspect_structured(c,r.tenant_id,ids['demo_user_account'],row['strategyId'],node,row['eventKey'])['eventKey']==row['eventKey']
 assert read(c,r,strategyId=None,attention='ACTIONABLE')['total']==0


def test_frozen_swap_reference_mismatch_never_displays_changed_contract(notes,monkeypatch):
 from lifecycle import worklist_structured as reader
 c,r,node,swap,trade,events,execute=notes;execute(swap)
 before=read(c,r,instrumentId=swap)
 assert before['total']==4 and all(x['status']!='SOURCE_UNAVAILABLE' for x in before['items'])
 original=reader.load_terms_schedules
 def changed(*args,**kwargs):
  views=original(*args,**kwargs)
  views[swap].layers[0].economics['performanceReferenceId']=str(uuid4())
  return views
 monkeypatch.setattr(reader,'load_terms_schedules',changed)
 rows=read(c,r,instrumentId=swap)['items']
 assert len(rows)==1 and rows[0]['status']=='SOURCE_UNAVAILABLE' and rows[0]['attention']=='INFORMATION'
 view=reader.inspect_structured(c,r.tenant_id,ids['demo_user_account'],r.strategy_id,swap,rows[0]['eventKey'])
 assert view['observedInstrumentId'] is None and view['conditions']==[]
 assert any('original booked' in reason for reason in view['reasons'])


def test_database_cap_and_reviewed_downgrade_preserve_information_only_boundary(notes):
 from sqlalchemy.exc import IntegrityError
 from lifecycle.assistance_transitions import preview_assistance_transition,apply_assistance_transition
 from lifecycle.assistance import assistance_view
 c,r,node,swap,trade,events,execute=notes
 table=m.strategy_lifecycle_assistance
 source=dict(c.execute(select(table).where(table.c.strategy_id==r.strategy_id,table.c.event_type=='STRUCTURED_OBSERVATION')).mappings().one())
 with pytest.raises(IntegrityError),c.begin_nested():c.execute(table.insert().values(**(source|dict(selected_tier=2,revision=2,previous_revision=1))))
 from lifecycle.entitlements import lifecycle_subscription_view
 subscription=lifecycle_subscription_view(c,r.tenant_id)
 request=dict(expectedSubscriptionRevision=subscription['revision'],proposedMaximumTier=2,scope='ALL_CONFIGURED',replacement='HIGHEST_AVAILABLE')
 preview=preview_assistance_transition(c,r.tenant_id,ids['demo_user_account'],request)
 row=next(x for x in preview['items'] if x['strategyId']==r.strategy_id and x['eventType']=='STRUCTURED_OBSERVATION')
 assert row['beforeTier']==row['afterTier']==1
 with pytest.raises(ValueError):preview_assistance_transition(c,r.tenant_id,ids['demo_user_account'],request|dict(replacement='EXPLICIT',targetTier=2))
 reset=request|dict(proposedMaximumTier=0)
 preview=preview_assistance_transition(c,r.tenant_id,ids['demo_user_account'],reset)
 apply_assistance_transition(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],reset|dict(inputHash=preview['inputHash'],confirmChange=True,confirmReplaceAllowed=True,reason='Synthetic reset to manual'))
 assert assistance_view(c,r.tenant_id,ids['demo_user_account'],r.strategy_id,'STRUCTURED_OBSERVATION')['selectedTier']==0
 assert read(c,r)['total']==0


def test_shared_terms_lookups_are_request_local_and_preserve_complete_projection(notes):
 from security_master_schema import instrument_terms_schedule as source
 from security_master_schema.instrument_terms_batch import TermsScheduleBatch
 from sqlalchemy import event
 c,r,node,swap,trade,events,execute=notes
 baseline=source.load_terms_schedule(c,r.tenant_id,swap).model_dump(mode='json')
 batch=TermsScheduleBatch(c,r.tenant_id,[node,swap]);queries=[]
 def query(*args):queries.append(True)
 event.listen(c,'before_cursor_execute',query)
 try:
  source.load_terms_schedule(c,r.tenant_id,node,source=batch)
  actual=source.load_terms_schedule(c,r.tenant_id,swap,source=batch).model_dump(mode='json')
 finally:event.remove(c,'before_cursor_execute',query)
 assert actual==baseline and not queries
 with pytest.raises(ValueError):source.load_terms_schedule(c,ids['second_tenant'],node,source=batch)
 scope=m.reference_node_scope
 c.execute(scope.update().where(scope.c.reference_node_id==ids['hsbc_instrument_node']).values(scope_type='TENANT_PRIVATE',owner_tenant_id=ids['second_tenant']))
 with pytest.raises(LookupError):source.load_terms_schedule(c,r.tenant_id,node)
