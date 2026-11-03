"""Pre-extraction command schema hashes captured on 29 October 2026."""
import hashlib
import json
import pytest
from apps.reference_api import contracts


@pytest.mark.parametrize('name,digest', [
    ('TradePropertyInput','627f8e63a09b5fccd2304258976b4ba0765a5ade5fffbd241277e54d62623c41'),
    ('TradeReferenceInput','cef31a599a4b12c17346496987b06143a5c59062f6a00f74c271683d152b309f'),
    ('CancelBookingRequest','7e0875259d19d6d9eabed533847f3c8aebb5fec39cb6d5aeac5b6bdd7938edbb'),
    ('BookingCorrectionRequest','df44775f790cc13b5eef703fa1b3c43fb292371c327161e9745399f92a7e8c76'),
    ('ValuationRecognitionFields','cb762bcfa4f3373ea59c3e0b82f830979c93ef00f0cb45871934c2872d5069de'),
    ('TradeBookingRequest','b0ea93f5711a1d5f2f7d53d06c87cc6f90f7f22147a3cef16eafa3421336ea71'),
    ('OptionBookingRequest','5593b389ae1c7d67b0e936f67c39007a87fe73b446e0f13f36f3e8f65948f173'),
    ('FxForwardBookingRequest','e5e08ec0d3a0de853c37f742bde080ee26c118a2c690e5a20b7206b873bfcd26'),
])
def test_command_schemas_are_unchanged(name,digest):
    schema=getattr(contracts,name).model_json_schema(by_alias=True)
    assert hashlib.sha256(json.dumps(schema,sort_keys=True,separators=(',',':')).encode()).hexdigest()==digest


def test_api_exports_are_identical_shared_commands_and_helpers():
    from trading import booking_contracts,booking_store,annotations,corrections,recognition,cash_reference
    from apps.reference_api import repository,trade_properties,trade_corrections,valuation_recognition,cash_booking_integrity
    for name in ('TradePropertyInput','TradeReferenceInput','CancelBookingRequest','BookingCorrectionRequest','ValuationRecognitionFields','TradeBookingRequest'):
        assert getattr(contracts,name) is getattr(booking_contracts,name)
    assert repository._trade_booking_fingerprint is booking_store.booking_fingerprint
    assert repository.persist_trade_annotations is booking_store.persist_trade_annotations
    assert trade_properties.validate_trade_annotations is annotations.validate_trade_annotations
    assert trade_corrections.complete_correction is corrections.complete_correction
    assert valuation_recognition.recognition is recognition.recognition
    assert cash_booking_integrity.load_cash_booking_listing is cash_reference.load_cash_booking_listing
    from apps.reference_api import import_service
    from apps.reference_api.import_adapters import trades
    from trading.booking import book_cash_trade
    assert import_service.book_cash_trade is book_cash_trade
    assert trades.TradeBookingRequest is booking_contracts.TradeBookingRequest
