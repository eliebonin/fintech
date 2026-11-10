"""Typed request boundaries for lifecycle-specific custom values."""
from uuid import uuid4
import pytest
from pydantic import ValidationError
from apps.reference_api.bond_redemption_routes import Preview

def test_preview_accepts_typed_per_movement_inputs():
    value=dict(strategyId=uuid4(),instrumentId=uuid4(),allocationInputs={'a'*64:[dict(definitionId=uuid4(),value=False)]})
    request=Preview.model_validate(value)
    assert request.allocationInputs['a'*64][0].value is False

@pytest.mark.parametrize('value',[1,{},[],None])
def test_lifecycle_values_reject_untyped_scalar_values(value):
    with pytest.raises(ValidationError):
        Preview.model_validate(dict(strategyId=uuid4(),instrumentId=uuid4(),allocationInputs={'a'*64:[dict(definitionId=uuid4(),value=value)]}))
