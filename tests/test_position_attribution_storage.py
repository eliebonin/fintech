"""V2 has real position owners, immutable ledger links and zero-result review."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from uuid import uuid4
import pytest
from sqlalchemy import select
from tests.test_valuation_service import valued
from apps.reference_api.db import get_engine
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from valuation import storage,tables as t
from valuation.evidence_access import batch_datasets
from valuation.service import calculate_position

def staged(c,r,result):
    attempt=storage.begin_attempt(get_engine(),r,ids['demo_user_account'],str(uuid4()))
    return storage.stage(c,attempt,ids['demo_user_account'],result)

def reviewer(c):
    actor=uuid4(); c.execute(m.user_account.insert().values(user_account_id=actor,account_type='HUMAN',status='ACTIVE'))
    return actor

def test_position_owner_and_immutable_lineage(valued):
    c,r,trade=valued
    result=calculate_position(c,r)
    batch=staged(c,r,result); view=storage.batch_view(c,r.tenant_id,batch)
    item=view['items'][0]
    assert item['trade_id'] is None and item['position_key']
    assert item['subject_id']==ids['hsbc_xlon_listing_node']
    assert item['market_pnl']==Decimal('109.877')
    assert item['lineage'][0]['trade_id']==trade
    assert view['summary']['resultFormat']=='POSITION_V2'
    with pytest.raises(Exception,match='immutable'):
        with c.begin_nested():
            c.execute(t.attribution.update().where(t.attribution.c.attribution_id==item['attribution_id']).values(net_pnl=0))
    with pytest.raises(Exception,match='immutable'):
        with c.begin_nested():
            c.execute(t.lineage.delete().where(t.lineage.c.attribution_id==item['attribution_id']))

def test_zero_result_is_evidenced_publishable_and_idempotent(valued):
    c,r,_=valued
    # Requested economic dates precede the fixture trade, so this is truly empty.
    r=replace(r,opening_cutoff=r.opening_cutoff-timedelta(days=10),closing_cutoff=r.closing_cutoff-timedelta(days=10))
    result=calculate_position(c,r); batch=staged(c,r,result)
    view=storage.batch_view(c,r.tenant_id,batch)
    assert view['items']==[] and view['summary']['marketPnl']=='0'
    assert batch_datasets(view)==set()
    storage.publish(c,r.tenant_id,batch,reviewer(c),'Empty population and source scope verified')
    assert storage.batch_view(c,r.tenant_id,batch)['status']=='PUBLISHED'

def test_empty_result_still_requires_a_real_tenant_policy(valued):
    c,r,_=valued
    r=replace(r,policy_id=uuid4(),opening_cutoff=r.opening_cutoff-timedelta(days=10),closing_cutoff=r.closing_cutoff-timedelta(days=10))
    with pytest.raises(ValueError,match='policy'): calculate_position(c,r)

def test_closed_round_trip_without_prices_is_publishable(valued):
    c,r,trade=valued
    row=dict(c.execute(select(m.trade).where(m.trade.c.trade_id==trade)).mappings().one())
    ev=dict(c.execute(select(m.trade_lifecycle_event).where(m.trade_lifecycle_event.c.trade_id==trade)).mappings().one())
    sale=uuid4(); when=r.closing_cutoff-timedelta(hours=1)
    c.execute(m.trade.insert().values(**(row|dict(trade_id=sale,quantity=-row['quantity'],execution_price=Decimal('2.23'),trade_datetime_utc=when))))
    c.execute(m.trade_lifecycle_event.insert().values(**(ev|dict(trade_lifecycle_event_id=uuid4(),trade_id=sale,event_datetime_utc=when))))
    c.execute(m.market_data_observation.delete().where(m.market_data_observation.c.market_date>=r.opening_cutoff.date()))
    result=calculate_position(c,r)
    assert result.period.market_pnl==Decimal('0.1') and result.resolution_snapshot_ids==()
    batch=staged(c,r,result); view=storage.batch_view(c,r.tenant_id,batch)
    assert batch_datasets(view)==set()
    storage.publish(c,r.tenant_id,batch,reviewer(c),'Execution-only bridge verified')

def test_legacy_results_remain_readable_and_v2_replaces_population(valued):
    from tests.legacy_valuation_reference import calculate
    c,r,_=valued
    old=staged(c,r,calculate(c,r)); actor=reviewer(c)
    storage.publish(c,r.tenant_id,old,actor,'Legacy reviewed')
    new=staged(c,r,calculate_position(c,r))
    storage.publish(c,r.tenant_id,new,actor,'Position-owned bridge reviewed')
    assert storage.batch_view(c,r.tenant_id,old)['items'][0]['trade_id'] is not None
    assert storage.batch_view(c,r.tenant_id,old)['status']=='SUPERSEDED'
    assert all(x['trade_id'] is None for x in storage.published(c,r.tenant_id,r.strategy_id,r.closing_cutoff.date()))

def test_closed_period_exposure_still_blocks_known_split(valued):
    c,r,trade=valued
    row=dict(c.execute(select(m.trade).where(m.trade.c.trade_id==trade)).mappings().one())
    ev=dict(c.execute(select(m.trade_lifecycle_event).where(m.trade_lifecycle_event.c.trade_id==trade)).mappings().one())
    sale=uuid4();when=r.closing_cutoff-timedelta(hours=1)
    c.execute(m.trade.insert().values(**(row|dict(trade_id=sale,quantity=-row['quantity'],trade_datetime_utc=when))))
    c.execute(m.trade_lifecycle_event.insert().values(**(ev|dict(trade_id=sale,trade_lifecycle_event_id=uuid4(),event_datetime_utc=when))))
    action=uuid4()
    c.execute(m.corporate_action.insert().values(corporate_action_id=action,affected_instrument_node_id=ids['hsbc_instrument_node'],event_type='STOCK_SPLIT',status='CONFIRMED'))
    c.execute(m.corporate_action_date.insert().values(corporate_action_id=action,date_role='EFFECTIVE',timestamp_value_utc=when-timedelta(hours=1)))
    with pytest.raises(ValueError,match='Corporate action'): calculate_position(c,r)

def test_nominally_flat_preperiod_history_cannot_hide_an_unreplayed_split(valued):
    c,r,trade=valued
    row=dict(c.execute(select(m.trade).where(m.trade.c.trade_id==trade)).mappings().one())
    ev=dict(c.execute(select(m.trade_lifecycle_event).where(m.trade_lifecycle_event.c.trade_id==trade)).mappings().one())
    sale=uuid4();when=r.closing_cutoff-timedelta(hours=1)
    c.execute(m.trade.insert().values(**(row|dict(trade_id=sale,quantity=-row['quantity'],trade_datetime_utc=when))))
    c.execute(m.trade_lifecycle_event.insert().values(**(ev|dict(trade_id=sale,trade_lifecycle_event_id=uuid4(),event_datetime_utc=when))))
    action=uuid4()
    c.execute(m.corporate_action.insert().values(corporate_action_id=action,affected_instrument_node_id=ids['hsbc_instrument_node'],event_type='STOCK_SPLIT',status='CONFIRMED'))
    c.execute(m.corporate_action_date.insert().values(corporate_action_id=action,date_role='EFFECTIVE',timestamp_value_utc=when-timedelta(hours=1)))
    # Raw +10/-10 looks flat BEFORE the period, but a split between those
    # executions makes that conclusion unsafe without transformed quantities.
    later=replace(r,opening_cutoff=r.closing_cutoff+timedelta(days=1),closing_cutoff=r.closing_cutoff+timedelta(days=2))
    with pytest.raises(ValueError,match='Corporate action'): calculate_position(c,later)

def test_v2_result_immutability_includes_rejecting_late_lineage_inserts(valued):
    c,r,trade=valued
    batch=staged(c,r,calculate_position(c,r))
    item=storage.batch_view(c,r.tenant_id,batch)['items'][0]
    original=dict(c.execute(select(m.trade_lifecycle_event).where(m.trade_lifecycle_event.c.trade_id==trade)).mappings().one())
    added=uuid4()
    # A valid later ledger event must not retroactively alter retained result lineage.
    c.execute(m.trade_lifecycle_event.insert().values(**(original|dict(trade_lifecycle_event_id=added,sequence_no=2,event_type='CORRECTED'))))
    with pytest.raises(Exception,match='immutable'):
        with c.begin_nested():
            c.execute(t.lineage.insert().values(attribution_id=item['attribution_id'],trade_id=trade,event_id=added,role='LIFECYCLE_EVIDENCE'))
