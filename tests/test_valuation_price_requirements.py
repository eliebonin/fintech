"""Economic requirements must not silently broaden legacy price selection."""
import pytest
from apps.reference_api.valuation_policy_contracts import PolicyRuleInput


def test_as_traded_requirement_round_trips_without_forcing_a_source_basis():
    rule = PolicyRuleInput.model_validate(dict(ruleSequence=1, seriesType='CLOSE',
        pricingConvention='SESSION_CLOSE', priceRequirement='AS_TRADED', allowSplitConversion=True))
    dumped = rule.model_dump(by_alias=True)
    assert dumped['priceRequirement'] == 'AS_TRADED'
    assert dumped['allowSplitConversion'] is True
    assert dumped['valueBasis'] is None


@pytest.mark.parametrize('changes', [dict(allowSplitConversion=True),
    dict(priceRequirement='AS_TRADED', valueBasis='VENDOR_ADJUSTED'),
    dict(priceRequirement='AS_TRADED', seriesType='ADJUSTED_CLOSE'),
    dict(priceRequirement='AS_TRADED', pricingConvention='LEGACY')])
def test_incompatible_economic_requests_reject(changes):
    with pytest.raises(ValueError):
        PolicyRuleInput.model_validate(dict(ruleSequence=1, seriesType='CLOSE',
            pricingConvention='SESSION_CLOSE') | changes)


def test_legacy_raw_rules_remain_native_only():
    rule = PolicyRuleInput.model_validate(dict(ruleSequence=1, seriesType='CLOSE',
        pricingConvention='SESSION_CLOSE', valueBasis='RAW'))
    assert getattr(rule, 'price_requirement', 'MISSING') is None
    assert getattr(rule, 'allow_split_conversion', 'MISSING') is False
