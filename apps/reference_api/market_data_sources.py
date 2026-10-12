"""Tenant-visible delivery catalogue and immutable priority administration."""
import hashlib
import json
from sqlalchemy import select, or_, func
from security_master_schema import models as m
from security_master_schema.tenant_workspace import resolve_tenant_workspace
from market_data.source_priority import latest_version, ordered_datasets
from market_data.rights import denied_activity_datasets
from .resource_limits import governance_date
from .repository import IdempotencyKeyConflict


def authority(c, tenant, actor):
    workspace = resolve_tenant_workspace(c, tenant, actor, governance_date())
    if 'MARKET_DATA' not in workspace.module_codes:
        raise PermissionError('MARKET_DATA access is required')
    return workspace


def priority_view(c, row):
    return dict(versionId=row['source_priority_version_id'], instrumentTypeId=row['instrument_type_id'],
        scope='TENANT' if row['tenant_id'] else 'PLATFORM', mode=row['mode'], versionNo=row['version_no'],
        datasetIds=ordered_datasets(c, row['source_priority_version_id']), createdAt=row['created_at_utc'])


def catalogue(c, tenant, actor):
    workspace = authority(c, tenant, actor)
    today = governance_date()
    def current(table):
        return [table.c.status == 'ACTIVE', table.c.valid_from <= today,
            or_(table.c.valid_to.is_(None), table.c.valid_to >= today)]
    ent, dataset, product, provider = m.tenant_dataset_entitlement, m.dataset, m.provider_product, m.data_provider
    grants = c.execute(select(ent, dataset.c.dataset_code, dataset.c.display_name.label('dataset_name'),
        dataset.c.coverage_description, dataset.c.valid_from.label('dataset_from'), dataset.c.valid_to.label('dataset_to'),
        product.c.display_name.label('product_name'), provider.c.display_name.label('provider_name'), provider.c.owner_tenant_id)
        .select_from(ent.join(dataset).join(product).join(provider)).where(ent.c.tenant_id == tenant,
            *current(ent), *current(dataset), product.c.status == 'ACTIVE', provider.c.status == 'ACTIVE',
            or_(provider.c.owner_tenant_id.is_(None), provider.c.owner_tenant_id == tenant))).mappings().all()
    denied = set(denied_activity_datasets(c, tenant, today, ['NON_DISPLAY']))
    sources = {}
    owner = m.data_provider.alias('content_owner')
    package, grant, venue = m.dataset_coverage_package, m.tenant_dataset_coverage, m.market_venue
    for row in grants:
        did = row['dataset_id']
        source = sources.setdefault(did, dict(datasetId=did, provider=row['provider_name'], product=row['product_name'],
            code=row['dataset_code'], label=row['dataset_name'], tenantOwned=row['owner_tenant_id'] == tenant,
            coverageDescription=row['coverage_description'], coverageMode='SCOPED', packages=[], purposes=[], entitlementScopes=[],
            nonDisplayAllowed=False, validFrom=row['dataset_from'], validTo=row['dataset_to']))
        source['purposes'].append(row['use_purpose'])
        source['nonDisplayAllowed'] |= row['use_purpose'] == 'VALUATION' and did not in denied
        whole = row['coverage_mode'] == 'DATASET'
        if whole:
            source['coverageMode'] = 'DATASET'
        query = select(package.c.package_code, package.c.display_name, owner.c.display_name.label('owner'),
            venue.c.display_name.label('market'), package.c.information_timing, package.c.valid_from, package.c.valid_to
        ).select_from(package.join(owner, package.c.content_owner_provider_id == owner.c.data_provider_id)
            .outerjoin(venue, package.c.licensing_market_venue_id == venue.c.market_venue_id)).where(
                package.c.dataset_id == did, *current(package))
        if not whole:
            query = query.where(package.c.coverage_package_id.in_(select(grant.c.coverage_package_id).where(
                grant.c.tenant_dataset_entitlement_id == row['tenant_dataset_entitlement_id'], grant.c.dataset_id == did)))
        granted_packages = c.execute(query.order_by(package.c.package_code)).mappings().all()
        source['entitlementScopes'].append(dict(purpose=row['use_purpose'], coverageMode=row['coverage_mode'],
            packageCodes=[p['package_code'] for p in granted_packages], validFrom=row['valid_from'], validTo=row['valid_to']))
        for p in granted_packages:
            item = dict(code=p['package_code'], label=p['display_name'], contentOwner=p['owner'], market=p['market'],
                timing=p['information_timing'], validFrom=p['valid_from'], validTo=p['valid_to'])
            if item not in source['packages']:
                source['packages'].append(item)
    for source in sources.values():
        if len({grant['coverageMode'] for grant in source['entitlementScopes']}) > 1:
            source['coverageMode'] = 'MIXED'
    types = [dict(id=r[0], label=r[1]) for r in c.execute(select(m.instrument_type.c.instrument_type_id,
        m.instrument_type.c.type_code).order_by(m.instrument_type.c.type_code))]
    priorities = []
    for t in types:
        for scope in (None, tenant):
            row = latest_version(c, scope, t['id'])
            if row:
                priorities.append(priority_view(c, row))
    return dict(canManage='MARKET_DATA_MANAGE' in workspace.permission_codes, canManagePlatform=workspace.platform_role == 'PLATFORM_ADMIN',
        sources=sorted(sources.values(), key=lambda s: (not s['tenantOwned'], s['provider'], s['label'])),
        instrumentTypes=types, priorities=priorities)


