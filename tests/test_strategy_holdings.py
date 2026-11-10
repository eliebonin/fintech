"""Quantity projections are independent of prices, tax lots and valuation support."""
from dataclasses import replace
from datetime import datetime, timezone, timedelta
from decimal import Decimal as D
from uuid import UUID
import pytest
from positions.contracts import Booking, LedgerFact, ProjectionRequest, SplitEvent
from positions.holdings import project_holdings
from positions.holdings_repository import holding_conventions

TENANT=UUID(int=1); STRATEGY=UUID(int=2); SUBJECT=UUID(int=3)
END=datetime(2026,9,30,23,59,59,999999,tzinfo=timezone.utc)
INFO=END+timedelta(days=15)

def request(**kw):
    return replace(ProjectionRequest(TENANT,STRATEGY,END,INFO),**kw)

def booked(n,qty,**kw):
    booking=Booking(UUID(int=n+100),SUBJECT,UUID(int=4),'CONTRACTS',D(qty),D('0'),D('1'),D('1'),UUID(int=5),'SWAP')
    booking=replace(booking,**kw)
    return LedgerFact(UUID(int=n+200),booking.trade_id,TENANT,STRATEGY,1,'BOOKED',END-timedelta(days=10-n),END,booking)

def test_buys_and_sells_leave_exact_nonzero_residual_without_price_requirements():
    result=project_holdings([booked(1,'100'),booked(2,'50'),booked(3,'-120')],request())
    assert result.buckets[0].closing_quantity==D('30')
    assert len(result.buckets[0].trade_ids)==3


@pytest.mark.parametrize('day,quantity,expected',[
    ('2026-09-29','10','PAST_CONTRACT_DATE'),('2026-09-30','10','CONTRACT_DATE_TODAY'),
    ('2026-10-01','10',None),('2026-09-29','-10','PAST_CONTRACT_DATE'),('2026-09-29','0',None)])
def test_contract_attention_uses_selected_date_and_only_open_positions(day,quantity,expected):
    from apps.reference_api.strategy_workspace import position_rows
    first=booked(1,'10',product_basis='BOND')
    facts=[first] if quantity=='10' else [first,booked(2,str(D(quantity)-10),product_basis='BOND')]
    desc={f.booking.trade_id:dict(name='Bond',instrumentId=str(SUBJECT),currency='GBP',contractDate=day,contractDateLabel='Maturity') for f in facts}
    row=position_rows(project_holdings(facts,request()),desc)[0]
    assert row['contractDate']==day
    assert row['attentionCode']==expected


def test_missing_or_conflicting_contract_dates_warn_without_guessing_a_date():
    from apps.reference_api.strategy_workspace import position_rows
    first=booked(1,'10',product_basis='SWAP');second=booked(2,'5',product_basis='SWAP')
    desc={f.booking.trade_id:dict(name='Swap',instrumentId=str(SUBJECT),currency='GBP') for f in (first,second)}
    assert position_rows(project_holdings([first],request()),desc)[0]['attentionCode']=='CONTRACT_DATE_MISSING'
    desc[first.booking.trade_id].update(contractDate='2027-01-01',contractDateLabel='Maturity')
    desc[second.booking.trade_id].update(contractDate='2028-01-01',contractDateLabel='Maturity')
    row=position_rows(project_holdings([first,second],request()),desc)[0]
    assert row['contractDate'] is None and row['attentionCode']=='CONTRACT_DATE_CONFLICT'


@pytest.mark.parametrize('payload,expected',[
    ({'economics':{'terms':{'kind':'BOND','maturityDate':'2027-01-01'}}},('2027-01-01','Maturity')),
    ({'economics':{'terms':{'expiryDate':'2027-02-01'}}},('2027-02-01','Expiry')),
    ({'valuationConventions':{'maturityDate':'2027-03-01'}},('2027-03-01','Maturity')),
    ({'economics':{'terms':{'convention':{'kind':'FUTURE','lastTradingAtUtc':'2027-03-19T13:30:00+00:00','finalSettlementDate':'2027-03-22'}}}},('2027-03-19','Last trading')),
    ({},(None,None)),
    ({'economics':{'terms':{'maturityDate':'invalid'}}},(None,None)),
])
def test_contract_dates_come_from_frozen_terms_not_settlement_or_current_reference(payload,expected):
    from positions.holdings_repository import holding_contract_date
    assert holding_contract_date(payload)==expected


