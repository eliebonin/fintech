"""Read-only Ops projections must not change financial evidence or precision."""
from copy import deepcopy
from apps.reference_api.valuation_presentation import component_display
from apps.reference_api import valuation_presentation as presentation
from decimal import Decimal


def test_source_coverage_is_disjoint_exact_and_does_not_invent_cash_pnl():
    batch={'summary':{'netPnl':'16.115678901234'},'items':[
        {'components':{'PRICE':'10.123456789012','FX':'2','PRICE_FX_CROSS':'0.002222112222',
            'ACCRUAL':'1.25','CARRY':'0.02','RESET':'3','BROKER_FEE':'-0.5','ADJUSTMENT':'0.22'}}]}
    before=deepcopy(batch)
    coverage=presentation.source_coverage(batch)
    rows={row['code']:row for row in coverage['rows']}
    assert rows['PRICE']['amount']=='10.123456789012'
    assert rows['FX']['amount']=='2'
    assert rows['ACCRUAL']['amount']=='1.25'
    assert rows['COSTS']['amount']=='-0.5'
    assert rows['CASH_BALANCE_FX']['status']=='NOT_ASSESSED'
    assert rows['CASH_BALANCE_FX']['amount'] is None
    assert rows['CASH_BALANCE_FX']['positionCount']==0
    assert rows['DIVIDEND']['status']=='NOT_RECORDED'
    assert rows['DIVIDEND']['amount'] is None
    assert sum((Decimal(r['amount']) for r in coverage['rows'] if r['amount'] is not None),Decimal(0))==Decimal('16.115678901234')
    assert coverage['reconciliation']=='MATCH'
    assert batch==before


def test_explicit_zero_and_netting_are_recorded_not_missing():
    coverage=presentation.source_coverage({'summary':{'netPnl':'0'},'items':[
        {'components':{'RESET':'5','ACCRUAL':'0'}},{'components':{'RESET':'-5'}}]})
    rows={r['code']:r for r in coverage['rows']}
    assert rows['ACCRUAL']['amount']=='0'
    assert rows['ACCRUAL']['status']=='INCLUDED'
    assert rows['RESET']['amount']=='0'
    assert rows['RESET']['positionCount']==2
    assert rows['PRICE']['amount'] is None
    assert coverage['reconciliation']=='MATCH'


def test_partial_interest_retains_supplied_amount_and_missing_input_status():
    coverage=presentation.source_coverage({'summary':{'netPnl':'1.25',
        'accrualCoverage':{'missingCount':2}},'items':[{'components':{'ACCRUAL':'1.25'}}]})
    row=next(r for r in coverage['rows'] if r['code']=='ACCRUAL')
    assert row['amount']=='1.25'
    assert row['status']=='PARTIAL'
    assert row['missingCount']==2


def test_missing_interest_without_supplied_amount_is_not_a_recorded_zero():
    coverage=presentation.source_coverage({'summary':{'netPnl':'0'},'items':[
        {'components':{'PRICE':'0'},'evidence':{'economicInputs':[{'kind':'MISSING_DAILY_ACCRUAL'}]}}]})
    row=next(r for r in coverage['rows'] if r['code']=='ACCRUAL')
    assert row['status']=='MISSING_INPUTS'
    assert row['amount'] is None


def test_legacy_unclassified_or_missing_components_never_claim_reconciliation():
    coverage=presentation.source_coverage({'summary':{'marketPnl':'10'},'items':[{'market_pnl':'10'}]})
    assert coverage['reconciliation']=='NOT_ASSESSED'
    assert coverage['includedTotal'] is None
    assert next(r for r in coverage['rows'] if r['code']=='PRICE')['status']=='NOT_ASSESSED'
    future=presentation.source_coverage({'summary':{'netPnl':'7'},'items':[{'components':{'NEW_COMPONENT':'7'}}]})
    unknown=next(r for r in future['rows'] if r['code']=='OTHER_STORED')
    assert unknown['componentCodes']==['NEW_COMPONENT']
    assert unknown['amount']=='7'
    assert future['reconciliation']=='MATCH'
    mismatch=presentation.source_coverage({'summary':{'netPnl':'8'},'items':[{'components':{'PRICE':'7'}}]})
    assert mismatch['reconciliation']=='MISMATCH'
    assert mismatch['includedTotal']=='7'


