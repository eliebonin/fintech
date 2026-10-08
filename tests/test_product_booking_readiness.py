"""Advisory categories must not bypass visibility or replace writer refusal."""
from datetime import date
import pytest
from sqlalchemy import select, update
from apps.reference_api.product_booking import load_context
from apps.reference_api.booking_errors import RepositoryNotFound
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from tests.test_cash_booking_integrity import connection


def test_incomplete_family_metadata_does_not_turn_refusal_into_server_error(connection):
    connection.execute(update(m.future_family).where(m.future_family.c.future_family_id == ids['future_family']).values(specification_payload='{}'))
    result = load_context(connection, ids['tenant'], ids['future_instrument_node'], ids['future_listing_node'], date(2026, 10, 5))
    assert result.booking_eligible is False
    assert result.readiness_status == 'NOT_READY'
    assert 'Futures family configuration is invalid' in result.ineligibility_message


def test_unavailable_future_with_foreign_family_remains_opaque(connection):
    key = m.reference_node_scope.c.reference_node_id == ids['future_family_node']
    values = dict(scope_type='TENANT_PRIVATE', owner_tenant_id=ids['second_tenant'], status='ACTIVE')
    if connection.execute(select(m.reference_node_scope).where(key)).first():
        connection.execute(update(m.reference_node_scope).where(key).values(**values))
    else:
        connection.execute(m.reference_node_scope.insert().values(reference_node_id=ids['future_family_node'], **values))
    with pytest.raises(RepositoryNotFound):
        load_context(connection, ids['tenant'], ids['future_instrument_node'], ids['future_listing_node'], date(2026, 10, 5))
