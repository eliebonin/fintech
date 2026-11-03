"""Optional omissions stay reviewable, never new publication blockers or amounts."""
from copy import deepcopy
from decimal import Decimal as D
import pytest


def test_cash_only_gap_is_partial_but_absent_historical_scopes_are_not_expected():
    from valuation.review_coverage import pnl_completeness
    assert pnl_completeness({}, {}, {'missingCount':2})=='PARTIAL'
    assert pnl_completeness({}, {}, {'status':'NOT_ASSESSED','missingCount':0})=='RECORDED_COMPONENTS'
    assert pnl_completeness({'missingCount':1}, {}, {})=='PARTIAL'
    assert pnl_completeness({}, {'missingCount':1}, {})=='PARTIAL'


def test_attention_includes_optional_fx_stock_and_anchor_cases_without_duplicates():
    from valuation.review_coverage import position_attention
    evidence=dict(economicInputs=[{'kind':'MISSING_DAILY_ACCRUAL_FX'}, {'kind':'MISSING_DAILY_ACCRUAL_FX'},
        {'kind':'ACCRUED_BALANCE_FX','days':[{'reason':'ACCRUED_BALANCE_FX_UNAVAILABLE','balance':{'warnings':['CLOSING_ANCHOR_DIFFERS_FROM_REPLAY']}},
        {'reason':'OPENING_ACCRUED_BALANCE_UNAVAILABLE','balance':{'warnings':[]}}]}])
    before=deepcopy(evidence);notes=position_attention(evidence)
    assert notes==['Interest FX unavailable','Accrued FX unavailable','Accrued balance unavailable','Accrued balance mismatch']
    assert evidence==before
    assert position_attention({'economicInputs':[{'kind':'DAILY_ACCRUAL_NOT_APPLICABLE'}]})==[]


def proof(opening='1000',closing='20',fx0='0.75',fx1='0.76',currency='usd'):
    return dict(economicInputs=[dict(kind='ACCRUED_BALANCE_FX',currencyId=currency,
        days=[dict(balance=dict(value_date='2026-10-01',opening=opening,closing=closing),opening_fx=fx0,closing_fx=fx1)])])


def test_stock_projection_uses_exact_frozen_rates_without_changing_evidence():
    from valuation.accrued_balance_presentation import project_stocks
    evidence=proof('1234.123456789012','-20.25','0.712345678901','0.76');before=deepcopy(evidence)
    row=project_stocks(evidence,'gbp')[0]
    assert D(row['openingReporting'])==D('1234.123456789012')*D('0.712345678901')
    assert D(row['closingReporting'])==D('-15.39')
    assert row['currencyId']=='usd' and row['reportingCurrencyId']=='gbp'
    assert evidence==before


@pytest.mark.parametrize('opening,closing,fx0,fx1,want0,want1',[
    ('0','20',None,None,'0',None),('10','20','0.75',None,'7.50',None),
    (None,'20','0.75','0.76',None,'15.20'),('10','0',None,None,None,'0')])
def test_stock_boundary_availability_is_independent(opening,closing,fx0,fx1,want0,want1):
    from valuation.accrued_balance_presentation import project_stocks
    row=project_stocks(proof(opening,closing,fx0,fx1),'gbp')[0]
    assert row['openingReporting']==want0 and row['closingReporting']==want1


def test_equal_recorded_currencies_use_identity_without_new_market_data():
    from valuation.accrued_balance_presentation import project_stocks
    row=project_stocks(proof('1000','20',None,None,currency='gbp'),'gbp')[0]
    assert row['openingReporting']=='1000' and row['closingReporting']=='20'
    assert project_stocks({},'gbp')==[]


def test_api_projection_includes_review_notes_and_stocks_without_repricing_pnl():
    from apps.reference_api.valuation_presentation import component_display
    item={'components':{'CARRY':'10'},'evidence':proof()};before=deepcopy(item)
    display=component_display(item,'gbp')
    assert display['accruedBalanceStocks'][0]['openingReporting']=='750.00'
    assert display['other']=='10' and item==before


def test_stock_projection_never_assigns_an_unknown_reporting_currency():
    from valuation.accrued_balance_presentation import project_stocks
    assert project_stocks(proof(),None)[0]['openingReporting'] is None


def test_coverage_scope_failure_maps_to_frozen_canonical_instrument_on_its_listing():
    from apps.reference_api.valuation_presentation import component_display
    item={'subject_id':'listing','evidence':{'identity':{'facts':[{'booking':{'product_evidence':{'instrumentId':'canonical'}}}]}}}
    coverage={'canonical':[{'instrumentId':'canonical','reason':'ACCRUAL_CURRENCY_CHANGED_WITHOUT_SINGLE_BASIS'}]}
    assert component_display(item,'gbp',coverage)['attention']==['Accrued currency needs review']


def test_missing_interest_fx_is_missing_coverage_even_without_legacy_summary_counts():
    from apps.reference_api.valuation_source_coverage import source_coverage
    coverage=source_coverage({'summary':{},'items':[{'components':{'PRICE':'1'},'evidence':{'economicInputs':[{'kind':'MISSING_DAILY_ACCRUAL_FX'}]}}]})
    row=next(row for row in coverage['rows'] if row['code']=='ACCRUAL')
    assert row['status']=='MISSING_INPUTS' and row['missingCount']==1


def test_stock_translation_can_reuse_an_unambiguous_frozen_policy_fx_for_the_exact_boundary():
    from valuation.accrued_balance_presentation import project_stocks
    evidence=proof('0','20',None,None)
    evidence['selections']=[dict(input_role='FX',valuation_date='2026-10-01',conversion=dict(sourceCurrencyId='usd',targetCurrencyId='gbp',rate='0.76')),
        dict(input_role='FX',valuation_date='2026-09-30',conversion=dict(sourceCurrencyId='eur',targetCurrencyId='gbp',rate='0.99'))]
    row=project_stocks(evidence,'gbp')[0]
    assert row['openingReporting']=='0' and row['closingReporting']=='15.20'
    assert row['closingFx']=='0.76'
    evidence['selections'].append(dict(input_role='FX',valuation_date='2026-10-01',conversion=dict(sourceCurrencyId='usd',targetCurrencyId='gbp',rate='0.77')))
    assert project_stocks(evidence,'gbp')[0]['closingReporting'] is None # No arbitrary choice among conflicting inputs.


def test_stock_translation_does_not_use_another_day_currency_orientation_or_current_rate():
    from valuation.accrued_balance_presentation import project_stocks
    evidence=proof('0','20',None,None)
    evidence['selections']=[dict(input_role='FX',valuation_date='2026-09-30',conversion=dict(sourceCurrencyId='usd',targetCurrencyId='gbp',rate='0.75')),
        dict(input_role='FX',valuation_date='2026-10-01',conversion=dict(sourceCurrencyId='gbp',targetCurrencyId='usd',rate='1.3'))]
    assert project_stocks(evidence,'gbp')[0]['closingReporting'] is None
