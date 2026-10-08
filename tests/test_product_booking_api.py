"""Real approval, execution and immutable history on an isolated database."""
from datetime import date
from uuid import uuid4, UUID
import pytest
from sqlalchemy import select, func
from apps.reference_api.db import get_engine
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS
from tests.test_fx_forward_booking_api import request


def approve(response):
    assert response.status_code == 201, response.text
    proposal_id = response.json()['data']['proposalId']
    queue = request('GET', '/v1/work-queue')
    assert any(i['referenceId'] == proposal_id and i['reviewPath'] for i in queue.json()['items'])
    approved = request('POST', f'/v1/reference-data-proposals/{proposal_id}/decision', {'decision': 'APPROVED', 'reason': 'Verified synthetic contract facts.'})
    assert approved.status_code == 200, approved.text
    return approved.json()['data']['referenceNodeId']


def structured_convention(**changes):
    return dict(kind='STRUCTURED_PRODUCT', effectiveFrom='2026-09-01', priceCurrencyId=str(DEMO_IDS['gbp_currency']),
        quoteFactor='100', sourceReference='Synthetic issuer terms', funding='FULLY_FUNDED', quantityUnit='NOMINAL',
        priceBasis='PCT_OF_PAR', quantityMinimum='1000', quantityIncrement='1000', accrual='NONE', otcAllowed=True) | changes


@pytest.fixture(scope='module')
def structured():
    # Separate synthetic canonical record; no changes to the operating fixture.
    with get_engine().begin() as connection:
        node = uuid4()
        for table, key in [(m.financial_reference_node, 'reference_node_id'), (m.instrument, 'instrument_node_id'),
                           (m.instrument_definition_version, 'instrument_node_id'), (m.instrument_dates, 'instrument_node_id'),
                           (m.structured_product_terms, 'instrument_node_id')]:
            values = dict(connection.execute(select(table).where(table.c[key] == DEMO_IDS['autocall_instrument_node'])).mappings().one())
            values[key] = node
            for primary in table.primary_key.columns:
                if primary.name != key: values[primary.name] = uuid4()
            if table is m.financial_reference_node: values.update(canonical_name=f'Synthetic funded note {node}', internal_code=f'NOTE_{node.hex}')
            if table in (m.instrument, m.instrument_definition_version, m.structured_product_terms): values['effective_from'] = date(2026,9,1)
            if table is m.structured_product_terms: values['source_payload_id'] = None
            connection.execute(table.insert().values(**values))
        connection.execute(m.reference_node_scope.insert().values(reference_node_id=node, scope_type='TENANT_PRIVATE', owner_tenant_id=DEMO_IDS['tenant'], status='ACTIVE'))
    approve(request('POST', '/v1/instrument-booking-convention-proposals', dict(instrumentId=str(node), convention=structured_convention())))
    return str(node)


@pytest.fixture(scope='module')
def future():
    node = approve(request('POST', '/v1/future-proposals', dict(canonicalName=f'Synthetic index future {uuid4()}',
        familyCode='TEST_' + uuid4().hex[:8].upper(), underlyingId=str(DEMO_IDS['mvp_sp500_price_index_node']),
        contractMonth='2027-03-01', convention=dict(kind='FUTURE', effectiveFrom='2026-09-01',
        priceCurrencyId=str(DEMO_IDS['usd_currency']), quoteFactor='1', sourceReference='Synthetic exchange specification',
        quantityUnit='CONTRACTS', priceBasis='INDEX_POINTS', monetaryMultiplier='5', tickSize='.25',
        allowNegativePrice=False, lastTradingAtUtc='2027-03-19T13:30:00Z', finalSettlementDate='2027-03-19'))))
    listing = approve(request('POST', '/v1/listing-proposals', dict(instrumentId=node, listing=dict(
        marketVenueId=str(DEMO_IDS['xlon_venue']), tradingSymbol='FUT' + uuid4().hex[:6],
        tradingCurrencyId=str(DEMO_IDS['usd_currency']), quoteFactor='1', unitMultiplier='5', effectiveFrom='2026-09-01'))))
    with get_engine().connect() as connection:
        listing_id = str(connection.scalar(select(m.listing.c.listing_node_id).where(m.listing.c.instrument_node_id == UUID(node))))
    return node, listing_id


def payload(node, listing=None, **changes):
    path = f'/v1/trades/product-instruments/{node}?asOfDate=2026-10-01' + (f'&listingId={listing}' if listing else '')
    context = request('GET', path)
    assert context.status_code == 200, context.text
    assert context.json()['data']['bookingEligible'], context.text
    return dict(instrumentId=node, listingId=listing, strategyId=str(DEMO_IDS['strategy']), side='BUY',
        quantity='100000' if not listing else '2', executionPrice='98.5' if not listing else '6000',
        executionRoute='LISTED' if listing else 'OTC', tradeDatetime='2026-10-01T10:00:00Z',
        settlementDate='2026-10-05' if not listing else None, positionEffect='OPEN' if listing else None,
        counterpartyOrganisationId=str(DEMO_IDS['bank_a_organisation']), expectedTermsFingerprint=context.json()['data']['termsFingerprint']) | changes


