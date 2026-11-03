"""Reassessment transport must remain bounded, scoped and explicit."""
from tests.test_valuation_api import call
from tests.test_valuation_service import valued


def test_reassessment_list_is_live_and_paginated():
    response=call('GET','/v1/valuation/reassessments?limit=1')
    assert response.status_code==200,response.text
    assert isinstance(response.json()['items'],list)
    assert isinstance(response.json()['total'],int)
    assert len(response.json()['items'])<=1


def test_recalculation_requires_explicit_confirmation_and_bounded_selection():
    from uuid import uuid4
    response=call('POST','/v1/valuation/reassessments/recalculate',dict(batchIds=[str(uuid4())],reason='Synthetic'))
    assert response.status_code==422,response.text
    response=call('POST','/v1/valuation/reassessments/recalculate',dict(batchIds=[str(uuid4()) for _ in range(26)],reason='Synthetic',confirmRecalculation=True))
    assert response.status_code==422,response.text


def test_unknown_batch_is_not_recalculated_or_disclosed():
    from uuid import uuid4
    response=call('POST','/v1/valuation/reassessments/recalculate',dict(batchIds=[str(uuid4())],reason='Synthetic',confirmRecalculation=True))
    assert response.status_code==404,response.text


def test_actual_recalculation_freezes_retry_and_preserves_original_result(valued):
    from tests.test_valuation_ledger_impacts import staged
    from valuation import storage
    from sqlalchemy import select
    from security_master_schema import models as m
    from security_master_schema.demo_data import DEMO_IDS as ids
    from uuid import uuid4
    c,r,trade=valued
    batch=staged(c,r)
    frozen=storage.batch_view(c,r.tenant_id,batch)['summary']
    original=c.execute(select(m.trade).where(m.trade.c.trade_id==trade)).mappings().one()
    c.execute(m.trade_lifecycle_event.insert().values(trade_id=trade,sequence_no=2,event_type='CANCELLED',event_datetime_utc=original['trade_datetime_utc'],recorded_by_user_account_id=ids['demo_user_account'],event_payload='{}'))
    c.commit()
    affected=call('GET',f'/v1/valuation/reassessments?strategy_id={r.strategy_id}')
    assert affected.status_code==200,affected.text
    selected=next(row for row in affected.json()['items'] if row['batchId']==str(batch))
    assert selected['strategyLabel'] and str(r.strategy_id) not in selected['strategyLabel']
    body=dict(batchIds=[str(batch)],reason='Synthetic ledger correction',confirmRecalculation=True)
    key=str(uuid4())
    first=call('POST','/v1/valuation/reassessments/recalculate',body,headers={'Idempotency-Key':key})
    assert first.status_code==200,first.text
    outcome=first.json()['items'][0]
    assert outcome['status']=='STAGED',first.text
    assert outcome['comparison']['new']['closingValue']=='0'
    second=call('POST','/v1/valuation/reassessments/recalculate',body,headers={'Idempotency-Key':key})
    assert second.status_code==200,second.text
    assert second.json()['items'][0]['attemptId']==outcome['attemptId']
    assert second.json()['informationCutoff']==first.json()['informationCutoff']
    assert storage.batch_view(c,r.tenant_id,batch)['summary']==frozen
    # Two base revisions for one strategy/date would cancel each other's new
    # candidates. Reject that selection rather than report misleading success.
    from valuation import tables as t
    clone=dict(c.execute(select(t.batch).where(t.batch.c.batch_id==batch)).mappings().one())
    clone_id=uuid4()
    c.execute(t.batch.insert().values(**(clone | {'batch_id':clone_id,'input_hash':'f'*64})))
    c.commit()
    duplicate_scope=call('POST','/v1/valuation/reassessments/recalculate',dict(batchIds=[str(batch),str(clone_id)],reason='Synthetic duplicate date',confirmRecalculation=True))
    assert duplicate_scope.status_code==409,duplicate_scope.text
    # A failed second date must not discard a successful first recalculation.
    from datetime import timedelta
    from copy import deepcopy
    bad_summary=deepcopy(frozen)
    old_request=bad_summary['request']
    from datetime import datetime
    old_request['opening_cutoff']=(datetime.fromisoformat(old_request['opening_cutoff'])+timedelta(days=10)).isoformat()
    old_request['closing_cutoff']=(datetime.fromisoformat(old_request['closing_cutoff'])+timedelta(days=10)).isoformat()
    old_request['policy_id']=str(uuid4())
    for name in ('marketPnl','netPnl','grossPnl','openingValue','closingValue','executionValue','marketRoundingAdjustment'):bad_summary[name]='0'
    bad_summary['positionEvidence']=dict(engine='position-reconstruction-v1',completeKnowledge=True,inputHash='b'*64,bucketCount=0,executionCount=0,requiredMarkCount=0)
    bad_id=uuid4()
    c.execute(t.batch.insert().values(**(clone | {'batch_id':bad_id,'input_hash':'c'*64,'value_date':clone['value_date']+timedelta(days=10),'summary':bad_summary})))
    c.commit()
    partial=call('POST','/v1/valuation/reassessments/recalculate',dict(batchIds=[str(batch),str(bad_id)],reason='Synthetic partial failure',confirmRecalculation=True))
    assert partial.status_code==200,partial.text
    assert [item['status'] for item in partial.json()['items']]==['STAGED','BLOCKED'],partial.text
    assert all(item['attemptId'] for item in partial.json()['items'])
