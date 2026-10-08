"""Operator-only Yahoo catalogue for one local simulated personal workspace."""
from datetime import date, datetime, timezone

from sqlalchemy import select

from security_master_schema import models as m
from security_master_schema.index_universe_seed import load_manifest
from market_data.storage import insert_returning as _insert


DATASET_CODE = 'YAHOO_PERSONAL_EQUITY_DAILY'
TERMS_URL = 'https://legal.yahoo.com/ie/en/yahoo/terms/otos/index.html'


def yahoo_symbol(symbol: str, mic: str) -> str:
    if mic in {'XNAS', 'XNYS', 'BATS'}:
        return symbol.replace('.', '-')
    if mic in {'XPAR', 'XAMS'}:
        return symbol + ('.PA' if mic == 'XPAR' else '.AS')
    raise ValueError('Unsupported venue for Yahoo equity mapping')


def onboard_personal(c, tenant_id, actor_id, declaration: str) -> dict:
    if not declaration.strip():
        raise ValueError('An explicit personal-project declaration is required')
    actor = c.scalar(select(m.user_account.c.user_account_id).where(
        m.user_account.c.user_account_id == actor_id, m.user_account.c.status == 'ACTIVE'))
    tenant = c.scalar(select(m.tenant.c.tenant_id).where(m.tenant.c.tenant_id == tenant_id, m.tenant.c.status == 'ACTIVE'))
    if not actor or not tenant:
        raise ValueError('An active recorded actor and tenant are required')
    existing = c.execute(select(m.dataset_access_profile).join(m.dataset).where(
        m.dataset.c.dataset_code == DATASET_CODE)).mappings().one_or_none()
    if existing and existing['permitted_tenant_id'] != tenant_id:
        raise ValueError('Personal dataset is configured for a different tenant')
    from security_master_schema.tenant_workspace import resolve_tenant_workspace
    workspace = resolve_tenant_workspace(c, tenant_id, actor_id, date.today())
    if workspace.membership_role != 'TENANT_ADMIN':
        raise ValueError('Personal source activation requires the tenant administrator')
    module_id = c.scalar(select(m.platform_module.c.platform_module_id).where(m.platform_module.c.module_code == 'MARKET_DATA'))
    if 'MARKET_DATA' not in workspace.module_codes:
        if c.scalar(select(m.tenant_module_entitlement.c.tenant_module_entitlement_id).where(
                m.tenant_module_entitlement.c.tenant_id == tenant_id,
                m.tenant_module_entitlement.c.platform_module_id == module_id).limit(1)):
            raise ValueError('Existing market-data module grant is not effective; refusing automatic reactivation')
        now = datetime.now(timezone.utc)
        c.execute(m.tenant_module_entitlement.insert().values(tenant_id=tenant_id, platform_module_id=module_id,
            entitlement_state='GRANTED', entitlement_source='MANUAL',
            approved_by_user_account_id=actor_id, approved_at_utc=now, valid_from=date.today(), recorded_at_utc=now))
    if existing:
        if existing['status'] != 'ACTIVE' or existing['usage_scope'] != 'PERSONAL' or not existing['provider_enabled']:
            raise ValueError('Existing profile is not active personal scope; refusing automatic reactivation')
        dataset_id, namespace_id = existing['dataset_id'], existing['external_id_namespace_id']
    else:
        if c.scalar(select(m.dataset.c.dataset_id).where(m.dataset.c.dataset_code == DATASET_CODE)):
            raise ValueError('Dataset exists without a reviewed profile; refusing implicit activation')
        today = date.today()
        orgs = []
        for code, name, kind in [('YAHOO_PERSONAL_DELIVERY', 'Yahoo Finance delivery identity', 'VENDOR'),
                                  ('PERSONAL_PROJECT_OPERATOR', 'Local personal project operator', 'OPERATIONAL')]:
            entity_id = c.scalar(select(m.entity.c.entity_id).where(m.entity.c.entity_code == code))
            if not entity_id:
                entity_id = _insert(c, m.entity, 'entity_id', entity_code=code, display_name=name)
            org_id = c.scalar(select(m.organisation.c.organisation_id).where(m.organisation.c.entity_id == entity_id))
            if not org_id:
                org_id = _insert(c, m.organisation, 'organisation_id', entity_id=entity_id,
                                 organisation_type=kind, display_name=name)
            orgs.append(org_id)
        provider = _insert(c, m.data_provider, 'data_provider_id', organisation_id=orgs[0],
                           provider_code='YAHOO_FINANCE_PERSONAL', display_name='Yahoo Finance personal project')
        product = _insert(c, m.provider_product, 'provider_product_id', data_provider_id=provider,
                          product_code='PUBLIC_CHART_DAILY', display_name='Public daily equity charts')
        dataset_id = _insert(c, m.dataset, 'dataset_id', provider_product_id=product, dataset_code=DATASET_CODE,
                            display_name='Yahoo daily equity history — personal project', data_domain='MARKET_DATA',
                            coverage_description='Seeded S&P 500 and CAC 40 listings; provider Close and Adj Close, separate adjustment bases. Not official prices.',
                            delivery_channel='API', valid_from=today)
        source = _insert(c, m.integration_source_system, 'integration_source_system_id',
                         owning_organisation_id=orgs[0], tenant_id=tenant_id,
                         system_code='YAHOO_FINANCE_PERSONAL', display_name='Local Yahoo chart adapter',
                         source_kind='VENDOR', environment='SANDBOX')
        namespace_id = _insert(c, m.external_id_namespace, 'external_id_namespace_id',
                               integration_source_system_id=source, namespace_code='YAHOO_PERSONAL_EQUITY_SYMBOL',
                               external_object_type='LISTING', valid_from=today,
                               description='Proposed current universe aliases; validate source venue, currency, timezone and equity type before publication. Historical continuity is not certified.')
        basis = f'Personal declaration by recorded actor {actor_id}: {declaration}. Source terms: {TERMS_URL}. Not contractual or commercial clearance; automated-access conditions require separate consideration.'
        licence = _insert(c, m.data_licence, 'data_licence_id', licensor_organisation_id=orgs[0],
                          licensee_organisation_id=orgs[1], licence_code='YAHOO_PERSONAL_PROJECT_DECLARATION',
                          display_name='Personal-use declaration — not commercial clearance', licence_reference=TERMS_URL,
                          permitted_use_description=basis, valid_from=today)
        assignment = _insert(c, m.dataset_licence_assignment, 'dataset_licence_assignment_id',
                             dataset_id=dataset_id, data_licence_id=licence, licence_role='ACQUISITION', valid_from=today)
        c.execute(m.dataset_access_profile.insert().values(dataset_id=dataset_id,
            licensee_organisation_id=orgs[1], permitted_tenant_id=tenant_id,
            external_id_namespace_id=namespace_id, usage_scope='PERSONAL', provider_enabled=True,
            activation_reference=basis, status='ACTIVE'))
        for activity in ('ACQUIRE', 'STORE', 'DISPLAY'):
            c.execute(m.licence_activity_grant.insert().values(dataset_licence_assignment_id=assignment,
                activity=activity, usage_scope='PERSONAL', evidence_basis='PERSONAL_DECLARATION',
                evidence_reference=basis, valid_from=today))
            c.execute(m.dataset_right_requirement.insert().values(dataset_id=dataset_id, activity=activity,
                requirement_code='PERSONAL_SOURCE_TERMS_DECLARATION', dataset_licence_assignment_id=assignment))
        c.execute(m.tenant_dataset_entitlement.insert().values(tenant_id=tenant_id, dataset_id=dataset_id,
            dataset_licence_assignment_id=assignment, use_purpose='INTERNAL_REPORTING', valid_from=today))
    # Personal purpose alone does not supply Yahoo's express prior automated-access permission.
    # Never overwrite a separately reviewed assignment; a missing layer remains unsatisfied.
    if not c.scalar(select(m.dataset_right_requirement.c.requirement_id).where(
            m.dataset_right_requirement.c.dataset_id == dataset_id,
            m.dataset_right_requirement.c.activity == 'ACQUIRE',
            m.dataset_right_requirement.c.requirement_code == 'AUTOMATED_SOURCE_ACCESS')):
        c.execute(m.dataset_right_requirement.insert().values(dataset_id=dataset_id, activity='ACQUIRE',
            requirement_code='AUTOMATED_SOURCE_ACCESS', dataset_licence_assignment_id=None))
    mappings = []
    for row in load_manifest()['securities']:
        node = c.execute(select(m.listing, m.currency.c.currency_code)
            .select_from(m.listing.join(m.financial_reference_node, m.listing.c.listing_node_id == m.financial_reference_node.c.reference_node_id)
                         .join(m.currency, m.listing.c.trading_currency_id == m.currency.c.currency_id))
            .where(m.financial_reference_node.c.internal_code == f"PUBLIC_LIST_{row['isin']}_{row['mic']}",
                   m.listing.c.status == 'ACTIVE')).mappings().one_or_none()
        if not node or node['trading_symbol'] != row['symbol'] or node['currency_code'] != row['currency']:
            raise ValueError('Seeded approved universe listing is missing or differs; refusing guessed mapping')
        symbol = yahoo_symbol(row['symbol'], row['mic'])
        rows = c.execute(select(m.external_object_mapping).where(
            m.external_object_mapping.c.external_id_namespace_id == namespace_id,
            m.external_object_mapping.c.external_id_value == symbol)).mappings().all()
        if rows:
            if (len(rows) != 1 or rows[0]['target_object_id'] != node['listing_node_id']
                    or rows[0]['context_market_venue_id'] != node['market_venue_id']
                    or rows[0]['status'] not in {'PROPOSED', 'VERIFIED'}):
                raise ValueError('Existing Yahoo mapping differs; refusing overwrite')
        else:
            c.execute(m.external_object_mapping.insert().values(external_id_namespace_id=namespace_id,
                external_object_type='LISTING', external_id_value=symbol, target_object_type='LISTING',
                target_object_id=node['listing_node_id'], context_market_venue_id=node['market_venue_id'],
                mapping_method='RULE', status='PROPOSED', valid_from=date.today()))
        mappings.append(dict(symbol=symbol, listingId=str(node['listing_node_id']), mic=row['mic'], universe=row['universe']))
    return dict(datasetId=str(dataset_id), namespaceId=str(namespace_id), mappings=mappings)


