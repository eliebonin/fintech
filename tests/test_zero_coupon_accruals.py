"""Real position reconstruction and accrual applicability, with only input I/O stubbed."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
from uuid import UUID

import pytest

from positions.reconstruction import reconstruct
from tests.test_position_reconstruction import booked,request,OPEN,CLOSE,INFO,TENANT,STRATEGY,SUBJECT,CURRENCY
from valuation.accruals import load_accrual_inputs,attach_accruals
from valuation.decisions import applied_decisions
from valuation.position_calculation import attribute_projection,MarkKey
from valuation.service import ValuationRequest

INSTRUMENT=UUID(int=900)


def bond(number=1,coupon='ZERO',subject=SUBJECT,when=OPEN,quantity='100000',maturity='2030-01-01'):
    proof=dict(instrumentId=str(INSTRUMENT),maturityDate=maturity,couponRate='0')
    if coupon is not None:proof['couponType']=coupon
    return booked(number,quantity,when,'99',subject_id=subject,product_basis='BOND',
        quantity_unit='NOMINAL',quote_factor=D(100),product_evidence=proof)


def context(monkeypatch,facts=None,rows=(),strict=False):
    monkeypatch.setattr('valuation.accruals.read_accruals',lambda *_:list(rows))
    projection=reconstruct([bond()] if facts is None else facts,request())
    valuation=ValuationRequest(TENANT,STRATEGY,UUID(int=7),UUID(int=8),CURRENCY,OPEN,CLOSE,INFO,
        require_complete_accruals=strict)
    return valuation,projection


@pytest.mark.parametrize('strict',[False,True])
def test_confirmed_zero_coupon_needs_no_missing_interest_or_invented_zero(monkeypatch,strict):
    r,p=context(monkeypatch,strict=strict)
    coverage=load_accrual_inputs(None,r,p)
    assert coverage.inputs==coverage.missing==()
    proof=coverage.evidence(strict)
    assert proof['suppliedCount']==proof['missingCount']==0
    assert proof['notApplicableCount']==1
    assert proof['notApplicable']==[dict(instrumentId=str(INSTRUMENT),valueDate='2026-10-07',reason='ZERO_COUPON')]
    period=attribute_projection(p,{MarkKey(SUBJECT,OPEN):D(99),MarkKey(SUBJECT,CLOSE):D(100)},CURRENCY)
    result=attach_accruals(period,coverage.inputs,missing=coverage.missing,not_applicable=coverage.not_applicable)
    assert result.market_pnl==result.lines[0].gross_pnl==D(1000)
    assert 'ACCRUAL' not in result.lines[0].components()
    inputs=result.lines[0].economic_evidence
    assert [item['kind'] for item in inputs]==['DAILY_ACCRUAL_NOT_APPLICABLE']
    rules=applied_decisions(dict(economicInputs=list(inputs)))
    assert rules[0]['code']=='DAILY_ACCRUAL_NOT_APPLICABLE'
    assert rules[0]['reason']=='ZERO_COUPON'


@pytest.mark.parametrize('coupon',['FIXED','FLOATING','OTHER',None,''])
def test_zero_rate_or_unknown_terms_do_not_imply_zero_coupon(monkeypatch,coupon):
    r,p=context(monkeypatch,[bond(coupon=coupon)])
    coverage=load_accrual_inputs(None,r,p)
    assert coverage.evidence(False)['missingCount']==1
    with pytest.raises(ValueError,match='Missing assessed daily'):
        load_accrual_inputs(None,replace(r,require_complete_accruals=True),p)


@pytest.mark.parametrize('other',['FIXED',None])
def test_mixed_listing_coupon_proofs_cannot_silence_an_unassessed_bond(monkeypatch,other):
    r,p=context(monkeypatch,[bond(),bond(2,coupon=other,subject=UUID(int=901))])
    coverage=load_accrual_inputs(None,r,p)
    assert coverage.evidence(False)['missingCount']==1
    assert len(coverage.missing[0].position_keys)==2


def test_zero_coupon_multiple_listings_have_one_canonical_applicability_count(monkeypatch):
    r,p=context(monkeypatch,[bond(),bond(2,subject=UUID(int=901))])
    coverage=load_accrual_inputs(None,r,p)
    assert coverage.evidence(False)['notApplicableCount']==1
    assert len(coverage.not_applicable[0].position_keys)==2


@pytest.mark.parametrize('amount',['0','12.125'])
def test_supplied_zero_coupon_interest_is_still_validated_and_included(monkeypatch,amount):
    row=dict(instrument_id=INSTRUMENT,value_date=CLOSE.date(),input_id=UUID(int=999),revision=1,
        daily_earned_interest=D(amount),currency_id=CURRENCY,payload=dict(currencyId=str(CURRENCY),dailyEarned=amount))
    r,p=context(monkeypatch,rows=[row],strict=True)
    coverage=load_accrual_inputs(None,r,p)
    assert len(coverage.inputs)==1
    assert coverage.inputs[0].payload['amounts']['dailyBase']==amount
    assert coverage.evidence(True)['notApplicableCount']==0


def test_zero_coupon_does_not_hide_invalid_supplied_interest(monkeypatch):
    row=dict(instrument_id=INSTRUMENT,value_date=CLOSE.date(),input_id=UUID(int=999),revision=1,
        daily_earned_interest=D('12'),currency_id=CURRENCY,payload=dict(currencyId=str(CURRENCY),dailyEarned='13'))
    r,p=context(monkeypatch,rows=[row])
    with pytest.raises(ValueError,match='differs from retained source'):
        load_accrual_inputs(None,r,p)


def test_zero_coupon_does_not_bypass_unclosed_maturity(monkeypatch):
    r,p=context(monkeypatch,[bond(maturity='2026-10-07')])
    with pytest.raises(ValueError,match='Mature bond requires recorded'):
        load_accrual_inputs(None,r,p)


def test_earlier_flat_coupon_episode_does_not_change_current_zero_coupon_coverage(monkeypatch):
    facts=[bond(coupon='FIXED',when=OPEN-timedelta(days=3)),
        bond(2,coupon='FIXED',when=OPEN-timedelta(days=2),quantity='-100000'),bond(3)]
    r,p=context(monkeypatch,facts)
    assert p.buckets[0].trade_ids==(UUID(int=103),)
    assert load_accrual_inputs(None,r,p).evidence(False)['notApplicableCount']==1


def test_flat_zero_coupon_history_does_not_expect_interest(monkeypatch):
    r,p=context(monkeypatch,[bond(when=OPEN-timedelta(days=3)),
        bond(2,when=OPEN-timedelta(days=2),quantity='-100000')])
    coverage=load_accrual_inputs(None,r,p)
    assert coverage.inputs==coverage.missing==()
    assert coverage.evidence(False)['notApplicableCount']==0