def test_structured_book_and_replay(structured):
    data, key = payload(structured), str(uuid4())
    first = request('POST', '/v1/trades/structured-products', data, key)
    assert first.status_code == 201, first.text
    trade = first.json()['data']['trade']
    assert trade['quantityUnit'] == 'NOMINAL'
    assert trade['productEconomics']['amount'] == '98500'
    assert trade['productEconomics']['direction'] == 'PAY'
    assert trade['listingId'] is None and trade['executionVenueId'] is None
    replay = request('POST', '/v1/trades/structured-products', data | {'executionPrice':'98.500'}, key)
    assert replay.status_code == 201, replay.text
    assert replay.json()['data']['trade']['tradeId'] == trade['tradeId']
    assert request('POST', '/v1/trades/structured-products', data | {'quantity':'101000'}, key).status_code == 409


def test_futures_no_purchase_payment(future):
    node, listing = future
    response = request('POST', '/v1/trades/futures', payload(node, listing, side='SELL', positionEffect='CLOSE'))
    assert response.status_code == 201, response.text
    trade = response.json()['data']['trade']
    assert trade['quantityUnit'] == 'CONTRACTS' and trade['settlementDate'] is None
    assert trade['productEconomics']['amount'] == '60000'
    assert trade['productEconomics']['amountKind'] == 'REFERENCE_CONTRACT_VALUE'
    assert trade['productEconomics']['direction'] is None


@pytest.mark.parametrize('changes', [{'quantity':'1.5'}, {'executionPrice':'6000.1'}, {'executionPrice':'-1'},
    {'settlementDate':'2026-10-05'}, {'positionEffect':None}, {'tradeDatetime':'2027-03-19T13:30:01Z'}])
def test_invalid_futures(future, changes):
    node, listing = future
    assert request('POST','/v1/trades/futures',payload(node,listing,**changes)).status_code == 422


@pytest.mark.parametrize('changes', [{'quantity':'1'}, {'counterpartyOrganisationId':None}, {'settlementDate':None}, {'positionEffect':'OPEN'}, {'executionPrice':'-1'}])
def test_invalid_structured(structured, changes):
    assert request('POST','/v1/trades/structured-products',payload(structured,**changes)).status_code == 422


def test_hidden_context(structured):
    assert request('GET',f'/v1/trades/product-instruments/{structured}',tenant='second_tenant').status_code in {403,404}


def test_future_cannot_reenter_retired_pnl(future):
    node, listing = future
    assert request('POST','/v1/trades/futures',payload(node,listing)).status_code == 201
    with get_engine().connect() as connection:
        code = connection.scalar(select(m.strategy.c.strategy_code).where(m.strategy.c.strategy_id == DEMO_IDS['strategy']))
    response = request('GET',f'/v1/portfolios/{code}/pnl?asOfDate=2026-10-01')
    assert response.status_code == 410, response.text


def test_snapshot_survives_new_convention(structured):
    old = payload(structured)
    booked = request('POST','/v1/trades/structured-products',old)
    assert booked.status_code == 201, booked.text
    approve(request('POST','/v1/instrument-booking-convention-proposals',dict(instrumentId=structured,
        convention=structured_convention(sourceReference='Corrected synthetic denomination',quantityUnit='UNITS',denomination='1000',quantityMinimum='1',quantityIncrement='1'))))
    stale = request('POST','/v1/trades/structured-products',old)
    assert stale.status_code == 409, stale.text
    detail = request('GET',f"/v1/trades/{booked.json()['data']['trade']['tradeId']}")
    assert detail.json()['data']['trade']['productEconomics']['terms']['convention']['quantityUnit'] == 'NOMINAL'


def test_futures_midnight_offset_without_cash_settlement(future):
    node, listing = future
    response=request('POST','/v1/trades/futures',payload(node,listing,tradeDatetime='2026-10-02T00:30:00+02:00'))
    assert response.status_code == 201, response.text
    assert response.json()['data']['trade']['settlementDate'] is None


def test_futures_zero_quote(future):
    node, listing = future
    response=request('POST','/v1/trades/futures',payload(node,listing,executionPrice='0'))
    assert response.status_code == 201, response.text
    assert response.json()['data']['trade']['productEconomics']['amount']=='0'


def test_generic_cash_cannot_book_structured_or_future(structured,future):
    for node,listing in [(structured,None),future]:
        data=payload(node,listing)
        for key in ('instrumentId','executionRoute','positionEffect','expectedTermsFingerprint'):data.pop(key,None)
        data['settlementDate']='2026-10-05'
        response=request('POST','/v1/trades',data)
        assert response.status_code in {404,422},response.text


def test_future_configuration_cannot_change_expiry(future):
    node,listing=future
    convention=request('GET',f'/v1/trades/product-instruments/{node}?listingId={listing}').json()['data']['convention']
    response=request('POST','/v1/instrument-booking-convention-proposals',dict(instrumentId=node,convention=convention|{'finalSettlementDate':'2027-03-20'}))
    assert response.status_code==422,response.text


