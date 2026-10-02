from uuid import uuid4, UUID
from sqlalchemy import select, func
from apps.reference_api.db import get_engine
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS
from tests.test_fx_forward_booking_api import request
from tests.test_product_booking_api import approve


def test_standalone_family_approval_reuse_and_isolation():
    code = 'FAMILY_' + uuid4().hex[:8].upper()
    definition = dict(canonicalName='Standalone index family ' + code, familyCode=code,
        underlyingId=str(DEMO_IDS['mvp_sp500_price_index_node']), contractCurrencyId=str(DEMO_IDS['usd_currency']),
        sourceReference='Synthetic exchange specification')
    pending = request('POST', '/v1/future-family-proposals', definition)
    assert pending.status_code == 201, pending.text
    before = request('GET', '/v1/future-families?q=' + code)
    assert before.status_code == 200, before.text
    assert not before.json()['data']
    node = approve(pending)
    result = request('GET', '/v1/future-families?q=' + code + '&limit=1&offset=0')
    assert result.status_code == 200, result.text
    family = result.json()['data'][0]
    assert family['familyNodeId'] == node and family['currency'] == 'USD'
    with get_engine().connect() as connection:
        assert connection.scalar(select(m.financial_reference_node.c.is_tradable).where(m.financial_reference_node.c.reference_node_id == UUID(node))) is False
        assert connection.scalar(select(func.count()).select_from(m.future_terms).where(m.future_terms.c.future_family_id == UUID(family['familyId']))) == 0
    other = request('GET', '/v1/future-families?q=' + code, tenant='second_tenant')
    assert other.status_code == 403 or not other.json()['data']
    duplicate = request('POST', '/v1/future-family-proposals', definition)
    duplicate_id = duplicate.json()['data']['proposalId']
    assert request('POST', f'/v1/reference-data-proposals/{duplicate_id}/decision', {'decision':'APPROVED','reason':'Duplicate test'}).status_code == 409
    for month in ('03', '06'):
        payload = dict(canonicalName='Expiry ' + month + code, familyId=family['familyId'],familyCode=code,
            underlyingId=family['underlyingId'],contractMonth=f'2027-{month}-01',convention=dict(kind='FUTURE',
            effectiveFrom='2026-09-01',priceCurrencyId=family['contractCurrencyId'],quoteFactor='1',sourceReference='Synthetic expiry rules',
            quantityUnit='CONTRACTS',priceBasis='INDEX_POINTS',monetaryMultiplier='5',tickSize='.25',allowNegativePrice=False,
            lastTradingAtUtc=f'2027-{month}-19T13:30:00Z',finalSettlementDate=f'2027-{month}-19'))
        assert request('POST','/v1/future-proposals',payload | {'familyCode':'FORGED'}).status_code == 422
        approve(request('POST','/v1/future-proposals',payload))
    with get_engine().connect() as connection:
        assert connection.scalar(select(func.count()).select_from(m.future_terms).where(m.future_terms.c.future_family_id == UUID(family['familyId']))) == 2
