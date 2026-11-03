"""Typed unit changes must not create zero-cost purchase gains."""
from dataclasses import replace
from decimal import Decimal as D
from datetime import timedelta
import pytest
from tests.test_position_reconstruction import booked,request,OPEN,CLOSE,CURRENCY
from positions.reconstruction import reconstruct
from valuation.position_calculation import required_marks,attribute_projection,MarkKey


def movement(n,quantity,when,kind='TRANSFER'):
    return booked(n,quantity,when,'0',product_basis='FUND',quantity_unit='UNITS',product_evidence=dict(quantityMovement=dict(
        schemaVersion=1,kind=kind,signedQuantity=quantity,recognitionBasis='POLICY_DAY_END',incomeRecognition='UNASSESSED' if kind=='REINVESTMENT' else 'NOT_APPLICABLE',
        reason='Synthetic sourced unit movement')))


def test_plain_zero_price_fund_booking_remains_invalid():
    with pytest.raises(ValueError,match='positive'):
        reconstruct([booked(1,'10',CLOSE,'0',product_basis='FUND',quantity_unit='UNITS')],request(daily=True))


def test_transfer_in_adds_holdings_without_creating_profit():
    p=reconstruct([movement(1,'10',CLOSE)],request(daily=True))
    marks={MarkKey(p.buckets[0].key.subject_id,CLOSE):D('12')}
    r=attribute_projection(p,marks,CURRENCY)
    assert p.buckets[0].closing_quantity==10
    assert r.closing_value==120 and r.execution_value==120 and r.market_pnl==0


def test_movement_requires_a_policy_nav_and_an_explicit_daily_boundary():
    p=reconstruct([movement(1,'10',CLOSE)],request(daily=True))
    with pytest.raises(ValueError,match='mark|NAV'):attribute_projection(p,{},CURRENCY)
    with pytest.raises(ValueError,match='daily'):
        attribute_projection(replace(p,request=replace(p.request,daily=False)),{MarkKey(p.buckets[0].key.subject_id,CLOSE):D(12)},CURRENCY)


def test_transfer_out_requires_closing_nav_even_when_position_is_flat():
    original=booked(1,'10',OPEN,'8',product_basis='FUND',quantity_unit='UNITS')
    p=reconstruct([original,movement(2,'-10',CLOSE)],request(daily=True))
    subject=p.buckets[0].key.subject_id
    assert {m.key.cutoff for m in required_marks(p)}=={OPEN,CLOSE}
    r=attribute_projection(p,{MarkKey(subject,OPEN):D(10),MarkKey(subject,CLOSE):D(12)},CURRENCY)
    assert r.opening_value==100 and r.closing_value==0 and r.execution_value==-120 and r.market_pnl==20


def test_historical_movements_contribute_to_ordinary_next_day_price_pnl():
    p=reconstruct([movement(1,'10',OPEN-timedelta(days=100))],request(daily=True))
    subject=p.buckets[0].key.subject_id
    r=attribute_projection(p,{MarkKey(subject,OPEN):D(10),MarkKey(subject,CLOSE):D(12)},CURRENCY)
    assert r.market_pnl==20 and r.execution_value==0


def test_reinvestment_has_separate_unassessed_income_warning_not_market_gain():
    p=reconstruct([movement(1,'2',CLOSE,'REINVESTMENT')],request(daily=True))
    subject=p.buckets[0].key.subject_id
    r=attribute_projection(p,{MarkKey(subject,CLOSE):D(10)},CURRENCY)
    assert r.market_pnl==0 and r.lines[0].gross_pnl==0
    assert any(e['kind']=='REINVESTMENT_INCOME_NOT_ASSESSED' for e in r.lines[0].economic_evidence)


def test_movement_cannot_smuggle_a_different_quantity_or_product():
    f=movement(1,'2',CLOSE)
    for b in [replace(f.booking,quantity=D(3)),replace(f.booking,product_basis='BOND')]:
        with pytest.raises(ValueError):reconstruct([replace(f,booking=b)],request(daily=True))


def test_foreign_transfer_does_not_acquire_overnight_fx_profit():
    from uuid import uuid4
    old=booked(1,'10',OPEN,'10',product_basis='FUND',quantity_unit='UNITS')
    p=reconstruct([old,movement(2,'2',CLOSE)],request(daily=True));subject=p.buckets[0].key.subject_id
    result=attribute_projection(p,{MarkKey(subject,OPEN):D(10),MarkKey(subject,CLOSE):D(12)},uuid4(),
        {(CURRENCY,OPEN):D(1),(CURRENCY,CLOSE):D(2)})
    assert result.execution_value==48 and result.closing_value==288 and result.market_pnl==140


def test_offsetting_transfers_preserve_both_events_without_profit_or_holdings():
    p=reconstruct([movement(1,'2',CLOSE),movement(2,'-2',CLOSE)],request(daily=True));subject=p.buckets[0].key.subject_id
    result=attribute_projection(p,{MarkKey(subject,CLOSE):D(12)},CURRENCY)
    assert len(p.executions)==2 and result.market_pnl==0 and result.execution_value==0 and result.closing_value==0
