"""Futures quantities, quotation and original context identity stay bound."""
from copy import deepcopy
from datetime import datetime,timezone
from decimal import Decimal as D
from hashlib import sha256
from uuid import UUID
import json
import pytest
from security_master_schema.future_valuation import frozen_future_conventions


def frozen():
    parent,listing,currency=[UUID(int=i) for i in (10,11,12)]
    ids=dict(definitionId=str(UUID(int=13)),listingDefinitionId=str(UUID(int=14)),conventionId=str(UUID(int=15)),
        venueId=str(UUID(int=16)),familyId=str(UUID(int=17)),underlyingId=str(UUID(int=18)))
    cv=dict(kind='FUTURE',effectiveFrom='2026-01-01',priceCurrencyId=str(currency),quoteFactor='1',sourceReference='Synthetic contract',
        quantityUnit='CONTRACTS',priceBasis='INDEX_POINTS',monetaryMultiplier='50',tickSize='.25',allowNegativePrice=False,
        lastTradingAtUtc='2026-12-18T16:00:00Z',finalSettlementDate='2026-12-18')
    terms=dict(kind='FUTURE',instrumentId=str(parent),listingId=str(listing),executionRoute='LISTED',convention=cv,
        bookingEligible=False,termsFingerprint=None)
    digest=sha256(json.dumps(ids|terms,sort_keys=True,default=str).encode()).hexdigest()
    terms.update(bookingEligible=True,termsFingerprint=digest,readinessStatus='READY')
    snapshot=dict(kind='PRODUCT_BOOKING',economics=dict(terms=terms,amount='600000',amountKind='REFERENCE_CONTRACT_VALUE',direction=None))
    row=dict(reference_instrument_node_id=parent,trade_subject_reference_node_id=listing,quantity=D('2'),execution_price=D('6000'),
        quantity_unit='CONTRACTS',price_basis='INDEX_POINTS',price_currency_id=currency,execution_venue_id=UUID(ids['venueId']),trade_datetime_utc=datetime(2026,10,1,10,tzinfo=timezone.utc))
    return row,snapshot,ids


def test_frozen_future_multiplier_is_canonical_and_listing_multiplier_is_not_reapplied():
    row,snapshot,ids=frozen();proof=frozen_future_conventions(row,snapshot,ids)
    assert proof['unitMultiplier']=='50' and proof['quoteFactor']=='1'
    assert proof['instrumentDefinitionId']==ids['definitionId']


@pytest.mark.parametrize('change',['quantity','amount','multiplier','definition','currency','afterExpiry'])
def test_frozen_future_refuses_inconsistent_booked_evidence(change):
    row,snapshot,ids=frozen()
    if change=='quantity':row['quantity']=D('2.5')
    if change=='amount':snapshot['economics']['amount']='1'
    if change=='multiplier':snapshot['economics']['terms']['convention']['monetaryMultiplier']='500'
    if change=='definition':ids['definitionId']=str(UUID(int=999))
    if change=='currency':row['price_currency_id']=UUID(int=999)
    if change=='afterExpiry':row['trade_datetime_utc']=datetime(2027,1,1,tzinfo=timezone.utc)
    with pytest.raises(ValueError):frozen_future_conventions(row,snapshot,ids)


def test_cached_identity_still_validates_each_booked_execution_venue():
    from positions.future import normalize_booking
    row,snapshot,ids=frozen()
    cache={(row['reference_instrument_node_id'],row['trade_subject_reference_node_id'],snapshot['economics']['terms']['termsFingerprint']):ids}
    row['execution_venue_id']=UUID(int=999)
    with pytest.raises(ValueError):normalize_booking(None,row,snapshot,identity_cache=cache)
