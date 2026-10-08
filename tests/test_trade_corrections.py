"""Record corrections retain original executions; run with isolated database runner."""
import json
from uuid import uuid4

import pytest
from sqlalchemy import select, func, update

from apps.reference_api import repository as r
from apps.reference_api import contracts
from apps.reference_api.db import get_engine
from apps.reference_api.booking_errors import RepositoryNotFound, IdempotencyKeyConflict
from apps.reference_api.trade_properties import TradeFieldError
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from security_master_schema.tenant_workspace import TenantActionForbidden
from tests.test_cash_booking_integrity import payload
from tests.test_option_booking_api import listing, payload as option_payload
from tests.test_fx_forward_booking_api import instrument, payload as fx_payload, request
from tests.test_product_booking_api import structured, future, payload as product_payload
from tests.test_bond_booking_api import bond, ticket as bond_payload
from tests.test_generic_swap_booking_api import create_swap, ticket as swap_payload


@pytest.fixture
def c():
    with get_engine().connect() as connection:
        transaction=connection.begin()
        try: yield connection
        finally: transaction.rollback()


def original(c):
    return r.book_listed_cash_trade(c,ids['tenant'],ids['demo_user_account'],payload(),str(uuid4()),'correction').data


def cancel(c,trade_id,*,sequence=1,reason='Wrong booking',key=None,tenant=None):
    from apps.reference_api.trade_corrections import cancel_booking
    return cancel_booking(c,tenant or ids['tenant'],ids['demo_user_account'],trade_id,
        contracts.CancelBookingRequest(expectedSequenceNo=sequence,reason=reason),key or str(uuid4()),'correction')


def replacement(c,trade_id,*,sequence=1,key=None,**changes):
    request=payload().model_dump(by_alias=True)|changes|dict(correction=dict(tradeId=trade_id,expectedSequenceNo=sequence,reason='Correct executed quantity'))
    return r.book_listed_cash_trade(c,ids['tenant'],ids['demo_user_account'],contracts.TradeBookingRequest(**request),key or str(uuid4()),'correction')


def test_cancel_retains_economics_and_original_event(c):
    first=original(c)
    result=cancel(c,first.trade.trade_id).data
    assert result.trade.lifecycle_status=='CANCELLED'
    assert result.trade.quantity==first.trade.quantity and result.trade.execution_price==first.trade.execution_price
    assert [event.event_type for event in result.lifecycle_events]==['BOOKED','CANCELLED']
    assert result.lifecycle_events[0].event_payload==first.lifecycle_events[0].event_payload
    event=result.lifecycle_events[1]
    assert event.event_datetime_utc==first.trade.trade_datetime_utc
    assert json.loads(event.event_payload)['action']=='CANCEL_BOOKING'
    assert json.loads(event.event_payload)['reason']=='Wrong booking'


def test_cancel_retry_is_idempotent_and_changed_reason_conflicts(c):
    first=original(c);key=str(uuid4())
    cancel(c,first.trade.trade_id,key=key)
    assert len(cancel(c,first.trade.trade_id,key=key).data.lifecycle_events)==2
    with pytest.raises(IdempotencyKeyConflict): cancel(c,first.trade.trade_id,key=key,reason='Different reason')


def test_cancel_foreign_original_is_opaque(c):
    first=original(c)
    # The demo account is a viewer in tenant two. Give this isolated fixture
    # write authority so the test reaches ownership instead of stopping at auth.
    c.execute(update(m.tenant_user_account).where(m.tenant_user_account.c.tenant_id==ids['second_tenant'],
        m.tenant_user_account.c.user_account_id==ids['demo_user_account']).values(membership_role='TENANT_ADMIN'))
    entitlement=dict(c.execute(select(m.tenant_module_entitlement).where(
        m.tenant_module_entitlement.c.tenant_module_entitlement_id==ids['trading_module_entitlement'])).mappings().one())
    entitlement.update(tenant_module_entitlement_id=uuid4(),tenant_id=ids['second_tenant'])
    c.execute(m.tenant_module_entitlement.insert().values(**entitlement))
    with pytest.raises(RepositoryNotFound): cancel(c,first.trade.trade_id,tenant=ids['second_tenant'])
    assert r.get_booked_trade_detail(c,ids['tenant'],first.trade.trade_id,'v1','test').data.trade.lifecycle_status=='BOOKED'


