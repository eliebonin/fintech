"""Native/API/file parity and failure boundaries on runner-owned PostgreSQL."""
from concurrent.futures import ThreadPoolExecutor
import json
from uuid import UUID,uuid4

import pytest
from sqlalchemy import func,select,update
from apps.reference_api.db import get_engine
from security_master_schema import models as m,access_management as am
from security_master_schema.demo_data import DEMO_IDS as ids
from security_master_schema.errors import RepositoryNotFound,IdempotencyKeyConflict
from security_master_schema.tenant_workspace import TenantActionForbidden
from trading.booking import book_cash_trade
from trading.booking_contracts import TradeBookingRequest
from trading import booking_store


def ticket(**changes):
    return TradeBookingRequest.model_validate(dict(listingId=ids['hsbc_xlon_listing_node'],strategyId=ids['strategy'],
        side='BUY',quantity='10',executionPrice='10.23',tradeDatetime='2026-09-30T14:32:00Z',settlementDate='2026-10-02')|changes)


def book(c,payload=None,key=None):
    return book_cash_trade(c,ids['tenant'],ids['demo_user_account'],payload or ticket(),key or str(uuid4()))


@pytest.fixture
def connection():
    with get_engine().connect() as c:
        tx=c.begin()
        try:yield c
        finally:tx.rollback()


def counts(c):
    return tuple(c.scalar(select(func.count()).select_from(t)) for t in
        (m.trade,m.trade_lifecycle_event,m.trade_booking_idempotency))


def test_native_command_and_http_replay_return_the_same_execution_and_audit():
    from tests.api_client import FixtureTestClient as TestClient
    from apps.reference_api.main import create_app
    from apps.reference_api.repository import get_booked_trade_detail
    engine=get_engine();key=str(uuid4());payload=ticket()
    with engine.begin() as c:
        result=book(c,payload,key)
        expected=get_booked_trade_detail(c,ids['tenant'],result.trade_id,'v1','native').data.model_dump(mode='json',by_alias=True)
    with TestClient(create_app(engine=engine)) as client:
        response=client.post('/v1/trades',json=payload.model_dump(mode='json',by_alias=True),headers={
            'X-Tenant-Id':str(ids['tenant']),'X-User-Account-Id':str(ids['demo_user_account']),'Idempotency-Key':key})
    assert response.status_code==201,response.text
    assert response.json()['data']==expected
    assert response.headers['Location']==f'/v1/trades/{result.trade_id}'
    with engine.connect() as c:
        audit=c.execute(select(m.access_audit_event).where(m.access_audit_event.c.action=='TENANT_REQUEST',
            m.access_audit_event.c.details['resourceIds'].contains([str(result.trade_id)]))).mappings().one()
        assert audit['details']['permission']=='TRADE_WRITE'
        assert audit['details']['requestId']==response.headers['X-Request-ID']


def test_file_and_native_commands_keep_identical_economics_and_frozen_reference_facts(connection):
    from apps.reference_api import import_service
    from apps.reference_api.import_routes import ImportCreate
    from tests.test_import_trades import file_body
    c=connection;native=book(c)
    job=import_service.submit(c,ids['tenant'],ids['demo_user_account'],ImportCreate.model_validate(file_body(str(uuid4()),1)),str(uuid4()))
    job_id=UUID(job['jobId']);review=import_service.validate(c,ids['tenant'],ids['demo_user_account'],job_id)
    receipt=import_service.confirm(c,ids['tenant'],ids['demo_user_account'],job_id,review['reviewHash'],'file-parity')
    imported=UUID(receipt['receipt'][0]['tradeId'])
    def facts(trade_id):
        row=c.execute(select(m.trade).where(m.trade.c.trade_id==trade_id)).mappings().one()
        event=c.scalar(select(m.trade_lifecycle_event.c.event_payload).where(
            m.trade_lifecycle_event.c.trade_id==trade_id,m.trade_lifecycle_event.c.event_type=='BOOKED'))
        return tuple(row[k] for k in ('quantity','execution_price','price_currency_id','quantity_unit',
            'trade_datetime_utc','valuation_effective_date')),json.loads(event),row['execution_channel']
    a,b=facts(native.trade_id),facts(imported)
    assert a[:2]==b[:2]
    assert (a[2],b[2])==('MANUAL_UI','FILE_IMPORT')
    assert import_service.confirm(c,ids['tenant'],ids['demo_user_account'],job_id,review['reviewHash'],'file-replay')['receipt']==receipt['receipt']


