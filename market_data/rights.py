"""Activity-specific, conjunctive rights; declarations are never legal clearance."""
from dataclasses import dataclass
from datetime import date


ACTIVITIES = frozenset({'ACQUIRE', 'STORE', 'DISPLAY', 'NON_DISPLAY', 'CLIENT_REPORTING', 'REDISTRIBUTE', 'DERIVED_DATA'})


@dataclass(frozen=True)
class RightsDecision:
    allowed: bool
    reason: str
    evidence: tuple[dict, ...] = ()


def evaluate_rights(profile, requirements, grants, activity: str, on_date: date, scope: str) -> RightsDecision:
    if activity not in ACTIVITIES or scope not in {'PERSONAL', 'COMMERCIAL'}:
        return RightsDecision(False, 'Unsupported activity or scope')
    if not profile or profile['status'] != 'ACTIVE' or not profile['provider_enabled']:
        return RightsDecision(False, 'Dataset access is not activated')
    if profile['usage_scope'] != scope:
        return RightsDecision(False, 'Operating scope does not match')
    applicable = [r for r in requirements if r['dataset_id'] == profile['dataset_id'] and r['activity'] == activity]
    if not applicable:
        return RightsDecision(False, 'No reviewed requirements for this activity')
    evidence = []
    for requirement in applicable:
        # Reserved prerequisite: owner's intended purpose is not the provider's access permission.
        allowed_bases = ({'CONTRACT'} if scope == 'COMMERCIAL' or requirement['requirement_code'] == 'AUTOMATED_SOURCE_ACCESS'
                         else {'CONTRACT', 'PERSONAL_DECLARATION'})
        if (scope == 'PERSONAL' and activity == 'ACQUIRE'
                and requirement['requirement_code'] == 'AUTOMATED_SOURCE_ACCESS'
                and profile.get('dataset_code') in {'YAHOO_PERSONAL_EQUITY_DAILY','YAHOO_PERSONAL_FX_GBP'}
                and profile.get('permitted_tenant_id') is not None):
            allowed_bases = allowed_bases | {'PERSONAL_RESEARCH_EXCEPTION'}
        candidates = []
        for grant in grants:
            if (grant['dataset_licence_assignment_id'] != requirement['dataset_licence_assignment_id']
                    or grant['dataset_id'] != profile['dataset_id']
                    or grant['licensee_organisation_id'] != profile['licensee_organisation_id']
                    or grant['activity'] != activity or grant['usage_scope'] != scope
                    or any(grant[k] != 'ACTIVE' for k in ('status', 'assignment_status', 'licence_status'))
                    or not grant['evidence_reference'].strip()
                    or grant['evidence_basis'] not in allowed_bases):
                continue
            if any(grant[start] > on_date or (grant[end] is not None and grant[end] < on_date)
                   for start, end in (('valid_from', 'valid_to'), ('assignment_valid_from', 'assignment_valid_to'), ('licence_valid_from', 'licence_valid_to'))):
                continue
            candidates.append(grant)
        if not candidates:
            return RightsDecision(False, f"Unsatisfied requirement: {requirement['requirement_code']}")
        # Deterministic evidence if successive effective grants overlap.
        grant = max(candidates, key=lambda g: (g['valid_from'], str(g.get('grant_id', ''))))
        evidence.append(dict(requirement=requirement['requirement_code'],
                             assignmentId=str(grant['dataset_licence_assignment_id']),
                             grantId=str(grant.get('grant_id', '')), activity=activity,
                             scope=scope, basis=grant['evidence_basis'],
                             reference=grant['evidence_reference'], evaluatedOn=on_date.isoformat(),
                             licensee=str(grant['licensee_organisation_id'])))
    return RightsDecision(True, 'All required activity rights satisfied', tuple(evidence))


def load_rights(connection, dataset_id, activity: str, on_date: date, scope: str | None = None):
    from sqlalchemy import select
    from security_master_schema import models as m
    dataset = connection.execute(select(m.dataset).where(m.dataset.c.dataset_id == dataset_id)).mappings().one_or_none()
    if (not dataset or dataset['status'] != 'ACTIVE' or dataset['valid_from'] > on_date
            or dataset['valid_to'] is not None and dataset['valid_to'] < on_date):
        return RightsDecision(False, 'Dataset is inactive or outside its effective dates')
    profile = connection.execute(select(m.dataset_access_profile).where(
        m.dataset_access_profile.c.dataset_id == dataset_id)).mappings().one_or_none()
    if profile:
        profile = dict(profile, dataset_code=dataset['dataset_code'])
    requirements = connection.execute(select(m.dataset_right_requirement).where(
        m.dataset_right_requirement.c.dataset_id == dataset_id,
        m.dataset_right_requirement.c.activity == activity)).mappings().all()
    g, a, l = m.licence_activity_grant, m.dataset_licence_assignment, m.data_licence
    grants = connection.execute(select(g, a.c.dataset_id, l.c.licensee_organisation_id,
        a.c.status.label('assignment_status'), l.c.status.label('licence_status'),
        a.c.valid_from.label('assignment_valid_from'), a.c.valid_to.label('assignment_valid_to'),
        l.c.valid_from.label('licence_valid_from'), l.c.valid_to.label('licence_valid_to'))
        .select_from(g.join(a).join(l)).where(a.c.dataset_id == dataset_id, g.c.activity == activity)).mappings().all()
    return evaluate_rights(profile, requirements, grants, activity, on_date,
                           scope or (profile['usage_scope'] if profile else 'PERSONAL'))


def denied_display_datasets(connection, tenant_id, on_date: date):
    """Legacy fixtures keep their current model; all profiled datasets are strict."""
    return denied_activity_datasets(connection, tenant_id, on_date, ('DISPLAY',))


def denied_activity_datasets(connection, tenant_id, on_date: date, activities):
    from sqlalchemy import select
    from security_master_schema import models as m
    profiles = connection.execute(select(m.dataset_access_profile)).mappings().all()
    return [p['dataset_id'] for p in profiles
            if (p['permitted_tenant_id'] is not None and p['permitted_tenant_id'] != tenant_id)
            or any(not load_rights(connection, p['dataset_id'], activity, on_date).allowed
                   for activity in activities)]
