"""Pure profile rules keep field source/type and native metadata meanings explicit."""
from uuid import uuid4
import pytest
from pydantic import ValidationError
from trading.profiles.contracts import FieldRule,ProfileVersionInput,STANDARD_FIELDS


def test_custom_rules_pin_a_version_but_retain_stable_family():
    rule=FieldRule(propertyCode='MANDATE',propertyVersion=2,requirement='REQUIRED',lifecycleBehavior='ALLOCATION')
    assert rule.field_key=='CUSTOM:MANDATE' and rule.property_version==2


def test_standard_sources_cannot_be_redefined_as_custom_catalogues():
    assert STANDARD_FIELDS['COUNTERPARTY']['source']=='standard:COUNTERPARTY'
    with pytest.raises(ValidationError):FieldRule(standardFieldKey='COUNTERPARTY',propertyCode='OTHER',propertyVersion=1)
    with pytest.raises(ValidationError):FieldRule(standardFieldKey='QUANTITY',requirement='NOT_USED')


def test_two_versions_of_one_custom_field_cannot_be_in_one_profile():
    with pytest.raises(ValidationError,match='once'):
        ProfileVersionInput(label='Fund dealing',reason='New version',expectedVersion=1,fields=[dict(propertyCode='MANDATE',propertyVersion=1),dict(propertyCode='MANDATE',propertyVersion=2)])


def test_hidden_fields_are_not_allocation_dimensions():
    with pytest.raises(ValidationError):FieldRule(propertyCode='MANDATE',propertyVersion=1,requirement='NOT_USED',lifecycleBehavior='ALLOCATION')


def test_retained_custom_code_is_not_case_folded_into_a_different_identity():
    rule=FieldRule(propertyCode='Imported_abc123',propertyVersion=1)
    assert rule.field_key=='CUSTOM:Imported_abc123'
