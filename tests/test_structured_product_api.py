"""API boundary contract for structured-product proposals."""

from apps.reference_api.main import create_app
from apps.reference_api.repository import (
    decide_structured_product_proposal,
    submit_structured_product_proposal,
)


def test_structured_product_proposal_routes_are_explicit() -> None:
    # Included routers can be lazy wrappers without .path in this FastAPI version.
    # Assert the published API boundary, including router-mounted operations.
    paths = set(create_app().openapi()["paths"])

    assert "/v1/structured-product-proposals" in paths
    assert "/v1/structured-product-proposals/{proposal_id}/decision" in paths


def test_structured_product_workflow_functions_are_importable() -> None:
    assert callable(submit_structured_product_proposal)
    assert callable(decide_structured_product_proposal)
