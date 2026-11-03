"""Native maintained-history stages; disposable PostgreSQL only."""
from dataclasses import replace
from datetime import date,datetime,timedelta,timezone
from decimal import Decimal as D
from uuid import uuid4
import pytest
from sqlalchemy import select
from security_master_schema.demo_data import DEMO_IDS as ids
from tests.test_valuation_service import valued,service
from tests.test_economic_pnl_acceptance import add_bond
from tests.test_accrued_balance_integration import daily
from valuation.balance_history import refresh_history,record_balance_input,list_history
from valuation.balance_history_contracts import BalanceHistoryRefresh,BalanceInputCreate


def refresh(c,r,**changes):
    return refresh_history(c,r.tenant_id,ids['demo_user_account'],BalanceHistoryRefresh(strategyId=r.strategy_id,
        fromDate=r.opening_cutoff.date()+timedelta(days=1),toDate=r.closing_cutoff.date(),**changes),uuid4().hex)


def test_explicit_refresh_retains_local_history_and_valuation_consumes_it(valued,monkeypatch):
    c,r,trade=valued;add_bond(c,r,trade)
    daily(c,r,date(2026,9,30));daily(c,r,date(2026,10,1))
    before=service().calculate(c,r)
    assert before.evidence['accruedBalanceCoverage']['missingCount']>0
    build=refresh(c,r)
    rows=list_history(c,r.tenant_id,ids['demo_user_account'],r.strategy_id,date(2026,9,30),date(2026,10,1),r.information_cutoff)
    assert len(rows)==2 and rows[0]['closing_balance']==1260 and rows[1]['opening_balance']==1260
    monkeypatch.setattr('valuation.accrued_balance_inputs.reconstruct_local_balances',lambda *a,**k:pytest.fail('Valuation must read maintained history'))
    result=service().calculate(c,r)
    assert result.accrued_balance.lines[0].days[1].balance.opening==1260
    assert result.accrued_balance.lines[0].days[1].amount==0
    assert str(build['build_id']) in str(result.accrued_balance.lines[0].source_refs)


def test_independent_balance_anchor_bridges_missing_history_and_is_revisioned(valued):
    c,r,trade=valued;add_bond(c,r,trade);daily(c,r,date(2026,10,1))
    payload=BalanceInputCreate(strategyId=r.strategy_id,instrumentId=ids['bond_instrument_node'],currencyId=ids['gbp_currency'],
        valueDate='2026-09-30',closingBalance='5000',sourceReference='Synthetic assessed EoD stock',reason='Reconciliation anchor')
    key=uuid4().hex;anchor=record_balance_input(c,r.tenant_id,ids['demo_user_account'],payload,key)
    assert record_balance_input(c,r.tenant_id,ids['demo_user_account'],payload,key)['input_id']==anchor['input_id']
    refresh(c,r)
    result=service().calculate(c,r);day=result.accrued_balance.lines[0].days[-1]
    assert day.balance.opening==5000 and day.balance.closing==5010
    changed=payload.model_copy(update={'closing_balance':D('6000'),'supersedes_input_id':anchor['input_id']})
    record_balance_input(c,r.tenant_id,ids['demo_user_account'],changed,uuid4().hex)
    stale=service().calculate(c,r)
    assert any(x['reason']=='STALE_ACCRUED_BALANCE_HISTORY' for x in stale.evidence['accruedBalanceCoverage']['missing'])
    refresh(c,r)
    assert service().calculate(c,r).accrued_balance.lines[0].days[-1].balance.opening==6000


def test_refresh_retry_is_stable_and_history_is_immutable(valued):
    from valuation import balance_history_tables as t
    c,r,trade=valued;add_bond(c,r,trade);daily(c,r,date(2026,9,30))
    payload=BalanceHistoryRefresh(strategyId=r.strategy_id,fromDate='2026-09-30',toDate='2026-10-01');key=uuid4().hex
    a=refresh_history(c,r.tenant_id,ids['demo_user_account'],payload,key)
    assert refresh_history(c,r.tenant_id,ids['demo_user_account'],payload,key)['build_id']==a['build_id']
    with pytest.raises(Exception,match='immutable'):
        with c.begin_nested():c.execute(t.history_day.update().where(t.history_day.c.build_id==a['build_id']).values(closing_balance=0))
    with pytest.raises(ValueError,match='different content'):
        refresh_history(c,r.tenant_id,ids['demo_user_account'],payload.model_copy(update={'from_date':date(2026,10,1)}),key)


