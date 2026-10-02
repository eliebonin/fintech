from uuid import uuid4
import pytest
from pydantic import ValidationError
from apps.reference_api.product_booking_contracts import FutureFamilySpecification, FutureConvention


def specification(**changes):
    return dict(underlyingKind='CRYPTOASSET',symbolRoot='BTC',yearDigits=2,deliveryMonths=list(range(1,13)),
        settlementMethod='PHYSICAL',priceBasis='UNDERLYING_UNIT',contractSize='.1',contractSizeCurrencyId=str(uuid4()),
        monetaryMultiplier='.1',quoteFactor='1',tickSize='2.5',allowNegativePrice=False) | changes


def test_physical_asset_size_is_distinct_from_contract_count():
    result=FutureFamilySpecification.model_validate(specification())
    assert str(result.contract_size) == '0.1'
    for change in ({'monetaryMultiplier':'1'}, {'deliveryMonths':[1,1]}, {'deliveryMonths':[13]}, {'yearDigits':4}, {'contractSizeCurrencyId':None}):
        with pytest.raises(ValidationError): FutureFamilySpecification.model_validate(specification(**change))


def test_physical_delivery_requires_a_window():
    spec=specification()
    payload={k:v for k,v in spec.items() if k not in ('underlyingKind','symbolRoot','yearDigits','deliveryMonths')}
    payload.update(kind='FUTURE',quantityUnit='CONTRACTS',effectiveFrom='2026-09-01',priceCurrencyId=str(uuid4()),
        sourceReference='Synthetic rules',lastTradingAtUtc='2027-03-17T16:00:00Z',finalSettlementDate='2027-03-19')
    with pytest.raises(ValidationError): FutureConvention.model_validate(payload)
    assert FutureConvention.model_validate(payload | {'deliveryStartDate':'2027-03-19','deliveryEndDate':'2027-03-19'}).settlement_method == 'PHYSICAL'