def test_position_rows_group_by_booked_instrument_type_then_name_before_pagination():
    from apps.reference_api.strategy_workspace import position_rows
    facts=[booked(1,'2',product_basis='SWAP',subject_id=UUID(int=11)),
           booked(2,'3',product_basis='EQUITY',subject_id=UUID(int=12)),
           booked(3,'4',product_basis='EQUITY',subject_id=UUID(int=13)),
           booked(4,'5',product_basis='BOND',subject_id=UUID(int=14)),
           booked(5,'6',product_basis='OPTION_BOOKING',subject_id=UUID(int=15))]
    names=['A swap','zebra equity','Alpha equity','Z bond','An option']
    descriptions={fact.booking.trade_id:dict(name=name,instrumentId=str(fact.booking.subject_id),currency='GBP') for fact,name in zip(facts,names)}
    rows=position_rows(project_holdings(facts,request()),descriptions)
    assert [(row['instrumentType'],row['instrumentTypeLabel'],row['name']) for row in rows]==[
        ('BOND','Bonds','Z bond'),('EQUITY','Equities','Alpha equity'),('EQUITY','Equities','zebra equity'),
        ('OPTION','Options','An option'),('SWAP','Swaps','A swap')]
    assert [row['name'] for row in rows[1:3]]==['Alpha equity','zebra equity']

def test_short_and_closed_reopened_holdings():
    result=project_holdings([booked(1,'100'),booked(2,'-150')],request())
    assert result.buckets[0].closing_quantity==D('-50')
    result=project_holdings([booked(1,'100'),booked(2,'-100'),booked(3,'20')],request())
    assert result.buckets[0].closing_quantity==20
    assert len(result.facts)==3  # Earlier closed history stays inspectable.

def test_zero_holdings_are_retained_for_optional_closed_view():
    result=project_holdings([booked(1,'100'),booked(2,'-100')],request())
    assert result.buckets[0].closing_quantity==0

def test_execution_basis_ignores_later_valuation_recognition():
    fact=booked(1,'10',valuation_effective_date=END.date()+timedelta(days=1))
    assert project_holdings([fact],request()).buckets[0].closing_quantity==10
    assert project_holdings([fact],request(),basis='VALUATION_RECOGNISED').buckets==()

def test_cancelled_booking_is_not_a_sell_and_cutoff_retains_older_state():
    fact=booked(1,'10')
    cancel=replace(fact,event_id=UUID(int=999),sequence=2,kind='CANCELLED',booking=None,recorded_at=INFO)
    assert project_holdings([fact,cancel],request()).buckets==()
    assert project_holdings([fact,cancel],request(information_cutoff=INFO-timedelta(seconds=1))).buckets[0].closing_quantity==10

def test_different_contract_currency_or_unit_conventions_do_not_net():
    facts=[booked(1,'10'),booked(2,'-10',subject_id=UUID(int=66)),booked(3,'-10',currency_id=UUID(int=67)),booked(4,'-10',unit_multiplier=D('50'))]
    assert len(project_holdings(facts,request()).buckets)==4

def test_reviewed_split_adjusts_units_without_rewriting_trade():
    fact=booked(1,'100',product_basis='EQUITY',quantity_unit='SHARES')
    split=SplitEvent(UUID(int=70),UUID(int=71),SUBJECT,END-timedelta(days=3),END.date()-timedelta(days=3),END,D('2'),False,{'source':'mock'})
    sale=booked(8,'-50',product_basis='EQUITY',quantity_unit='SHARES')
    result=project_holdings([fact,sale],request(),splits=[split])
    assert result.buckets[0].closing_quantity==150
    assert fact.booking.quantity==100
    assert result.split_adjustments[0].quantity_after==200

def test_unknown_date_basis_is_rejected():
    with pytest.raises(ValueError):project_holdings([],request(),basis='SETTLEMENT')

def test_more_than_one_thousand_trades_are_included_without_float_rounding():
    facts=[replace(booked(n,'0.000000000001'),effective_at=END-timedelta(days=1)) for n in range(1,1002)]
    assert project_holdings(facts,request()).buckets[0].closing_quantity==D('0.000000001001')

def test_forward_maturity_and_original_booking_share_the_same_quantity_identity():
    opened=holding_conventions({'kind':'FX_FORWARD_BOOKING'},'CURRENCY_AMOUNT')
    closed=holding_conventions({'kind':'FX_FORWARD_MATURITY'},'CURRENCY_AMOUNT')
    assert opened==closed==('FX_FORWARD',D('1'),D('1'))

def test_product_and_option_frozen_unit_conventions_are_not_discarded():
    assert holding_conventions({'kind':'PRODUCT_BOOKING','economics':{'terms':{'convention':{'kind':'FUTURE','monetaryMultiplier':'50','quoteFactor':'1'}}}},'CONTRACTS')==('FUTURE',D('50'),D('1'))
    assert holding_conventions({'kind':'OPTION_BOOKING','economics':{'terms':{'premiumMultiplier':'100','quoteFactor':'1'}}},'CONTRACTS')==('OPTION',D('100'),D('1'))
