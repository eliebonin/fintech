"""Pure, decimal-exact economics for single-date deliverable FX contracts."""
from dataclasses import dataclass, asdict
from datetime import date
from decimal import Decimal, localcontext
from hashlib import sha256
import json
from typing import Literal
from uuid import UUID


class FxForwardBookingError(ValueError):
    def __init__(self, code: str, field: str, message: str):
        super().__init__(message)
        self.code, self.field, self.message = code, field, message


@dataclass(frozen=True)
class FxForwardBookingTerms:
    instrument_id: UUID
    base_currency_id: UUID
    quote_currency_id: UUID
    base_currency: str
    quote_currency: str
    quote_convention: str
    settlement_type: str
    agreed_rate: Decimal
    maturity_date: date
    settlement_date: date | None = None
    cash_settlement_date: date | None = None
    final_settlement_date: date | None = None


@dataclass(frozen=True)
class FxForwardObligations:
    signed_base_quantity: Decimal
    receive_currency: str
    receive_amount: Decimal
    pay_currency: str
    pay_amount: Decimal
    settlement_date: date


def decimal_text(value: Decimal) -> str:
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def resolve_fx_forward_settlement(terms: FxForwardBookingTerms) -> date:
    if not terms.maturity_date or not terms.agreed_rate.is_finite() or terms.agreed_rate <= 0 or terms.base_currency_id == terms.quote_currency_id or not terms.base_currency or not terms.quote_currency:
        raise FxForwardBookingError("fx_forward.invalid_terms", "instrumentId", "Complete positive-rate terms and distinct currencies are required.")
    if terms.settlement_type != "DELIVERABLE":
        raise FxForwardBookingError("fx_forward.unsupported_settlement", "instrumentId", "Only single-date deliverable FX forwards can be booked in this alpha.")
    if terms.quote_convention != f"{terms.quote_currency}_PER_{terms.base_currency}":
        raise FxForwardBookingError("fx_forward.unsupported_quote", "instrumentId", "The contract must be quoted as quote currency per base currency.")
    if any(value is not None and value != terms.maturity_date for value in (terms.settlement_date, terms.cash_settlement_date, terms.final_settlement_date)):
        raise FxForwardBookingError("fx_forward.date_conflict", "instrumentId", "Settlement dates conflict with maturity. Enrich the contract before booking.")
    return terms.maturity_date


def derive_fx_forward_obligations(terms: FxForwardBookingTerms, side: Literal["BUY", "SELL"], quantity: Decimal) -> FxForwardObligations:
    settlement = resolve_fx_forward_settlement(terms)
    if not quantity.is_finite() or quantity <= 0 or quantity >= Decimal("1e18"):
        raise FxForwardBookingError("fx_forward.invalid_terms", "quantity", "Enter a positive base amount with at most 18 integer and 12 fractional digits.")
    with localcontext() as context:
        context.prec = 80
        if quantity != quantity.quantize(Decimal("1e-12")) or side not in ("BUY", "SELL"):
            raise FxForwardBookingError("fx_forward.invalid_terms", "quantity", "Enter a BUY or SELL and a base amount with at most 12 fractional digits.")
        quote_amount = quantity * terms.agreed_rate
        if side == "BUY":
            return FxForwardObligations(quantity, terms.base_currency, quantity, terms.quote_currency, quote_amount, settlement)
        return FxForwardObligations(-quantity, terms.quote_currency, quote_amount, terms.base_currency, quantity, settlement)


def fx_forward_terms_fingerprint(terms: FxForwardBookingTerms) -> str:
    values = asdict(terms)
    values["agreed_rate"] = decimal_text(terms.agreed_rate)
    return sha256(json.dumps(values, default=str, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
