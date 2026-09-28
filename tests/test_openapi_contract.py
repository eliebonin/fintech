from apps.reference_api.main import create_app
from scripts.export_openapi_contract import export_contract


def test_openapi_operations_include_standard_problem_responses():
    schema = create_app().openapi()

    operation = schema["paths"]["/v1/instruments/search"]["get"]

    assert operation["responses"]["422"]["content"]["application/problem+json"]
    assert schema["components"]["schemas"]["ProblemDetails"]


def test_exporter_check_reports_stale_contract(tmp_path):
    output = tmp_path / "reference-data-api.v1.json"

    assert export_contract(output, check=False) == 0
    output.write_text("{}", encoding="utf-8")

    assert export_contract(output, check=True) == 1


def test_instrument_response_collections_are_required_in_the_contract():
    schema = create_app().openapi()
    instrument = schema["components"]["schemas"]["InstrumentView"]
    listing = schema["components"]["schemas"]["InstrumentListingView"]

    assert {"identifiers", "mappings", "listings", "instrumentMarketData", "taxonomy"} <= set(instrument["required"])
    assert {"identifiers", "marketData"} <= set(listing["required"])