def test_cancel_stale_sequence_and_repeat_are_refused(c):
    first=original(c)
    with pytest.raises(TradeFieldError): cancel(c,first.trade.trade_id,sequence=2)
    cancel(c,first.trade.trade_id)
    with pytest.raises(TradeFieldError): cancel(c,first.trade.trade_id,sequence=2)


@pytest.mark.parametrize('reason',['','   '])
def test_cancel_reason_must_not_be_blank(reason):
    with pytest.raises(ValueError): contracts.CancelBookingRequest(expectedSequenceNo=1,reason=reason)


def test_replacement_is_linked_and_does_not_overwrite_original(c):
    first=original(c)
    new=replacement(c,first.trade.trade_id,quantity='20').data
    old=r.get_booked_trade_detail(c,ids['tenant'],first.trade.trade_id,'v1','test').data
    assert old.trade.quantity==first.trade.quantity
    assert old.trade.lifecycle_status=='SUPERSEDED'
    assert new.trade.quantity=='20.000000000000' and new.trade.lifecycle_status=='BOOKED'
    assert json.loads(old.lifecycle_events[-1].event_payload)['replacementTradeId']==str(new.trade.trade_id)
    assert json.loads(new.lifecycle_events[-1].event_payload)['originalTradeId']==str(first.trade.trade_id)
    assert [event.event_type for event in new.lifecycle_events]==['BOOKED','CORRECTED']


def test_failed_replacement_leaves_original_and_no_new_trade(c):
    first=original(c);before=c.scalar(select(func.count()).select_from(m.trade))
    with pytest.raises(TradeFieldError): replacement(c,first.trade.trade_id,properties=[dict(definitionId=str(uuid4()),value='bad')])
    assert c.scalar(select(func.count()).select_from(m.trade))==before
    assert r.get_booked_trade_detail(c,ids['tenant'],first.trade.trade_id,'v1','test').data.trade.lifecycle_status=='BOOKED'


def test_replacement_chain_and_exact_retry(c):
    first=original(c);key=str(uuid4())
    second=replacement(c,first.trade.trade_id,quantity='20',key=key).data
    assert replacement(c,first.trade.trade_id,quantity='20',key=key).data.trade.trade_id==second.trade.trade_id
    third=replacement(c,second.trade.trade_id,sequence=2,quantity='30').data
    assert json.loads(third.lifecycle_events[-1].event_payload)['originalTradeId']==str(second.trade.trade_id)


def test_unknown_lifecycle_evidence_blocks_correction(c):
    first=original(c)
    c.execute(m.trade_lifecycle_event.insert().values(trade_id=first.trade.trade_id,sequence_no=2,event_type='NOVATED',event_datetime_utc=first.trade.trade_datetime_utc,recorded_by_user_account_id=ids['demo_user_account']))
    with pytest.raises(TradeFieldError): cancel(c,first.trade.trade_id,sequence=2)


def test_revoked_writer_cannot_replay_cancellation(c):
    first=original(c);key=str(uuid4());cancel(c,first.trade.trade_id,key=key)
    c.execute(update(m.user_account).where(m.user_account.c.user_account_id==ids['demo_user_account']).values(status='INACTIVE'))
    with pytest.raises(TenantActionForbidden): cancel(c,first.trade.trade_id,key=key)


