"""Cash input changes cannot silently alter or finalize frozen financial results."""
from dataclasses import replace
from datetime import date,datetime,timezone
from decimal import Decimal as D
from uuid import uuid4
from sqlalchemy import select,func
import pytest
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from tests.test_valuation_service import valued,service
from tests.test_cash_fx_storage import add_account,add_balance,daily,stage,reviewer
from valuation import storage


def prepared(valued):
    c,r,_=valued;account=add_account(c,r)
    for day in (date(2026,9,29),date(2026,9,30),date(2026,10,1)):add_balance(c,r,account,day,'100')
    r=replace(daily(r),information_cutoff=c.scalar(select(func.clock_timestamp())))
    result=service().calculate(c,r);batch=stage(c,r,result)
    return c,r,account,batch,storage.batch_view(c,r.tenant_id,batch)


def test_corrected_cash_blocks_staged_publication_and_pending_amendment(valued):
    from valuation.amendments import request_component_change,approve_component_change
    c,r,account,batch,view=prepared(valued)
    target=next(item for item in view['items'] if item['cash_account_id'])
    request=request_component_change(c,r.tenant_id,batch,target['attribution_id'],ids['demo_user_account'],
        dict(component='ADJUSTMENT',amount=D('1'),reason='Synthetic account adjustment',sourceReference='Synthetic evidence'),str(uuid4()))
    add_balance(c,r,account,date(2026,9,30),'200',revision=2,received=datetime.now(timezone.utc))
    fresh=storage.batch_view(c,r.tenant_id,batch)
    assert fresh['sourceHealth']['status']=='REASSESSMENT_REQUIRED'
    assert fresh['sourceHealth']['cashChanged'] is True
    with pytest.raises(ValueError,match='[Cc]ash|inputs changed'):
        storage.publish(c,r.tenant_id,batch,reviewer(c),'Should not publish stale data')
    with pytest.raises(ValueError,match='[Cc]ash'):
        approve_component_change(c,r.tenant_id,request,reviewer(c),'Should not amend stale data')


def test_published_cash_result_is_unchanged_but_warns_after_input_correction(valued):
    c,r,account,batch,view=prepared(valued)
    storage.publish(c,r.tenant_id,batch,reviewer(c),'Cash convention and supplied inputs reviewed')
    add_balance(c,r,account,date(2026,9,30),'200',revision=2,received=datetime.now(timezone.utc))
    fresh=storage.batch_view(c,r.tenant_id,batch)
    assert fresh['status']=='PUBLISHED'
    assert fresh['summary']==view['summary']
    assert fresh['items']==view['items']
    assert fresh['sourceHealth']['cashChanged'] is True
    assert fresh['sourceHealth']['status']=='REASSESSMENT_REQUIRED'


def test_approved_cash_adjustment_keeps_cash_ownership_and_source_identity(valued):
    from valuation.amendments import request_component_change,approve_component_change
    c,r,account,batch,view=prepared(valued)
    item=next(i for i in view['items'] if i['cash_account_id'])
    request=request_component_change(c,r.tenant_id,batch,item['attribution_id'],ids['demo_user_account'],
        dict(component='ADJUSTMENT',amount=D('-1.25'),reason='Synthetic correction explanation',sourceReference='Synthetic'),str(uuid4()))
    revised=approve_component_change(c,r.tenant_id,request,reviewer(c),'Independent review')
    new=storage.batch_view(c,r.tenant_id,revised)
    target=next(i for i in new['items'] if i['cash_account_id'])
    assert target['cash_account_id']==account
    assert target['position_key'] is target['trade_id'] is None
    assert target['version']==item['version']+1
    assert target['net_pnl']==D('-1.25')
    assert target['evidence']['cashFx']==item['evidence']['cashFx']
    with pytest.raises(ValueError,match='source input correction|recalculation'):
        request_component_change(c,r.tenant_id,revised,target['attribution_id'],ids['demo_user_account'],
            dict(component='CASH_FX',amount=D('1'),reason='Should not override FX',sourceReference='Synthetic'),str(uuid4()))
    storage.publish(c,r.tenant_id,revised,reviewer(c),'Reviewed adjusted mixed population')


def test_request_identity_has_no_cash_opt_out_and_owners_stay_distinct():
    from valuation.service import ValuationRequest
    from valuation.economics import evidence_hash
    from dataclasses import asdict
    stamp=datetime(2026,10,1,tzinfo=timezone.utc)
    r=ValuationRequest(ids['tenant'],ids['strategy'],ids['valuation_policy'],ids['valuation_cut'],ids['gbp_currency'],
        stamp.replace(day=1),stamp.replace(day=2),stamp.replace(day=3))
    assert 'include_cash_balances' not in asdict(r)
    assert 'include_cash_balances' not in storage.request_identity(r)
    assert storage.population_hash([dict(cash_account_id='a',cash_currency_id='usd',attribution_id='1')])!=storage.population_hash([dict(cash_account_id='b',cash_currency_id='usd',attribution_id='1')])


