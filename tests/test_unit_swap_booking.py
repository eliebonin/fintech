"""Unit swaps retain genuine quantity/quote dimensions; nominal swaps unchanged."""
from decimal import Decimal as D
import pytest
from pydantic import ValidationError
from apps.reference_api.swap_creation_contracts import GenericSwapTerms
from apps.reference_api.product_booking_contracts import SwapConvention
from tests.test_swap_creation_rules import payload

def unit_terms(**changes):
    return GenericSwapTerms.model_validate(payload(quantityUnit='UNITS',contractualUnits='25000',
        notionalPerUnit='8250',contractualNotional='206250000',quoteFactor='1',leverage='1.5')|changes)

def test_units_have_an_explicit_funding_notional_and_no_second_leverage_multiplication():
    terms=unit_terms()
    assert terms.quantity_unit=='UNITS'
    assert terms.booked_reference_notional(D('2500'))==D('20625000')
    assert terms.contractual_units==25000

@pytest.mark.parametrize('changes',[dict(contractualNotional='1'),dict(notionalPerUnit=None),
    dict(contractualUnits=None),dict(contractualUnits='0'),dict(notionalPerUnit='NaN'),dict(notionalPerUnit=8250)])
def test_inconsistent_or_ambiguous_unit_terms_are_rejected(changes):
    with pytest.raises(ValidationError):unit_terms(**changes)

def test_existing_nominal_payloads_do_not_gain_fields_or_change_retry_fingerprints():
    terms=GenericSwapTerms.model_validate(payload())
    dump=terms.model_dump(mode='json',by_alias=True)
    assert not {'quantityUnit','contractualUnits','notionalPerUnit'} & dump.keys()
    assert terms.booked_reference_notional(D('100'))==100
    with pytest.raises(ValidationError):GenericSwapTerms.model_validate(payload(notionalPerUnit='100'))

def test_swap_quote_and_quantity_dimensions_must_agree():
    common=dict(kind='SWAP',effectiveFrom='2024-10-15',priceCurrencyId=payload()['notionalCurrencyId'],quoteFactor='1',
        sourceReference='Synthetic sourced unit contract',quantityMinimum='1',quantityIncrement='1',otcAllowed=True)
    assert SwapConvention(**common,quantityUnit='UNITS',priceBasis='SWAP_VALUE_PER_UNIT').quantity_unit=='UNITS'
    with pytest.raises(ValidationError):SwapConvention(**common,quantityUnit='UNITS',priceBasis='SWAP_VALUE_PER_NOTIONAL')
