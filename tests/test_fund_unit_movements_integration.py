"""Native fund movement authority, retry, immutable projection and review signals."""
from datetime import datetime,time,timezone,timedelta
from decimal import Decimal as D
from uuid import uuid4
import json
import pytest
from sqlalchemy import select,func
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from tests.test_valuation_service import valued
from tests.test_cash_product_pnl_integration import ready
from trading.position_movements import FundUnitMovementRequest,book_fund_unit_movement


def movement(r,listing,kind='TRANSFER',side='BUY',q='2',day=None):
    day=day or r.closing_cutoff.date()
    return FundUnitMovementRequest(listingId=listing,strategyId=r.strategy_id,side=side,quantity=q,
        tradeDatetime=datetime.combine(day,time(10),timezone.utc),settlementDate=day,
        movementKind=kind,movementReason='Synthetic owner-classified unit movement')


def test_native_fund_movement_projects_and_replays_without_cash(valued):
    from positions.repository import iter_ledger_facts
    from positions.contracts import ProjectionRequest
    from positions.reconstruction import reconstruct
    from positions.holdings_repository import load_holdings_facts
    c,r,_,listing,_,_,_=ready(valued,'FUND_SHARE_CLASS')
    request=movement(r,listing);key=uuid4().hex
    before=c.scalar(select(func.count()).select_from(m.cash_balance))
    native=book_fund_unit_movement(c,r.tenant_id,ids['demo_user_account'],request,key)
    assert book_fund_unit_movement(c,r.tenant_id,ids['demo_user_account'],request,key)==native
    row=c.execute(select(m.trade).where(m.trade.c.trade_id==native.trade_id)).mappings().one()
    assert row['trade_type']=='TRANSFER' and row['quantity']==2 and row['execution_price']==0
    assert c.scalar(select(func.count()).select_from(m.cash_balance))==before
    pr=ProjectionRequest(r.tenant_id,r.strategy_id,r.closing_cutoff,r.information_cutoff,r.opening_cutoff,'PERIOD',True)
    facts=tuple(iter_ledger_facts(c,pr));projected=reconstruct(facts,pr)
    assert next(b.closing_quantity for b in projected.buckets if b.key.subject_id==listing)==2
    holdings,_=load_holdings_facts(c,pr)
    assert next(f.booking.quantity for f in holdings if f.trade_id==native.trade_id and f.booking)==2
    from trading.booking import book_cash_trade
    with pytest.raises(ValueError,match='positive'):book_cash_trade(c,r.tenant_id,ids['demo_user_account'],request,uuid4().hex)
    with pytest.raises(PermissionError):book_fund_unit_movement(c,uuid4(),ids['demo_user_account'],request,key)


def test_regular_security_cannot_be_substituted_and_reinvestments_cannot_remove_units(valued):
    c,r,_,listing,_,_,_=ready(valued,'ETN')
    with pytest.raises(ValueError,match='fund'):book_fund_unit_movement(c,r.tenant_id,ids['demo_user_account'],movement(r,listing),uuid4().hex)
    with pytest.raises(ValueError,match='add units'):movement(r,listing,'REINVESTMENT',side='SELL')


def test_movement_retry_checks_current_authority_before_returning_identity(valued):
    c,r,_,listing,_,_,_=ready(valued,'FUND_SHARE_CLASS');key=uuid4().hex;request=movement(r,listing)
    book_fund_unit_movement(c,r.tenant_id,ids['demo_user_account'],request,key)
    c.execute(m.user_account.update().where(m.user_account.c.user_account_id==ids['demo_user_account']).values(status='SUSPENDED'))
    with pytest.raises(PermissionError):book_fund_unit_movement(c,r.tenant_id,ids['demo_user_account'],request,key)


def test_transfer_out_keeps_all_native_quantity_digits(valued):
    c,r,_,listing,_,_,_=ready(valued,'FUND_SHARE_CLASS')
    q='999999999999999999.123456789012'
    native=book_fund_unit_movement(c,r.tenant_id,ids['demo_user_account'],movement(r,listing,side='SELL',q=q),uuid4().hex)
    stored=c.scalar(select(m.trade.c.quantity).where(m.trade.c.trade_id==native.trade_id))
    assert stored==D('-'+q)
    frozen=json.loads(c.scalar(select(m.trade_lifecycle_event.c.event_payload).where(m.trade_lifecycle_event.c.trade_id==native.trade_id)))
    assert D(frozen['quantityMovement']['signedQuantity'])==stored