def test_old_cashless_retry_key_cannot_return_an_obsolete_calculation(valued):
    from apps.reference_api.db import get_engine
    from valuation import tables as t
    from valuation.economics import evidence_hash,canonical_payload
    from dataclasses import asdict
    c,r,_=valued;key='obsolete-'+uuid4().hex
    old={k:v for k,v in asdict(r).items() if k not in ('daily','require_complete_accruals','predecessor_batch_id','recalculation_reason')}
    with get_engine().begin() as setup:
        setup.execute(t.attempt.insert().values(tenant_id=r.tenant_id,strategy_id=r.strategy_id,
            initiated_by=ids['demo_user_account'],request_key=key,
            request_hash=evidence_hash(dict(request=old,actor=ids['demo_user_account'])),request_payload=canonical_payload(old),
            correlation_id='Synthetic obsolete request',status='RUNNING'))
    with pytest.raises(ValueError,match='different valuation inputs'):
        storage.begin_attempt(get_engine(),r,ids['demo_user_account'],key)


@pytest.mark.parametrize('snapshots',[False,True])
def test_missing_cash_is_visible_and_does_not_prevent_publication(valued,snapshots):
    c,r,_=valued;account=add_account(c,r)
    if snapshots:add_balance(c,r,account,date(2026,10,1),'100')
    r=replace(r,daily=True,opening_cutoff=r.opening_cutoff.replace(hour=23,minute=59,second=59,microsecond=999999),
        closing_cutoff=r.closing_cutoff.replace(hour=23,minute=59,second=59,microsecond=999999))
    result=service().calculate(c,r)
    assert result.cash is not None
    assert result.cash.lines==()
    assert result.cash.coverage['status'] in ('NOT_ASSESSED','MISSING_INPUTS')
    view=storage.batch_view(c,r.tenant_id,stage(c,r,result))
    assert view['summary']['cashCoverage']
    assert view['summary']['cashFxPnl'] is None
    storage.publish(c,r.tenant_id,view['batch_id'],reviewer(c),'Missing cash disclosed; supplied components reviewed')
    assert storage.batch_view(c,r.tenant_id,view['batch_id'])['status']=='PUBLISHED'


def test_cash_correction_enters_scoped_reassessment_queue_before_pagination(valued):
    from tests.test_valuation_api import call
    c,r,account,batch,_=prepared(valued)
    # A future value date is irrelevant, even though received after staging.
    add_balance(c,r,account,date(2026,10,2),'300',received=c.scalar(select(func.clock_timestamp())))
    c.commit()
    response=call('GET',f'/v1/valuation/reassessments?strategy_id={r.strategy_id}&limit=1')
    assert response.status_code==200,response.text
    assert response.json()['total']==0
    add_balance(c,r,account,date(2026,9,30),'200',revision=2,received=c.scalar(select(func.clock_timestamp())))
    c.commit()
    response=call('GET',f'/v1/valuation/reassessments?strategy_id={r.strategy_id}&limit=1')
    assert response.status_code==200,response.text
    assert response.json()['total']==1
    assert response.json()['items'][0]['batchId']==str(batch)
    assert response.json()['items'][0]['sourceHealth']['cashChanged'] is True


def test_irrelevant_old_cash_does_not_stale_or_block_a_current_result(valued):
    from tests.test_valuation_api import call
    c,r,account,batch,_=prepared(valued)
    add_balance(c,r,account,date(2026,1,1),'300',received=c.scalar(select(func.clock_timestamp())))
    add_account(c,r,'Unused account')
    c.commit()
    response=call('GET',f'/v1/valuation/reassessments?strategy_id={r.strategy_id}&limit=1')
    assert response.status_code==200,response.text
    assert response.json()['total']==0
    view=storage.batch_view(c,r.tenant_id,batch)
    assert view['sourceHealth']['cashChanged'] is False
    assert view['sourceHealth']['status']=='CURRENT'
    storage.publish(c,r.tenant_id,batch,reviewer(c),'Only valuation-window cash inputs are relevant')
    assert storage.batch_view(c,r.tenant_id,batch)['status']=='PUBLISHED'


def test_opening_boundary_cash_correction_still_requires_reassessment(valued):
    from tests.test_valuation_api import call
    c,r,account,batch,_=prepared(valued)
    add_balance(c,r,account,date(2026,9,29),'200',revision=2,received=c.scalar(select(func.clock_timestamp())))
    c.commit()
    response=call('GET',f'/v1/valuation/reassessments?strategy_id={r.strategy_id}&limit=1')
    assert response.status_code==200,response.text
    assert response.json()['total']==1
    assert response.json()['items'][0]['batchId']==str(batch)
    with pytest.raises(ValueError,match='[Cc]ash|inputs changed'):
        storage.publish(c,r.tenant_id,batch,reviewer(c),'Must not publish stale opening cash')


def test_direct_cash_writer_serializes_with_publication_strategy_lock(valued):
    from apps.reference_api.db import get_engine
    from sqlalchemy.exc import DBAPIError
    c,r,_=valued;account=add_account(c,r);c.commit()
    # Publication uses NO KEY UPDATE. Foreign-key KEY SHARE alone does not
    # serialize an INSERT, so the database cash writer must lock the parent.
    c.execute(select(m.strategy.c.strategy_id).where(m.strategy.c.strategy_id==r.strategy_id).with_for_update(key_share=True))
    with get_engine().connect() as writer,writer.begin():
        writer.exec_driver_sql("SET LOCAL lock_timeout='150ms'")
        with pytest.raises(DBAPIError,match='lock timeout'):
            add_balance(writer,r,account,date(2026,9,30),'100')