def enable_personal_research(c, tenant_id, actor_id, reference: str) -> dict:
    """Explicit owner exception for local research; never fabricate provider consent."""
    from market_data.rights import load_rights
    result = onboard_personal(c, tenant_id, actor_id, reference)
    dataset_id = result['datasetId']
    c.execute(select(m.dataset.c.dataset_id).where(m.dataset.c.dataset_id == dataset_id).with_for_update())
    requirement = c.execute(select(m.dataset_right_requirement).where(
        m.dataset_right_requirement.c.dataset_id == dataset_id,
        m.dataset_right_requirement.c.activity == 'ACQUIRE',
        m.dataset_right_requirement.c.requirement_code == 'AUTOMATED_SOURCE_ACCESS').with_for_update()).mappings().one()
    if requirement['dataset_licence_assignment_id'] is not None:
        if not load_rights(c, dataset_id, 'ACQUIRE', date.today(), 'PERSONAL').allowed:
            raise ValueError('Existing reviewed access assignment is not effective; refusing reactivation')
        return result
    profile = c.execute(select(m.dataset_access_profile).where(m.dataset_access_profile.c.dataset_id == dataset_id)).mappings().one()
    licence_code = 'YAHOO_PERSONAL_RESEARCH_EXCEPTION'
    if c.scalar(select(m.data_licence.c.data_licence_id).where(m.data_licence.c.licence_code == licence_code)):
        raise ValueError('Existing research exception needs explicit review; refusing replacement')
    evidence = (f'Owner-authorized PERSONAL_RESEARCH_EXCEPTION by recorded tenant administrator {actor_id} '
                f'on {datetime.now(timezone.utc).isoformat()}: {reference.strip()}. '
                'Local personal research only; not provider permission, not contractual evidence, '
                'not commercial clearance; no redistribution or non-display grant.')
    licence_id = _insert(c, m.data_licence, 'data_licence_id',
        licensor_organisation_id=profile['licensee_organisation_id'],
        licensee_organisation_id=profile['licensee_organisation_id'], licence_code=licence_code,
        display_name='Owner personal research exception — not provider permission',
        licence_reference=reference.strip(), permitted_use_description=evidence, valid_from=date.today())
    assignment_id = _insert(c, m.dataset_licence_assignment, 'dataset_licence_assignment_id',
        dataset_id=dataset_id, data_licence_id=licence_id, licence_role='ACQUISITION', valid_from=date.today())
    c.execute(m.licence_activity_grant.insert().values(dataset_licence_assignment_id=assignment_id,
        activity='ACQUIRE', usage_scope='PERSONAL', evidence_basis='PERSONAL_RESEARCH_EXCEPTION',
        evidence_reference=evidence, valid_from=date.today()))
    c.execute(m.dataset_right_requirement.update().where(
        m.dataset_right_requirement.c.requirement_id == requirement['requirement_id']).values(
            dataset_licence_assignment_id=assignment_id))
    return result
