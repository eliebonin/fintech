from datetime import date
from uuid import uuid4
import pytest
from sqlalchemy import select,func
from tests.test_valuation_service import valued
from tests.test_economic_pnl_acceptance import add_bond
from tests.test_accrued_balance_integration import daily
from security_master_schema.demo_data import DEMO_IDS as ids
from valuation.interest_review import review_view,save_review
from valuation.interest_review_contracts import ReviewCommand
from valuation import interest_review_tables as t


def command(view,stage,**updates):
    return ReviewCommand(strategyId=view['strategyId'],valueDate=view['valueDate'],stage=stage,state='VALIDATED',sourceHash=view['sourceHash'],
        supersedesReviewId=view['review']['review_id'] if view['review'] else None,
        rows=[dict(instrumentId=r['instrumentId'],currencyId=r['currencyId'],amount=r['amount'],coveredDays=r['coveredDays'],
                   sourceReference=r['sourceReference'],reason='Ops assessment',decision=r['decision'],**updates) for r in view['rows']])


def test_balance_review_requires_current_daily_validation_and_retains_typed_receipt(valued):
    c,r,trade=valued;add_bond(c,r,trade);daily(c,r,date(2026,9,30));daily(c,r,date(2026,10,1))
    actor=ids['demo_user_account'];day=date(2026,10,1)
    with pytest.raises(ValueError,match='daily'):
        review_view(c,r.tenant_id,actor,r.strategy_id,day,'BALANCE')
    view=review_view(c,r.tenant_id,actor,r.strategy_id,day,'DAILY')
    payload=command(view,'DAILY');key=uuid4().hex
    receipt=save_review(c,r.tenant_id,actor,actor,payload,key)
    assert receipt['state']=='VALIDATED'
    assert save_review(c,r.tenant_id,actor,actor,payload,key)['review_id']==receipt['review_id']
    assert c.scalar(select(func.count()).select_from(t.item).where(t.item.c.review_id==receipt['review_id']))==len(view['rows'])
    balances=review_view(c,r.tenant_id,actor,r.strategy_id,day,'BALANCE')
    assert balances['dailyReviewId']==str(receipt['review_id'])
    assert balances['rows'][0]['dailyIncrement']=='10'
    final=save_review(c,r.tenant_id,actor,actor,command(balances,'BALANCE'),uuid4().hex)
    assert final['state']=='VALIDATED'
    after=review_view(c,r.tenant_id,actor,r.strategy_id,day,'BALANCE')
    assert after['reviewCurrent'] and after['dailyValidated']
    assert after['review']['items'][0]['balance_input_id']
    # Deferred population guards must also pass at a real transaction boundary.
    c.exec_driver_sql('SET CONSTRAINTS nav.interest_review_population, nav.interest_review_item_population IMMEDIATE')
    with pytest.raises(Exception,match='immutable'):
        with c.begin_nested():c.execute(t.review.update().where(t.review.c.review_id==receipt['review_id']).values(state='DRAFT'))


def test_bulk_validation_rejects_partial_population_and_changed_sources(valued):
    c,r,trade=valued;add_bond(c,r,trade);daily(c,r,date(2026,10,1));actor=ids['demo_user_account']
    view=review_view(c,r.tenant_id,actor,r.strategy_id,date(2026,10,1),'DAILY')
    payload=command(view,'DAILY')
    with pytest.raises(ValueError,match='population'):
        save_review(c,r.tenant_id,actor,actor,payload.model_copy(update={'rows':[]}),uuid4().hex)
    daily(c,r,date(2026,9,30))
    with pytest.raises(ValueError,match='changed'):
        save_review(c,r.tenant_id,actor,actor,payload,uuid4().hex)


def test_daily_draft_is_not_financial_until_validated_and_changes_invalidate_balance_review(valued):
    from decimal import Decimal as D
    from valuation.accruals import read_accruals
    from datetime import datetime,timezone
    c,r,trade=valued;add_bond(c,r,trade);daily(c,r,date(2026,9,30));daily(c,r,date(2026,10,1));actor=ids['demo_user_account'];day=date(2026,10,1)
    view=review_view(c,r.tenant_id,actor,r.strategy_id,day,'DAILY');payload=command(view,'DAILY')
    changed=payload.rows[0].model_copy(update={'amount':D('25'),'reason':'Source corrected','source_reference':'Ops statement'})
    draft=payload.model_copy(update={'state':'DRAFT','rows':[changed]})
    save_review(c,r.tenant_id,actor,actor,draft,uuid4().hex)
    assert read_accruals(c,r.tenant_id,r.strategy_id,day,day,datetime.now(timezone.utc))[0]['daily_earned_interest']==10
    view=review_view(c,r.tenant_id,actor,r.strategy_id,day,'DAILY')
    assert view['rows'][0]['amount']=='25'
    save_review(c,r.tenant_id,actor,actor,command(view,'DAILY'),uuid4().hex)
    assert read_accruals(c,r.tenant_id,r.strategy_id,day,day,datetime.now(timezone.utc))[0]['daily_earned_interest']==25
    assert review_view(c,r.tenant_id,actor,r.strategy_id,day,'BALANCE')['dailyValidated']
    daily(c,r,date(2026,9,29))
    with pytest.raises(ValueError,match='daily'):
        review_view(c,r.tenant_id,actor,r.strategy_id,day,'BALANCE')