def test_new_assessed_stock_requires_recalculation_before_publication(valued):
    from tests.test_economic_pnl_acceptance import staged,reviewer
    from valuation import storage
    c,r,trade=valued;add_bond(c,r,trade)
    daily(c,r,date(2026,9,30));daily(c,r,date(2026,10,1));refresh(c,r)
    batch=staged(c,r,service().calculate(c,r))
    record_balance_input(c,r.tenant_id,ids['demo_user_account'],BalanceInputCreate(strategyId=r.strategy_id,
        instrumentId=ids['bond_instrument_node'],currencyId=ids['gbp_currency'],valueDate='2026-09-30',closingBalance='5000',
        sourceReference='Synthetic assessed stock',reason='Reconcile retained stock'),uuid4().hex)
    assert storage.batch_view(c,r.tenant_id,batch)['sourceHealth']['accruedBalanceChanged'] is True
    with pytest.raises(ValueError,match='inputs changed'):
        storage.publish(c,r.tenant_id,batch,reviewer(c),'Superseded stock must not publish')


def test_unchanged_update_reuses_history_without_invalidating_staged_evidence(valued):
    from sqlalchemy import func
    from valuation import balance_history_tables as t
    from valuation.accrued_balance_health import capture_balance_sources
    c,r,trade=valued;add_bond(c,r,trade);daily(c,r,date(2026,9,30))
    refresh(c,r);before=capture_balance_sources(c,r)
    count=c.scalar(select(func.count()).select_from(t.history_day).where(t.history_day.c.strategy_id==r.strategy_id))
    repeated=refresh(c,r)
    assert repeated['reusedBuildId']
    assert c.scalar(select(func.count()).select_from(t.history_day).where(t.history_day.c.strategy_id==r.strategy_id))==count
    assert capture_balance_sources(c,r)==before


def test_history_built_later_can_reproduce_only_sources_known_at_its_cutoff(valued):
    c,r,trade=valued;add_bond(c,r,trade);daily(c,r,date(2026,10,1))
    source=BalanceInputCreate(strategyId=r.strategy_id,instrumentId=ids['bond_instrument_node'],currencyId=ids['gbp_currency'],
        valueDate='2026-09-30',closingBalance='5000',sourceReference='Synthetic historical statement',reason='Assessed balance')
    original=record_balance_input(c,r.tenant_id,ids['demo_user_account'],source,uuid4().hex)
    historical=datetime.now(timezone.utc)
    record_balance_input(c,r.tenant_id,ids['demo_user_account'],source.model_copy(update={'closing_balance':D('6000'),'supersedes_input_id':original['input_id']}),uuid4().hex)
    refresh(c,r)
    refresh(c,r,informationCutoff=historical)
    assert service().calculate(c,replace(r,information_cutoff=historical)).accrued_balance.lines[0].days[-1].balance.opening==5000
    assert service().calculate(c,r).accrued_balance.lines[0].days[-1].balance.opening==6000


def test_coupon_receipts_clear_only_the_paid_stock_and_reversals_restore_it(valued):
    from lifecycle import coupon_service as coupons
    from lifecycle.coupon_contracts import ScheduleCreate,PaymentCreate
    from tests.test_bond_coupons import grant_coupon_ops,schedule_data
    c,r,trade=valued;add_bond(c,r,trade);daily(c,r,date(2026,10,1),'20')
    source=BalanceInputCreate(strategyId=r.strategy_id,instrumentId=ids['bond_instrument_node'],currencyId=ids['gbp_currency'],
        valueDate='2026-09-30',closingBalance='1000',sourceReference='Synthetic opening coupon stock',reason='Assessed balance')
    record_balance_input(c,r.tenant_id,ids['demo_user_account'],source,uuid4().hex)
    grant_coupon_ops(c,r.tenant_id,r.strategy_id)
    schedule=coupons.save_schedule(c,r.tenant_id,ids['demo_user_account'],ScheduleCreate.model_validate(schedule_data()),uuid4().hex)
    payment=coupons.record_payment(c,r.tenant_id,ids['demo_user_account'],PaymentCreate(strategyId=r.strategy_id,periodId=schedule['cashflows'][0]['cashflow_id'],
        paymentDate='2026-10-01',amount='1000',currencyId=ids['gbp_currency'],sourceReference='Synthetic full coupon receipt',confirmPayment=True),uuid4().hex)
    refresh(c,r);paid=service().calculate(c,r)
    assert paid.accrued_balance.lines[0].days[-1].balance.closing==20
    coupons.reverse_payment(c,r.tenant_id,ids['demo_user_account'],r.strategy_id,payment['payment_id'],'Synthetic reversal',uuid4().hex)
    refresh(c,r);reversed_result=service().calculate(c,r)
    assert reversed_result.accrued_balance.lines[0].days[-1].balance.closing==1020
    assert paid.gross_pnl==reversed_result.gross_pnl  # Receipt/reversal is not new income.


