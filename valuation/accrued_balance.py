"""Local monetary stocks, separate from earned income and actual cash holdings."""
from dataclasses import dataclass
from datetime import date,timedelta
from decimal import Decimal,localcontext


@dataclass(frozen=True)
class BalanceDay:
    value_date:date
    opening:Decimal|None
    daily_earned:Decimal|None
    trade_movements:Decimal|None
    coupon_paid:Decimal|None
    closing:Decimal|None
    basis:str
    warnings:tuple[str,...]=()


def replay_balances(start,end,*,earnings,movements,payments,opening=None,anchors=None,opening_anchors=None):
    """Replay exact supplied flows. Missing earnings/payment conversion is unknown.

    Anchors are assessed local stocks, not new income. An anchor can recover a
    broken chain; a bridge difference is retained for Ops rather than hidden.
    """
    anchors=anchors or {};opening_anchors=opening_anchors or {};rows=[];day=start
    with localcontext() as ctx:
        ctx.prec=512
        balance=opening
        while day<=end:
            warnings=[];basis='DERIVED'
            if day in opening_anchors:
                if balance is not None and balance!=opening_anchors[day]:warnings.append('OPENING_ANCHOR_DIFFERS_FROM_REPLAY')
                balance=opening_anchors[day];basis='SUPPLIED_OPENING_ANCHOR'
            earned=earnings.get(day);movement=movements.get(day,Decimal(0));paid=payments.get(day,Decimal(0))
            closing=None if any(v is None for v in (balance,earned,movement,paid)) else balance+earned+movement-paid
            if earned is None:warnings.append('DAILY_INTEREST_NOT_SUPPLIED')
            if movement is None:warnings.append('TRADE_ACCRUAL_UNAVAILABLE')
            if paid is None:warnings.append('COUPON_CURRENCY_CONVERSION_UNAVAILABLE')
            if day in anchors:
                if closing is not None and closing!=anchors[day]:warnings.append('CLOSING_ANCHOR_DIFFERS_FROM_REPLAY')
                closing=anchors[day];basis='SUPPLIED_CLOSING_ANCHOR'
            rows.append(BalanceDay(day,balance,earned,movement,paid,closing,basis,tuple(warnings)))
            balance=closing;day+=timedelta(days=1)
    return tuple(rows)


@dataclass(frozen=True)
class BalanceFxDay:
    balance:BalanceDay
    opening_fx:Decimal|None
    closing_fx:Decimal|None
    amount:Decimal|None
    reason:str|None
    sources:dict
    fx_evidence:tuple=()


@dataclass(frozen=True)
class BalanceFxLine:
    instrument_id:object
    currency_id:object
    days:tuple[BalanceFxDay,...]
    selections:tuple=()
    source_refs:dict|None=None

    @property
    def amount(self):
        with localcontext() as ctx:
            ctx.prec=512
            return sum((day.amount for day in self.days if day.amount is not None),Decimal(0))


@dataclass(frozen=True)
class BalanceFxResult:
    lines:tuple[BalanceFxLine,...]
    coverage:dict
    source_proof:dict
    snapshot_ids:tuple=()


def optional_interest_fx(c,request,source,target,day):
    """Classify documented absence only, local to optional interest components.

    The shared resolver and mandatory market/position FX behavior stay unchanged.
    Structural, timing, currency, database and permission exceptions propagate.
    """
    from .fx import resolve_fx
    try:return resolve_fx(c,request,source,target,day)
    except ValueError as exc:
        message=str(exc)
        if message=='Missing or ambiguous governed FX currency pair' or message.startswith('FX input selection blocked: '):
            return message
        raise
