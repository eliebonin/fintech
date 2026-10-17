"""Reviewed source snapshots and cutoffs: use the owned disposable runner."""
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal as D
from dataclasses import replace
from uuid import uuid4
import pytest
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from tests.test_valuation_service import valued, service


@pytest.fixture
def action(valued):
    c,request,trade=valued
    identity=uuid4()
    c.execute(m.corporate_action.insert().values(corporate_action_id=identity,
        affected_instrument_node_id=ids['hsbc_instrument_node'],event_type='STOCK_SPLIT',
        status='ANNOUNCED',external_event_reference='SYNTHETIC_SPLIT_'+identity.hex))
    c.execute(m.corporate_action_date.insert().values(corporate_action_id=identity,date_role='EX',
        date_value=date(2026,10,1),timezone_name='Europe/London'))
    c.execute(m.corporate_action_effect.insert().values(corporate_action_id=identity,
        effect_type='QUANTITY_CHANGE',target_reference_node_id=ids['hsbc_instrument_node'],ratio=D('2')))
    return c,request,trade,identity


def approve(c,identity,**changes):
    from market_data.split_replay import publish_split_decision
    review=dict(numerator='2',denominator='1',wholeSharesOnly=True,
        sourceReferences=['https://example.test/synthetic-split'],reviewReason='Synthetic test; no live event',
        entitlementScope='BASIC_RATIO_ONLY',boundaryConvention='EX_DATE_START')
    return publish_split_decision(c,ids['platform_admin_user_account'],identity,review|changes)


def load(c,request):
    from market_data.split_replay import load_reviewed_splits
    return load_reviewed_splits(c,{ids['hsbc_xlon_listing_node']},request.information_cutoff,tenant_id=request.tenant_id)


def test_private_source_review_is_not_shared_with_another_tenant(action):
    from market_data.split_replay import load_reviewed_splits
    c,request,trade,identity=action
    payload=ids['source_payload']
    c.execute(m.source_payload.update().where(m.source_payload.c.source_payload_id==payload).values(tenant_id=request.tenant_id))
    c.execute(m.corporate_action.update().where(m.corporate_action.c.corporate_action_id==identity).values(source_payload_id=payload))
    approve(c,identity)
    assert len(load(c,request))==1
    assert load_reviewed_splits(c,{ids['hsbc_xlon_listing_node']},request.information_cutoff,tenant_id=uuid4())==()


def test_staged_line_freezes_quantity_change_and_review_identity(action):
    from tests.test_position_attribution_storage import staged
    from valuation import storage
    c,request,trade,identity=action
    review=approve(c,identity)
    result=service().calculate(c,request)
    batch=staged(c,request,result)
    evidence=storage.batch_view(c,request.tenant_id,batch)['items'][0]['evidence']
    adjustment=evidence['splitAdjustments'][0]
    assert adjustment['quantity_before']=='10' and adjustment['quantity_after']=='20'
    assert adjustment['event']['review_id']==str(review)
    assert evidence['identity']['splitAdjustments']==evidence['splitAdjustments']


def test_stale_raw_mark_crossing_split_blocks_even_when_policy_allows_prior_day(action):
    c,request,trade,identity=action
    approve(c,identity)
    c.execute(m.market_data_observation.update().where(
        m.market_data_observation.c.market_date==date(2026,10,1),
        m.market_data_observation.c.market_data_series_id==ids['market_data_series']).values(
            market_date=date(2026,9,30),observed_at_utc=datetime(2026,9,30,16,tzinfo=timezone.utc),
            source_published_at_utc=datetime(2026,9,30,16,tzinfo=timezone.utc)))
    c.execute(m.valuation_policy_rule.update().where(
        m.valuation_policy_rule.c.valuation_policy_rule_id==ids['valuation_policy_rule']).values(
            pricing_date_rule='PRIOR_AVAILABLE',max_staleness_business_days=2))
    with pytest.raises(service().ValuationBlocked,match='pre-action'):
        service().calculate(c,request)


def test_announced_event_without_review_is_not_financially_replayed(action):
    c,request,trade,identity=action
    assert load(c,request)==()
    with pytest.raises(service().ValuationBlocked,match='Corporate action'):
        service().calculate(c,request)


def test_review_retains_frozen_action_and_requires_platform_authority(action):
    from market_data.split_replay import publish_split_decision
    c,request,trade,identity=action
    with pytest.raises(PermissionError): publish_split_decision(c,ids['demo_user_account'],identity,{})
    review=approve(c,identity)
    events=load(c,request)
    assert len(events)==1 and events[0].review_id==review
    assert events[0].ratio==2 and events[0].effective_date==date(2026,10,1)
    assert events[0].effective_at==datetime(2026,9,30,23,tzinfo=timezone.utc)
    assert events[0].evidence['sourceSnapshot']['action']['status']=='ANNOUNCED'
    assert events[0].evidence['review']['entitlementScope']=='BASIC_RATIO_ONLY'


def test_decision_cannot_be_seen_before_its_recorded_cutoff(action):
    c,request,trade,identity=action
    approve(c,identity)
    event=load(c,request)[0]
    assert load(c,replace(request,information_cutoff=event.recorded_at-timedelta(microseconds=1)))==()


