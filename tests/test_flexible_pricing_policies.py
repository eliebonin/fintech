"""Mode selection never lets a missing explicit convention borrow a default."""
from uuid import uuid4
import pytest
from sqlalchemy import select
from security_master_schema import models as m
from security_master_schema.market_data_resolver import resolve_market_data
from security_master_schema.demo_data import DEMO_IDS
from apps.reference_api.valuation_policy_contracts import PolicyCreate
from test_composite_policy_resolution import composite
from test_composite_policy_api import call, policy_payload
from test_valuation_service import valued, service


def test_flexible_unmatched_uses_default_with_frozen_origin(composite):
    c, request, _ = composite
    c.execute(m.valuation_policy.update().where(m.valuation_policy.c.valuation_policy_id == request.valuation_policy_id).values(selection_mode='FLEXIBLE'))
    c.execute(m.valuation_policy_rule.update().where(m.valuation_policy_rule.c.valuation_policy_rule_id == DEMO_IDS['valuation_policy_rule']).values(is_default=True))
    result = resolve_market_data(c, request)
    assert result.status == 'SELECTED'
    assert result.pricing_evidence['policyMode'] == 'FLEXIBLE'
    assert result.pricing_evidence['ruleOrigin'] == 'DEFAULT'


def test_strict_ignores_default_rows(composite):
    c, request, _ = composite
    c.execute(m.valuation_policy_rule.update().where(m.valuation_policy_rule.c.valuation_policy_rule_id == DEMO_IDS['valuation_policy_rule']).values(is_default=True))
    result = resolve_market_data(c, request)
    assert result.exception_code == 'NO_MATCHING_POLICY_RULE'
    assert result.pricing_evidence['policyMode'] == 'STRICT'


def test_missing_broad_explicit_rule_beats_more_specific_default(composite):
    c, request, _ = composite
    c.execute(m.valuation_policy.update().where(m.valuation_policy.c.valuation_policy_id == request.valuation_policy_id).values(selection_mode='FLEXIBLE'))
    c.execute(m.valuation_policy_rule.update().where(m.valuation_policy_rule.c.valuation_policy_rule_id == DEMO_IDS['valuation_policy_rule']).values(is_default=True))
    exact = c.execute(m.valuation_policy_rule.insert().values(valuation_policy_id=request.valuation_policy_id,
        rule_sequence=900, series_type='NO_SUCH_CLOSE', pricing_convention='SESSION_CLOSE', selection_method='OFFICIAL')
        .returning(m.valuation_policy_rule.c.valuation_policy_rule_id)).scalar_one()
    result = resolve_market_data(c, request)
    assert result.status == 'MISSING' and result.policy_rule_id == exact
    assert result.pricing_evidence['ruleOrigin'] == 'EXPLICIT'


def test_flexible_api_defaults_round_trip_and_replay():
    payload = policy_payload()
    payload.update(selectionMode='FLEXIBLE', defaultRules=payload.pop('rules'), rules=[])
    payload['defaultRules'][0].update(valueBasis='RAW', subjectType='LISTING')
    key = str(uuid4())
    response = call('POST', '/v1/market-data/valuation-policies', payload, key)
    assert response.status_code == 201, response.text
    saved = response.json()
    assert saved['selectionMode'] == 'FLEXIBLE' and not saved['rules']
    assert saved['defaultRules'][0]['valueBasis'] == 'RAW'
    assert call('POST', '/v1/market-data/valuation-policies', payload, key).json() == saved
    assert call('GET', '/v1/market-data/valuation-policies/' + saved['valuationPolicyId']).json() == saved


@pytest.mark.parametrize('change', ['strict_defaults', 'unbounded', 'duplicate', 'empty'])
def test_invalid_default_configuration_is_rejected(change):
    payload = policy_payload()
    payload.update(selectionMode='FLEXIBLE', defaultRules=[dict(payload['rules'][0], ruleSequence=2)])
    if change == 'strict_defaults': payload['selectionMode'] = 'STRICT'
    if change == 'unbounded': payload['defaultRules'][0]['maxStalenessBusinessDays'] = None
    if change == 'duplicate': payload['defaultRules'][0]['ruleSequence'] = 1
    if change == 'empty': payload.update(rules=[], defaultRules=[])
    with pytest.raises(ValueError):
        PolicyCreate.model_validate(payload)


def test_explicit_bounded_carry_forward_is_accepted_in_valuation(valued):
    from datetime import date
    c, request, _ = valued
    c.execute(m.market_data_observation.delete().where(m.market_data_observation.c.market_date == date(2026,10,1)))
    c.execute(m.valuation_policy_rule.update().where(m.valuation_policy_rule.c.valuation_policy_rule_id == DEMO_IDS['valuation_policy_rule']).values(
        pricing_date_rule='PRIOR_AVAILABLE', max_staleness_business_days=2))
    result = service().calculate(c, request)
    assert result.evidence['selections'][0]['pricing_date_used'] == '2026-09-29'
    assert result.evidence['selections'][0]['staleness_business_days'] == 2


def test_exceeded_carry_forward_still_blocks_valuation(valued):
    from datetime import date
    c, request, _ = valued
    c.execute(m.market_data_observation.delete().where(m.market_data_observation.c.market_date == date(2026,10,1)))
    c.execute(m.valuation_policy_rule.update().where(m.valuation_policy_rule.c.valuation_policy_rule_id == DEMO_IDS['valuation_policy_rule']).values(
        pricing_date_rule='PRIOR_AVAILABLE', max_staleness_business_days=1))
    with pytest.raises(service().ValuationBlocked, match='MAX_STALENESS_EXCEEDED'):
        service().calculate(c, request)


def test_strict_creation_uses_canonical_official_close_fingerprint():
    import hashlib, json
    from uuid import UUID
    from apps.reference_api.db import get_engine
    payload = PolicyCreate.model_validate(policy_payload())
    # This checks a newly saved canonical fingerprint, not an old replay.
    canonical=payload.model_dump(mode='json')
    canonical.pop('selection_mode');canonical.pop('default_rules')
    # The historical request omitted these later economic/FX controls. Absent
    # controls must not change retry identity merely because the schema grew.
    for rule in canonical['rules']:
        rule.pop('price_requirement');rule.pop('allow_split_conversion');rule.pop('allow_inverse_fx')
    expected=hashlib.sha256(json.dumps(canonical,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    response = call('POST','/v1/market-data/valuation-policies',payload.model_dump(mode='json', by_alias=True))
    assert response.status_code == 201, response.text
    with get_engine().connect() as c:
        assert c.scalar(select(m.valuation_policy.c.submission_fingerprint).where(
            m.valuation_policy.c.valuation_policy_id == UUID(response.json()['valuationPolicyId']))) == expected


def test_execution_price_basis_is_frozen_alongside_market_marks(valued):
    from tests.test_valuation_storage import store
    from apps.reference_api.db import get_engine
    c, request, trade = valued
    result = service().calculate(c, request)
    k = store()
    run = k.begin_attempt(get_engine(), request, DEMO_IDS['demo_user_account'], str(uuid4()))
    batch = k.stage(c, run, DEMO_IDS['demo_user_account'], result)
    evidence = k.batch_view(c, request.tenant_id, batch)['items'][0]['evidence']
    assert evidence['executionInputs'][0]['booking']['trade_id'] == str(trade)
    assert evidence['executionInputs'][0]['booking']['price'] == '1.23'
    assert len(evidence['selections']) == 1  # No invented opening market mark.
