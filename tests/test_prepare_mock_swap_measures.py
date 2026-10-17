"""Mock setup must not alter existing policies or invent third-party grants."""
from datetime import date
from uuid import UUID
import pytest
from apps.reference_api.valuation_policy_contracts import PolicyView,PolicyRuleInput


def test_additive_policy_pins_owned_mark_index_and_existing_fx_separately():
    from scripts.prepare_mock_swap_measures import build_policy
    def uid(n):return UUID(int=n)
    base=PolicyView(valuationPolicyId=uid(1),policyCode='BASE',displayName='Existing',valuationCutId=uid(2),
        strategyId=None,versionNo=4,status='ACTIVE',validFrom=date(1900,1,1),validTo=None,
        createdByUserAccountId=None,createdAtUtc=None,selectionMode='FLEXIBLE',rules=[],
        defaultRules=[PolicyRuleInput(ruleSequence=1,subjectType='LISTING',seriesType='CLOSE',pricingConvention='SESSION_CLOSE',
            priceRequirement='AS_TRADED',allowSplitConversion=True)])
    pairs=[dict(subject=uid(10),index=uid(11),markSeries=uid(12),indexSeries=uid(13),cut=uid(14),calendar=uid(15),dataset=uid(16))]
    fx=PolicyRuleInput(ruleSequence=3,subjectReferenceNodeId=uid(20),marketDataSeriesId=uid(21),datasetId=uid(22),
        seriesType='FX_SPOT',valueBasis='RAW',pricingConvention='EXPLICIT_TIME',pricingCutId=uid(23),marketCalendarId=uid(24))
    policy=build_policy(base,uid(30),pairs,fx)
    assert policy.strategy_id==uid(30) and policy.policy_code!='BASE'
    assert len(base.rules)==0 and base.versionNo==4
    assert policy.default_rules[0].price_requirement=='AS_TRADED'
    by_subject={r.subject_reference_node_id:r for r in policy.rules}
    assert by_subject[uid(10)].market_data_series_id==uid(12)
    assert by_subject[uid(10)].value_basis=='RAW' and by_subject[uid(10)].price_requirement is None
    assert by_subject[uid(11)].market_data_series_id==uid(13)
    assert by_subject[uid(11)].value_basis=='INDEX_LEVEL'
    assert by_subject[uid(20)].market_data_series_id==uid(21)
    assert all(r.max_staleness_business_days==0 for r in policy.rules)


@pytest.mark.parametrize('field,value',[('indexLevel','NaN'),('indexLevel','-1'),('close','Infinity')])
def test_invented_history_rejects_invalid_values_before_writes(field,value):
    from scripts.prepare_mock_swap_measures import validate_history
    history=dict(synthetic=True,code='SPX',quote='WHOLE_SWAP_MTM_PER_UNIT',quoteFactor='1',
        prices=[dict(date='2026-10-07',observedAt='2026-10-07T20:00:00Z',indexLevel='6000',close='-20')])
    history['prices'][0][field]=value
    with pytest.raises(ValueError):validate_history(history)


def test_invented_history_keeps_negative_whole_swap_mark_and_rejects_duplicate_day():
    from scripts.prepare_mock_swap_measures import validate_history
    history=dict(synthetic=True,code='UKX',quote='WHOLE_SWAP_MTM_PER_UNIT',quoteFactor='1',
        prices=[dict(date='2026-10-07',observedAt='2026-10-07T15:30:00Z',indexLevel='9000',close='-20')])
    assert validate_history(history)[0]['close']=='-20'
    history['prices']*=2
    with pytest.raises(ValueError):validate_history(history)
