"""Non-ledger revisions require review without rewriting financial evidence."""
from datetime import timedelta
from uuid import uuid4
from decimal import Decimal
import pytest
from sqlalchemy import select
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from tests.test_valuation_service import valued
from tests.test_valuation_ledger_impacts import staged
from valuation import storage,tables as t
from valuation.ledger_impacts import batch_source_health,source_health_statuses


def corrected_mark(c,r):
    row=dict(c.execute(select(m.market_data_observation).where(m.market_data_observation.c.market_data_series_id==ids['market_data_series'],m.market_data_observation.c.market_date==r.closing_cutoff.date())).mappings().first())
    c.execute(m.market_data_observation.insert().values(**(row|dict(market_data_observation_id=uuid4(),market_data_vintage_id=None,value=Decimal('1120'),source_observation_key='CORRECTION_'+uuid4().hex,supersedes_observation_id=row['market_data_observation_id']))))


def test_corrected_mark_flags_detail_history_and_queue_without_changing_results(valued):
    from valuation.source_dependencies import source_reassessment_predicate
    c,r,_=valued;batch=staged(c,r)
    before=storage.batch_view(c,r.tenant_id,batch)
    assert batch_source_health(c,r.tenant_id,batch)['status']=='CURRENT'
    corrected_mark(c,r)
    after=storage.batch_view(c,r.tenant_id,batch)
    assert after['items']==before['items'] and after['summary']==before['summary']
    assert after['sourceHealth']['status']=='REASSESSMENT_REQUIRED'
    assert 'MARKET_DATA' in after['sourceHealth']['sourceChangeKinds']
    assert source_health_statuses(c,[after])[batch]=='REASSESSMENT_REQUIRED'
    assert c.scalar(select(t.batch.c.batch_id).where(t.batch.c.batch_id==batch,source_reassessment_predicate(t.batch)))==batch
    with pytest.raises(ValueError,match='recalculate'):
        storage.publish(c,r.tenant_id,batch,ids['platform_admin_user_account'],'Independent synthetic review')


@pytest.mark.parametrize('kind',['POLICY','CALENDAR','CORPORATE_ACTION'])
def test_relevant_non_market_sources_are_tracked(valued,kind):
    c,r,_=valued;batch=staged(c,r)
    if kind=='POLICY':
        c.execute(m.valuation_policy_rule.update().where(m.valuation_policy_rule.c.valuation_policy_id==r.policy_id).values(max_staleness_business_days=2))
    elif kind=='CALENDAR':
        calendar=c.scalar(select(m.valuation_policy_rule.c.market_calendar_id).where(m.valuation_policy_rule.c.valuation_policy_rule_id==ids['valuation_policy_rule']))
        c.execute(m.calendar_assignment.insert().values(tenant_id=r.tenant_id,market_calendar_id=calendar,target_kind='STRATEGY',target_id=r.strategy_id,purpose='VALUATION',valid_from=r.closing_cutoff.date(),valid_to=r.closing_cutoff.date(),reason='Synthetic reassignment',created_by_user_account_id=ids['demo_user_account'],submission_key=str(uuid4()),submission_fingerprint='a'*64))
    else:
        event=uuid4()
        c.execute(m.corporate_action.insert().values(corporate_action_id=event,affected_instrument_node_id=ids['hsbc_instrument_node'],event_type='STOCK_SPLIT',status='ANNOUNCED',sequence_no=1))
        c.execute(m.corporate_action_date.insert().values(corporate_action_id=event,date_role='EX',date_value=r.closing_cutoff.date(),timezone_name='Europe/London'))
        c.execute(m.corporate_action_effect.insert().values(corporate_action_id=event,effect_type='QUANTITY_CHANGE',target_reference_node_id=ids['hsbc_instrument_node'],ratio=Decimal('2')))
    health=batch_source_health(c,r.tenant_id,batch)
    assert health['status']=='REASSESSMENT_REQUIRED'
    assert kind in health['sourceChangeKinds']


