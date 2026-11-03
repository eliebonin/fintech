"""Manual marks fill exact missing inputs after independent, scoped review."""
from dataclasses import replace
from decimal import Decimal as D
from uuid import uuid4
import pytest
from sqlalchemy import select,func
from tests.test_valuation_service import valued
from tests.test_partial_price_staging import missing_series
from tests.test_position_attribution_storage import staged,reviewer
from tests.test_bond_dirty_market_integration import dirty_bond,bond
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from valuation import service,storage


def authorized_reviewer(c):
    actor=reviewer(c)
    original=dict(c.execute(select(m.tenant_user_account).where(m.tenant_user_account.c.tenant_id==ids['tenant'],m.tenant_user_account.c.user_account_id==ids['demo_user_account'])).mappings().one())
    c.execute(m.tenant_user_account.insert().values(**(original|dict(tenant_user_account_id=uuid4(),user_account_id=actor))))
    groups=c.scalars(select(m.access_group_member.c.group_id).where(m.access_group_member.c.tenant_id==ids['tenant'],m.access_group_member.c.user_account_id==ids['demo_user_account'])).all()
    for group in groups:c.execute(m.access_group_member.insert().values(tenant_id=ids['tenant'],group_id=group,user_account_id=actor))
    return actor


def setup_missing(c,r):
    series=missing_series(c)
    c.execute(m.valuation_policy_rule.update().where(m.valuation_policy_rule.c.valuation_policy_rule_id==ids['valuation_policy_rule']).values(require_official_close=False))
    result=service.calculate(c,r);batch=staged(c,r,result)
    gap=result.evidence['inputCoverage']['gaps'][0]
    from valuation.mark_override_contracts import MarkOverrideCreate
    payload=MarkOverrideCreate(baseBatchId=batch,inputKey=gap['inputKey'],seriesId=series,value='1200.000000000001',confirmQuoteBasis=True,
        reason='Synthetic independently assessed closing quote',sourceReference='Synthetic administrator evidence')
    return payload,batch


def test_request_review_recalculate_and_withdraw_preserve_original_observations(valued):
    from valuation.mark_overrides import request_mark,decide_mark
    c,r,_=valued;payload,batch=setup_missing(c,r)
    before=[dict(row) for row in c.execute(select(m.market_data_observation)).mappings()]
    owner=ids['demo_user_account'];key=str(uuid4())
    mark=request_mark(c,r.tenant_id,owner,payload,key)
    assert request_mark(c,r.tenant_id,owner,payload,key)==mark
    assert service.calculate(c,r).evidence['requiredInputsComplete'] is False
    actor=authorized_reviewer(c);cutoff=c.scalar(select(func.clock_timestamp()))
    decide_mark(c,r.tenant_id,mark,actor,'APPROVED','Synthetic quote checked')
    assert service.calculate(c,replace(r,information_cutoff=cutoff)).evidence['requiredInputsComplete'] is False
    result=service.calculate(c,r)
    assert result.evidence['requiredInputsComplete'] is True
    assert result.period.market_pnl==D('119.8770000000001')
    selection=result.evidence['selections'][0]
    assert selection['market_data_observation_id'] is None
    assert selection['pricing_evidence']['manualOverride']['requestId']==str(mark)
    new_batch=staged(c,r,result)
    decide_mark(c,r.tenant_id,mark,actor,'WITHDRAWN','Synthetic source correction required')
    assert storage.batch_view(c,r.tenant_id,new_batch)['sourceHealth']['marksChanged'] is True
    with pytest.raises(ValueError,match='manual mark|override'):
        storage.publish(c,r.tenant_id,new_batch,actor,'Attempting stale manual-mark publication')
    assert service.calculate(c,r).evidence['requiredInputsComplete'] is False
    assert [dict(row) for row in c.execute(select(m.market_data_observation)).mappings()]==before


def test_same_person_cannot_review_by_switching_selected_user(valued):
    from valuation.mark_overrides import request_mark,decide_mark
    c,r,_=valued;payload,_=setup_missing(c,r);owner=ids['demo_user_account']
    mark=request_mark(c,r.tenant_id,owner,payload,str(uuid4()),real_operator_id=owner)
    other=authorized_reviewer(c)
    with pytest.raises(PermissionError,match='real operator'):
        decide_mark(c,r.tenant_id,mark,other,'APPROVED','Switched identity',real_operator_id=owner)
    with pytest.raises(PermissionError,match='independent'):
        decide_mark(c,r.tenant_id,mark,owner,'APPROVED','Self approval')