def test_real_nav_selection_stages_reinvestment_with_a_nonblocking_income_warning(valued):
    from dataclasses import replace
    from tests.test_trade_corrections import cancel
    from valuation.service import calculate_position
    from valuation.review_coverage import position_attention
    from tests.test_cash_product_pnl_integration import cash_line,stage
    from valuation.storage import batch_view
    # The shared fixture's unrelated equity is not part of this fund-only case.
    cancel(valued[0],valued[2])
    c,r,parent,listing,series,rule,_=ready(valued,'FUND_SHARE_CLASS')
    r=replace(r,daily=True,opening_cutoff=r.closing_cutoff-timedelta(days=1))
    c.execute(m.market_data_series.update().where(m.market_data_series.c.market_data_series_id==series).values(reference_node_id=parent,series_type='NAV'))
    c.execute(m.valuation_policy_rule.update().where(m.valuation_policy_rule.c.valuation_policy_rule_id==rule).values(
        subject_type='INSTRUMENT',subject_reference_node_id=parent,series_type='NAV',pricing_convention='NAV_DATE'))
    book_fund_unit_movement(c,r.tenant_id,ids['demo_user_account'],movement(r,listing,'REINVESTMENT'),uuid4().hex)
    result=calculate_position(c,r);line=cash_line(result,listing)
    assert line.bucket.closing_quantity==2 and line.attribution.market_pnl==0
    assert result.evidence['pnlCompleteness']=='PARTIAL'
    assert 'Reinvestment income unassessed' in position_attention(dict(economicInputs=line.economic_evidence))
    batch=stage(c,r,result);stored=batch_view(c,r.tenant_id,batch)
    item=next(i for i in stored['items'] if i['subject_id']==listing)
    assert item['market_pnl']==0 and line.attribution.closing_value==220


def test_movement_can_be_cancelled_but_not_replaced_by_an_ordinary_purchase(valued):
    from tests.test_trade_corrections import cancel
    from trading.corrections import _chain,CorrectionConflict
    from positions.repository import iter_ledger_facts
    from positions.contracts import ProjectionRequest
    from positions.reconstruction import reconstruct
    c,r,_,listing,_,_,_=ready(valued,'FUND_SHARE_CLASS')
    native=book_fund_unit_movement(c,r.tenant_id,ids['demo_user_account'],movement(r,listing),uuid4().hex)
    row=c.execute(select(m.trade).where(m.trade.c.trade_id==native.trade_id)).mappings().one()
    with pytest.raises(CorrectionConflict):_chain(c,row,1)
    result=cancel(c,native.trade_id).data
    assert result.trade.lifecycle_status=='CANCELLED'
    assert [e.event_type for e in result.lifecycle_events]==['BOOKED','CANCELLED']
    assert json.loads(result.lifecycle_events[0].event_payload)['quantityMovement']['kind']=='TRANSFER'
    pr=ProjectionRequest(r.tenant_id,r.strategy_id,r.closing_cutoff,r.information_cutoff,r.opening_cutoff,'PERIOD',True)
    assert not any(b.key.subject_id==listing for b in reconstruct(tuple(iter_ledger_facts(c,pr)),pr).buckets)


def test_same_currency_multi_day_transfers_use_each_movement_days_nav(valued):
    from dataclasses import replace
    from tests.test_trade_corrections import cancel
    from valuation.service import calculate_position
    from tests.test_cash_product_pnl_integration import cash_line
    cancel(valued[0],valued[2])
    c,r,parent,listing,series,rule,_=ready(valued,'FUND_SHARE_CLASS');r=replace(r,daily=True)
    c.execute(m.market_data_series.update().where(m.market_data_series.c.market_data_series_id==series).values(reference_node_id=parent,series_type='NAV'))
    c.execute(m.valuation_policy_rule.update().where(m.valuation_policy_rule.c.valuation_policy_rule_id==rule).values(
        subject_type='INSTRUMENT',subject_reference_node_id=parent,series_type='NAV',pricing_convention='NAV_DATE'))
    observation=dict(c.execute(select(m.market_data_observation).where(m.market_data_observation.c.market_data_series_id==series).order_by(m.market_data_observation.c.market_date)).mappings().first())
    day=r.closing_cutoff.date()-timedelta(days=1);stamp=datetime.combine(day,time(16),timezone.utc)
    observation.update(market_data_observation_id=uuid4(),market_date=day,value=D(100),observed_at_utc=stamp,received_at_utc=stamp,
        source_published_at_utc=stamp,source_observation_key='FUND_MOVE_'+uuid4().hex)
    c.execute(m.market_data_observation.insert().values(**observation))
    book_fund_unit_movement(c,r.tenant_id,ids['demo_user_account'],movement(r,listing,q='2',day=day),uuid4().hex)
    book_fund_unit_movement(c,r.tenant_id,ids['demo_user_account'],movement(r,listing,side='SELL',q='1'),uuid4().hex)
    result=calculate_position(c,r);line=cash_line(result,listing)
    assert line.bucket.closing_quantity==1 and line.attribution.market_pnl==20
    assert line.execution_value==90 and line.attribution.closing_value==110
    assert result.evidence['dailyBridgeCount']==2
