"""API boundary contract for structured-product proposals."""

from apps.reference_api.main import create_app
from apps.reference_api.repository import (
    decide_structured_product_proposal,
    submit_structured_product_proposal,
)


def test_structured_product_proposal_routes_are_explicit() -> None:
    paths = {route.path for route in create_app().routes}

    assert "/v1/structured-product-proposals" in paths
    assert "/v1/structured-product-proposals/{proposal_id}/decision" in paths


def test_structured_product_workflow_functions_are_importable() -> None:
    assert callable(submit_structured_product_proposal)
    assert callable(decide_structured_product_proposal)
