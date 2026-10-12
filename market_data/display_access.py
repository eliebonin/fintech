"""Current display authority for frozen inputs; never grants calculation rights."""
from datetime import date
from sqlalchemy import select, or_
from security_master_schema import models as m
from .rights import denied_display_datasets


class EvidenceDisplayDenied(PermissionError):
    """Retained inputs exist but must not be disclosed to this caller now."""


def assert_dataset_display(c, tenant, datasets, *, series_contexts=None):
    datasets=set(datasets)
    if not datasets:
        return
    today=date.today()
    profiles=set(c.execute(select(m.dataset_access_profile.c.dataset_id).where(
        m.dataset_access_profile.c.dataset_id.in_(datasets))).scalars())
    ent=m.tenant_dataset_entitlement
    allowed=set(c.execute(select(ent.c.dataset_id).join(m.dataset,m.dataset.c.dataset_id==ent.c.dataset_id).where(
        ent.c.tenant_id==tenant, ent.c.dataset_id.in_(datasets), ent.c.status=='ACTIVE',
        ent.c.valid_from<=today, or_(ent.c.valid_to.is_(None),ent.c.valid_to>=today),
        m.dataset.c.status=='ACTIVE', m.dataset.c.valid_from<=today,
        or_(m.dataset.c.valid_to.is_(None),m.dataset.c.valid_to>=today),
        or_(ent.c.dataset_id.not_in(profiles),ent.c.use_purpose=='INTERNAL_REPORTING'))).scalars())
    denied=set(denied_display_datasets(c,tenant,today)) & datasets
    if datasets-allowed or denied:
        raise EvidenceDisplayDenied('Current dataset display rights and tenant reporting entitlement are required to inspect these inputs.')
    from .entitlements import tenant_series_entitlement_clause
    contexts = set(series_contexts or ())
    # An omitted context may satisfy a dataset-wide grant, never a scoped grant.
    contexts.update((dataset, None) for dataset in datasets - {d for d, _ in contexts})
    for dataset, series in contexts:
        if dataset not in datasets:
            raise EvidenceDisplayDenied('Unexpected source dataset context.')
        purpose = 'INTERNAL_REPORTING' if dataset in profiles else None
        if not c.scalar(select(1).where(tenant_series_entitlement_clause(
                dataset, series, tenant, purpose, today))):
            raise EvidenceDisplayDenied('Current tenant coverage does not permit this source series.')