def test_review_failure_rolls_back_financial_changes_and_receipt_together(valued,monkeypatch):
    from decimal import Decimal as D
    from valuation.accruals import read_accruals
    from datetime import datetime,timezone
    c,r,trade=valued;add_bond(c,r,trade);daily(c,r,date(2026,10,1));actor=ids['demo_user_account'];day=date(2026,10,1)
    view=review_view(c,r.tenant_id,actor,r.strategy_id,day,'DAILY');payload=command(view,'DAILY')
    payload=payload.model_copy(update={'rows':[payload.rows[0].model_copy(update={'amount':D('99'),'reason':'Correct value','source_reference':'Synthetic source'})]})
    monkeypatch.setattr('valuation.interest_review.audit',lambda *a,**kw:(_ for _ in ()).throw(RuntimeError('Audit unavailable')))
    with pytest.raises(RuntimeError,match='Audit unavailable'):
        save_review(c,r.tenant_id,actor,actor,payload,uuid4().hex)
    assert read_accruals(c,r.tenant_id,r.strategy_id,day,day,datetime.now(timezone.utc))[0]['daily_earned_interest']==10
    assert c.scalar(select(func.count()).select_from(t.review).where(t.review.c.strategy_id==r.strategy_id))==0


def test_acknowledged_gaps_unlock_balance_review_without_fabricating_zero_inputs(valued):
    from datetime import datetime,timezone
    from valuation.accruals import read_accruals
    from valuation.balance_history import read_inputs
    c,r,trade=valued;add_bond(c,r,trade);daily(c,r,date(2026,9,30));actor=ids['demo_user_account'];day=date(2026,10,1)
    view=review_view(c,r.tenant_id,actor,r.strategy_id,day,'DAILY');payload=command(view,'DAILY')
    assert view['rows'][0]['amount'] is None
    payload=payload.model_copy(update={'rows':[payload.rows[0].model_copy(update={'decision':'NOT_SUPPLIED','reason':'Provider file not received'})]})
    receipt=save_review(c,r.tenant_id,actor,actor,payload,uuid4().hex)
    assert receipt['gap_count']==1
    assert read_accruals(c,r.tenant_id,r.strategy_id,day,day,datetime.now(timezone.utc))==[]
    balance=review_view(c,r.tenant_id,actor,r.strategy_id,day,'BALANCE')
    assert balance['dailyValidated'] and balance['rows'][0]['dailyIncrement'] is None
    assert balance['rows'][0]['amount'] is None
    payload=command(balance,'BALANCE');payload=payload.model_copy(update={'rows':[payload.rows[0].model_copy(update={'decision':'NOT_SUPPLIED','reason':'Closing stock not received'})]})
    receipt=save_review(c,r.tenant_id,actor,actor,payload,uuid4().hex)
    assert receipt['gap_count']==1
    assert read_inputs(c,r.tenant_id,r.strategy_id,day,day,datetime.now(timezone.utc))==[]
    c.exec_driver_sql('SET CONSTRAINTS nav.interest_review_population, nav.interest_review_item_population IMMEDIATE')


def test_known_values_cannot_be_hidden_as_missing(valued):
    c,r,trade=valued;add_bond(c,r,trade);daily(c,r,date(2026,10,1));actor=ids['demo_user_account']
    view=review_view(c,r.tenant_id,actor,r.strategy_id,date(2026,10,1),'DAILY');payload=command(view,'DAILY')
    payload=payload.model_copy(update={'rows':[payload.rows[0].model_copy(update={'decision':'NOT_SUPPLIED','amount':None,'reason':'Hide supplied input'})]})
    with pytest.raises(ValueError,match='known amounts'):
        save_review(c,r.tenant_id,actor,actor,payload,uuid4().hex)


def test_a_concurrent_position_change_is_not_blessed_by_the_post_write_hash(valued,monkeypatch):
    from decimal import Decimal as D
    from datetime import datetime,timezone
    from valuation import interest_review as service
    from valuation.accruals import read_accruals
    c,r,trade=valued;add_bond(c,r,trade);daily(c,r,date(2026,10,1));actor=ids['demo_user_account'];day=date(2026,10,1)
    view=review_view(c,r.tenant_id,actor,r.strategy_id,day,'DAILY');payload=command(view,'DAILY')
    payload=payload.model_copy(update={'rows':[payload.rows[0].model_copy(update={'amount':D('99'),'source_reference':'Source correction','reason':'Ops assessment'})]})
    original=service._sources;calls=[]
    def concurrent(*args,**kwargs):
        result=original(*args,**kwargs);calls.append(True)
        if len(calls)>1:result[-1]['projection']=result[-1]['projection']+['new-event']
        return result
    monkeypatch.setattr(service,'_sources',concurrent)
    with pytest.raises(ValueError,match='changed during review'):
        save_review(c,r.tenant_id,actor,actor,payload,uuid4().hex)
    assert read_accruals(c,r.tenant_id,r.strategy_id,day,day,datetime.now(timezone.utc))[0]['daily_earned_interest']==10
