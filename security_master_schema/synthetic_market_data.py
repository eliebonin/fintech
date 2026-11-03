"""Explicit provenance for the five loader-owned invented datasets only.

This is seed governance, not a missing-profile fallback. Existing profiles,
requirements, grants and revocations are never repaired/re-enabled implicitly.
"""
from datetime import date
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from . import models as m

ORIGIN='repo:security_master_schema/demo_data.py + mvp_demo_data.py; invented fixture observations only; not provider permission or commercial clearance'
SEEDS=[(19,'UK_EQUITIES_EOD','LSEG_DEMO'),(50,'MULTI_ASSET_DEMO','LSEG_DEMO'),
    (116,'BBG_MVP_MULTI_ASSET_EOD','BLOOMBERG_MOCK'),(122,'YAHOO_MVP_EQUITIES_EOD','YAHOO_FINANCE_MOCK'),
    (126,'LSEG_MVP_REFERENCE_EOD','LSEG_MOCK')]
PLATFORM=UUID('00000000-0000-7000-8000-000000000002')
TENANTS=[UUID('00000000-0000-7000-8000-000000000011'),UUID('00000000-0000-7000-8000-000000000012')]


def provision_seed_profiles(c):
    """Caller owns transaction/audit; returns newly provisioned identities."""
    changed=[]
    for suffix,code,provider in SEEDS:
        identity=UUID(f'00000000-0000-7000-8000-{suffix:012d}')
        if c.scalar(select(m.dataset_access_profile.c.dataset_id).where(m.dataset_access_profile.c.dataset_id==identity)):
            continue
        d,pp,p=m.dataset,m.provider_product,m.data_provider
        row=c.execute(select(d,p.c.provider_code,p.c.owner_tenant_id).select_from(d.join(pp).join(p)).where(d.c.dataset_id==identity)).mappings().one_or_none()
        if not row:continue
        if row['dataset_code']!=code or row['provider_code']!=provider:
            raise ValueError('Seed identity differs; refusing synthetic classification')
        licence=c.scalar(select(m.data_licence.c.data_licence_id).where(m.data_licence.c.licence_code=='PLATFORM_SYNTHETIC_ORIGIN'))
        if not licence:
            licence=c.scalar(m.data_licence.insert().values(licensor_organisation_id=PLATFORM,licensee_organisation_id=PLATFORM,
                licence_code='PLATFORM_SYNTHETIC_ORIGIN',display_name='Invented seed-data origin — not a vendor contract',
                licence_reference='repo:security_master_schema/synthetic_market_data.py',permitted_use_description=ORIGIN,
                valid_from=date(1900,1,1)).returning(m.data_licence.c.data_licence_id))
        owner=c.execute(select(m.data_licence).where(m.data_licence.c.data_licence_id==licence)).mappings().one()
        if owner['licensee_organisation_id']!=PLATFORM or owner['licensor_organisation_id']!=PLATFORM or owner['status']!='ACTIVE':
            raise ValueError('Synthetic origin record needs explicit review; refusing overwrite')
        assignment=c.scalar(m.dataset_licence_assignment.insert().values(dataset_id=identity,data_licence_id=licence,
            licence_role='INTERNAL_USE',valid_from=row['valid_from'],valid_to=row['valid_to']).returning(m.dataset_licence_assignment.c.dataset_licence_assignment_id))
        c.execute(m.dataset_access_profile.insert().values(dataset_id=identity,licensee_organisation_id=PLATFORM,
            permitted_tenant_id=row['owner_tenant_id'],usage_scope='SYNTHETIC',provider_enabled=True,status='ACTIVE',activation_reference=ORIGIN))
        for activity in ('STORE','DISPLAY','NON_DISPLAY'):
            c.execute(m.licence_activity_grant.insert().values(dataset_licence_assignment_id=assignment,activity=activity,
                usage_scope='SYNTHETIC',evidence_basis='SYNTHETIC_ORIGIN',evidence_reference=ORIGIN,
                valid_from=row['valid_from'],valid_to=row['valid_to']))
            c.execute(m.dataset_right_requirement.insert().values(dataset_id=identity,activity=activity,
                requirement_code='INVENTED_SEED_ORIGIN',dataset_licence_assignment_id=assignment))
        # Make the old seed UI's display purpose explicit for its two fixture
        # tenants only; preserve effective dates, state and package coverage.
        ent=m.tenant_dataset_entitlement
        for source in c.execute(select(ent).where(ent.c.dataset_id==identity,ent.c.tenant_id.in_(TENANTS),ent.c.use_purpose=='VALUATION')).mappings().all():
            values={k:source[k] for k in ('tenant_id','dataset_id','coverage_mode','status','valid_from','valid_to')}
            added=c.scalar(insert(ent).values(**values,use_purpose='INTERNAL_REPORTING',dataset_licence_assignment_id=assignment)
                .on_conflict_do_nothing().returning(ent.c.tenant_dataset_entitlement_id))
            if added:
                for package in c.scalars(select(m.tenant_dataset_coverage.c.coverage_package_id).where(
                        m.tenant_dataset_coverage.c.tenant_dataset_entitlement_id==source['tenant_dataset_entitlement_id'])):
                    c.execute(m.tenant_dataset_coverage.insert().values(tenant_dataset_entitlement_id=added,dataset_id=identity,coverage_package_id=package))
        changed.append(identity)
    return changed
