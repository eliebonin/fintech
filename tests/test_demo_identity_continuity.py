"""Neutral fixture labels must not replace an existing installation's records."""
from sqlalchemy import func, select, update

from apps.reference_api.db import get_engine
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids, load_demo_data


def test_loader_preserves_existing_names_evidence_and_record_counts():
    engine = get_engine()
    with engine.connect() as connection:
        tenant = dict(connection.execute(select(m.tenant).where(m.tenant.c.tenant_id == ids['tenant'])).mappings().one())
        organisation = dict(connection.execute(select(m.organisation).where(m.organisation.c.organisation_id == ids['platform_organisation'])).mappings().one())
        definitions = connection.execute(select(m.instrument_definition_version)).mappings().all()
        counts = {table.name: connection.scalar(select(func.count()).select_from(table))
                  for table in (m.tenant, m.organisation, m.trade, m.trade_lifecycle_event)}
    try:
        with engine.begin() as connection:
            connection.execute(update(m.tenant).where(m.tenant.c.tenant_id == ids['tenant']).values(
                tenant_code='EXISTING_CUSTOMER', display_name='Existing customer workspace'))
            connection.execute(update(m.organisation).where(m.organisation.c.organisation_id == ids['platform_organisation']).values(
                display_name='Existing customer organisation'))
        load_demo_data(engine)
        load_demo_data(engine)
        with engine.connect() as connection:
            current = connection.execute(select(m.tenant).where(m.tenant.c.tenant_id == ids['tenant'])).mappings().one()
            assert (current['tenant_code'], current['display_name']) == ('EXISTING_CUSTOMER', 'Existing customer workspace')
            assert connection.scalar(select(m.organisation.c.display_name).where(
                m.organisation.c.organisation_id == ids['platform_organisation'])) == 'Existing customer organisation'
            assert [dict(row) for row in connection.execute(select(m.instrument_definition_version)).mappings()] == [dict(row) for row in definitions]
            for table in (m.tenant, m.organisation, m.trade, m.trade_lifecycle_event):
                assert connection.scalar(select(func.count()).select_from(table)) == counts[table.name]
    finally:
        with engine.begin() as connection:
            connection.execute(update(m.tenant).where(m.tenant.c.tenant_id == ids['tenant']).values(
                tenant_code=tenant['tenant_code'], display_name=tenant['display_name']))
            connection.execute(update(m.organisation).where(m.organisation.c.organisation_id == ids['platform_organisation']).values(
                display_name=organisation['display_name']))
