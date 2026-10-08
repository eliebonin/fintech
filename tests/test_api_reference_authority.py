"""Instrument stewardship is independent of trading, and denied by default."""
import asyncio
from contextlib import contextmanager
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, update, delete, func

from apps.reference_api.main import create_app
from apps.reference_api.db import get_engine
from apps.reference_api import repository as r
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from security_master_schema.tenant_workspace import TenantActionForbidden

DECISIONS = [
    'reference-data', 'reference-mapping', 'equity', 'bond', 'etp',
    'fx-forward', 'crypto-asset', 'index', 'index-family', 'structured-product',
]


@pytest.fixture
def connection():
    with get_engine().connect() as c:
        transaction = c.begin()
        try:
            yield c
        finally:
            transaction.rollback()


class BoundEngine:
    def __init__(self, connection): self.connection = connection
    @contextmanager
    def begin(self): yield self.connection


def request(c, method, path, payload=None):
    async def run():
        async with AsyncClient(transport=ASGITransport(app=create_app(engine=BoundEngine(c)), raise_app_exceptions=False), base_url='http://test') as client:
            return await client.request(method, path, json=payload, headers={
                'X-Tenant-Id': str(ids['tenant']), 'X-User-Account-Id': str(ids['demo_user_account'])})
    return asyncio.run(run())


def revoke_module(c, code):
    module = c.scalar(select(m.platform_module.c.platform_module_id).where(m.platform_module.c.module_code == code))
    c.execute(delete(m.tenant_module_entitlement).where(
        m.tenant_module_entitlement.c.tenant_id == ids['tenant'],
        m.tenant_module_entitlement.c.platform_module_id == module))


@pytest.mark.parametrize('kind', DECISIONS)
@pytest.mark.parametrize('denial', ['READ_ONLY', 'NO_SECURITY_MASTER'])
def test_every_approval_alias_denies_unqualified_member(connection, kind, denial):
    c = connection
    if denial == 'READ_ONLY':
        c.execute(update(m.tenant_user_account).where(m.tenant_user_account.c.tenant_id == ids['tenant'],
            m.tenant_user_account.c.user_account_id == ids['demo_user_account']).values(membership_role='READ_ONLY'))
    else:
        revoke_module(c, 'SECURITY_MASTER')
    before = c.scalar(select(func.count()).select_from(m.reference_data_approval))
    response = request(c, 'POST', f'/v1/{kind}-proposals/{uuid4()}/decision', {'decision': 'APPROVED', 'reason': 'Authority test'})
    assert response.status_code == 403, response.text
    assert c.scalar(select(func.count()).select_from(m.reference_data_approval)) == before


@pytest.mark.parametrize('path', ['/v1/strategies', '/v1/instruments/search', '/v1/work-queue', '/v1/trades'])
def test_inactive_tenant_is_not_readable(connection, path):
    connection.execute(update(m.tenant).where(m.tenant.c.tenant_id == ids['tenant']).values(status='INACTIVE'))
    response = request(connection, 'GET', path)
    assert response.status_code == 403, response.text


def test_security_master_admin_can_propose_without_trading(connection):
    revoke_module(connection, 'TRADING')
    response = request(connection, 'POST', '/v1/bond-proposals', {
        'canonicalName': f'Stewardship {uuid4()}', 'effectiveFrom': '2026-09-01',
        'couponType': 'ZERO', 'baseCurrencyId': str(ids['gbp_currency']), 'maturityDate': '2031-09-08'})
    assert response.status_code == 201, response.text
    approved = request(connection, 'POST', f"/v1/reference-data-proposals/{response.json()['data']['proposalId']}/decision",
        {'decision': 'APPROVED', 'reason': 'Security master approval'})
    assert approved.status_code == 200, approved.text


@pytest.mark.parametrize('service', [r.decide_mapping_proposal, r.decide_equity_proposal,
    r.decide_bond_proposal, r.decide_etp_proposal, r.decide_fx_forward_proposal,
    r.decide_crypto_asset_proposal, r.decide_index_proposal, r.decide_index_family_proposal,
    r.decide_structured_product_proposal, r.decide_reference_data_proposal])
def test_direct_approval_service_requires_stewardship_authority(connection, service):
    connection.execute(update(m.tenant_user_account).where(m.tenant_user_account.c.tenant_id == ids['tenant'],
        m.tenant_user_account.c.user_account_id == ids['demo_user_account']).values(membership_role='READ_ONLY'))
    with pytest.raises(TenantActionForbidden):
        service(connection, ids['tenant'], ids['demo_user_account'], uuid4(), 'APPROVED', 'Direct authority test')