def test_replay_is_transactional_under_concurrency(future):
    from concurrent.futures import ThreadPoolExecutor
    node,listing=future
    data,key=payload(node,listing),str(uuid4())
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:request('POST','/v1/trades/futures',data,key),range(2)))
    assert all(r.status_code==201 for r in results),[r.text for r in results]
    assert len({r.json()['data']['trade']['tradeId'] for r in results})==1


def test_approved_conventions_are_append_only(future):
    from sqlalchemy.exc import DBAPIError
    node,_=future
    with get_engine().connect() as connection:
        for statement in [m.instrument_booking_convention.update().where(m.instrument_booking_convention.c.instrument_node_id==UUID(node)).values(version_no=99),m.instrument_booking_convention.delete().where(m.instrument_booking_convention.c.instrument_node_id==UUID(node))]:
            with pytest.raises(DBAPIError),connection.begin_nested():connection.execute(statement)


def test_listed_structured_security_and_otc_isin_are_distinct(structured):
    # Current convention is units/denomination after the snapshot test.
    approve(request('POST','/v1/listing-proposals',dict(instrumentId=structured,listing=dict(marketVenueId=str(DEMO_IDS['xlon_venue']),tradingSymbol='NOTE'+uuid4().hex[:6],tradingCurrencyId=str(DEMO_IDS['gbp_currency']),quoteFactor='100',unitMultiplier='1',effectiveFrom='2026-09-01'))))
    with get_engine().begin() as connection:
        listing=str(connection.scalar(select(m.listing.c.listing_node_id).where(m.listing.c.instrument_node_id==UUID(structured))))
        isin='SYNTHETIC_'+uuid4().hex
        scheme=connection.scalar(select(m.identifier_scheme.c.identifier_scheme_id).where(m.identifier_scheme.c.scheme_code=='ISIN'))
        connection.execute(m.financial_reference_identifier.insert().values(reference_node_id=UUID(structured),identifier_scheme_id=scheme,identifier_value=isin))
    for selected_listing in (listing,None):
        data=payload(structured,selected_listing,quantity='100',executionPrice='98.5',settlementDate='2026-10-05',positionEffect=None)
        response=request('POST','/v1/trades/structured-products',data)
        assert response.status_code==201,response.text
        result=response.json()['data']['trade']
        assert result['productEconomics']['amount']=='98500'
        assert result['listingId']==selected_listing
        assert result['productEconomics']['terms']['executionRoute']==('LISTED' if selected_listing else 'OTC')
    search=request('GET',f'/v1/trades/product-instruments?kind=STRUCTURED_PRODUCT&route=OTC&q={isin}')
    assert any(r['instrumentId']==structured for r in search.json()['data'])


def test_invalid_property_rolls_back_the_entire_booking(future):
    node,listing=future
    with get_engine().connect() as connection:before=connection.scalar(select(func.count()).select_from(m.trade))
    response=request('POST','/v1/trades/futures',payload(node,listing,properties=[{'definitionId':str(uuid4()),'value':'0'}]))
    assert response.status_code==422,response.text
    with get_engine().connect() as connection:assert connection.scalar(select(func.count()).select_from(m.trade))==before


def test_negative_quote_requires_an_approved_convention(future):
    node,listing=future
    convention=request('GET',f'/v1/trades/product-instruments/{node}?listingId={listing}').json()['data']['convention']
    approve(request('POST','/v1/instrument-booking-convention-proposals',dict(instrumentId=node,convention=convention|{'allowNegativePrice':True,'sourceReference':'Synthetic approved signed-price rule'})))
    response=request('POST','/v1/trades/futures',payload(node,listing,executionPrice='-0.25'))
    assert response.status_code==201,response.text
    assert response.json()['data']['trade']['productEconomics']['amount']=='-2.5'


def test_private_product_is_not_disclosed_to_another_tenant(structured):
    from apps.reference_api.product_booking import load_context
    from apps.reference_api.repository import RepositoryNotFound
    with get_engine().connect() as connection,pytest.raises(RepositoryNotFound):
        load_context(connection,DEMO_IDS['second_tenant'],UUID(structured))


def test_missing_module_cannot_create_product():
    response=request('POST','/v1/future-proposals',dict(canonicalName='Unauthorised future',familyCode='FORBIDDEN',underlyingId=str(DEMO_IDS['mvp_sp500_price_index_node']),contractMonth='2027-03-01',convention=dict(kind='FUTURE',effectiveFrom='2026-09-01',priceCurrencyId=str(DEMO_IDS['usd_currency']),quoteFactor='1',sourceReference='Synthetic',quantityUnit='CONTRACTS',priceBasis='INDEX_POINTS',monetaryMultiplier='5',tickSize='0.25',allowNegativePrice=False,lastTradingAtUtc='2027-03-19T13:30:00Z',finalSettlementDate='2027-03-19')),tenant='second_tenant')
    assert response.status_code==403,response.text
