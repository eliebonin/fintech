"""Real tenant-scoped interest/payment sources; no operating database writes."""
from dataclasses import replace
from datetime import date,datetime,timedelta,timezone
from decimal import Decimal as D
from uuid import uuid4

import pytest
from sqlalchemy import select
from security_master_schema.demo_data import DEMO_IDS as ids
from tests.test_valuation_service import valued,service
from tests.test_economic_pnl_acceptance import add_bond,staged,reviewer
from valuation.accruals import record_accrual


def daily(c,r,day,amount='10',**extra):
    return record_accrual(c,r.tenant_id,ids['demo_user_account'],dict(strategyId=r.strategy_id,
        instrumentId=ids['bond_instrument_node'],valueDate=day,inputType='DAILY_INTEREST',dailyEarned=D(amount),
        currencyId=ids['gbp_currency'],sourceReference='Synthetic earned interest')|extra,str(uuid4()))


def calculated(c,r):
    """Explicit stage 2 precedes FX valuation in the maintained-history workflow."""
    from valuation.balance_history import refresh_history
    from valuation.balance_history_contracts import BalanceHistoryRefresh
    refresh_history(c,r.tenant_id,ids['demo_user_account'],BalanceHistoryRefresh(strategyId=r.strategy_id,
        fromDate=r.opening_cutoff.date()+timedelta(days=1),toDate=r.closing_cutoff.date(),
        informationCutoff=min(r.information_cutoff,datetime.now(timezone.utc))),uuid4().hex)
    return service().calculate(c,r)


def test_default_missing_balance_history_is_partial_not_a_failed_valuation(valued):
    c,r,trade=valued;add_bond(c,r,trade)
    result=calculated(c,r)
    assert result.gross_pnl==result.period.market_pnl
    coverage=result.evidence['accruedBalanceCoverage']
    assert coverage['missingCount']>0
    assert result.evidence['pnlCompleteness']=='PARTIAL'
    batch=staged(c,r,result)
    from valuation import storage
    storage.publish(c,r.tenant_id,batch,reviewer(c),'Partial interest coverage explicitly reviewed')
    assert storage.batch_view(c,r.tenant_id,batch)['status']=='PUBLISHED'


def test_complete_daily_history_reconstructs_bought_accrued_without_quantity_multiplication(valued):
    c,r,trade=valued;add_bond(c,r,trade)
    daily(c,r,date(2026,9,30));daily(c,r,date(2026,10,1))
    result=calculated(c,r)
    assert result.gross_pnl==result.period.market_pnl+D(20)
    balance=result.accrued_balance.lines[0]
    assert balance.days[0].balance.closing==D(1260)
    assert balance.days[1].balance.opening==D(1260)
    assert balance.days[1].amount==0  # Identity currency, not unassessed.
    assert sum(line.components().get('CARRY',D(0)) for line in result.period.lines)==0


def test_foreign_stock_fx_uses_real_governed_rates_and_keeps_local_anchor_independent(valued):
    from tests.test_valuation_fx import test_service_freezes_independent_fx_inputs_and_uses_execution_day_rate
    test_service_freezes_independent_fx_inputs_and_uses_execution_day_rate(valued)
    c,r,trade=valued;add_bond(c,r,trade)
    daily(c,r,date(2026,9,30));daily(c,r,date(2026,10,1))
    base=calculated(c,r)
    from valuation.accrued_balance_inputs import load_accrued_balance_fx
    foreign=load_accrued_balance_fx(c,replace(r,reporting_currency_id=ids['usd_currency']),base.projection)
    day=foreign.lines[0].days[1]
    assert (day.opening_fx,day.closing_fx,day.amount)==(D('1.5'),D('2'),D('630'))
    assert len(day.fx_evidence)==2