def test_observations_after_the_valuation_window_do_not_create_a_warning(valued):
    c,r,_=valued;batch=staged(c,r)
    row=dict(c.execute(select(m.market_data_observation).where(m.market_data_observation.c.market_data_observation_id==ids['market_data_observation'])).mappings().one())
    c.execute(m.market_data_observation.insert().values(**(row|dict(market_data_observation_id=uuid4(),market_date=r.closing_cutoff.date()+timedelta(days=10),market_data_vintage_id=None,source_observation_key='UNRELATED_'+uuid4().hex))))
    assert batch_source_health(c,r.tenant_id,batch)['status']=='CURRENT'


def test_correction_moved_outside_window_still_flags_the_suppressed_mark(valued):
    c,r,_=valued;batch=staged(c,r)
    row=dict(c.execute(select(m.market_data_observation).where(m.market_data_observation.c.market_data_series_id==ids['market_data_series'],m.market_data_observation.c.market_date==r.closing_cutoff.date())).mappings().first())
    c.execute(m.market_data_observation.insert().values(**(row|dict(market_data_observation_id=uuid4(),market_data_vintage_id=None,market_date=r.closing_cutoff.date()+timedelta(days=10),source_observation_key='MOVED_'+uuid4().hex,supersedes_observation_id=row['market_data_observation_id']))))
    assert batch_source_health(c,r.tenant_id,batch)['sourceChangeKinds']==['MARKET_DATA']


def test_published_financial_values_stay_frozen_after_market_revision(valued):
    c,r,_=valued;batch=staged(c,r)
    storage.publish(c,r.tenant_id,batch,ids['platform_admin_user_account'],'Independent synthetic review')
    before=storage.batch_view(c,r.tenant_id,batch)
    corrected_mark(c,r)
    after=storage.batch_view(c,r.tenant_id,batch)
    assert after['status']=='PUBLISHED'
    assert after['items']==before['items'] and after['summary']==before['summary']
    assert after['sourceHealth']['status']=='REASSESSMENT_REQUIRED'


def test_action_successor_with_moved_date_remains_in_the_dependency_chain(valued):
    from valuation.service import calculate_position
    from valuation.source_dependencies import capture_sources,state_expression
    from sqlalchemy import literal
    from sqlalchemy.dialects.postgresql import JSONB
    c,r,_=valued;calculation=calculate_position(c,r);reference='SYNTHETIC_'+uuid4().hex
    def event(sequence,day):
        identity=uuid4()
        c.execute(m.corporate_action.insert().values(corporate_action_id=identity,affected_instrument_node_id=ids['hsbc_instrument_node'],event_type='STOCK_SPLIT',status='ANNOUNCED',external_event_reference=reference,sequence_no=sequence))
        c.execute(m.corporate_action_date.insert().values(corporate_action_id=identity,date_role='EX',date_value=day,timezone_name='Europe/London'))
    event(1,r.closing_cutoff.date())
    # Test the source tracker independently of the replay engine: these announced
    # actions intentionally are not used to calculate or stage financial results.
    proof=capture_sources(c,r,calculation.projection,calculation.evidence['selections'])
    event(2,r.closing_cutoff.date()+timedelta(days=10))
    current=c.scalar(select(state_expression(r.tenant_id,literal(proof['scope'],type_=JSONB),r.information_cutoff)))
    assert current['CORPORATE_ACTION']!=proof['fingerprints']['CORPORATE_ACTION']


def test_tracker_respects_pricing_dates_rather_than_the_later_economic_date(valued):
    from valuation.service import calculate_position
    from valuation.source_dependencies import capture_sources,state_expression
    from sqlalchemy import literal
    from sqlalchemy.dialects.postgresql import JSONB
    c,r,_=valued;calculation=calculate_position(c,r)
    # Exercise the tracking contract independently: a lagged input has an actual
    # requested price date earlier than its economic valuation date.
    selection=dict(calculation.evidence['selections'][0],pricing_date_requested=r.opening_cutoff.date(),pricing_date_used=r.opening_cutoff.date())
    proof=capture_sources(c,r,calculation.projection,[selection])
    corrected_mark(c,r)
    current=c.scalar(select(state_expression(r.tenant_id,literal(proof['scope'],type_=JSONB),r.information_cutoff)))
    assert current['MARKET_DATA']==proof['fingerprints']['MARKET_DATA']


