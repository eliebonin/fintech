from datetime import date,datetime,timezone,timedelta
from uuid import uuid4
import json
from sqlalchemy import select
from tests.test_valuation_service import valued
from tests.test_economic_pnl_acceptance import add_bond
from tests.api_client import ConnectionEngine,FixtureTestClient
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from apps.reference_api.main import create_app


def clone(c,trade,*,quantity,recognition,cancel=False):
    original=dict(c.execute(select(m.trade).where(m.trade.c.trade_id==trade)).mappings().one())
    identity=uuid4();stamp=original['trade_datetime_utc']+timedelta(hours=1)
    c.execute(m.trade.insert().values(**(original|dict(trade_id=identity,quantity=quantity,trade_datetime_utc=stamp,valuation_effective_date=recognition,valuation_date_basis='EXPLICIT_OVERRIDE',valuation_override_reason='Synthetic next-day recognition'))))
    event=dict(c.execute(select(m.trade_lifecycle_event).where(m.trade_lifecycle_event.c.trade_id==trade,m.trade_lifecycle_event.c.event_type=='BOOKED')).mappings().one())
    snapshot=json.loads(event['event_payload']);snapshot['valuationRecognition']=dict(date=recognition.isoformat(),timezone='UTC',basis='EXPLICIT_OVERRIDE',reason='Synthetic next-day recognition')
    event['event_payload']=json.dumps(snapshot)
    c.execute(m.trade_lifecycle_event.insert().values(**(event|dict(trade_lifecycle_event_id=uuid4(),trade_id=identity,event_datetime_utc=stamp))))
    if cancel:c.execute(m.trade_lifecycle_event.insert().values(trade_id=identity,sequence_no=2,event_type='CANCELLED',event_datetime_utc=stamp,recorded_by_user_account_id=ids['demo_user_account'],event_payload='{}'))
    return identity


def test_balance_trade_events_follow_frozen_recognition_signs_and_cancellations(valued,monkeypatch):
    c,r,trade=valued;first=add_bond(c,r,trade)
    second=clone(c,first,quantity=-100000,recognition=date(2026,10,1))
    removed=clone(c,first,quantity=100000,recognition=date(2026,10,1),cancel=True)
    organisation=c.scalar(select(m.organisation.c.organisation_id).limit(1))
    c.execute(m.trade_party_role.insert().values(trade_id=second,organisation_id=organisation,role='COUNTERPARTY'))
    from valuation.balance_trade_events import trade_events
    monkeypatch.setattr('positions.repository.CHUNK_SIZE',1)
    events=trade_events(c,r.tenant_id,ids['demo_user_account'],r.strategy_id,ids['bond_instrument_node'],date(2026,9,30),date(2026,10,1),datetime.now(timezone.utc))
    assert {item['tradeId'] for item in events}=={str(first),str(second)}
    assert str(removed) not in str(events)
    sell=next(item for item in events if item['tradeId']==str(second))
    assert sell['balanceDate']=='2026-10-01' and sell['executionDatetime'].startswith('2026-09-30')
    assert sell['side']=='SELL' and sell['signedQuantity']=='-100000'
    assert sell['tradeAccruedAmount']=='-1250' and sell['currency']=='GBP' and sell['counterparty']
    only=trade_events(c,r.tenant_id,ids['demo_user_account'],r.strategy_id,ids['bond_instrument_node'],date(2026,10,1),date(2026,10,1),datetime.now(timezone.utc))
    assert [item['tradeId'] for item in only]==[str(second)]
    # A historical instrument need not remain active to inspect its bookings.
    c.execute(m.financial_reference_node.update().where(m.financial_reference_node.c.reference_node_id==ids['bond_instrument_node']).values(status='INACTIVE'))
    assert len(trade_events(c,r.tenant_id,ids['demo_user_account'],r.strategy_id,ids['bond_instrument_node'],date(2026,9,30),date(2026,10,1),datetime.now(timezone.utc)))==2


def test_balance_trade_api_preserves_read_only_chart_access_without_trade_disclosure(valued):
    c,r,trade=valued;add_bond(c,r,trade)
    params=dict(strategyId=str(r.strategy_id),instrumentId=str(ids['bond_instrument_node']),fromDate='2026-09-01',toDate='2026-10-01')
    from tests.test_strategy_scopes_api import scoped_user
    with FixtureTestClient(create_app(engine=ConnectionEngine(c))) as client:
        reader,_=scoped_user(client,['VALUATION_READ','MARKET_DATA_READ'],[r.strategy_id])
        assert client.get('/v1/valuation/balance-trades',headers=reader,params=params).status_code==403
        assert client.get('/v1/valuation/balance-series',headers=reader,params=params).status_code==200
        trader,_=scoped_user(client,['VALUATION_READ','MARKET_DATA_READ','TRADE_READ'],[r.strategy_id])
        result=client.get('/v1/valuation/balance-trades',headers=trader,params=params)
        assert result.status_code==200,result.text
        assert result.json()['total']==len(result.json()['items'])==1
        assert result.json()['strategyId']==str(r.strategy_id)
        assert client.get('/v1/valuation/balance-trades',headers=trader,params=params|dict(strategyId=str(ids['uk_fund_strategy']))).status_code==403
        assert client.get('/v1/valuation/balance-trades',headers=trader,params=params|dict(fromDate='2026-10-02')).status_code==422
