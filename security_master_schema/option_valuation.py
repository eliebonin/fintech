"""Frozen listed vanilla-option premium units, never an underlying valuation."""
from hashlib import sha256
import json
from decimal import Decimal
from uuid import UUID
from .option_booking import gross_option_premium


def frozen_option_conventions(row,snapshot,identities,currency_code):
    """Bind reviewed IDs to the original fingerprint; apply premium multiplier once."""
    try:
        economics=snapshot['economics'];terms=economics['terms']
        fields=('listingId','instrumentId','name','listingName','optionType','underlyingId','strike','strikeCurrency',
            'deliverableUnits','expiryDate','lastTradingAtUtc','exerciseStyle','settlementMethod',
            'premiumCurrency','premiumMultiplier','quoteFactor')
        facts={name:terms[name] for name in fields}
        facts.update(termsFingerprint=None,bookingEligible=False,optionTermsId=str(identities['optionTermsId']),
            definitionId=str(identities['instrumentDefinitionId']),listingDefinitionId=str(identities['listingDefinitionId']),
            venueId=str(identities['marketVenueId']))
        if sha256(json.dumps(facts,sort_keys=True,default=str).encode()).hexdigest()!=terms['termsFingerprint']:
            raise ValueError('Option booking fingerprint does not match retained definition identities')
        if (snapshot['kind']!='OPTION_BOOKING' or snapshot['schemaVersion']!=1
            or UUID(terms['instrumentId'])!=UUID(str(row['reference_instrument_node_id']))
            or UUID(terms['listingId'])!=UUID(str(row['trade_subject_reference_node_id']))
            or str(identities['marketVenueId'])!=str(row['execution_venue_id'])
            or terms['premiumCurrency']!=currency_code or row['quantity_unit']!='CONTRACTS'
            or row['price_basis']!='OPTION_PREMIUM' or terms['bookingEligible'] is not True
            or snapshot['positionEffect']!=row['position_effect'] or row['position_effect'] not in ('OPEN','CLOSE')):
            raise ValueError('Inconsistent frozen option booking units/identity')
        quantity=Decimal(row['quantity']);multiplier=Decimal(terms['premiumMultiplier']);factor=Decimal(terms['quoteFactor'])
        gross=gross_option_premium(abs(quantity),Decimal(row['execution_price']),multiplier,factor)
        if Decimal(economics['grossPremium'])!=gross or economics['premiumDirection']!=('PAY' if quantity>0 else 'RECEIVE'):
            raise ValueError('Frozen option premium differs from booked contract economics')
        proof=dict(instrumentDefinitionId=str(identities['instrumentDefinitionId']),instrumentId=terms['instrumentId'],
            listingDefinitionId=str(identities['listingDefinitionId']),optionTermsId=str(identities['optionTermsId']),
            marketVenueId=str(identities['marketVenueId']),priceCurrencyId=str(row['price_currency_id']),
            unitMultiplier=str(multiplier),quoteFactor=str(factor),productBasis='OPTION',priceBasis='OPTION_PREMIUM',
            optionPriceBasis='PREMIUM_POINTS',expiryDate=terms['expiryDate'],lastTradingAtUtc=terms['lastTradingAtUtc'])
        explicit=snapshot.get('valuationConventions')
        if explicit is not None:
            for name,value in proof.items():
                equal=Decimal(explicit[name])==Decimal(value) if name in ('unitMultiplier','quoteFactor') else explicit[name]==value
                if not equal:raise ValueError('Option valuation metadata conflicts with retained booking')
        return proof
    except (KeyError,TypeError,ArithmeticError) as exc:
        raise ValueError('Complete frozen option premium conventions required') from exc
