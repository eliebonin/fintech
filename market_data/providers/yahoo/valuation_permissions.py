"""Explicit operator activation for local personal Yahoo valuation use.

This records owner intent, not a Yahoo licence or commercial clearance. It does
not relax price-basis, calendar, currency, acquisition or tenant-boundary checks.
"""
from datetime import date,datetime,timezone
from sqlalchemy import select
from security_master_schema import models as m
from security_master_schema.tenant_workspace import resolve_tenant_workspace
from market_data.history import require_admin
from market_data.rights import load_rights
from market_data.storage import insert_returning

DATASETS=frozenset({'YAHOO_PERSONAL_EQUITY_DAILY','YAHOO_PERSONAL_FX_GBP'})


def enable_personal_valuation(c,tenant_id,actor_id,dataset_id,reference:str)->dict:
    if not reference.strip():
        raise ValueError('An explicit owner authorization reference is required')
    require_admin(c,tenant_id,actor_id)
    if 'VALUATION' not in resolve_tenant_workspace(c,tenant_id,actor_id,date.today()).module_codes:
        raise PermissionError('An active VALUATION module is required')
    dataset=c.execute(select(m.dataset).where(m.dataset.c.dataset_id==dataset_id).with_for_update()).mappings().one_or_none()
    if not dataset or dataset['dataset_code'] not in DATASETS:
        raise ValueError('Only existing personal Yahoo datasets can be activated')
    profile=c.execute(select(m.dataset_access_profile).where(m.dataset_access_profile.c.dataset_id==dataset_id)).mappings().one_or_none()
    if not profile or profile['permitted_tenant_id']!=tenant_id or profile['usage_scope']!='PERSONAL':
        raise PermissionError('Dataset is outside this tenant personal scope')
    for activity in ('ACQUIRE','STORE','DISPLAY'):
        if not load_rights(c,dataset_id,activity,date.today(),'PERSONAL').allowed:
            raise ValueError('Existing personal access is not effective; refusing reactivation')
    ent=m.tenant_dataset_entitlement
    existing=c.execute(select(ent).where(ent.c.dataset_id==dataset_id,ent.c.tenant_id==tenant_id,
        ent.c.use_purpose=='VALUATION')).mappings().all()
    if existing:
        if len(existing)!=1 or existing[0]['status']!='ACTIVE' or existing[0]['coverage_mode']!='DATASET' or existing[0]['valid_from']>date.today() or existing[0]['valid_to'] is not None and existing[0]['valid_to']<date.today():
            raise ValueError('Existing valuation entitlement needs review; refusing reactivation or broadening')
        if not load_rights(c,dataset_id,'NON_DISPLAY',date.today(),'PERSONAL').allowed:
            raise ValueError('Existing non-display permission needs review; refusing reactivation')
        return dict(datasetId=str(dataset_id),entitlementId=str(existing[0]['tenant_dataset_entitlement_id']))
    requirements=c.execute(select(m.dataset_right_requirement).where(
        m.dataset_right_requirement.c.dataset_id==dataset_id,m.dataset_right_requirement.c.activity=='NON_DISPLAY')).mappings().all()
    if requirements:
        if not load_rights(c,dataset_id,'NON_DISPLAY',date.today(),'PERSONAL').allowed:
            raise ValueError('Existing non-display requirements are unresolved; refusing replacement')
        assignment=requirements[0]['dataset_licence_assignment_id']
    else:
        code=f'YAHOO_PERSONAL_VALUATION_{dataset_id}'
        if c.scalar(select(m.data_licence.c.data_licence_id).where(m.data_licence.c.licence_code==code)):
            raise ValueError('Existing declaration needs review; refusing replacement')
        evidence=(f'Owner personal valuation declaration by tenant administrator {actor_id} for tenant {tenant_id}, '
            f'recorded at {datetime.now(timezone.utc).isoformat()}: {reference.strip()}. '
            'Local personal research valuation and automated internal calculation only. '
            'Not provider permission, not contractual or commercial clearance; no client reporting or redistribution. '
            f'Authorizes current calculation over dataset business dates from {dataset["valid_from"]}; not a claim of historical authorization.')
        licence=insert_returning(c,m.data_licence,'data_licence_id',
            licensor_organisation_id=profile['licensee_organisation_id'],licensee_organisation_id=profile['licensee_organisation_id'],
            licence_code=code,display_name='Owner personal valuation declaration — not provider permission',
            licence_reference=reference.strip()[:500],permitted_use_description=evidence,valid_from=date.today())
        assignment=insert_returning(c,m.dataset_licence_assignment,'dataset_licence_assignment_id',
            dataset_id=dataset_id,data_licence_id=licence,licence_role='INTERNAL_USE',valid_from=date.today())
        c.execute(m.licence_activity_grant.insert().values(dataset_licence_assignment_id=assignment,
            activity='NON_DISPLAY',usage_scope='PERSONAL',evidence_basis='PERSONAL_DECLARATION',
            evidence_reference=evidence,valid_from=date.today()))
        c.execute(m.dataset_right_requirement.insert().values(dataset_id=dataset_id,activity='NON_DISPLAY',
            requirement_code='OWNER_PERSONAL_VALUATION_DECLARATION',dataset_licence_assignment_id=assignment))
    entitlement=insert_returning(c,ent,'tenant_dataset_entitlement_id',tenant_id=tenant_id,dataset_id=dataset_id,
        dataset_licence_assignment_id=assignment,use_purpose='VALUATION',coverage_mode='DATASET',
        valid_from=dataset['valid_from'],valid_to=dataset['valid_to'])
    return dict(datasetId=str(dataset_id),entitlementId=str(entitlement))
