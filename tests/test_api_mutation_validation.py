"""Malformed management inputs are client errors, not database/server errors."""
import pytest
from pydantic import ValidationError
from apps.reference_api.contracts import StrategyStatusRequest, StrategyCreateRequest, MappingDecisionRequest


@pytest.mark.parametrize('payload', [{'status': 'INVALID'}, {'status': 'ARCHIVED', 'statuz': 'ARCHIVED'}])
def test_strategy_status_rejects_invalid_or_unknown_fields(payload):
    with pytest.raises(ValidationError): StrategyStatusRequest.model_validate(payload)


@pytest.mark.parametrize('extra', [
    {'strategyType': 'UNKNOWN'}, {'strategyCode': '   '}, {'displayName': '   '},
    {'baseCurrencyCode': 'X' * 31}, {'operatingModelLabel': 'invalid for FUND'}, {'displyName': 'typo'},
])
def test_strategy_creation_rejects_invalid_controlled_data(extra):
    with pytest.raises(ValidationError):
        StrategyCreateRequest.model_validate({'strategyCode': 'ALPHA', 'displayName': 'Alpha', 'strategyType': 'FUND', **extra})


def test_decision_reason_cannot_be_whitespace():
    with pytest.raises(ValidationError):
        MappingDecisionRequest.model_validate({'decision': 'APPROVED', 'reason': '   '})


@pytest.mark.parametrize('kind',['bond','equity'])
def test_legacy_proposals_reject_unknown_fields(kind):
    from apps.reference_api.contracts import BondProposalRequest, EquityProposalRequest
    payload={'canonicalName':'Typed instrument','effectiveFrom':'2026-09-01','baseCurrencyId':'00000000-0000-4000-8000-000000000001','canoncalName':'typo'}
    if kind=='bond': payload['couponType']='ZERO'
    with pytest.raises(ValidationError):
        (BondProposalRequest if kind=='bond' else EquityProposalRequest).model_validate(payload)


def test_annotation_input_is_bounded_before_domain_validation():
    from apps.reference_api.contracts import TradePropertyInput
    with pytest.raises(ValidationError):
        TradePropertyInput(definitionId='00000000-0000-4000-8000-000000000001',value='x'*2001)


@pytest.mark.parametrize('kind',['bond','equity'])
def test_empty_source_retry_key_is_rejected(kind):
    from apps.reference_api.contracts import BondProposalRequest, EquityProposalRequest
    payload={'canonicalName':'Retry key','effectiveFrom':'2026-09-01','baseCurrencyId':'00000000-0000-4000-8000-000000000001','idempotencyKey':''}
    if kind=='bond':payload['couponType']='ZERO'
    with pytest.raises(ValidationError):
        (BondProposalRequest if kind=='bond' else EquityProposalRequest).model_validate(payload)


def test_nested_listing_does_not_silently_ignore_multiplier_typos():
    from apps.reference_api.contracts import EquityListingProposal
    with pytest.raises(ValidationError):
        EquityListingProposal.model_validate({'marketVenueId':'00000000-0000-4000-8000-000000000001',
            'tradingSymbol':'TYPED','tradingCurrencyId':'00000000-0000-4000-8000-000000000002',
            'effectiveFrom':'2026-09-01','unitMultiplir':'50'})
