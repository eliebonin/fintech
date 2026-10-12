"""As-known source preference selection. Preferences never grant data rights."""
from sqlalchemy import select
from security_master_schema import models as m


def latest_version(c, tenant, instrument_type, as_of=None, purpose='VALUATION'):
    table = m.source_priority_version
    query = select(table).where(table.c.tenant_id == tenant if tenant else table.c.tenant_id.is_(None),
        table.c.instrument_type_id == instrument_type, table.c.use_purpose == purpose)
    if as_of is not None:
        query = query.where(table.c.created_at_utc <= as_of)
    return c.execute(query.order_by(table.c.version_no.desc()).limit(1)).mappings().one_or_none()


def ordered_datasets(c, version_id):
    table = m.source_priority_entry
    return list(c.scalars(select(table.c.dataset_id).where(table.c.source_priority_version_id == version_id)
        .order_by(table.c.priority)))


def effective_priority(c, tenant, instrument_type, as_of, purpose='VALUATION'):
    """None means legacy arbitration; an empty order explicitly excludes all."""
    tenant_version = latest_version(c, tenant, instrument_type, as_of, purpose)
    platform_version = latest_version(c, None, instrument_type, as_of, purpose)
    selected = tenant_version if tenant_version and tenant_version['mode'] == 'CUSTOM' else platform_version
    return {
        'tenantVersionId': str(tenant_version['source_priority_version_id']) if tenant_version else None,
        'platformVersionId': str(platform_version['source_priority_version_id']) if platform_version else None,
        'scope': 'TENANT' if selected is tenant_version and selected else 'PLATFORM' if selected else 'UNCONFIGURED',
        'datasetIds': [str(d) for d in ordered_datasets(c, selected['source_priority_version_id'])] if selected else None,
    }


def rank(priority, dataset_id):
    order = priority['datasetIds']
    return 0 if order is None else order.index(str(dataset_id)) if str(dataset_id) in order else None


def choose_row(rows, priority, *, observed_time=False):
    """Rank only already eligible prices; freshness precedes source preference."""
    eligible = [r for r in rows if rank(priority, r['dataset_id']) is not None]
    return max(eligible, key=lambda r: (r['market_date'], -rank(priority, r['dataset_id']),
        r.get('value_basis') == 'RAW' if r.get('price_basis_evidence') else False,
        r['observed_at_utc'] if observed_time else r['received_at_utc'], r['received_at_utc'],
        str(r['market_data_observation_id']))) if eligible else None
