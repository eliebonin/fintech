"""Governed bond booking, using cloned synthetic terms only."""
from datetime import date
from uuid import UUID, uuid4
import pytest
from sqlalchemy import select
from apps.reference_api.db import get_engine
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS
from tests.test_fx_forward_booking_api import request
from tests.test_product_booking_api import approve, payload


@pytest.fixture(scope='module')
def bond():
    node = uuid4()
    with get_engine().begin() as connection:
        for table, key in [(m.financial_reference_node,'reference_node_id'), (m.instrument,'instrument_node_id'),
                          (m.instrument_definition_version,'instrument_node_id'), (m.instrument_dates,'instrument_node_id'),
                          (m.bond_terms,'instrument_node_id')]:
            values = dict(connection.execute(select(table).where(table.c[key] == DEMO_IDS['bond_instrument_node'])).mappings().one())
            values[key] = node
            for primary in table.primary_key.columns:
                if primary.name != key: values[primary.name] = uuid4()
            if table is m.financial_reference_node: values.update(canonical_name=f'Synthetic bond {node}', internal_code=f'BOND_{node.hex}')
            if table in (m.instrument,m.instrument_definition_version,m.bond_terms): values['effective_from'] = date(2026,9,1)
            if table is m.instrument_dates: values['maturity_date'] = date(2030,1,1)
            connection.execute(table.insert().values(**values))
        connection.execute(m.reference_node_scope.insert().values(reference_node_id=node,scope_type='TENANT_PRIVATE',owner_tenant_id=DEMO_IDS['tenant'],status='ACTIVE'))
    convention = dict(kind='BOND',effectiveFrom='2026-09-01',priceCurrencyId=str(DEMO_IDS['gbp_currency']),quoteFactor='100',
        sourceReference='Synthetic plain bullet fixed-rate terms',quantityUnit='NOMINAL',priceBasis='PCT_OF_PAR',
        principalBasis='UNADJUSTED_NOMINAL',quantityMinimum='1000',quantityIncrement='1000',accrual='MANUAL_CONFIRMATION',otcAllowed=True)
    approve(request('POST','/v1/instrument-booking-convention-proposals',dict(instrumentId=str(node),convention=convention)))
    return str(node)


def ticket(bond, **changes):
    return payload(bond,priceType='CLEAN',accruedInterestAmount='1250',settlementEvidence='Synthetic confirmation: total accrued amount and settlement eligibility verified.') | changes


@pytest.mark.parametrize('basis,price,accrual,total', [('CLEAN','98.5','1250','99750'),('DIRTY','99.75','1250','99750'),('CLEAN','98.5','-250','98250')])
def test_bond_amount_history_and_replay(bond,basis,price,accrual,total):
    data=ticket(bond,priceType=basis,executionPrice=price,accruedInterestAmount=accrual)
    key=str(uuid4())
    response=request('POST','/v1/trades/bonds',data,key)
    assert response.status_code==201,response.text
    trade=response.json()['data']['trade']
    assert trade['quantityUnit']=='NOMINAL' and trade['priceBasis']=='PCT_OF_PAR'
    economics=trade['productEconomics']
    assert economics['amount']==total and economics['direction']=='PAY'
    assert economics['bondDetails']['cleanAmount']=='98500'
    assert economics['bondDetails']['dirtyAmount']==total
    assert request('POST','/v1/trades/bonds',data,key).json()['data']['trade']['tradeId']==trade['tradeId']
    assert request('POST','/v1/trades/bonds',data|{'accruedInterestAmount':'0'},key).status_code==409
    history=request('GET',f"/v1/trades/{trade['tradeId']}")
    assert history.json()['data']['trade']['productEconomics']==economics


@pytest.mark.parametrize('changes',[{'priceType':None},{'accruedInterestAmount':None},{'settlementEvidence':'  '},
    {'settlementDate':None},{'settlementDate':'2030-01-01'},{'counterpartyOrganisationId':None},
    {'quantity':'100001'},{'accruedInterestAmount':'-100000'},{'positionEffect':'OPEN'}])
def test_invalid_bond(bond,changes):
    response=request('POST','/v1/trades/bonds',ticket(bond,**changes))
    assert response.status_code==422,response.text