def save_priority(c, tenant, actor, payload, key):
    workspace = authority(c, tenant, actor)
    platform = payload.scope == 'PLATFORM'
    if (platform and workspace.platform_role != 'PLATFORM_ADMIN') or (not platform and 'MARKET_DATA_MANAGE' not in workspace.permission_codes):
        raise PermissionError('Administrator authority is required for this priority scope')
    scope = None if platform else tenant
    digest = hashlib.sha256(json.dumps(payload.model_dump(mode='json'), sort_keys=True).encode()).hexdigest()
    def lock(name):
        c.execute(select(func.pg_advisory_xact_lock(int.from_bytes(hashlib.sha256(name.encode()).digest()[:8], 'big', signed=True))))
    lock(f'source-priority-key:{scope}:{key}')
    table = m.source_priority_version
    condition = table.c.tenant_id.is_(None) if platform else table.c.tenant_id == tenant
    old = c.execute(select(table).where(condition, table.c.submission_key == key)).mappings().one_or_none()
    if old:
        if old['submission_fingerprint'] != digest:
            raise IdempotencyKeyConflict('Priority key reused for a different request')
        return priority_view(c, old)
    if not c.scalar(select(m.instrument_type.c.instrument_type_id).where(m.instrument_type.c.instrument_type_id == payload.instrument_type_id)):
        raise ValueError('Unknown instrument type')
    available = {r['datasetId']: r for r in catalogue(c, tenant, actor)['sources']}
    if any(d not in available or (platform and available[d]['tenantOwned']) or 'VALUATION' not in available[d]['purposes'] for d in payload.dataset_ids):
        raise ValueError('Choose currently entitled valuation sources; platform defaults cannot contain tenant-private sources')
    lock(f'source-priority-scope:{scope}:{payload.instrument_type_id}')
    prior = latest_version(c, scope, payload.instrument_type_id)
    if payload.expected_version_id != (prior['source_priority_version_id'] if prior else None):
        raise IdempotencyKeyConflict('Priority settings have changed; reload before saving')
    row = c.execute(table.insert().values(tenant_id=scope, instrument_type_id=payload.instrument_type_id,
        mode=payload.mode, version_no=prior['version_no']+1 if prior else 1, created_by_user_account_id=actor,
        submission_key=key, submission_fingerprint=digest).returning(table)).mappings().one()
    if payload.dataset_ids:
        c.execute(m.source_priority_entry.insert(), [dict(source_priority_version_id=row['source_priority_version_id'],
            dataset_id=did, priority=index+1) for index, did in enumerate(payload.dataset_ids)])
    return priority_view(c, row)