def test_missing_optional_interest_fx_does_not_abort_valid_market_calculation(valued,monkeypatch):
    c,r,trade=valued;add_bond(c,r,trade)
    daily(c,r,date(2026,9,30),currencyId=ids['usd_currency'])
    daily(c,r,date(2026,10,1),currencyId=ids['usd_currency'])
    from valuation.fx import resolve_fx
    def missing(*args,**kwargs):
        if args[2]==args[3]:return resolve_fx(*args,**kwargs)
        raise ValueError('FX input selection blocked: NO_ELIGIBLE_OBSERVATION')
    monkeypatch.setattr('valuation.fx.resolve_fx',missing)
    result=calculated(c,r)
    assert result.gross_pnl==result.period.market_pnl
    assert result.evidence['accrualCoverage']['missingCount']==2
    assert result.evidence['accruedBalanceCoverage']['missingCount']>0


def test_malformed_optional_fx_evidence_is_not_swallowed_as_missing_data(valued,monkeypatch):
    c,r,trade=valued;add_bond(c,r,trade)
    daily(c,r,date(2026,9,30),currencyId=ids['usd_currency'])
    from valuation.fx import resolve_fx
    def invalid(*args,**kwargs):
        if args[2]==args[3]:return resolve_fx(*args,**kwargs)
        raise ValueError('FX selection currency orientation or rate semantics mismatch')
    monkeypatch.setattr('valuation.fx.resolve_fx',invalid)
    with pytest.raises(ValueError,match='orientation'):
        calculated(c,r)


def test_coupon_receipt_changes_stock_not_earned_income_and_blocks_stale_publication(valued):
    from lifecycle import coupon_service as coupons
    from lifecycle.coupon_contracts import ScheduleCreate,PaymentCreate
    from tests.test_bond_coupons import grant_coupon_ops,schedule_data
    from valuation import storage
    c,r,trade=valued;add_bond(c,r,trade)
    daily(c,r,date(2026,9,30));daily(c,r,date(2026,10,1))
    before=calculated(c,r);batch=staged(c,r,before)
    grant_coupon_ops(c,r.tenant_id,r.strategy_id)
    schedule=coupons.save_schedule(c,r.tenant_id,ids['demo_user_account'],ScheduleCreate.model_validate(schedule_data()),uuid4().hex)
    receipt=coupons.record_payment(c,r.tenant_id,ids['demo_user_account'],PaymentCreate(strategyId=r.strategy_id,
        periodId=schedule['cashflows'][0]['cashflow_id'],paymentDate='2026-10-01',amount='1000',currencyId=ids['gbp_currency'],
        sourceReference='Synthetic received coupon',confirmPayment=True),uuid4().hex)
    assert storage.batch_view(c,r.tenant_id,batch)['sourceHealth']['accruedBalanceChanged'] is True
    with pytest.raises(ValueError,match='inputs changed'):
        storage.publish(c,r.tenant_id,batch,reviewer(c),'Old receipt population must not publish')
    after=calculated(c,r)
    assert after.gross_pnl==before.gross_pnl
    assert after.accrued_balance.lines[0].days[-1].balance.closing==D('270')
    assert before.accrued_balance.lines[0].days[-1].balance.closing==D('1270')
    coupons.reverse_payment(c,r.tenant_id,ids['demo_user_account'],r.strategy_id,receipt['payment_id'],'Synthetic reversal',uuid4().hex)
    reversed_result=calculated(c,r)
    assert reversed_result.accrued_balance.lines[0].days[-1].balance.closing==D('1270')
    historical=calculated(c,replace(r,information_cutoff=receipt['recorded_at']))
    assert historical.accrued_balance.lines[0].days[-1].balance.closing==D('270')