def test_unentitled_observation_on_a_shared_series_does_not_leak_into_health(valued):
    c,r,_=valued;batch=staged(c,r)
    dataset_id=c.scalar(select(m.market_data_series.c.default_dataset_id).where(m.market_data_series.c.market_data_series_id==ids['market_data_series']))
    dataset=dict(c.execute(select(m.dataset).where(m.dataset.c.dataset_id==dataset_id)).mappings().one())
    hidden=uuid4();c.execute(m.dataset.insert().values(**(dataset|dict(dataset_id=hidden,dataset_code='UNENTITLED_'+hidden.hex))))
    observation=dict(c.execute(select(m.market_data_observation).where(m.market_data_observation.c.market_data_series_id==ids['market_data_series'],m.market_data_observation.c.market_date==r.closing_cutoff.date())).mappings().first())
    c.execute(m.market_data_observation.insert().values(**(observation|dict(market_data_observation_id=uuid4(),dataset_id=hidden,market_data_vintage_id=None,source_observation_key='UNENTITLED_'+uuid4().hex))))
    assert batch_source_health(c,r.tenant_id,batch)['status']=='CURRENT'


def test_a_new_policy_version_does_not_silently_replace_the_selected_version(valued):
    c,r,_=valued;batch=staged(c,r)
    policy=dict(c.execute(select(m.valuation_policy).where(m.valuation_policy.c.valuation_policy_id==r.policy_id)).mappings().one())
    c.execute(m.valuation_policy.insert().values(**(policy|dict(valuation_policy_id=uuid4(),version_no=policy['version_no']+100,submission_key=None,submission_fingerprint=None))))
    assert batch_source_health(c,r.tenant_id,batch)['status']=='CURRENT'


def test_publication_rechecks_non_display_rights_instead_of_reusing_calculation_authority(valued):
    c,r,_=valued;batch=staged(c,r)
    c.execute(m.licence_activity_grant.update().where(m.licence_activity_grant.c.activity=='NON_DISPLAY').values(status='INACTIVE'))
    with pytest.raises(ValueError,match='non-display source rights'):
        storage.publish(c,r.tenant_id,batch,ids['platform_admin_user_account'],'Independent synthetic review')


def test_source_fingerprints_are_identical_with_and_without_database_jit(valued):
    from time import perf_counter
    from sqlalchemy import literal,func,text
    from sqlalchemy.dialects.postgresql import JSONB
    from valuation.service import calculate_position
    from valuation.source_dependencies import state_expression
    c,r,_=valued;calculation=calculate_position(c,r)
    scope=calculation.evidence['sourceDependencies']['scope']
    statement=select(state_expression(r.tenant_id,literal(scope,type_=JSONB),r.information_cutoff))
    original=c.scalar(text('SHOW jit'));results=[];timings={}
    try:
        for mode in ('on','off'):
            c.execute(select(func.set_config('jit',mode,True)))
            started=perf_counter();results.append(c.scalar(statement));timings[mode]=round(perf_counter()-started,4)
    finally:c.execute(select(func.set_config('jit',original,True)))
    assert results[0]==results[1]
    assert c.scalar(text('SHOW jit'))==original
    print('Source fingerprint execution seconds:',timings)


def test_metadata_query_restores_connection_setting_after_a_python_failure(valued):
    from valuation.source_dependencies import metadata_query
    from sqlalchemy import text
    c,_,_=valued;original=c.scalar(text('SHOW jit'))
    with pytest.raises(RuntimeError,match='synthetic metadata failure'):
        with metadata_query(c):
            assert c.scalar(text('SHOW jit'))=='off'
            raise RuntimeError('synthetic metadata failure')
    assert c.scalar(text('SHOW jit'))==original


def test_failed_sql_rolls_back_metadata_settings_with_its_savepoint(valued):
    from valuation.source_dependencies import metadata_query
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError
    c,_,_=valued;original=c.scalar(text('SHOW jit'))
    with pytest.raises(DBAPIError):
        with c.begin_nested():
            with metadata_query(c):c.execute(text('SELECT 1 / 0'))
    assert c.scalar(text('SHOW jit'))==original
