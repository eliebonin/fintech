"""Unknown position inputs are retained, never converted into zero P&L."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
from uuid import UUID
import pytest
from tests.test_position_reconstruction import booked,request,OPEN,CLOSE,CURRENCY
from positions.reconstruction import reconstruct,key_identity


@pytest.mark.parametrize('action,code,allowed',[
    ('WARN','NO_ELIGIBLE_OBSERVATION',True),('MANUAL_OVERRIDE','NO_ELIGIBLE_OBSERVATION',True),
    ('WARN','MAX_STALENESS_EXCEEDED',True),('FAIL','NO_ELIGIBLE_OBSERVATION',False),
    ('WARN','NO_VALID_ENTITLEMENT',False),('WARN','NO_MATCHING_POLICY_RULE',False),
    ('WARN','CALENDAR_NOT_ASSESSED',False),('WARN','PRICE_BASIS_PROOF_MISSING',False)])
def test_only_missing_or_stale_prices_can_be_continued(action,code,allowed):
    from valuation.price_inputs import may_continue
    assert may_continue(action,code) is allowed


def test_unpriced_position_is_excluded_as_a_whole_without_changing_original_proof():
    from valuation.price_inputs import priced_projection
    a=booked(1,'10',OPEN-timedelta(days=1));b=booked(2,'5',CLOSE,'110')
    other=UUID(int=999)
    b=replace(b,booking=replace(b.booking,subject_id=other))
    original=reconstruct([a,b],request());missing=key_identity(next(bucket.key for bucket in original.buckets if bucket.key.subject_id!=other))
    selected=priced_projection(original,{missing})
    assert len(selected.buckets)==1 and selected.buckets[0].key.subject_id==other
    assert selected.facts==original.facts and selected.input_hash==original.input_hash
    assert len(original.buckets)==2
    assert all(e.key==selected.buckets[0].key for e in selected.executions)


def test_partial_publication_cannot_be_acknowledged_or_adjusted_away():
    from valuation.price_inputs import assert_complete_prices
    for summary in ({'requiredInputsComplete':False},{'inputCoverage':{'missingCount':1}},
                    {'inputCoverage':{'unpricedPositions':[{'positionKey':'x'}]}}):
        with pytest.raises(ValueError,match='required.*marks'):
            assert_complete_prices(summary)
    assert_complete_prices({'requiredInputsComplete':True,'inputCoverage':{'missingCount':0,'unpricedPositions':[]}})
    # Earlier optional accrued/cash omissions retain their existing contract.
    assert_complete_prices({'pnlCompleteness':'PARTIAL','cashCoverage':{'missingCount':1}})


def test_cash_fx_gaps_do_not_claim_missing_investment_prices_or_zero_portfolio_value():
    from apps.reference_api.valuation_source_coverage import source_coverage
    coverage=source_coverage({'items':[],'summary':{'netPnl':'0','hasCalculatedContributions':False,
        'cashCoverage':{'missingFxCount':2},'inputCoverage':{'missingCount':2,'gaps':[{'role':'CASH_FX'},{'role':'CASH_FX'}]}}})
    rows={row['code']:row for row in coverage['rows']}
    assert rows['PRICE']['missingCount']==0 and rows['PRICE']['amount'] is None
    assert rows['CASH_BALANCE_FX']['missingCount']==2 and rows['CASH_BALANCE_FX']['status']=='MISSING_INPUTS'
    assert coverage['includedTotal'] is coverage['recordedNet'] is None