def test_request_scope_values_and_replay_cannot_be_changed(valued):
    from valuation.mark_overrides import request_mark,decide_mark
    c,r,_=valued;payload,_=setup_missing(c,r);key=str(uuid4());owner=ids['demo_user_account']
    mark=request_mark(c,r.tenant_id,owner,payload,key)
    with pytest.raises(ValueError,match='key'):
        request_mark(c,r.tenant_id,owner,payload.model_copy(update={'value':D('1201')}),key)
    with pytest.raises((LookupError,PermissionError)):
        request_mark(c,uuid4(),owner,payload,str(uuid4()))
    from valuation import mark_override_tables as t
    with pytest.raises(Exception,match='immutable'):
        with c.begin_nested():c.execute(t.request.update().where(t.request.c.request_id==mark).values(value=0))
    decide_mark(c,r.tenant_id,mark,authorized_reviewer(c),'REJECTED','Quote is not evidenced')
    assert service.calculate(c,r).evidence['requiredInputsComplete'] is False


def test_withdrawal_does_not_revive_an_older_approved_mark(valued):
    from valuation.mark_overrides import request_mark,decide_mark,review_view
    from valuation.mark_override_contracts import MarkOverrideReviewView
    c,r,_=valued;payload,batch=setup_missing(c,r);owner=ids['demo_user_account'];actor=authorized_reviewer(c)
    first=request_mark(c,r.tenant_id,owner,payload,str(uuid4()))
    decide_mark(c,r.tenant_id,first,actor,'APPROVED','First checked mark')
    newer=request_mark(c,r.tenant_id,owner,payload.model_copy(update={'value':D('1201')}),str(uuid4()))
    decide_mark(c,r.tenant_id,newer,actor,'APPROVED','Revised checked mark')
    assert service.calculate(c,r).period.market_pnl==D('119.977')
    decide_mark(c,r.tenant_id,newer,actor,'WITHDRAWN','Withdraw latest evidence')
    assert service.calculate(c,r).evidence['requiredInputsComplete'] is False
    view=MarkOverrideReviewView.model_validate(review_view(c,r.tenant_id,actor,batch))
    assert {row.status for row in view.requests}=={'APPROVED','WITHDRAWN'}


def test_real_source_arrival_wins_and_invalidates_old_manual_candidate(valued):
    from valuation.mark_overrides import request_mark,decide_mark,assert_current_marks
    c,r,_=valued;payload,_=setup_missing(c,r);owner=ids['demo_user_account'];actor=authorized_reviewer(c)
    mark=request_mark(c,r.tenant_id,owner,payload,str(uuid4()))
    decide_mark(c,r.tenant_id,mark,actor,'APPROVED','Checked exact quote')
    result=service.calculate(c,r);batch=staged(c,r,result)
    source=dict(c.execute(select(m.market_data_observation).where(m.market_data_observation.c.market_data_observation_id==ids['market_data_observation'])).mappings().one())
    stamp=r.closing_cutoff.replace(hour=16,minute=0,second=0,microsecond=0)
    c.execute(m.market_data_observation.insert().values(**(source|dict(market_data_observation_id=uuid4(),market_data_series_id=payload.series_id,
        market_data_vintage_id=None,market_date=stamp.date(),value=D('1202'),received_at_utc=stamp,observed_at_utc=stamp,
        source_published_at_utc=stamp,source_observation_key='ARRIVAL_'+uuid4().hex))))
    fresh=service.calculate(c,r)
    assert fresh.period.market_pnl==D('120.077')
    assert not (fresh.evidence['selections'][0].get('pricing_evidence') or {}).get('manualOverride')
    with pytest.raises(ValueError,match='available|recalculate'):assert_current_marks(c,r.tenant_id,storage.batch_view(c,r.tenant_id,batch))


