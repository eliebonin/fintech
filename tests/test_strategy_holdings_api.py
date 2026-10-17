"""Actual HTTP holdings, aggregation and pagination over owned disposable data."""
from uuid import uuid4
import os
from datetime import date
from sqlalchemy import create_engine
from security_master_schema import models as m
from tests.test_access_api import client,headers
from tests.test_strategy_scopes_api import scoped_user
from security_master_schema.demo_data import DEMO_IDS as ids

def create_strategy(client):
    response=client.post('/v1/strategies',headers=headers(),json=dict(strategyCode='HOLD_'+uuid4().hex,displayName='Holdings test',strategyType='PROP_SLEEVE',baseCurrencyCode='GBP'))
    assert response.status_code==201,response.text
    identity=response.json()['data']['strategyId']
    # The owned synthetic strategy has historical test activity; do not relax
    # the calendar assignment API's legitimate strategy-lifetime validation.
    engine=create_engine(os.environ['DATABASE_URL'])
    with engine.begin() as c:
        c.execute(m.strategy.update().where(m.strategy.c.strategy_id==identity).values(effective_from=date(2020,1,1)))
    engine.dispose()
    return identity

def book(client,strategy,side,quantity):
    response=client.post('/v1/trades',headers=headers()|{'Idempotency-Key':str(uuid4())},json=dict(listingId=str(ids['hsbc_xlon_listing_node']),strategyId=strategy,side=side,quantity=quantity,executionPrice='1.23',tradeDatetime='2026-09-30T10:00:00Z',settlementDate='2026-10-02'))
    assert response.status_code==201,response.text
    return response.json()

def test_positions_net_all_trades_before_pagination_and_explain_running_quantity(client):
    strategy=create_strategy(client)
    for side,qty in [('BUY','100'),('BUY','50'),('SELL','120')]:book(client,strategy,side,qty)
    response=client.get(f'/v1/strategies/{strategy}/positions?asOf=2026-09-30&limit=1',headers=headers())
    assert response.status_code==200,response.text
    body=response.json();assert body['total']==1 and body['items'][0]['quantity']=='30'
    assert body['items'][0]['instrumentType']=='EQUITY'
    assert body['items'][0]['instrumentTypeLabel']=='Equities'
    assert body['items'][0]['contractDate'] is None and body['items'][0]['attentionCode'] is None
    position=body['items'][0]
    detail=client.get(f"/v1/strategies/{strategy}/positions/{position['positionId']}/movements",params=dict(asOf='2026-09-30',informationCutoff=body['informationCutoff'],limit=2),headers=headers())
    assert detail.status_code==200,detail.text
    assert detail.json()['total']==3 and len(detail.json()['items'])==2
    assert detail.json()['closingQuantity']=='30'
    chart=detail.json()['chart']
    assert chart['quantityUnit']=='SHARES'
    assert len(chart['points'])==1  # All three trades share a timestamp.
    assert chart['points'][0]['buyQuantity']=='150'
    assert chart['points'][0]['sellQuantity']=='-120'
    assert chart['points'][0]['runningQuantity']=='30'
    assert chart['points'][0]['tradeCount']==3


def test_holdings_contract_date_is_frozen_even_if_live_reference_dates_change(client):
    from tests.test_generic_swap_booking_api import create_swap,ticket
    strategy=create_strategy(client)
    node=create_swap(maturityDate='2027-01-01')
    response=client.post('/v1/trades/swaps',headers=headers()|{'Idempotency-Key':str(uuid4())},
        json=ticket(node,strategyId=strategy,quantity='1000'))
    assert response.status_code==201,response.text
    engine=create_engine(os.environ['DATABASE_URL'])
    with engine.begin() as c:
        c.execute(m.instrument_dates.update().where(m.instrument_dates.c.instrument_node_id==node).values(maturity_date=date(2028,1,1)))
    engine.dispose()
    response=client.get(f'/v1/strategies/{strategy}/positions?asOf=2027-01-02',headers=headers())
    assert response.status_code==200,response.text
    row=response.json()['items'][0]
    assert row['contractDate']=='2027-01-01' and row['contractDateLabel']=='Maturity'
    assert row['attentionCode']=='PAST_CONTRACT_DATE' and row['quantity']=='1000'

def test_holdings_require_trade_read_in_same_strategy_and_no_market_data_module(client):
    strategy=create_strategy(client);book(client,strategy,'BUY','10')
    h,_=scoped_user(client,['STRATEGY_READ'],[strategy])
    assert client.get(f'/v1/strategies/{strategy}/positions?asOf=2026-09-30',headers=h).status_code==403
    h,_=scoped_user(client,['STRATEGY_READ','TRADE_READ'],[strategy])
    assert client.get(f'/v1/strategies/{strategy}/positions?asOf=2026-09-30',headers=h).status_code==200
    assert client.get(f"/v1/strategies/{ids['strategy']}/positions?asOf=2026-09-30",headers=h).status_code==403
    assert client.get(f'/v1/strategies/{strategy}/positions?asOf=2026-09-30',headers=headers(tenant='second_tenant')).status_code==403

