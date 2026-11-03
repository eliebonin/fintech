"""Focused native partial staging; no missing price becomes a zero attribution."""
from decimal import Decimal as D
from uuid import uuid4
import pytest
from sqlalchemy import select,func
from tests.test_valuation_service import valued
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from apps.reference_api.db import get_engine
from valuation import service,storage,tables as t


def missing_series(c,action='WARN'):
    source=dict(c.execute(select(m.market_data_series).where(m.market_data_series.c.market_data_series_id==ids['market_data_series'])).mappings().one())
    series=uuid4()
    c.execute(m.market_data_series.insert().values(**(source|dict(market_data_series_id=series))))
    c.execute(m.valuation_policy_rule.update().where(m.valuation_policy_rule.c.valuation_policy_rule_id==ids['valuation_policy_rule']).values(
        market_data_series_id=series,missing_data_action=action))
    return series


def test_warn_stages_all_unpriced_positions_and_blocks_publication(valued):
    c,r,trade=valued;missing_series(c)
    result=service.calculate(c,r)
    assert result.period.lines==() and result.period.market_pnl==0
    coverage=result.evidence['inputCoverage']
    assert coverage['missingCount']==1 and coverage['affectedPositionCount']==1
    row=coverage['unpricedPositions'][0]
    assert row['pnl'] is None and row['bucket']['closing_quantity']=='10'
    assert row['facts'][0]['trade_id']==str(trade)
    attempt=storage.begin_attempt(get_engine(),r,ids['demo_user_account'],str(uuid4()))
    batch=storage.stage(c,attempt,ids['demo_user_account'],result)
    view=storage.batch_view(c,r.tenant_id,batch)
    assert view['status']=='STAGED' and view['items']==[]
    assert view['summary']['requiredInputsComplete'] is False
    assert view['summary']['inputCoverage']==coverage
    assert c.scalar(select(func.count()).select_from(t.attribution).where(t.attribution.c.attempt_id==attempt))==0
    from valuation.evidence_access import assert_batch_display
    assert_batch_display(c,r.tenant_id,view)
    reviewer=uuid4();c.execute(m.user_account.insert().values(user_account_id=reviewer,account_type='HUMAN'))
    with pytest.raises(ValueError,match='required.*marks'):
        storage.publish(c,r.tenant_id,batch,reviewer,'Acknowledged missing price')


def test_fail_rule_still_blocks_when_a_price_is_absent(valued):
    c,r,_=valued;missing_series(c,'FAIL')
    with pytest.raises(service.ValuationBlocked):service.calculate(c,r)


def test_partial_result_keeps_priced_bond_and_full_unpriced_trade_proof(valued):
    from tests.test_economic_pnl_acceptance import add_bond
    c,r,trade=valued
    add_bond(c,r,trade,coupon_type='ZERO')
    missing_series(c)
    result=service.calculate(c,r)
    assert len(result.projection.buckets)==2
    assert len(result.period.lines)==1
    assert result.period.lines[0].bucket.key.product_basis=='BOND'
    assert result.period.market_pnl==D('1250')
    coverage=result.evidence['inputCoverage']
    assert coverage['pricedPositionCount']==1 and coverage['affectedPositionCount']==1
    assert coverage['unpricedPositions'][0]['facts'][0]['trade_id']==str(trade)


def test_missing_both_boundaries_retains_both_dates(valued):
    from dataclasses import replace
    from datetime import timedelta
    c,r,_=valued;missing_series(c)
    result=service.calculate(c,replace(r,opening_cutoff=r.opening_cutoff+timedelta(days=1)))
    coverage=result.evidence['inputCoverage']
    assert coverage['missingCount']==2
    assert {g['selection']['pricing_date_requested'] for g in coverage['gaps']}=={'2026-09-30','2026-10-01'}
    assert result.period.lines==()


def test_warn_does_not_hide_invalid_calendar(valued):
    from dataclasses import replace
    from datetime import timedelta
    c,r,_=valued
    c.execute(m.valuation_policy_rule.update().where(m.valuation_policy_rule.c.valuation_policy_rule_id==ids['valuation_policy_rule']).values(missing_data_action='WARN'))
    with pytest.raises(service.ValuationBlocked):
        service.calculate(c,replace(r,closing_cutoff=r.closing_cutoff+timedelta(days=1)))
