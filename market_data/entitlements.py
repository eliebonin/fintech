"""Tenant coverage eligibility, independent of price ranking and activity rights.

Packages are explicit reviewed classifications, not inferred from provider names,
delivery channels or listing venues. Callers must ALSO enforce activity rights.
"""
from sqlalchemy import and_, exists, or_, select
from security_master_schema import models as m


def tenant_series_entitlement_clause(dataset_id, series_id, tenant_id, use_purpose,
                                    on_date, *, entitlement=None):
    """Eligible exact grant, or EXISTS eligible tenant grant for this series.

Missing series context can satisfy DATASET grants only. Correlation exclusions
prevent nested EXISTS queries from accidentally introducing observation tables.
"""
    ent = entitlement if entitlement is not None else m.tenant_dataset_entitlement.alias('coverage_entitlement')
    package = m.dataset_coverage_package.alias('eligible_package')
    classification = m.market_data_series_coverage.alias('eligible_classification')
    grant = m.tenant_dataset_coverage.alias('eligible_package_grant')
    dataset = m.dataset.alias('eligible_dataset')
    product = m.provider_product.alias('eligible_product')
    provider = m.data_provider.alias('eligible_provider')
    source = exists(select(1).select_from(dataset.join(product).join(provider)).where(
        dataset.c.dataset_id == dataset_id, dataset.c.status == 'ACTIVE',
        dataset.c.valid_from <= on_date,
        or_(dataset.c.valid_to.is_(None), dataset.c.valid_to >= on_date),
        product.c.status == 'ACTIVE', provider.c.status == 'ACTIVE',
        or_(provider.c.owner_tenant_id.is_(None), provider.c.owner_tenant_id == tenant_id)
    ).correlate_except(dataset, product, provider))
    scoped = exists(select(1).select_from(grant.join(package, and_(
        grant.c.coverage_package_id == package.c.coverage_package_id,
        grant.c.dataset_id == package.c.dataset_id)).join(classification, and_(
        classification.c.coverage_package_id == package.c.coverage_package_id,
        classification.c.dataset_id == package.c.dataset_id))).where(
        grant.c.tenant_dataset_entitlement_id == ent.c.tenant_dataset_entitlement_id,
        grant.c.dataset_id == dataset_id,
        classification.c.market_data_series_id == series_id,
        package.c.status == 'ACTIVE', package.c.valid_from <= on_date,
        or_(package.c.valid_to.is_(None), package.c.valid_to >= on_date)
    ).correlate_except(grant, package, classification)) if series_id is not None else False
    conditions = [ent.c.tenant_id == tenant_id, ent.c.dataset_id == dataset_id,
        ent.c.status == 'ACTIVE', ent.c.valid_from <= on_date,
        or_(ent.c.valid_to.is_(None), ent.c.valid_to >= on_date), source,
        or_(ent.c.coverage_mode == 'DATASET', and_(ent.c.coverage_mode == 'SCOPED', scoped))]
    if use_purpose is not None:
        conditions.append(ent.c.use_purpose == use_purpose)
    if entitlement is not None:
        return and_(*conditions)
    return exists(select(1).select_from(ent).where(*conditions).correlate_except(ent))
