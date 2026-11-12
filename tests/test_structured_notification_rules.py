"""An observation date is information, never proof of a financial outcome."""
from datetime import date,datetime,timezone
import pytest


def test_independent_structured_information_contract():
 from lifecycle.worklist_contracts import WorklistQuery
 from lifecycle.assistance_contracts import AssistanceChange
 from uuid import uuid4
 assert WorklistQuery(fromDate='2026-01-01',toDate='2028-01-01',eventType='STRUCTURED_OBSERVATION',status='DATE_PASSED').eventType=='STRUCTURED_OBSERVATION'
 assert AssistanceChange(strategyId=uuid4(),eventType='STRUCTURED_OBSERVATION',selectedTier=1,expectedRevision=0,expectedSubscriptionRevision=0,reason='Information only').selectedTier==1


@pytest.mark.parametrize('day,status',[(date(2026,11,10),'DATE_PASSED'),(date(2026,11,11),'SCHEDULED_TODAY'),(date(2026,11,12),'UPCOMING'),(None,'SOURCE_UNAVAILABLE')])
def test_information_never_becomes_overdue_or_actionable(day,status):
 from lifecycle.worklist_structured import information_state
 assert information_state(day,datetime(2026,11,11,tzinfo=timezone.utc))==(status,'INFORMATION')


def test_non_call_period_and_unknown_eligibility_are_explicit():
 from lifecycle.worklist_structured import observation_kind
 row=dict(schedule_type='AUTOCALL_OBSERVATION',event_date='2026-10-01')
 assert observation_kind(row,'2026-10-02')==('OBSERVATION','BEFORE_FIRST_DATE')
 assert observation_kind(row,'2026-10-01')==('AUTOCALL_OBSERVATION','ELIGIBLE_DATE')
 assert observation_kind(row,None)==('AUTOCALL_OBSERVATION','NOT_ASSESSED')
 assert observation_kind(row|dict(schedule_type='COUPON_OBSERVATION'),None)==('COUPON_OBSERVATION','NOT_APPLICABLE')


def test_only_current_linked_schedule_events_are_used():
 from lifecycle.worklist_structured import linked_events
 facts=dict(conditions=[dict(schedule_event_id='current')],couponPeriods=[],couponProgrammes=[],componentTerms=[],rangeAccrual=[],scheduleEvents=[dict(schedule_event_id='current',schedule_id='now',event_date='2026-10-01',status='SCHEDULED'),dict(schedule_event_id='old',schedule_id='history',event_date='2026-10-01',status='SCHEDULED')])
 assert [x['schedule_event_id'] for x in linked_events(facts)]==['current']
 facts['scheduleEvents'][0]['status']='CANCELLED'
 assert linked_events(facts)==[]


def test_payment_or_reset_rows_are_not_mislabelled_as_observations():
 from lifecycle.worklist_structured import linked_events
 rows=[dict(schedule_event_id=purpose,schedule_id='current',event_date='2026-10-01',event_type=purpose,schedule_type='AUTOCALL_OBSERVATION',status='SCHEDULED') for purpose in ['OBSERVATION','PAYMENT','RESET']]
 facts=dict(couponProgrammes=[dict(schedule_id='current')],scheduleEvents=rows)
 assert [row['event_type'] for row in linked_events(facts)]==['OBSERVATION']


def test_retired_child_links_and_actions_do_not_become_current_notices():
 from lifecycle.worklist_structured import linked_events,_conditions
 from types import SimpleNamespace
 event=dict(schedule_event_id='event',schedule_id='schedule',event_date='2026-10-01',event_type='OBSERVATION',status='SCHEDULED')
 group=dict(condition_group_id='group',schedule_event_id='event',group_code='old',logical_operator='ALL',underlying_aggregation='SINGLE',underlying_scope='SINGLE',status='RETIRED')
 facts=dict(conditions=[group],scheduleEvents=[event])
 assert linked_events(facts)==[]
 assert _conditions(SimpleNamespace(facts=facts),event,{})==[]
 group['status']='VALIDATED'
 facts['actions']=[dict(condition_group_id='group',action_type='REDEEM_PARENT',target_scope='PARENT',status='CANCELLED')]
 assert _conditions(SimpleNamespace(facts=facts),event,{})[0]['actions']==[]


def test_terms_lookup_cache_cannot_cross_connection_or_transaction_boundaries():
 from security_master_schema.instrument_terms_batch import TermsScheduleBatch
 from types import SimpleNamespace
 transaction=[object()];connection=SimpleNamespace(get_transaction=lambda:transaction[0]);other=SimpleNamespace(get_transaction=lambda:transaction[0])
 cache=TermsScheduleBatch(connection,'tenant')
 with pytest.raises(ValueError):cache.require_scope(other,'tenant')
 transaction[0]=object()
 with pytest.raises(ValueError):cache.require_scope(connection,'tenant')