def test_source_coverage_never_releases_denied_evidence():
    assert presentation.source_coverage({'summary':{'evidenceAccess':'DENIED'},'items':[
        {'components':{'PRICE':'99'}}]}) is None


def test_cash_coverage_is_its_own_source_not_position_fx_or_an_invented_zero():
    batch={'summary':{'netPnl':'1012',
        'cashCoverage':{'status':'PARTIAL','missingCount':2}},'items':[
        {'components':{'PRICE':'10','FX':'2'}},
        {'cash_account_id':'account','cash_currency_id':'usd','components':{'CASH_FX':'1000'}}]}
    coverage=presentation.source_coverage(batch)
    row=next(r for r in coverage['rows'] if r['code']=='CASH_BALANCE_FX')
    assert row['amount']=='1000' and row['status']=='PARTIAL'
    assert row['cashAccountCount']==1 and row['positionCount']==0
    assert row['missingCount']==2
    assert coverage['reconciliation']=='MATCH'
    excluded=presentation.source_coverage({'summary':{'netPnl':'0'},'items':[]})
    assert next(r for r in excluded['rows'] if r['code']=='CASH_BALANCE_FX')['status']=='NOT_ASSESSED'


def test_all_supported_components_are_classified_once_and_empty_result_is_evidenced_zero():
    from valuation.economics import MARKET,CASH,INCOME,COSTS
    codes=MARKET|CASH|INCOME|COSTS
    coverage=presentation.source_coverage({'summary':{'netPnl':str(len(codes))},'items':[
        {'components':{code:'1' for code in codes}}]})
    classified=[code for row in coverage['rows'] for code in row['componentCodes']]
    assert set(classified)==codes
    assert len(classified)==len(codes)
    assert coverage['reconciliation']=='MATCH'
    assert not any(row['code']=='OTHER_STORED' for row in coverage['rows'])
    empty=presentation.source_coverage({'summary':{'netPnl':'0'},'items':[]})
    assert empty['includedTotal']=='0'
    assert empty['reconciliation']=='MATCH'


def test_groups_stored_components_exactly_without_changing_evidence():
    item={'market_pnl':'12.345678901234','components':{'PRICE':'10','FX':'2',
        'PRICE_FX_CROSS':'0.345678901234','ACCRUAL':'1.25','CARRY':'0.02',
        'RESET':'3','BROKER_FEE':'-0.5'},'evidence':{}}
    before=deepcopy(item)
    display=component_display(item)
    assert display['interest']=='1.25'
    assert display['other']=='2.52'
    assert display['attention']==[]
    assert item==before


def test_missing_optional_interest_is_a_warning_not_a_sourced_zero():
    display=component_display({'components':{'PRICE':'0'},'evidence':{
        'economicInputs':[{'kind':'MISSING_DAILY_ACCRUAL','valueDate':'2026-10-20'}]}})
    assert display['interest'] is None
    assert 'Interest not supplied' in display['attention']
    assert display['other'] is None


def test_supplied_interest_and_missing_days_both_remain_visible():
    display=component_display({'components':{'ACCRUAL':'12.345678901234'},'evidence':{
        'economicInputs':[{'kind':'MISSING_DAILY_ACCRUAL'}],
        'selections':[{'staleness_business_days':1}]}})
    assert display['interest']=='12.345678901234'
    assert display['attention']==['Interest not supplied','Prior-session input']
def test_missing_accrued_stock_is_partial_not_a_confirmed_zero_or_bad_reconciliation():
    from apps.reference_api.valuation_source_coverage import source_coverage
    batch={'summary':{'netPnl':'10','accruedBalanceCoverage':{'missingCount':1}},
           'items':[{'components':{'PRICE':'10'}}]}
    value=source_coverage(batch)
    carry=next(row for row in value['rows'] if row['code']=='CARRY')
    assert carry['amount'] is None and carry['status']=='MISSING_INPUTS' and carry['missingCount']==1
    assert value['reconciliation']=='MATCH'
    batch['items'][0]['components']['CARRY']='0'
    carry=next(row for row in source_coverage(batch)['rows'] if row['code']=='CARRY')
    assert carry['amount']=='0' and carry['status']=='PARTIAL'
