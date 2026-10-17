"""Financial revisions must never silently refresh published evidence."""
from uuid import uuid4
from sqlalchemy import select
import pytest
from tests.test_valuation_service import valued
from apps.reference_api.db import get_engine
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids


@pytest.mark.parametrize('state',[None,{},dict(version=2,revision=1,informationCutoff='2026-10-14T12:00:00+00:00'),dict(version=1,revision='1',informationCutoff='invalid')])
def test_missing_or_invalid_source_proof_is_unknown_not_current(state):
    from valuation.ledger_impacts import source_health
    assert source_health(None,{'summary':{'ledgerSource':state}})['status']=='UNKNOWN_LEGACY'


def staged(c, r):
    from valuation import storage
    from valuation.service import calculate_position
    attempt = storage.begin_attempt(get_engine(),r,ids['demo_user_account'],str(uuid4()))
    return storage.stage(c,attempt,ids['demo_user_account'],calculate_position(c,r))


def test_known_cancellation_flags_result_and_blocks_staged_publication(valued):
    from valuation.ledger_impacts import batch_source_health
    from valuation import storage
    c,r,trade = valued
    batch = staged(c,r)
    frozen = storage.batch_view(c,r.tenant_id,batch)['summary']
    assert batch_source_health(c,r.tenant_id,batch)['status']=='CURRENT'
    original = c.execute(select(m.trade).where(m.trade.c.trade_id==trade)).mappings().one()
    c.execute(m.trade_lifecycle_event.insert().values(trade_id=trade,sequence_no=2,event_type='CANCELLED',event_datetime_utc=original['trade_datetime_utc'],recorded_by_user_account_id=ids['demo_user_account'],event_payload='{}'))
    health = batch_source_health(c,r.tenant_id,batch)
    assert health['status']=='REASSESSMENT_REQUIRED'
    assert health['changes'][0]['tradeId']==str(trade)
    assert storage.batch_view(c,r.tenant_id,batch)['summary']==frozen
    with pytest.raises(ValueError,match='recalculat'):
        storage.publish(c,r.tenant_id,batch,ids['platform_admin_user_account'],'Synthetic review')


def test_late_new_booking_not_in_old_lineage_flags_result(valued):
    from valuation.ledger_impacts import batch_source_health
    c,r,trade = valued
    batch = staged(c,r)
    original = dict(c.execute(select(m.trade).where(m.trade.c.trade_id==trade)).mappings().one())
    new = uuid4()
    c.execute(m.trade.insert().values(**(original | {'trade_id':new})))
    assert batch_source_health(c,r.tenant_id,batch)['status']=='REASSESSMENT_REQUIRED'


def test_future_booking_does_not_flag_prior_result(valued):
    from valuation.ledger_impacts import batch_source_health
    from datetime import timedelta
    c,r,trade = valued
    batch = staged(c,r)
    original = dict(c.execute(select(m.trade).where(m.trade.c.trade_id==trade)).mappings().one())
    new = uuid4(); future = r.closing_cutoff+timedelta(days=2)
    c.execute(m.trade.insert().values(**(original | {'trade_id':new,'trade_datetime_utc':future,'valuation_effective_date':None})))
    assert batch_source_health(c,r.tenant_id,batch)['status']=='CURRENT'


def test_calculation_serializes_late_booking_before_source_health_check(valued):
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError
    from valuation.ledger_impacts import batch_source_health
    c,r,trade=valued
    batch=staged(c,r)
    original=dict(c.execute(select(m.trade).where(m.trade.c.trade_id==trade)).mappings().one())
    added=original | {'trade_id':uuid4()}
    with get_engine().connect() as other:
        with pytest.raises(DBAPIError) as failure:
            with other.begin():
                other.execute(text("SET LOCAL lock_timeout='100ms'"))
                other.execute(m.trade.insert().values(**added))
        assert failure.value.orig.sqlstate=='55P03'
    assert batch_source_health(c,r.tenant_id,batch)['status']=='CURRENT'
    c.commit()
    with get_engine().begin() as other:
        other.execute(m.trade.insert().values(**added))
    assert batch_source_health(c,r.tenant_id,batch)['status']=='REASSESSMENT_REQUIRED'


def test_published_result_retains_financial_values_after_correction(valued):
    from valuation import storage
    from valuation.ledger_impacts import batch_source_health
    c,r,trade=valued
    batch=staged(c,r)
    storage.publish(c,r.tenant_id,batch,ids['platform_admin_user_account'],'Independent synthetic review')
    before=storage.batch_view(c,r.tenant_id,batch)
    original=c.execute(select(m.trade).where(m.trade.c.trade_id==trade)).mappings().one()
    c.execute(m.trade_lifecycle_event.insert().values(trade_id=trade,sequence_no=2,event_type='CANCELLED',event_datetime_utc=original['trade_datetime_utc'],recorded_by_user_account_id=ids['demo_user_account'],event_payload='{}'))
    after=storage.batch_view(c,r.tenant_id,batch)
    assert after['status']=='PUBLISHED' and after['summary']==before['summary']
    assert after['items']==before['items']
    assert batch_source_health(c,r.tenant_id,batch)['status']=='REASSESSMENT_REQUIRED'