def test_closed_position_is_optional_and_recognition_basis_is_explicit(client):
    strategy=create_strategy(client);book(client,strategy,'BUY','10');book(client,strategy,'SELL','10')
    base=f'/v1/strategies/{strategy}/positions?asOf=2026-09-30'
    assert client.get(base,headers=headers()).json()['total']==0
    body=client.get(base+'&includeClosed=true',headers=headers()).json()
    assert body['items'][0]['quantity']=='0' and body['items'][0]['direction']=='FLAT'
    assert client.get(base+'&basis=SETTLEMENT',headers=headers()).status_code==422

def test_calendar_visibility_is_separately_authorized_and_empty_is_explicit(client):
    strategy=create_strategy(client)
    h,_=scoped_user(client,['STRATEGY_READ'],[strategy])
    assert client.get(f'/v1/strategies/{strategy}/calendars?asOf=2026-09-30',headers=h).status_code==403
    response=client.get(f'/v1/strategies/{strategy}/calendars?asOf=2026-09-30',headers=headers())
    assert response.status_code==200,response.text
    assert response.json()['assignments']==[]
    assert 'indirectCalendars' in response.json()


def test_measures_require_calculation_authority_and_never_publish(client):
    strategy=create_strategy(client);book(client,strategy,'BUY','10')
    url=f'/v1/strategies/{strategy}/measures?asOf=2026-09-30&policyId={ids["valuation_policy"]}'
    h,_=scoped_user(client,['STRATEGY_READ','TRADE_READ','VALUATION_READ'],[strategy])
    assert client.get(url,headers=h).status_code==403
    assert client.get(url,headers=headers(tenant='second_tenant')).status_code==403
    response=client.get(url,headers=headers())
    assert response.status_code==200,response.text
    body=response.json();assert body['status']=='PREVIEW_NOT_PUBLISHED' and body['total']==1
    assert body['items'][0]['quantity']=='10'
    assert set(body['items'][0]['measures'])=={'referenceNotional','economicExposure','marketValue'}
    assert body['items'][0]['evidenceHash']

def test_assigned_calendar_displays_sealed_version_closures_sources_and_scope(client):
    strategy=create_strategy(client)
    payload=dict(calendarCode='CAL_'+uuid4().hex,displayName='Synthetic UK Irish US schedule',purpose='VALUATION',
        timezoneName='Europe/Dublin',decisionTime='16:30:00',coverageFrom='2026-09-01',coverageTo='2026-10-31',
        mode='WEEKDAYS',sourceReference='Synthetic fund administrator notice',
        exceptions=[dict(date='2026-09-30',status='CLOSED',reason='Fund-specific closure',sourceReference='Synthetic notice')])
    created=client.post('/v1/market-data/calendars',headers=headers()|{'Idempotency-Key':str(uuid4())},json=payload)
    assert created.status_code==201,created.text
    assignment=client.post('/v1/market-data/calendars/assignments',headers=headers()|{'Idempotency-Key':str(uuid4())},json=dict(
        calendarId=created.json()['calendarId'],targetKind='STRATEGY',targetId=strategy,validFrom='2026-09-01',validTo='2026-10-31',reason='Test strategy schedule'))
    assert assignment.status_code==201,assignment.text
    result=client.get(f'/v1/strategies/{strategy}/calendars?asOf=2026-09-30',headers=headers())
    assert result.status_code==200,result.text
    row=result.json()['assignments'][0]
    assert row['statusOnDate']=='CLOSED' and row['activeOnDate'] is True
    assert row['calendar']['versionNo']==1 and row['calendar']['configuration']['sourceReference']=='Synthetic fund administrator notice'
    assert row['days'][0]['date']=='2026-09-30'
    revised=client.post('/v1/market-data/calendars/assignments',headers=headers()|{'Idempotency-Key':str(uuid4())},json=dict(
        calendarId=created.json()['calendarId'],targetKind='STRATEGY',targetId=strategy,validFrom='2026-09-01',validTo='2026-10-31',reason='Reaffirmed schedule revision'))
    assert revised.status_code==201,revised.text
    revised_rows=client.get(f'/v1/strategies/{strategy}/calendars?asOf=2026-09-30',headers=headers()).json()['assignments']
    assert sum(r['activeOnDate'] for r in revised_rows)==1
    assert {r['assignment']['reason'] for r in revised_rows}=={'Test strategy schedule','Reaffirmed schedule revision'}
    assert sum(r['superseded'] for r in revised_rows)==1
    h,_=scoped_user(client,['STRATEGY_READ','CALENDAR_READ'],[ids['strategy']])
    assert client.get(f'/v1/strategies/{strategy}/calendars?asOf=2026-09-30',headers=h).status_code==403

def test_cancellation_removes_a_sale_instead_of_manufacturing_a_new_buy(client):
    strategy=create_strategy(client);book(client,strategy,'BUY','100')
    sale=book(client,strategy,'SELL','70')['data']['trade']['tradeId']
    cancelled=client.post(f'/v1/trades/{sale}/cancel-booking',headers=headers()|{'Idempotency-Key':str(uuid4())},json=dict(expectedSequenceNo=1,reason='Synthetic wrong booking'))
    assert cancelled.status_code==200,cancelled.text
    result=client.get(f'/v1/strategies/{strategy}/positions?asOf=2026-09-30',headers=headers())
    assert result.status_code==200,result.text
    assert result.json()['items'][0]['quantity']=='100' and result.json()['items'][0]['tradeCount']==1
