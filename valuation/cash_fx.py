"""Daily opening-balance FX attribution; cash movements are not earnings.

Rates are reporting-currency units per native cash unit. Intraday flows are
treated at the closing rate, so only opening cash earns the day's FX movement.
This is neither a cash ledger nor an intraday execution-rate accounting model.
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, Inexact, localcontext
from uuid import UUID
from .economics import finite_decimal

METHOD = 'cash-fx-opening-balance-v1'


def cash_fx_amount(opening: Decimal, opening_fx: Decimal | None, closing_fx: Decimal | None) -> Decimal:
    finite_decimal(opening, 'opening cash')
    if opening == 0:
        return Decimal(0)
    finite_decimal(opening_fx, 'opening cash FX', positive=True)
    finite_decimal(closing_fx, 'closing cash FX', positive=True)
    with localcontext() as context:
        context.prec = 512
        context.traps[Inexact] = True
        return opening * (closing_fx - opening_fx)


@dataclass(frozen=True)
class CashFxDay:
    value_date: date
    opening: dict
    closing: dict
    opening_fx: Decimal | None
    closing_fx: Decimal | None
    amount: Decimal
    fx_mode: str
    fx_evidence: tuple[dict, ...] = ()


@dataclass(frozen=True)
class CashFxLine:
    account_id: UUID
    currency_id: UUID
    days: tuple[CashFxDay, ...]
    selections: tuple[dict, ...] = ()
    missing: tuple[dict, ...] = ()

    @property
    def amount(self):
        with localcontext() as context:
            context.prec = 512
            return sum((day.amount for day in self.days), Decimal(0))

    def components(self):
        return {'CASH_FX': self.amount}


@dataclass(frozen=True)
class CashFxResult:
    lines: tuple[CashFxLine, ...]
    coverage: dict
    snapshot_ids: tuple[UUID, ...] = ()

    @property
    def amount(self):
        with localcontext() as context:
            context.prec = 512
            return sum((line.amount for line in self.lines), Decimal(0))
