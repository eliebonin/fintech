"""Premium conventions must agree with the original reviewed booking fingerprint."""
from copy import deepcopy
from decimal import Decimal as D
from hashlib import sha256
from uuid import uuid4
import json
import pytest


def frozen():
    node,listing,currency,definition,listing_definition,option_terms,venue=[str(uuid4()) for _ in range(7)]
    terms=dict(listingId=listing,instrumentId=node,name='Synthetic option',listingName='OPT',optionType='PUT',underlyingId=str(uuid4()),
        strike='5800',strikeCurrency='GBP',deliverableUnits='100',expiryDate='2026-12-18',lastTradingAtUtc='2026-12-17T22:00:00+00:00',
        exerciseStyle='EUROPEAN',settlementMethod='CASH',premiumCurrency='GBP',premiumMultiplier='100',quoteFactor='1')
    ids=dict(instrumentDefinitionId=definition,listingDefinitionId=listing_definition,optionTermsId=option_terms,marketVenueId=venue)
    facts=terms|dict(termsFingerprint=None,bookingEligible=False,optionTermsId=option_terms,definitionId=definition,listingDefinitionId=listing_definition,venueId=venue)
    terms.update(termsFingerprint=sha256(json.dumps(facts,sort_keys=True,default=str).encode()).hexdigest(),bookingEligible=True,ineligibilityMessage=None)
    row=dict(reference_instrument_node_id=node,trade_subject_reference_node_id=listing,quantity=D(20),quantity_unit='CONTRACTS',
        execution_price=D('23.8'),price_basis='OPTION_PREMIUM',price_currency_id=currency,execution_venue_id=venue,position_effect='OPEN')
    snapshot=dict(schemaVersion=1,kind='OPTION_BOOKING',positionEffect='OPEN',economics=dict(terms=terms,grossPremium='47600',premiumDirection='PAY'))
    return row,snapshot,ids


def test_multiplier_is_frozen_premium_multiplier_not_deliverable_or_listing_units():
    from security_master_schema.option_valuation import frozen_option_conventions
    row,snapshot,ids=frozen();before=deepcopy(snapshot)
    proof=frozen_option_conventions(row,snapshot,ids,'GBP')
    assert proof['unitMultiplier']=='100' and proof['quoteFactor']=='1' and proof['priceBasis']=='OPTION_PREMIUM'
    assert proof['instrumentDefinitionId']==ids['instrumentDefinitionId'] and snapshot==before


@pytest.mark.parametrize('change',['multiplier','quantity','currency','definition','gross','effect','explicit'])
def test_inconsistent_option_booking_evidence_is_not_repriced(change):
    from security_master_schema.option_valuation import frozen_option_conventions
    row,snapshot,ids=frozen()
    proof=frozen_option_conventions(row,snapshot,ids,'GBP')
    if change=='multiplier':snapshot['economics']['terms']['premiumMultiplier']='1'
    if change=='quantity':row['quantity']=D('20.5')
    if change=='currency':code='USD'
    else:code='GBP'
    if change=='definition':ids['instrumentDefinitionId']=str(uuid4())
    if change=='gross':snapshot['economics']['grossPremium']='476'
    if change=='effect':row['position_effect']='CLOSE'
    if change=='explicit':snapshot['valuationConventions']=proof|dict(unitMultiplier='10000')
    with pytest.raises(ValueError):frozen_option_conventions(row,snapshot,ids,code)
