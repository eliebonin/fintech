"""Native approved dated crypto futures: booking, retries and retained terms."""
from uuid import UUID,uuid4
import pytest
from sqlalchemy import select
from apps.reference_api.db import get_engine
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from tests.test_fx_forward_booking_api import request as api_request
from tests.test_product_booking_api import approve,payload


@pytest.fixture(scope='module',params=[('CASH','5'),('PHYSICAL','1')])
def linear_future(request):
    settlement,size=request.param;code='LINEAR_'+uuid4().hex[:8].upper()
    spec=dict(underlyingKind='CRYPTOASSET',symbolRoot='BTC',yearDigits=2,deliveryMonths=[3,6,9,12],
        settlementMethod=settlement,priceBasis='UNDERLYING_UNIT',contractSize=size,
        contractSizeCurrencyId=str(ids['mvp_btc_currency']),monetaryMultiplier=size,
        quoteFactor='1',tickSize='5',allowNegativePrice=False)
    approve(api_request('POST','/v1/future-family-proposals',dict(canonicalName=code,familyCode=code,
        underlyingId=str(ids['mvp_btc_node']),contractCurrencyId=str(ids['usd_currency']),
        sourceReference='Synthetic linear future family',specification=spec)))
    family=api_request('GET','/v1/future-families?q='+code).json()['data'][0]
    convention={key:value for key,value in spec.items() if key not in ('underlyingKind','symbolRoot','yearDigits','deliveryMonths')}
    convention.update(kind='FUTURE',quantityUnit='CONTRACTS',effectiveFrom='2026-09-01',priceCurrencyId=str(ids['usd_currency']),
        sourceReference='Synthetic dated linear contract',lastTradingAtUtc='2027-03-17T16:00:00Z',finalSettlementDate='2027-03-19')
    if settlement=='PHYSICAL':convention.update(deliveryStartDate='2027-03-19',deliveryEndDate='2027-03-19')
    node=approve(api_request('POST','/v1/future-proposals',dict(canonicalName=code+' March 2027',familyId=family['familyId'],
        familyCode=code,underlyingId=family['underlyingId'],contractMonth='2027-03-01',convention=convention)))
    approve(api_request('POST','/v1/listing-proposals',dict(instrumentId=node,listing=dict(
        marketVenueId=str(ids['coinbase_venue']),tradingSymbol=code+'H27',tradingCurrencyId=str(ids['usd_currency']),
        quoteFactor='1',unitMultiplier='1',effectiveFrom='2026-09-01'))))
    with get_engine().connect() as c:
        listing=str(c.scalar(select(m.listing.c.listing_node_id).where(m.listing.c.instrument_node_id==UUID(node))))
    return dict(node=node,listing=listing,convention=convention,settlement=settlement,size=size)


def test_approved_cash_and_physical_crypto_futures_book_and_retry_without_cash_posting(linear_future):
    f=linear_future;data=payload(f['node'],f['listing'],executionPrice='100000')
    key=str(uuid4());response=api_request('POST','/v1/trades/futures',data,key)
    assert response.status_code==201,response.text
    trade=response.json()['data']['trade'];economics=trade['productEconomics']
    assert trade['quantityUnit']=='CONTRACTS' and trade['priceBasis']=='UNDERLYING_UNIT'
    assert trade['settlementDate'] is None and economics['direction'] is None
    assert economics['terms']['convention']['settlementMethod']==f['settlement']
    assert economics['amount']==str(200000*int(f['size']))
    replay=api_request('POST','/v1/trades/futures',data,key)
    assert replay.status_code==201 and replay.json()['data']['trade']['tradeId']==trade['tradeId']
    assert api_request('POST','/v1/trades/futures',data|dict(quantity='3'),key).status_code==409


def test_crypto_convention_amendment_must_preserve_approved_family_and_delivery_terms(linear_future):
    f=linear_future
    response=api_request('POST','/v1/instrument-booking-convention-proposals',dict(instrumentId=f['node'],
        convention=f['convention']|dict(sourceReference='Reviewed synthetic source wording')))
    assert response.status_code==201,response.text
    assert api_request('POST','/v1/instrument-booking-convention-proposals',dict(instrumentId=f['node'],
        convention=f['convention']|dict(contractSize='2',monetaryMultiplier='2'))).status_code==422
    assert api_request('GET',f"/v1/trades/product-instruments/{f['node']}?listingId={f['listing']}",tenant='second_tenant').status_code in (403,404)


@pytest.mark.parametrize('changes',[{'quantity':'1.5'},{'executionPrice':'-5'},{'executionPrice':'100001'},
    {'tradeDatetime':'2027-03-17T16:00:01Z'},{'settlementDate':'2026-10-05'}])
def test_extended_futures_keep_whole_contract_tick_and_trading_cutoff_guards(linear_future,changes):
    f=linear_future;data=payload(f['node'],f['listing'],executionPrice='100000')|changes
    response=api_request('POST','/v1/trades/futures',data)
    assert response.status_code==422,response.text