def test_native_failure_after_trade_insert_rolls_back_the_entire_command(connection,monkeypatch):
    before=counts(connection)
    def fail(*args): raise ValueError('injected native annotation failure')
    monkeypatch.setattr(booking_store,'persist_trade_annotations',fail)
    with pytest.raises(ValueError,match='native annotation'):
        book(connection)
    assert counts(connection)==before
    assert connection.in_transaction()
    assert connection.scalar(select(m.strategy.c.strategy_id).where(m.strategy.c.strategy_id==ids['strategy']))==ids['strategy']


def test_projection_failure_rolls_back_successful_inner_command(connection,monkeypatch):
    from apps.reference_api import repository
    before=counts(connection)
    monkeypatch.setattr(repository,'get_booked_trade_detail',lambda *args:None)
    with pytest.raises(RepositoryNotFound,match='Booked trade'):
        repository.book_listed_cash_trade(connection,ids['tenant'],ids['demo_user_account'],ticket(),str(uuid4()),'projection-failure')
    assert counts(connection)==before
    assert connection.in_transaction()


def test_native_retry_conflict_and_replay_after_reference_retirement(connection):
    c=connection;key=str(uuid4());first=book(c,key=key)
    c.execute(update(m.strategy).where(m.strategy.c.strategy_id==ids['strategy']).values(status='INACTIVE'))
    c.execute(update(m.financial_reference_node).where(m.financial_reference_node.c.reference_node_id==ids['hsbc_xlon_listing_node']).values(status='INACTIVE'))
    assert book(c,key=key)==first
    with pytest.raises(IdempotencyKeyConflict):book(c,ticket(quantity='11'),key)
    c.execute(update(m.tenant_module_entitlement).where(m.tenant_module_entitlement.c.tenant_id==ids['tenant'],
        m.tenant_module_entitlement.c.platform_module_id.in_(select(m.platform_module.c.platform_module_id).where(
            m.platform_module.c.module_code=='TRADING'))).values(entitlement_state='SUSPENDED'))
    with pytest.raises(TenantActionForbidden):book(c,key=key)


def test_native_command_does_not_commit_outer_transaction():
    engine=get_engine()
    with engine.connect() as c:
        tx=c.begin()
        result=book(c)
        assert c.in_transaction()
        tx.rollback()
    with engine.connect() as c:
        assert c.scalar(select(m.trade.c.trade_id).where(m.trade.c.trade_id==result.trade_id)) is None


def test_native_recognition_and_sell_sign_are_frozen(connection):
    result=book(connection,ticket(side='SELL',valuationEffectiveDate='2026-10-01',valuationOverrideReason='After close'))
    row=connection.execute(select(m.trade).where(m.trade.c.trade_id==result.trade_id)).mappings().one()
    payload=json.loads(connection.scalar(select(m.trade_lifecycle_event.c.event_payload).where(m.trade_lifecycle_event.c.trade_id==result.trade_id)))
    assert row['quantity']==-10
    assert payload['valuationRecognition']==dict(date='2026-10-01',timezone='UTC',basis='EXPLICIT_OVERRIDE',reason='After close')


def test_concurrent_native_retries_create_one_execution():
    engine=get_engine();key=str(uuid4())
    def execute(_):
        with engine.begin() as c:return book(c,key=key).trade_id
    with ThreadPoolExecutor(max_workers=3) as pool:
        results=list(pool.map(execute,range(3)))
    assert len(set(results))==1
    with engine.connect() as c:
        assert c.scalar(select(func.count()).select_from(m.trade_lifecycle_event).where(
            m.trade_lifecycle_event.c.trade_id==results[0],m.trade_lifecycle_event.c.event_type=='BOOKED'))==1


def test_cash_request_audit_failure_rolls_back_execution_and_replay(monkeypatch):
    from tests.api_client import FixtureTestClient as TestClient
    from apps.reference_api.main import create_app
    engine=get_engine();original=am.audit;key=str(uuid4())
    with engine.connect() as c:before=counts(c)
    def fail(c,actor,tenant,action,details,subject=None):
        if action=='TENANT_REQUEST':raise RuntimeError('injected cash audit failure')
        return original(c,actor,tenant,action,details,subject)
    monkeypatch.setattr(am,'audit',fail)
    with TestClient(create_app(engine=engine),raise_server_exceptions=False) as client:
        response=client.post('/v1/trades',json=ticket().model_dump(mode='json',by_alias=True),headers={
            'X-Tenant-Id':str(ids['tenant']),'X-User-Account-Id':str(ids['demo_user_account']),'Idempotency-Key':key})
    assert response.status_code==500
    assert 'injected cash audit' not in response.text
    with engine.connect() as c:assert counts(c)==before