@pytest.mark.parametrize('kind',['CASH','OPTION','FX_FORWARD','STRUCTURED_PRODUCT','FUTURE','BOND','SWAP'])
def test_http_replacement_and_stale_conflict_for_every_supported_product(kind,request):
    # Reuse real approval fixtures; all state belongs to the isolated runner.
    api_request=globals()['request']
    if kind=='CASH': path='/v1/trades';data=payload().model_dump(mode='json',by_alias=True,exclude_none=True)
    elif kind=='OPTION': path='/v1/trades/options';data=option_payload(request.getfixturevalue('listing'))
    elif kind=='FX_FORWARD': path='/v1/trades/fx-forwards';data=fx_payload(request.getfixturevalue('instrument'))
    elif kind=='STRUCTURED_PRODUCT': path='/v1/trades/structured-products';data=product_payload(request.getfixturevalue('structured'))
    elif kind=='FUTURE': path='/v1/trades/futures';data=product_payload(*request.getfixturevalue('future'))
    elif kind=='BOND': path='/v1/trades/bonds';data=bond_payload(request.getfixturevalue('bond'))
    else: path='/v1/trades/swaps';data=swap_payload(create_swap())
    first=api_request('POST',path,data,str(uuid4()));assert first.status_code==201,first.text
    old_id=first.json()['data']['trade']['tradeId']
    correction=dict(tradeId=old_id,expectedSequenceNo=1,reason='Synthetic record correction')
    key=str(uuid4());new=api_request('POST',path,data|dict(correction=correction),key)
    assert new.status_code==201,new.text
    new_id=new.json()['data']['trade']['tradeId'];assert new_id!=old_id
    assert [e['eventType'] for e in new.json()['data']['lifecycleEvents']]==['BOOKED','CORRECTED']
    assert api_request('POST',path,data|dict(correction=correction),key).json()['data']['trade']['tradeId']==new_id
    stale=api_request('POST',path,data|dict(correction=correction),str(uuid4()))
    assert stale.status_code==409,stale.text
    assert stale.json()['code']=='trade.correction_conflict'
    cancelled=api_request('POST',f'/v1/trades/{new_id}/cancel-booking',dict(expectedSequenceNo=2,reason='Erroneous replacement'),str(uuid4()))
    assert cancelled.status_code==200,cancelled.text
    old=api_request('GET',f'/v1/trades/{old_id}').json()['data']
    assert old['trade']['lifecycleStatus']=='SUPERSEDED'
    assert json.loads(old['lifecycleEvents'][-1]['eventPayload'])['replacementTradeId']==new_id


def test_late_replacement_failure_rolls_back_both_records(c,monkeypatch):
    from apps.reference_api import trade_corrections as service
    first=original(c);before=c.scalar(select(func.count()).select_from(m.trade))
    real_append=service._append
    def fail_second(*args,**kwargs):
        real_append(*args,**kwargs)
        if args[4]=='CORRECTED': raise RuntimeError('Synthetic finalization failure')
    monkeypatch.setattr(service,'_append',fail_second)
    with pytest.raises(RuntimeError): replacement(c,first.trade.trade_id,quantity='20')
    assert c.scalar(select(func.count()).select_from(m.trade))==before
    old=r.get_booked_trade_detail(c,ids['tenant'],first.trade.trade_id,'v1','test').data
    assert old.trade.lifecycle_status=='BOOKED' and len(old.lifecycle_events)==1


def test_cancellation_remains_available_after_reference_and_strategy_retirement(c):
    first=original(c)
    c.execute(update(m.strategy).where(m.strategy.c.strategy_id==ids['strategy']).values(status='INACTIVE'))
    c.execute(update(m.listing).where(m.listing.c.listing_node_id==ids['hsbc_xlon_listing_node']).values(status='SUSPENDED'))
    assert cancel(c,first.trade.trade_id).data.trade.lifecycle_status=='CANCELLED'


def test_cancel_and_replace_compete_without_orphan_replacement():
    from concurrent.futures import ThreadPoolExecutor
    data=payload().model_dump(mode='json',by_alias=True,exclude_none=True)
    first=request('POST','/v1/trades',data,str(uuid4()));assert first.status_code==201,first.text
    old_id=first.json()['data']['trade']['tradeId']
    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs=[pool.submit(request,'POST',f'/v1/trades/{old_id}/cancel-booking',dict(expectedSequenceNo=1,reason='Duplicate'),str(uuid4())),
            pool.submit(request,'POST','/v1/trades',data|dict(correction=dict(tradeId=old_id,expectedSequenceNo=1,reason='Wrong quantity')),str(uuid4()))]
        results=[job.result(timeout=20) for job in jobs]
    assert sorted(result.status_code for result in results) in ([200,409],[201,409]),[result.text for result in results]
    old=request('GET',f'/v1/trades/{old_id}').json()['data']
    assert len(old['lifecycleEvents'])==2
    if old['trade']['lifecycleStatus']=='SUPERSEDED':
        new_id=json.loads(old['lifecycleEvents'][-1]['eventPayload'])['replacementTradeId']
        assert request('GET',f'/v1/trades/{new_id}').json()['data']['trade']['lifecycleStatus']=='BOOKED'


