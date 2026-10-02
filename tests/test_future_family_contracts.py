from uuid import uuid4
import pytest
from pydantic import ValidationError
from apps.reference_api.product_booking_contracts import FutureFamilyProposalRequest


def test_family_definition_is_typed_and_nonblank():
    payload = dict(canonicalName=' Index family ', familyCode='INDEX_ROOT', underlyingId=str(uuid4()),
                   contractCurrencyId=str(uuid4()), sourceReference=' Exchange spec ')
    assert FutureFamilyProposalRequest.model_validate(payload).canonical_name == 'Index family'
    for change in ({'canonicalName': ' '}, {'sourceReference': ' '}, {'familyCode': 'invalid-code'}, {'multiplier': 5}):
        with pytest.raises(ValidationError): FutureFamilyProposalRequest.model_validate(payload | change)
