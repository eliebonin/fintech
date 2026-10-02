"""Pure contractual economics: catch side, date and precision mistakes."""
from dataclasses import replace
from datetime import date
from decimal import Decimal
from uuid import UUID

import pytest

def terms(**overrides):
    from security_master_schema.fx_forward_booking import FxForwardBookingTerms
    values = dict(instrument_id=UUID(int=1), base_currency_id=UUID(int=2), quote_currency_id=UUID(int=3), base_currency="EUR", quote_currency="USD", quote_convention="USD_PER_EUR", settlement_type="DELIVERABLE", agreed_rate=Decimal("1.10"), maturity_date=date(2026, 12, 15))
    return FxForwardBookingTerms(**(values | overrides))

@pytest.mark.parametrize("side,receive,pay,signed", [("BUY", "EUR", "USD", "1000000"), ("SELL", "USD", "EUR", "-1000000")])
def test_buy_sell_obligations(side, receive, pay, signed):
    from security_master_schema.fx_forward_booking import derive_fx_forward_obligations
    result = derive_fx_forward_obligations(terms(), side, Decimal("1000000"))
    assert result.receive_currency == receive
    assert result.pay_currency == pay
    assert result.receive_amount == Decimal("1000000" if side == "BUY" else "1100000")
    assert result.pay_amount == Decimal("1100000" if side == "BUY" else "1000000")
    assert result.signed_base_quantity == Decimal(signed)
    assert result.settlement_date == date(2026, 12, 15)

def test_precision_preserved():
    from security_master_schema.fx_forward_booking import derive_fx_forward_obligations
    assert derive_fx_forward_obligations(terms(agreed_rate=Decimal("1.123456789012")), "BUY", Decimal("0.000001")).pay_amount == Decimal("0.000001123456789012")

def test_settlement_inherited():
    from security_master_schema.fx_forward_booking import resolve_fx_forward_settlement
    assert resolve_fx_forward_settlement(terms()) == date(2026, 12, 15)

@pytest.mark.parametrize("field", ["settlement_date", "cash_settlement_date", "final_settlement_date"])
def test_conflicting_dates_rejected(field):
    from security_master_schema.fx_forward_booking import resolve_fx_forward_settlement, FxForwardBookingError
    with pytest.raises(FxForwardBookingError) as error:
        resolve_fx_forward_settlement(terms(**{field:date(2026, 12, 16)}))
    assert error.value.code == "fx_forward.date_conflict"

@pytest.mark.parametrize("changes,code", [({"settlement_type":"NDF"}, "fx_forward.unsupported_settlement"), ({"settlement_type":"CASH"}, "fx_forward.unsupported_settlement"), ({"quote_convention":"EUR_PER_USD"}, "fx_forward.unsupported_quote"), ({"agreed_rate":Decimal("0")}, "fx_forward.invalid_terms"), ({"maturity_date":None}, "fx_forward.invalid_terms")])
def test_unsupported_settlement_and_quote_rejected(changes, code):
    from security_master_schema.fx_forward_booking import resolve_fx_forward_settlement, FxForwardBookingError
    with pytest.raises(FxForwardBookingError) as error:
        resolve_fx_forward_settlement(terms(**changes))
    assert error.value.code == code

@pytest.mark.parametrize("quantity", ["0", "-1", "0.0000000000001", "1000000000000000000", "NaN", "Infinity"])
def test_invalid_quantity_and_rate_rejected(quantity):
    from security_master_schema.fx_forward_booking import derive_fx_forward_obligations, FxForwardBookingError
    with pytest.raises(FxForwardBookingError):
        derive_fx_forward_obligations(terms(), "BUY", Decimal(quantity))

def test_fingerprint_numeric_normalization():
    from security_master_schema.fx_forward_booking import fx_forward_terms_fingerprint
    assert fx_forward_terms_fingerprint(terms()) == fx_forward_terms_fingerprint(terms(agreed_rate=Decimal("1.100000000000")))
    assert fx_forward_terms_fingerprint(terms()) != fx_forward_terms_fingerprint(terms(agreed_rate=Decimal("1.11")))
