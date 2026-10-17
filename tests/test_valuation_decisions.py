from valuation.decisions import applied_decisions


def test_daily_only_rule_does_not_claim_accumulated_balance_evidence():
    rule=applied_decisions({'economicInputs':[{'kind':'DAILY_ACCRUAL','inputId':'daily',
        'payload':{'balanceReconciliation':'NOT_PROVIDED','amounts':{'dailyBase':'10'}}}]})[0]
    assert rule['balanceReconciliation']=='NOT_PROVIDED'


def test_nav_rule_retains_availability_and_requested_actual_dates():
    rule=applied_decisions({'selections':[dict(valuation_date='2026-10-13',pricing_date_requested='2026-10-12',
        pricing_date_used='2026-10-12',selected_value='101',source_published_at_utc='2026-10-13T09:00:00Z',
        received_at_utc='2026-10-13T09:01:00Z',staleness_business_days=0,pricing_evidence={'convention':'NAV_DATE'})]})[0]
    assert rule['sourcePublishedAt']=='2026-10-13T09:00:00Z'
    assert rule['receivedAt']=='2026-10-13T09:01:00Z'
    assert rule['requestedDate']==rule['actualDate']=='2026-10-12'
    assert rule['stalenessBusinessDays']==0


def test_clean_bond_rule_and_bridge_explain_frozen_values_not_new_calculations():
    rules=applied_decisions({'identity':dict(bucket={'key':{'product_basis':'BOND','quantity_unit':'NOMINAL',
        'unit_multiplier':'1','quote_factor':'100'}},openingValue='99000',closingValue='100000',executionValue='0',
        components={'PRICE':'1000','ACCRUAL':'10'})})
    by_code={r['code']:r for r in rules}
    assert by_code['CLEAN_BOND_NOMINAL']['quoteFactor']=='100'
    assert by_code['POSITION_VALUE_BRIDGE']['openingValue']=='99000'
    assert by_code['POSITION_VALUE_BRIDGE']['closingValue']=='100000'
    assert by_code['POSITION_VALUE_BRIDGE']['executionValue']=='0'
    assert by_code['POSITION_VALUE_BRIDGE']['components']=={'PRICE':'1000','ACCRUAL':'10'}


def test_partial_legacy_identity_does_not_invent_financial_bridge():
    assert not any(r['code']=='POSITION_VALUE_BRIDGE' for r in applied_decisions({'identity':{'openingValue':'100'}}))


def test_fund_price_date_and_fx_date_are_independently_explained():
    evidence={'selections':[
        {'valuation_date':'2026-10-13','pricing_date_requested':'2026-10-12','pricing_date_used':'2026-10-12',
         'selected_value':'101','policy_rule_id':'nav-rule','pricing_evidence':{'convention':'NAV_DATE'}},
        {'input_role':'FX','valuation_date':'2026-10-13','pricing_date_used':'2026-10-13',
         'selected_value':'.85','conversion':{'method':'RECIPROCAL','rate':'.85'},'policy_rule_id':'fx-rule'}]}
    rules=applied_decisions(evidence)
    assert rules[0]['code']=='FUND_NAV_DATE'
    assert rules[0]['actualDate']=='2026-10-12'
    assert rules[1]['code']=='FX_RECIPROCAL'
    assert rules[1]['actualDate']=='2026-10-13'
    assert all(r['version']==1 and r['explanation'] for r in rules)


def test_booked_cost_and_zero_boundary_do_not_invent_opening_mark():
    rules=applied_decisions({'executionInputs':[{'event_id':'event','effective_at':'2026-10-13T10:00:00Z',
        'booking':{'trade_id':'trade','price':'100','quantity':'10'}}], 'noMarketMarksRequired':True})
    assert [r['code'] for r in rules]==['BOOKED_EXECUTION_PRICE','ZERO_BOUNDARY_NO_MARK']
    assert rules[0]['evidenceRefs']==['event','trade']


def test_missing_old_evidence_is_not_inferred_as_a_rule():
    assert applied_decisions({})==[]


def test_share_ratio_payment_only_and_daily_interest_have_distinct_explanations():
    rules=applied_decisions({'splitAdjustments':[{'event':{'action_id':'split','review_id':'review'},'quantity_before':'100','quantity_after':'110'}],
        'economicInputs':[{'tradeId':'payment','booking':{'recognitionRole':'PAYMENT_ONLY','component':'DIVIDEND'}},
                          {'kind':'DAILY_ACCRUAL','inputId':'accrual','payload':{'amounts':{'dailyBase':'8.60'}}}]})
    assert [r['code'] for r in rules]==['REVIEWED_SHARE_RATIO','PAYMENT_ONLY_NO_INCOME','DAILY_EARNED_ACCRUAL']
    assert rules[0]['evidenceRefs']==['split','review']
    assert '100' in rules[0]['explanation'] and '110' in rules[0]['explanation']


def test_normalised_mark_explanation_uses_the_applied_value_not_source_value():
    rule=applied_decisions({'selections':[{'valuation_date':'2026-10-13','pricing_date_used':'2026-10-13',
        'selected_value':'40','valuation_value':'80','pricing_evidence':{'priceBasis':{'valuationValue':'80'}}}]})[0]
    assert '80' in rule['explanation']


def test_same_currency_identity_is_explicit_without_inventing_fx_observation():
    rules=applied_decisions({'identity':{'bucket':{'key':{'currency_id':'GBP'}},'reportingCurrency':'GBP'}})
    assert rules[0]['code']=='SAME_CURRENCY_FX_IDENTITY'
    assert rules[0]['evidenceRefs']==[]


def test_new_foreign_fund_uses_booked_cost_and_current_fx_with_prior_nav():
    from decimal import Decimal as D
    from tests.test_position_reconstruction import booked,request,CLOSE,CURRENCY
    from positions.reconstruction import reconstruct
    from valuation.position_calculation import attribute_projection,MarkKey
    from uuid import UUID
    projection=reconstruct([booked(1,'10',CLOSE,'98',product_basis='FUND',quantity_unit='UNITS')],request())
    key=projection.buckets[0].key
    result=attribute_projection(projection,{MarkKey(key.subject_id,CLOSE):D('100')},UUID(int=888),{(CURRENCY,CLOSE):D('.86')})
    assert result.market_pnl==D('17.20')
    assert result.opening_value==0 and result.execution_value==D('842.80')
    assert result.lines[0].attribution.fx==result.lines[0].attribution.cross==0
