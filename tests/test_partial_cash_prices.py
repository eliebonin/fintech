"""Missing governed cash FX is required-price incompleteness, never zero P&L."""
from dataclasses import replace
from datetime import date
from decimal import Decimal as D
from uuid import uuid4
import pytest
from sqlalchemy import select
from tests.test_valuation_service import valued
from tests.test_cash_fx_storage import add_account,add_balance,cancel_investment,seed_fx,daily,stage,reviewer
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from valuation import service,storage


def missing_cash(c,r,trade,action='WARN'):
    cancel_investment(c,trade);seed_fx(c,r)
    original=dict(c.execute(select(m.market_data_series).where(m.market_data_series.c.source_system_id=='SYNTHETIC_CASH_FX')).mappings().one())
    empty=uuid4();c.execute(m.market_data_series.insert().values(**(original|dict(market_data_series_id=empty,source_system_id='SYNTHETIC_MISSING_CASH_FX'))))
    for code,value in [('BASE_CURRENCY','GBP'),('QUOTE_CURRENCY','USD')]:c.execute(m.market_data_series_dimension.insert().values(market_data_series_id=empty,dimension_code=code,dimension_value=value))
    c.execute(m.valuation_policy_rule.update().where(m.valuation_policy_rule.c.market_data_series_id==original['market_data_series_id']).values(market_data_series_id=empty,missing_data_action=action))
    account=add_account(c,r)
    for day,amount in [(date(2026,9,29),'100000'),(date(2026,9,30),'120000'),(date(2026,10,1),'90000')]:add_balance(c,r,account,day,amount)
    return replace(daily(r),reporting_currency_id=ids['usd_currency']),account,empty


def test_cash_only_missing_fx_retains_unknown_account_and_blocks_publication(valued):
    c,r,trade=valued;r,account,_=missing_cash(c,r,trade)
    result=service.calculate(c,r)
    assert result.cash.lines==()
    coverage=result.evidence['inputCoverage']
    assert coverage['missingCount']==3 and coverage['unpricedPositions']==[]
    cash=coverage['unpricedCashAccounts'][0]
    assert cash['accountId']==str(account) and cash['pnl'] is None
    assert len(cash['snapshots'])==3
    batch=storage.batch_view(c,r.tenant_id,stage(c,r,result))
    assert batch['items']==[] and batch['summary']['hasCalculatedContributions'] is False
    from valuation.evidence_access import assert_batch_display
    assert_batch_display(c,r.tenant_id,batch)
    with pytest.raises(ValueError,match='required.*marks'):storage.publish(c,r.tenant_id,batch['batch_id'],reviewer(c),'Cannot publish unknown cash FX')


def test_reviewed_cash_fx_fills_exact_dates_on_recalculation(valued):
    from tests.test_reviewed_mark_overrides import authorized_reviewer
    from valuation.mark_overrides import request_mark,decide_mark
    from valuation.mark_override_contracts import MarkOverrideCreate
    c,r,trade=valued;r,_,series=missing_cash(c,r,trade)
    result=service.calculate(c,r);base=stage(c,r,result);actor=authorized_reviewer(c)
    for gap in result.evidence['inputCoverage']['gaps']:
        day=gap['selection']['pricing_date_requested'];rate={'2026-09-29':'.75','2026-09-30':'.76','2026-10-01':'.77'}[day]
        payload=MarkOverrideCreate(baseBatchId=base,inputKey=gap['inputKey'],seriesId=series,value=rate,confirmQuoteBasis=True,
            reason='Synthetic exact-date FX quotation',sourceReference='Synthetic independently verified statement')
        mark=request_mark(c,r.tenant_id,ids['demo_user_account'],payload,str(uuid4()))
        decide_mark(c,r.tenant_id,mark,actor,'APPROVED','Orientation and exact-date quote checked')
    result=service.calculate(c,r)
    assert result.evidence['requiredInputsComplete'] is True and result.cash.amount==D('2200')