def test_closed_security_keeps_outstanding_receivable_without_price_or_fake_trade(valued):
    import json
    from datetime import timedelta
    from security_master_schema import models as m
    from valuation import storage
    from valuation.evidence_access import batch_datasets
    c,r,trade=valued;buy=add_bond(c,r,trade)
    daily(c,r,date(2026,9,30));daily(c,r,date(2026,10,1))
    original=dict(c.execute(select(m.trade).where(m.trade.c.trade_id==buy)).mappings().one())
    booked=dict(c.execute(select(m.trade_lifecycle_event).where(m.trade_lifecycle_event.c.trade_id==buy)).mappings().one())
    sale=uuid4();at=r.closing_cutoff.replace(hour=10)
    c.execute(m.trade.insert().values(**(original|dict(trade_id=sale,quantity=-original['quantity'],trade_datetime_utc=at))))
    c.execute(m.trade_lifecycle_event.insert().values(**(booked|dict(trade_lifecycle_event_id=uuid4(),trade_id=sale,event_datetime_utc=at))))
    original_equity=c.execute(select(m.trade).where(m.trade.c.trade_id==trade)).mappings().one()
    c.execute(m.trade_lifecycle_event.insert().values(trade_id=trade,sequence_no=2,event_type='CANCELLED',
        event_datetime_utc=original_equity['trade_datetime_utc'],recorded_by_user_account_id=ids['demo_user_account'],event_payload='{}'))
    r=replace(r,opening_cutoff=r.closing_cutoff,closing_cutoff=r.closing_cutoff+timedelta(days=1))
    result=calculated(c,r)
    assert not result.period.lines and result.receivables
    assert result.receivables[0].days[0].balance.opening==20
    assert result.evidence['requiredMarkCount']==0
    batch=staged(c,r,result);view=storage.batch_view(c,r.tenant_id,batch)
    assert len(view['items'])==1 and view['items'][0]['trade_id'] is None
    assert view['items'][0]['evidence']['resultFormat']=='ACCRUED_RECEIVABLE_V1'
    assert batch_datasets(view)==set()
    from valuation import tables as vt
    row=dict(c.execute(select(vt.attribution).where(vt.attribution.c.attribution_id==view['items'][0]['attribution_id'])).mappings().one())
    with pytest.raises(Exception,match='scope/evidence mismatch'):
        with c.begin_nested():c.execute(vt.attribution.insert().values(**(row|dict(attribution_id=uuid4(),version=2,subject_id=ids['hsbc_instrument_node']))))
    with pytest.raises(Exception,match='amount differs'):
        with c.begin_nested():c.execute(vt.attribution.insert().values(**(row|dict(attribution_id=uuid4(),version=2,components={'CARRY':'1'},gross_pnl=1,net_pnl=1))))
    storage.publish(c,r.tenant_id,batch,reviewer(c),'Outstanding local receivable reviewed')


def test_derived_balance_dataset_is_typed_exact_immutable_and_attempt_scoped(valued):
    from valuation.accrued_balance_tables import balance_snapshot
    from valuation import storage
    c,r,trade=valued;add_bond(c,r,trade)
    daily(c,r,date(2026,9,30),'0.123456789012');daily(c,r,date(2026,10,1),'0.111111111111')
    result=calculated(c,r);batch=staged(c,r,result)
    header=storage.batch_view(c,r.tenant_id,batch)
    records=c.execute(select(balance_snapshot).where(balance_snapshot.c.attempt_id==header['attempt_id']).order_by(balance_snapshot.c.value_date)).mappings().all()
    assert records[-1]['opening_balance']==D('1250.123456789012')
    assert records[-1]['closing_balance']==D('1250.234567900123')
    assert records[-1]['fx_status']=='CALCULATED'
    from apps.reference_api.valuation_presentation import decorate_batch
    decorated=decorate_batch(c,r.tenant_id,header)
    stocks=[row for item in decorated['items'] for row in item['display']['accruedBalanceStocks']]
    assert D(stocks[-1]['openingReporting'])==D('1250.123456789012')
    assert D(stocks[-1]['closingReporting'])==D('1250.234567900123')
    assert decorated['summary']==header['summary']
    assert [item['evidence'] for item in decorated['items']]==[item['evidence'] for item in header['items']]
    with pytest.raises(Exception,match='attempt scope mismatch'):
        with c.begin_nested():c.execute(balance_snapshot.insert().values(**(dict(records[-1])|dict(balance_id=uuid4(),strategy_id=ids['strategy']))))
    with pytest.raises(Exception,match='canonical bond'):
        with c.begin_nested():c.execute(balance_snapshot.insert().values(**(dict(records[-1])|dict(balance_id=uuid4(),instrument_id=ids['hsbc_instrument_node']))))
    with pytest.raises(Exception,match='immutable'):
        with c.begin_nested():c.execute(balance_snapshot.update().values(closing_balance=0))