def test_sell_and_unsupported_pnl(bond):
    result=request('POST','/v1/trades/bonds',ticket(bond,side='SELL',accruedInterestAmount='0'))
    assert result.status_code==201,result.text
    assert result.json()['data']['trade']['productEconomics']['direction']=='RECEIVE'
    with get_engine().connect() as connection:
        code=connection.scalar(select(m.strategy.c.strategy_code).where(m.strategy.c.strategy_id==DEMO_IDS['strategy']))
    assert request('GET',f'/v1/portfolios/{code}/pnl?asOfDate=2026-10-01').status_code==422


def test_hidden_bond(bond):
    assert request('GET',f'/v1/trades/product-instruments/{bond}',tenant='second_tenant').status_code in {403,404}


def test_accrual_replay_preserves_all_supported_digits(bond):
    data=ticket(bond,executionPrice='0',accruedInterestAmount='99999999999999999.123456789012')
    key=str(uuid4())
    first=request('POST','/v1/trades/bonds',data,key)
    assert first.status_code==201,first.text
    assert first.json()['data']['trade']['productEconomics']['amount']==data['accruedInterestAmount']
    assert request('POST','/v1/trades/bonds',data|{'accruedInterestAmount':'99999999999999999.123456789013'},key).status_code==409
    ordinary=ticket(bond)
    key=str(uuid4())
    first=request('POST','/v1/trades/bonds',ordinary,key)
    assert first.status_code==201,first.text
    assert request('POST','/v1/trades/bonds',ordinary|{'accruedInterestAmount':'1250.00'},key).json()['data']['trade']['tradeId']==first.json()['data']['trade']['tradeId']


def test_listed_bond_and_cash_boundary(bond):
    approve(request('POST','/v1/listing-proposals',dict(instrumentId=bond,listing=dict(marketVenueId=str(DEMO_IDS['xlon_venue']),
        tradingSymbol='BOND'+uuid4().hex[:6],tradingCurrencyId=str(DEMO_IDS['gbp_currency']),quoteFactor='100',unitMultiplier='1',effectiveFrom='2026-09-01'))))
    with get_engine().connect() as connection:
        listing=str(connection.scalar(select(m.listing.c.listing_node_id).where(m.listing.c.instrument_node_id==UUID(bond))))
    context=request('GET',f'/v1/trades/product-instruments/{bond}?listingId={listing}&asOfDate=2026-10-01').json()['data']
    data=ticket(bond,listingId=listing,executionRoute='LISTED',expectedTermsFingerprint=context['termsFingerprint'])
    result=request('POST','/v1/trades/bonds',data)
    assert result.status_code==201,result.text
    assert result.json()['data']['trade']['listingId']==listing
    cash={k:v for k,v in data.items() if k not in {'instrumentId','executionRoute','expectedTermsFingerprint','priceType','accruedInterestAmount','settlementEvidence','positionEffect'}}
    assert request('POST','/v1/trades',cash).status_code==422


def test_stale_and_unsupported_terms_and_zero_coupon(bond):
    original=ticket(bond)
    with get_engine().begin() as connection:
        saved=dict(connection.execute(select(m.bond_terms).where(m.bond_terms.c.instrument_node_id==UUID(bond))).mappings().one())
        connection.execute(m.bond_terms.update().where(m.bond_terms.c.instrument_node_id==UUID(bond)).values(coupon_rate='0.05'))
    try:
        assert request('POST','/v1/trades/bonds',original).status_code==409
        with get_engine().begin() as connection:
            connection.execute(m.bond_terms.update().where(m.bond_terms.c.instrument_node_id==UUID(bond)).values(coupon_type='FLOATING'))
        context=request('GET',f'/v1/trades/product-instruments/{bond}?asOfDate=2026-10-01').json()['data']
        assert not context['bookingEligible']
        with get_engine().begin() as connection:
            connection.execute(m.bond_terms.update().where(m.bond_terms.c.instrument_node_id==UUID(bond)).values(coupon_type='ZERO',coupon_rate=None))
        assert request('POST','/v1/trades/bonds',ticket(bond)).status_code==422
        assert request('POST','/v1/trades/bonds',ticket(bond,accruedInterestAmount='0')).status_code==201
    finally:
        with get_engine().begin() as connection:
            connection.execute(m.bond_terms.update().where(m.bond_terms.c.instrument_node_id==UUID(bond)).values(coupon_type=saved['coupon_type'],coupon_rate=saved['coupon_rate']))
