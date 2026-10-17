"""Characterize public/frozen contracts before moving ownership below HTTP.

Schema fingerprints were captured from the pre-extraction implementation. They
guard this behavior-preserving move; an intentional future API change must review
and update the affected baseline rather than accidentally changing saved terms.
"""
import hashlib
import importlib
import json
from decimal import Decimal

import pytest
from apps.reference_api.product_booking_contracts import ConventionBase,FutureConvention
from apps.reference_api.swap_creation_contracts import GenericSwapTerms,SwapProposalRequest


SCHEMAS = [
    (ConventionBase,'165c4b5b4ee73d906eb5812ee7aa7cbc0c514f5afc64dc6e7c83d3aca6654b5f','99e27b1d1f185d43b8251aa671af47ceca7be92be8a82db9ed7e04d39c1c5a78'),
    (FutureConvention,'04110631af8552ecf5dae81282ad0e97c6ef017a483d8fef7c0c65a80f519b04','1c2eb4d7052c300083c1e6315cde812a5c718d8053bca9def8d6b5f7e0975025'),
    (GenericSwapTerms,'95bad456785b350801dde301ce552b020572123adb73a17ade4c99d7408fe0af','87ff1d05296c5720b87d2fe1f9fcc25d3edb7a6e03d27379929b2a68f132e796'),
    (SwapProposalRequest,'264289646014d5c1e589af3444e9bd9c52d8c9f5b94e301a205a65dd965702cf','600e226fcec5edfdde47873329a982f278577651df5d51ce27b626aa52259bb2'),
]


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


@pytest.mark.parametrize('model,validation,serialization',SCHEMAS)
def test_public_schemas_keep_pre_extraction_contract(model,validation,serialization):
    assert digest(model.model_json_schema(mode='validation',by_alias=True))==validation
    assert digest(model.model_json_schema(mode='serialization',by_alias=True))==serialization


@pytest.mark.parametrize('model,module',[
    (ConventionBase,'security_master_schema.booking_conventions'),
    (FutureConvention,'security_master_schema.booking_conventions'),
    (GenericSwapTerms,'security_master_schema.swap_terms'),
])
def test_api_import_is_the_same_domain_owned_class(model,module):
    assert model.__module__==module
    assert getattr(importlib.import_module(module),model.__name__) is model
    assert issubclass(FutureConvention,ConventionBase)


CURRENCY='00000000-0000-7000-8000-000000000201'


def future_payload():
    return dict(kind='FUTURE',effectiveFrom='2024-10-01',priceCurrencyId=CURRENCY,quoteFactor='1',
        sourceReference=' Synthetic exchange specification ',quantityUnit='CONTRACTS',priceBasis='INDEX_POINTS',
        monetaryMultiplier='50',tickSize='0.25',allowNegativePrice=False,
        lastTradingAtUtc='2026-12-18T14:30:00Z',finalSettlementDate='2026-12-18')


def swap_payload(*,units=False):
    payload=dict(performanceReferenceId='00000000-0000-7000-8000-000000000101',contractualNotional='1000000',
        notionalCurrencyId=CURRENCY,effectiveDate='2024-10-01',maturityDate='2027-10-01',
        performanceDirection='RECEIVE',returnBasis='TOTAL',returnProfileId='00000000-0000-7000-8000-000000000301',
        quoteCurrencyId=CURRENCY,quoteFactor='100',sourceReference=' Synthetic confirmation ',
        performanceResetFrequency='AT_MATURITY',redemptionRule='TERMINATE',financingTreatment='NONE')
    if units:payload.update(quantityUnit='UNITS',contractualUnits='25000',notionalPerUnit='40',leverage='1.5')
    return payload


def test_legacy_nominal_serialization_and_exact_unit_semantics_are_preserved():
    nominal=GenericSwapTerms.model_validate(swap_payload())
    encoded=nominal.model_dump(mode='json',by_alias=True)
    assert 'quantityUnit' not in encoded and 'contractualUnits' not in encoded and 'notionalPerUnit' not in encoded
    unit=GenericSwapTerms.model_validate(swap_payload(units=True))
    assert unit.booked_reference_notional(Decimal('25000'))==Decimal('1000000')
    assert unit.model_dump(mode='json',by_alias=True)['leverage']=='1.5'
    assert GenericSwapTerms.model_validate_json(unit.model_dump_json())==unit
    future=FutureConvention.model_validate(future_payload())
    assert future.monetary_multiplier==Decimal('50')
    assert future.source_reference=='Synthetic exchange specification'
    assert FutureConvention.model_validate_json(future.model_dump_json())==future


@pytest.mark.parametrize('model,payload,expected',[
    (FutureConvention,future_payload(),'ca4a2f95124454ce8ea0276172665cf5b0538450a2b6c3316305fa5e1d528ec7'),
    (GenericSwapTerms,swap_payload(),'3967674fc82712d5d4b850ccb2d23f2e3ba1261dd4a871a7ad330b1e5c9b236a'),
    (GenericSwapTerms,swap_payload(units=True),'0acf332172a102c7794e90c363b69eaeae7e1d6b4f4c6577302e11678267ad34'),
])
def test_frozen_alias_json_is_byte_identical_to_pre_extraction(model,payload,expected):
    encoded=model.model_validate(payload).model_dump_json(by_alias=True)
    assert hashlib.sha256(encoded.encode()).hexdigest()==expected