def test_outstanding_receivable_is_disclosed_when_later_history_has_not_been_updated(valued):
    from types import SimpleNamespace
    from valuation.accrued_balance_inputs import load_accrued_balance_fx
    c,r,_=valued
    record_balance_input(c,r.tenant_id,ids['demo_user_account'],BalanceInputCreate(strategyId=r.strategy_id,
        instrumentId=ids['bond_instrument_node'],currencyId=ids['gbp_currency'],valueDate='2026-09-30',closingBalance='5000',
        sourceReference='Synthetic unpaid coupon receivable',reason='Assessed stock after disposal'),uuid4().hex)
    refresh(c,r)
    later=replace(r,opening_cutoff=r.closing_cutoff+timedelta(days=1),closing_cutoff=r.closing_cutoff+timedelta(days=2))
    result=load_accrued_balance_fx(c,later,SimpleNamespace(facts=(),buckets=()))
    assert len(result.lines)==1 and result.coverage['missingCount']==1
    assert result.lines[0].days[0].amount is None


def test_database_rejects_a_balance_revision_linked_to_another_strategy(valued):
    from valuation.balance_history_tables import balance_input
    c,r,_=valued
    payload=BalanceInputCreate(strategyId=r.strategy_id,instrumentId=ids['bond_instrument_node'],currencyId=ids['gbp_currency'],
        valueDate='2026-09-30',closingBalance='1000',sourceReference='Synthetic assessed stock',reason='Input scope check')
    original=record_balance_input(c,r.tenant_id,ids['demo_user_account'],payload,uuid4().hex)
    foreign=record_balance_input(c,r.tenant_id,ids['demo_user_account'],payload.model_copy(update={'strategy_id':ids['strategy']}),uuid4().hex)
    forged={k:v for k,v in original.items() if k!='input_id'}
    forged.update(revision=2,supersedes_input_id=foreign['input_id'],submission_key=uuid4().hex)
    with pytest.raises(Exception,match='revision scope'):
        with c.begin_nested():c.execute(balance_input.insert().values(**forged))


def test_next_day_update_uses_a_source_verified_balance_checkpoint(valued,monkeypatch):
    from valuation import accrued_balance_inputs as inputs
    c,r,trade=valued;add_bond(c,r,trade)
    daily(c,r,date(2026,9,30));daily(c,r,date(2026,10,1));refresh(c,r)
    daily(c,r,date(2026,10,2))
    original=inputs.reconstruct_local_balances;seen=[]
    def inspected(*args,**kwargs):
        seen.extend(kwargs.get('history_checkpoints',()))
        return original(*args,**kwargs)
    monkeypatch.setattr(inputs,'reconstruct_local_balances',inspected)
    next_day=replace(r,opening_cutoff=r.closing_cutoff,closing_cutoff=r.closing_cutoff+timedelta(days=1))
    refresh(c,next_day)
    assert seen and seen[0]['value_date']==date(2026,10,1)
    rows=list_history(c,r.tenant_id,ids['demo_user_account'],r.strategy_id,date(2026,10,2),date(2026,10,2),r.information_cutoff)
    assert rows[0]['opening_balance']==1270 and rows[0]['closing_balance']==1280
    seen.clear()
    record_balance_input(c,r.tenant_id,ids['demo_user_account'],BalanceInputCreate(strategyId=r.strategy_id,
        instrumentId=ids['bond_instrument_node'],currencyId=ids['gbp_currency'],valueDate='2026-09-30',closingBalance='5000',
        sourceReference='Synthetic backdated stock correction',reason='Invalidate derived checkpoint'),uuid4().hex)
    refresh(c,next_day)
    assert not seen
    rows=list_history(c,r.tenant_id,ids['demo_user_account'],r.strategy_id,date(2026,10,2),date(2026,10,2),r.information_cutoff)
    assert rows[0]['opening_balance']==5010 and rows[0]['closing_balance']==5020
