"""Explicit activity rights must satisfy every prerequisite, not their union."""
from datetime import date

import pytest

from market_data import rights


DAY = date(2026, 10, 6)


def bundle():
    profile = dict(dataset_id='D', licensee_organisation_id='P', usage_scope='PERSONAL',
                   status='ACTIVE', provider_enabled=True)
    requirements = [dict(requirement_code=code, dataset_id='D', activity='DISPLAY',
                         dataset_licence_assignment_id=code) for code in ('distributor', 'owner')]
    grants = [dict(dataset_licence_assignment_id=code, dataset_id='D',
                   licensee_organisation_id='P', activity='DISPLAY', usage_scope='PERSONAL',
                   evidence_basis='PERSONAL_DECLARATION', evidence_reference='owner declaration',
                   status='ACTIVE', assignment_status='ACTIVE', licence_status='ACTIVE',
                   valid_from=DAY, valid_to=None, assignment_valid_from=DAY,
                   assignment_valid_to=None, licence_valid_from=DAY, licence_valid_to=None)
              for code in ('distributor', 'owner')]
    return profile, requirements, grants


def test_all_layers_are_required_and_evidence_is_retained():
    profile, requirements, grants = bundle()
    result = rights.evaluate_rights(profile, requirements, grants, 'DISPLAY', DAY, 'PERSONAL')
    assert result.allowed
    assert len(result.evidence) == 2
    assert {r['requirement'] for r in result.evidence} == {'distributor', 'owner'}
    assert not rights.evaluate_rights(profile, requirements, grants[:1], 'DISPLAY', DAY, 'PERSONAL').allowed


@pytest.mark.parametrize('change', ['licensee', 'dataset', 'activity', 'expired', 'future', 'suspended', 'contract', 'activation', 'missing'])
def test_rights_cannot_be_borrowed_or_inferred(change):
    profile, requirements, grants = bundle()
    if change == 'licensee': grants[1]['licensee_organisation_id'] = 'ANOTHER'
    if change == 'dataset': grants[1]['dataset_id'] = 'ANOTHER'
    if change == 'activity': grants[1]['activity'] = 'REDISTRIBUTE'
    if change == 'expired': grants[1]['licence_valid_to'] = date(2026, 10, 5)
    if change == 'future': grants[1]['assignment_valid_from'] = date(2026, 10, 7)
    if change == 'suspended': grants[1]['assignment_status'] = 'SUSPENDED'
    if change == 'contract': profile['usage_scope'] = 'COMMERCIAL'
    if change == 'activation': profile['provider_enabled'] = False
    if change == 'missing': requirements = []
    scope = profile['usage_scope']
    assert not rights.evaluate_rights(profile, requirements, grants, 'DISPLAY', DAY, scope).allowed


def test_personal_declaration_is_never_commercial_permission():
    profile, requirements, grants = bundle()
    assert not rights.evaluate_rights(profile, requirements, grants, 'DISPLAY', DAY, 'COMMERCIAL').allowed
    profile['usage_scope'] = 'COMMERCIAL'
    for grant in grants:
        grant['usage_scope'] = 'COMMERCIAL'
    assert not rights.evaluate_rights(profile, requirements, grants, 'DISPLAY', DAY, 'COMMERCIAL').allowed
    for grant in grants:
        grant['evidence_basis'] = 'CONTRACT'
    assert rights.evaluate_rights(profile, requirements, grants, 'DISPLAY', DAY, 'COMMERCIAL').allowed


def test_valid_to_is_inclusive_but_blank_evidence_denies():
    profile, requirements, grants = bundle()
    for grant in grants:
        grant['valid_to'] = DAY
    assert rights.evaluate_rights(profile, requirements, grants, 'DISPLAY', DAY, 'PERSONAL').allowed
    grants[0]['evidence_reference'] = ' '
    assert not rights.evaluate_rights(profile, requirements, grants, 'DISPLAY', DAY, 'PERSONAL').allowed


def test_automated_source_permission_cannot_be_an_owner_purpose_declaration():
    profile, requirements, grants = bundle()
    for row in requirements + grants:
        row['activity'] = 'ACQUIRE'
    requirements[1]['requirement_code'] = 'AUTOMATED_SOURCE_ACCESS'
    assert not rights.evaluate_rights(profile, requirements, grants, 'ACQUIRE', DAY, 'PERSONAL').allowed
    grants[1]['evidence_basis'] = 'CONTRACT'
    grants[1]['evidence_reference'] = 'Reviewed provider permission for personal automated acquisition'
    assert rights.evaluate_rights(profile, requirements, grants, 'ACQUIRE', DAY, 'PERSONAL').allowed


@pytest.mark.parametrize('change', [None, 'dataset', 'tenant', 'activity', 'scope', 'ordinary_layer'])
def test_personal_research_exception_is_narrow_and_identified(change):
    profile, requirements, grants = bundle()
    profile.update(dataset_code='YAHOO_PERSONAL_EQUITY_DAILY', permitted_tenant_id='T')
    requirements, grants = requirements[:1], grants[:1]
    requirements[0].update(requirement_code='AUTOMATED_SOURCE_ACCESS', activity='ACQUIRE')
    grants[0].update(activity='ACQUIRE', evidence_basis='PERSONAL_RESEARCH_EXCEPTION',
                     evidence_reference='Owner explicitly approved local personal research')
    if change == 'dataset': profile['dataset_code'] = 'OTHER_PROVIDER'
    if change == 'tenant': profile['permitted_tenant_id'] = None
    if change == 'activity':
        requirements[0]['activity'] = grants[0]['activity'] = 'REDISTRIBUTE'
    if change == 'scope':
        profile['usage_scope'] = grants[0]['usage_scope'] = 'COMMERCIAL'
    if change == 'ordinary_layer': requirements[0]['requirement_code'] = 'UPSTREAM_PERMISSION'
    result = rights.evaluate_rights(profile, requirements, grants, grants[0]['activity'], DAY, profile['usage_scope'])
    assert result.allowed is (change is None)
    if result.allowed:
        assert result.evidence[0]['basis'] == 'PERSONAL_RESEARCH_EXCEPTION'