def test_decision_is_immutable_and_revocation_is_append_only(action):
    from market_data.split_replay import revoke_split_decision
    c,request,trade,identity=action
    review=approve(c,identity); prior=load(c,request)[0]
    with pytest.raises(DBAPIError),c.begin_nested():
        c.execute(m.corporate_action_replay_decision.update().where(
            m.corporate_action_replay_decision.c.replay_decision_id==review).values(status='REVOKED'))
    revoke_split_decision(c,ids['platform_admin_user_account'],identity,'Synthetic correction')
    assert load(c,request)==()
    assert len(load(c,replace(request,information_cutoff=prior.recorded_at)))==1


def test_reviewed_source_cannot_be_edited_in_place(action):
    c,request,trade,identity=action
    approve(c,identity)
    with pytest.raises(DBAPIError,match='immutable'),c.begin_nested():
        c.execute(m.corporate_action_effect.update().where(
            m.corporate_action_effect.c.corporate_action_id==identity).values(ratio=D('3')))
    with pytest.raises(DBAPIError,match='immutable'),c.begin_nested():
        c.execute(m.corporate_action.update().where(
            m.corporate_action.c.corporate_action_id==identity).values(status='CANCELLED'))
    with pytest.raises(DBAPIError,match='immutable'),c.begin_nested():
        c.execute(m.corporate_action_date.insert().values(corporate_action_id=identity,
            date_role='EFFECTIVE',date_value=date(2026,10,2)))
    assert load(c,request)[0].ratio==2


def test_new_source_version_does_not_double_apply_or_reuse_old_review(action):
    c,request,trade,identity=action
    approve(c,identity)
    old=dict(c.execute(select(m.corporate_action).where(m.corporate_action.c.corporate_action_id==identity)).mappings().one())
    c.execute(m.corporate_action.insert().values(**(old|dict(corporate_action_id=uuid4(),sequence_no=2,
        recorded_at_utc=datetime.now(timezone.utc)))))
    assert load(c,request)==()


@pytest.mark.parametrize('status,event_type',[('CANCELLED','STOCK_SPLIT'),('ANNOUNCED','STOCK_SPLIT'),('ANNOUNCED','CASH_DIVIDEND')])
def test_unreviewed_source_correction_cannot_undo_a_reviewed_historical_unit_change(action,status,event_type):
    c,request,trade,identity=action
    approve(c,identity)
    old=dict(c.execute(select(m.corporate_action).where(m.corporate_action.c.corporate_action_id==identity)).mappings().one())
    successor=uuid4()
    c.execute(m.corporate_action.insert().values(**(old|dict(corporate_action_id=successor,sequence_no=2,
        status=status,event_type=event_type,recorded_at_utc=datetime.now(timezone.utc)))))
    c.execute(m.corporate_action_date.insert().values(corporate_action_id=successor,date_role='EX',
        date_value=date(2026,10,2),timezone_name='Europe/London'))
    with pytest.raises(service().ValuationBlocked,match='Corporate action'):
        service().calculate(c,request)


def test_reviewed_successor_supersedes_old_ratio_without_compounding(action):
    c,request,trade,identity=action
    approve(c,identity)
    old=dict(c.execute(select(m.corporate_action).where(m.corporate_action.c.corporate_action_id==identity)).mappings().one())
    successor=uuid4()
    c.execute(m.corporate_action.insert().values(**(old|dict(corporate_action_id=successor,sequence_no=2,
        recorded_at_utc=datetime.now(timezone.utc)))))
    c.execute(m.corporate_action_date.insert().values(corporate_action_id=successor,date_role='EX',
        date_value=date(2026,10,1),timezone_name='Europe/London'))
    c.execute(m.corporate_action_effect.insert().values(corporate_action_id=successor,effect_type='QUANTITY_CHANGE',
        target_reference_node_id=ids['hsbc_instrument_node'],ratio=D('3')))
    approve(c,successor,numerator='3')
    result=service().calculate(c,request)
    assert result.projection.buckets[0].closing_quantity==30
    assert len(result.projection.split_adjustments)==1 and result.projection.split_adjustments[0].event.action_id==successor


@pytest.mark.parametrize('changes',[{'numerator':'3'},{'numerator':'0'},
    {'sourceReferences':[]},{'wholeSharesOnly':'false'},{'entitlementScope':'LOYALTY'},
    {'boundaryConvention':'PAYMENT_DATE'}])
def test_review_does_not_override_source_or_assume_entitlements(action,changes):
    c,request,trade,identity=action
    with pytest.raises(ValueError): approve(c,identity,**changes)


def test_approved_split_reaches_calculation_with_original_execution_evidence(action):
    c,request,trade,identity=action
    approve(c,identity)
    result=service().calculate(c,request)
    assert result.period.lines[0].bucket.closing_quantity==20
    assert result.period.execution_value==D('0.123')
    assert result.period.closing_value==220
    assert result.projection.split_adjustments[0].quantity_before==10
    assert result.projection.split_adjustments[0].quantity_after==20
    assert result.evidence['projection']['split_adjustments'][0]['event']['action_id']==str(identity)