def test_same_key_concurrent_cancellation_appends_once():
    from concurrent.futures import ThreadPoolExecutor
    first=request('POST','/v1/trades',payload().model_dump(mode='json',by_alias=True,exclude_none=True),str(uuid4()))
    assert first.status_code==201,first.text
    trade_id=first.json()['data']['trade']['tradeId'];key=str(uuid4())
    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs=[pool.submit(request,'POST',f'/v1/trades/{trade_id}/cancel-booking',dict(expectedSequenceNo=1,reason='Duplicate'),key) for _ in range(2)]
        results=[job.result(timeout=20) for job in jobs]
    assert [result.status_code for result in results]==[200,200],[result.text for result in results]
    assert all(len(result.json()['data']['lifecycleEvents'])==2 for result in results)


def test_legacy_missing_snapshot_is_not_silently_reconstructed(c):
    # Construct a deterministic legacy-shaped record with no event evidence;
    # physical row order changes after other modules reload the demo fixture.
    first=original(c)
    row=dict(c.execute(select(m.trade).where(m.trade.c.trade_id==first.trade.trade_id)).mappings().one())
    legacy_id=uuid4();row['trade_id']=legacy_id
    c.execute(m.trade.insert().values(**row))
    with pytest.raises(TradeFieldError): cancel(c,legacy_id)


def test_correction_event_cannot_be_updated_or_deleted(c):
    from sqlalchemy import delete
    from sqlalchemy.exc import DBAPIError
    first=original(c);result=cancel(c,first.trade.trade_id)
    event_id=result.data.lifecycle_events[-1].trade_lifecycle_event_id
    for statement in [update(m.trade_lifecycle_event).where(m.trade_lifecycle_event.c.trade_lifecycle_event_id==event_id).values(event_payload='{}'),
        delete(m.trade_lifecycle_event).where(m.trade_lifecycle_event.c.trade_lifecycle_event_id==event_id)]:
        with pytest.raises(DBAPIError):
            with c.begin_nested(): c.execute(statement)


def test_malformed_predecessor_link_blocks_new_correction(c):
    first=original(c)
    c.execute(m.trade_lifecycle_event.insert().values(trade_id=first.trade.trade_id,sequence_no=2,event_type='CORRECTED',event_datetime_utc=first.trade.trade_datetime_utc,
        recorded_by_user_account_id=ids['demo_user_account'],event_payload=json.dumps(dict(schemaVersion=1,kind='BOOKING_CORRECTION',action='REPLACES_BOOKING'))))
    with pytest.raises(TradeFieldError): cancel(c,first.trade.trade_id,sequence=2)


def test_replacement_cannot_move_original_strategy(c):
    first=original(c);before=c.scalar(select(func.count()).select_from(m.trade))
    with pytest.raises(TradeFieldError) as error:
        replacement(c,first.trade.trade_id,strategyId=str(uuid4()))
    assert error.value.field=='correction'
    assert c.scalar(select(func.count()).select_from(m.trade))==before
    assert r.get_booked_trade_detail(c,ids['tenant'],first.trade.trade_id,'v1','test').data.trade.lifecycle_status=='BOOKED'


def test_replacement_cannot_switch_booking_product(c):
    from apps.reference_api.option_booking import book
    first=original(c);before=c.scalar(select(func.count()).select_from(m.trade))
    data=payload().model_dump(by_alias=True)|dict(positionEffect='OPEN',expectedTermsFingerprint='a'*64,
        correction=dict(tradeId=first.trade.trade_id,expectedSequenceNo=1,reason='Wrong product'))
    with pytest.raises(TradeFieldError) as error:
        book(c,ids['tenant'],ids['demo_user_account'],contracts.OptionBookingRequest(**data),str(uuid4()),'correction')
    assert error.value.field=='correction'
    assert c.scalar(select(func.count()).select_from(m.trade))==before


def test_exact_cancellation_replay_survives_strategy_retirement(c):
    first=original(c);key=str(uuid4());cancel(c,first.trade.trade_id,key=key)
    c.execute(update(m.strategy).where(m.strategy.c.strategy_id==ids['strategy']).values(status='INACTIVE'))
    replay=cancel(c,first.trade.trade_id,key=key)
    assert replay.data.trade.lifecycle_status=='CANCELLED' and len(replay.data.lifecycle_events)==2
