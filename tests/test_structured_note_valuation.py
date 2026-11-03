"""Whole-note marks and exact quotation factors; no payoff repricing."""
from dataclasses import replace
from decimal import Decimal as D
from uuid import UUID
import pytest
from tests.test_position_reconstruction import booked,request,OPEN,CLOSE,SUBJECT,CURRENCY
from positions.reconstruction import reconstruct
from valuation.position_calculation import attribute_projection,MarkKey


def convention(**changes):
    return dict(kind='STRUCTURED_PRODUCT',funding='FULLY_FUNDED',quantityUnit='NOMINAL',priceBasis='PCT_OF_PAR',
        quoteFactor='100',accrual='DIRTY')|changes


@pytest.mark.parametrize('unit,denomination,multiplier', [('NOMINAL',None,'1'),('UNITS','1000','1000')])
def test_note_percentage_quotation_applies_denomination_once(unit,denomination,multiplier):
    from security_master_schema.structured_note_valuation import quotation_factors
    assert quotation_factors(convention(quantityUnit=unit,denomination=denomination),unit)==(D(multiplier),D(100))


@pytest.mark.parametrize('basis',['CLEAN','DIRTY','NONE'])
def test_note_quote_basis_is_explicit(basis):
    from apps.reference_api.product_booking_contracts import StructuredConvention
    cv=StructuredConvention.model_validate(convention(accrual=basis)|dict(effectiveFrom='2026-01-01',
        priceCurrencyId=str(CURRENCY),sourceReference='Synthetic terms',quantityMinimum='1',quantityIncrement='1',otcAllowed=True))
    assert cv.accrual==basis


def note(n,q,when,price='97.5',**changes):
    return booked(n,q,when,price,product_basis='STRUCTURED_PRODUCT',quantity_unit='NOMINAL',quote_factor=D(100),
        product_evidence=dict(instrumentId=str(SUBJECT),noteConvention=convention()),**changes)


@pytest.mark.parametrize('opening,execution,price,want',[
    ('100000',None,None,'1000'),('0','100000','98','500'),('100000','-100000','98','500'),
    ('100000','-50000','98','750'),('-100000',None,None,'-1000')])
def test_note_security_bridge_and_manual_closures(opening,execution,price,want):
    facts=[] if opening=='0' else [note(1,opening,OPEN)]
    if execution:facts.append(note(2,execution,CLOSE,price))
    result=attribute_projection(reconstruct(facts,request()),{MarkKey(SUBJECT,OPEN):D('97.5'),MarkKey(SUBJECT,CLOSE):D('98.5')},CURRENCY)
    assert result.market_pnl==D(want)


def test_confirmed_zero_note_price_is_not_missing():
    p=reconstruct([note(1,'100000',OPEN)],request())
    assert attribute_projection(p,{MarkKey(SUBJECT,OPEN):D('97.5'),MarkKey(SUBJECT,CLOSE):D(0)},CURRENCY).market_pnl==-97500


def test_whole_note_price_uses_common_fx_bridge():
    p=reconstruct([note(1,'100000',OPEN)],request())
    result=attribute_projection(p,{MarkKey(SUBJECT,OPEN):D('100'),MarkKey(SUBJECT,CLOSE):D('100')},UUID(int=99),
        {(CURRENCY,OPEN):D('.75'),(CURRENCY,CLOSE):D('.76')})
    assert result.market_pnl==1000


def test_coupon_income_is_note_specific_and_bond_payment_guard_remains():
    from valuation.flows import flow_component
    assert flow_component('COUPON','INCOME',D(2000),D('.75'),instrument_type='STRUCTURED_PRODUCT')==('COUPON',D(1500))
    assert flow_component('COUPON','PAYMENT_ONLY',D(2000),D('.75'),instrument_type='STRUCTURED_PRODUCT')==(None,D(0))
    with pytest.raises(ValueError):flow_component('COUPON','INCOME',D(2000),D(1),instrument_type='BOND')


def frozen():
    from hashlib import sha256
    import json
    parent,listing,currency=[UUID(int=i) for i in (10,11,12)]
    ids=dict(definitionId=str(UUID(int=13)),listingDefinitionId=str(UUID(int=14)),conventionId=str(UUID(int=15)),
        venueId=str(UUID(int=16)),structuredTermsId=str(UUID(int=17)))
    cv=convention(priceCurrencyId=str(currency))
    terms=dict(kind='STRUCTURED_PRODUCT',instrumentId=str(parent),listingId=str(listing),executionRoute='LISTED',convention=cv,
        bookingEligible=False,termsFingerprint=None,maturityDate='2027-12-01')
    digest=sha256(json.dumps(ids|terms,sort_keys=True,default=str).encode()).hexdigest()
    terms.update(bookingEligible=True,termsFingerprint=digest,readinessStatus='READY')
    snapshot=dict(kind='PRODUCT_BOOKING',economics=dict(terms=terms,amount='98500',amountKind='CONSIDERATION',direction='PAY'))
    row=dict(reference_instrument_node_id=parent,trade_subject_reference_node_id=listing,quantity=D('100000'),execution_price=D('98.5'),
        quantity_unit='NOMINAL',price_basis='PCT_OF_PAR',price_currency_id=currency,execution_venue_id=UUID(ids['venueId']))
    return row,snapshot,ids


def test_original_note_hash_and_listed_identity_can_be_normalized_without_new_facts():
    from security_master_schema.structured_note_valuation import frozen_note_conventions
    row,snapshot,ids=frozen();proof=frozen_note_conventions(row,snapshot,ids)
    assert proof['unitMultiplier']=='1' and proof['notePriceType']=='DIRTY'
    assert proof['instrumentDefinitionId']==ids['definitionId']


@pytest.mark.parametrize('values',[[],['100','100'],['n/a'],['sNaN'],['NaN'],['Infinity'],['-100'],['1']])
def test_source_quote_divisor_is_finite_numeric_unique_and_equal(values):
    from valuation.structured_note_inputs import validate_note_divisor
    with pytest.raises(ValueError,match='quote divisor'):validate_note_divisor(values,D(100))


@pytest.mark.parametrize('change',['quantity','amount','denomination','definition','currency','venue','direction'])
def test_note_rejects_changed_financial_or_identity_evidence_even_with_cached_identities(change):
    from positions.structured_note import normalize_booking
    row,snapshot,ids=frozen()
    cache={(row['reference_instrument_node_id'],row['trade_subject_reference_node_id'],snapshot['economics']['terms']['termsFingerprint']):ids}
    if change=='quantity':row['quantity']=D('100001')
    if change=='amount':snapshot['economics']['amount']='1'
    if change=='denomination':snapshot['economics']['terms']['convention']['denomination']='1000'
    if change=='definition':ids['definitionId']=str(UUID(int=999))
    if change=='currency':row['price_currency_id']=UUID(int=999)
    if change=='venue':row['execution_venue_id']=UUID(int=999)
    if change=='direction':snapshot['economics']['direction']='RECEIVE'
    with pytest.raises(ValueError):normalize_booking(None,row,snapshot,identity_cache=cache)
