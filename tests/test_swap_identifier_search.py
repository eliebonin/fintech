"""Tenant confirmation identifiers are searchable without a second identifier store."""
from uuid import UUID, uuid4
from datetime import date
from sqlalchemy import select
from apps.reference_api.db import get_engine
from apps.reference_api.product_booking import search
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS
from tests.test_fx_forward_booking_api import request
from tests.test_swap_creation_api import create_reference, proposal, submit, decide


def approved_swap(identifier):
    payload = proposal(create_reference())
    payload['tenantIdentifier'] = identifier
    response = decide(submit(payload))
    assert response.status_code == 200, response.text
    return response.json()['data']['referenceNodeId']


def lookup(query):
    from urllib.parse import urlencode
    response = request('GET', '/v1/trades/product-instruments?' + urlencode(
        dict(kind='SWAP', route='OTC', q=query, asOfDate='2026-10-01')))
    assert response.status_code == 200, response.text
    return response.json()


def test_booking_and_catalogue_find_approved_tenant_identifier_case_insensitively():
    from urllib.parse import quote
    identifier = 'CONFIRM_' + uuid4().hex
    node = approved_swap(identifier)
    result = lookup(identifier.lower())
    assert [item['instrumentId'] for item in result['data']] == [node]
    assert result['meta']['total'] == 1
    assert result['data'][0]['bookingEligible']
    catalogue = request('GET', '/v1/instruments/search?q=' + quote(identifier.lower()))
    assert catalogue.status_code == 200, catalogue.text
    assert [item['instrumentId'] for item in catalogue.json()['data']] == [node]


def test_identifier_wildcards_are_literal_and_partial_search_is_supported():
    prefix = uuid4().hex
    node = approved_swap(prefix + '_A%Z')
    approved_swap(prefix + 'XAhelloZ')
    assert [item['instrumentId'] for item in lookup(prefix + '_A%')['data']] == [node]


def test_identifier_match_preserves_tenant_scope_and_does_not_count_foreign_contracts():
    identifier = 'PRIVATE_' + uuid4().hex
    approved_swap(identifier)
    with get_engine().connect() as connection:
        rows, total = search(connection, DEMO_IDS['second_tenant'], 'SWAP', 'OTC',
            identifier, 25, 0, date(2026, 10, 1))
    assert rows == [] and total == 0


def test_identifier_on_noncurrent_definition_is_not_a_search_alias():
    identifier = 'OLD_' + uuid4().hex
    node = UUID(approved_swap('CURRENT_' + uuid4().hex))
    with get_engine().begin() as connection:
        definition = dict(connection.execute(select(m.instrument_definition_version).where(
            m.instrument_definition_version.c.instrument_node_id == node)).mappings().one())
        payload = dict(connection.scalar(select(m.swap_definition_version.c.economics_payload).where(
            m.swap_definition_version.c.instrument_definition_version_id == definition['instrument_definition_version_id'])))
        version = uuid4()
        definition.update(instrument_definition_version_id=version, sequence_no=2, is_current=False,
            effective_from=date(2026, 1, 1), effective_to=date(2026, 8, 31))
        connection.execute(m.instrument_definition_version.insert().values(**definition))
        connection.execute(m.swap_definition_version.insert().values(instrument_definition_version_id=version,
            schema_version=1, economics_payload=payload | {'tenantIdentifier': identifier}))
    assert lookup(identifier)['data'] == []
    assert lookup(identifier)['meta']['total'] == 0