def test_manual_quote_validator_requires_exact_strings_and_dirty_pair():
    from valuation.mark_override_contracts import MarkOverrideCreate
    from valuation.mark_overrides import _validate_quote
    from datetime import date
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        MarkOverrideCreate(baseBatchId=uuid4(),inputKey='a'*64,seriesId=uuid4(),value=1.2,confirmQuoteBasis=True,reason='Test',sourceReference='Test')
    series=dict(currency_id=uuid4(),value_type='PRICE',dimensions={'BOND_PRICE_TYPE':{'DIRTY'},'QUOTE_FACTOR':{'100'}})
    with pytest.raises(ValueError,match='paired quoted accrual'):_validate_quote(series,D('101'),'BOND',pricing_date=date(2026,10,1))
    _validate_quote(series,D('101'),'BOND',D('1'),date(2026,10,3),date(2026,10,1))


def test_reviewed_dirty_bond_marks_keep_quote_accrual_separate_from_daily_earnings(dirty_bond):
    from tests.test_cash_product_pnl_integration import stage as stage_in_transaction
    from datetime import date,timedelta
    from valuation.mark_overrides import request_mark,decide_mark,assert_current_marks
    from valuation.mark_override_contracts import MarkOverrideCreate
    from valuation.bond_quote_review import assert_current_normalized_bond_quotes
    c,r,node,series,_,_=dirty_bond
    original=dict(c.execute(select(m.market_data_series).where(m.market_data_series.c.market_data_series_id==series)).mappings().one())
    empty=uuid4();c.execute(m.market_data_series.insert().values(**(original|dict(market_data_series_id=empty))))
    for code,value in [('BOND_PRICE_TYPE','DIRTY'),('QUOTE_FACTOR','100')]:
        c.execute(m.market_data_series_dimension.insert().values(market_data_series_id=empty,dimension_code=code,dimension_value=value))
    c.execute(m.valuation_policy_rule.update().where(m.valuation_policy_rule.c.market_data_series_id==series).values(market_data_series_id=empty,missing_data_action='MANUAL_OVERRIDE'))
    partial=service.calculate(c,r);base=stage_in_transaction(c,r,partial);actor=authorized_reviewer(c)
    for gap in partial.evidence['inputCoverage']['gaps']:
        day=date.fromisoformat(gap['selection']['pricing_date_requested']);closing=day==r.closing_cutoff.date()
        payload=MarkOverrideCreate(baseBatchId=base,inputKey=gap['inputKey'],seriesId=empty,value='101.02' if closing else '101',
            quotedAccrualPer100='1.02' if closing else '1',quoteSettlementDate=day+timedelta(days=2),confirmQuoteBasis=True,
            reason='Synthetic administrator paired dirty quote',sourceReference='Synthetic quote with paired accrual')
        mark=request_mark(c,r.tenant_id,ids['demo_user_account'],payload,str(uuid4()))
        decide_mark(c,r.tenant_id,mark,actor,'APPROVED','Checked quote, accrual and settlement')
    result=service.calculate(c,r)
    line=next(line for line in result.period.lines if line.bucket.key.subject_id==node)
    assert line.attribution.market_pnl==0
    selections=[s for s in result.evidence['selections'] if s.get('subject_reference_node_id')==str(node)]
    assert selections and all(D(s['valuation_value'])==100 for s in selections)
    view=storage.batch_view(c,r.tenant_id,stage_in_transaction(c,r,result))
    assert_current_marks(c,r.tenant_id,view)
    assert_current_normalized_bond_quotes(c,r.tenant_id,view,view['items'])


def test_manual_mark_does_not_bypass_revoked_valuation_entitlement(valued):
    from valuation.mark_overrides import request_mark,decide_mark,assert_current_marks
    c,r,_=valued;payload,_=setup_missing(c,r);actor=authorized_reviewer(c)
    mark=request_mark(c,r.tenant_id,ids['demo_user_account'],payload,str(uuid4()))
    decide_mark(c,r.tenant_id,mark,actor,'APPROVED','Checked source')
    view=storage.batch_view(c,r.tenant_id,staged(c,r,service.calculate(c,r)))
    dataset=c.scalar(select(m.market_data_series.c.default_dataset_id).where(m.market_data_series.c.market_data_series_id==payload.series_id))
    c.execute(m.tenant_dataset_entitlement.update().where(m.tenant_dataset_entitlement.c.tenant_id==r.tenant_id,
        m.tenant_dataset_entitlement.c.dataset_id==dataset,m.tenant_dataset_entitlement.c.use_purpose=='VALUATION').values(status='INACTIVE'))
    with pytest.raises((service.ValuationBlocked,PermissionError)):service.calculate(c,r)
    with pytest.raises(PermissionError):assert_current_marks(c,r.tenant_id,view)
