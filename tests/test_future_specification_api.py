from uuid import uuid4, UUID
from sqlalchemy import select
from apps.reference_api.db import get_engine
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS
from tests.test_fx_forward_booking_api import request
from tests.test_product_booking_api import approve
from tests.test_future_specification_rules import specification


def test_physical_crypto_creation_keeps_existing_booking_closed():
    code='BTC_'+uuid4().hex[:8].upper()
    spec=specification(contractSizeCurrencyId=str(DEMO_IDS['mvp_btc_currency']),deliveryMonths=[3,6,9,12])
    family_node=approve(request('POST','/v1/future-family-proposals',dict(canonicalName=code,familyCode=code,
        underlyingId=str(DEMO_IDS['mvp_btc_node']),contractCurrencyId=str(DEMO_IDS['usd_currency']),
        sourceReference='Synthetic physical BTC family',specification=spec)))
    response=request('GET','/v1/future-families?q='+code)
    assert response.status_code==200,response.text
    family=response.json()['data'][0]
    assert family['familyNodeId']==family_node and family['specification']['deliveryMonths']==[3,6,9,12]
    convention={k:v for k,v in spec.items() if k not in ('underlyingKind','symbolRoot','yearDigits','deliveryMonths')}
    convention.update(kind='FUTURE',quantityUnit='CONTRACTS',effectiveFrom='2026-09-01',priceCurrencyId=str(DEMO_IDS['usd_currency']),
        sourceReference='Synthetic expiry',lastTradingAtUtc='2027-03-17T16:00:00Z',finalSettlementDate='2027-03-19',
        deliveryStartDate='2027-03-19',deliveryEndDate='2027-03-19')
    payload=dict(canonicalName=code+' March 2027',familyId=family['familyId'],familyCode=code,
        underlyingId=family['underlyingId'],contractMonth='2027-03-01',convention=convention)
    assert request('POST','/v1/future-proposals',payload|{'contractMonth':'2027-02-01'}).status_code==422
    assert request('POST','/v1/future-proposals',payload|{'convention':convention|{'monetaryMultiplier':'1','contractSize':'1'}}).status_code==422
    node=approve(request('POST','/v1/future-proposals',payload))
    with get_engine().connect() as connection:
        terms=connection.execute(select(m.future_terms).where(m.future_terms.c.instrument_node_id==UUID(node))).mappings().one()
        assert terms.settlement_method=='PHYSICAL' and terms.delivery_start_date.isoformat()=='2027-03-19'
    context=request('GET',f'/v1/trades/product-instruments/{node}?asOfDate=2026-10-02')
    assert context.status_code==200 and context.json()['data']['bookingEligible'] is False
    assert context.json()['data']['contractMonth']=='2027-03-01'
    assert request('POST','/v1/instrument-booking-convention-proposals',{'instrumentId':node,'convention':convention}).status_code==422


def test_crypto_currency_endpoint_is_available():
    result=request('GET','/v1/currencies?groups=REGULAR,CRYPTO')
    assert result.status_code==200,result.text
    assert any(item['currencyCode']=='BTC' for group in result.json()['data'] for item in group['items'])


def test_private_crypto_currency_does_not_leak_to_another_tenant():
    token=uuid4().hex[:8].upper()
    with get_engine().begin() as connection:
        node=uuid4()
        node_type=connection.scalar(select(m.reference_node_type.c.reference_node_type_id).where(m.reference_node_type.c.type_code=='INSTRUMENT'))
        connection.execute(m.financial_reference_node.insert().values(reference_node_id=node,reference_node_type_id=node_type,canonical_name='Private test crypto '+token,is_tradable=True,status='ACTIVE'))
        connection.execute(m.reference_node_scope.insert().values(reference_node_id=node,scope_type='TENANT_PRIVATE',owner_tenant_id=DEMO_IDS['tenant'],status='ACTIVE'))
        connection.execute(m.currency.insert().values(reference_node_id=node,currency_code=token,display_name='Private test crypto',currency_kind='CRYPTOASSET',status='ACTIVE'))
    own=request('GET','/v1/currencies?groups=CRYPTO')
    other=request('GET','/v1/currencies?groups=CRYPTO',tenant='second_tenant')
    assert own.status_code==other.status_code==200
    assert any(item['currencyCode']==token for group in own.json()['data'] for item in group['items'])
    assert not any(item['currencyCode']==token for group in other.json()['data'] for item in group['items'])
