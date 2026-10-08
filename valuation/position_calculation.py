"""Position-owned market bridge; no market mark for a zero value boundary."""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal,localcontext,Inexact
from uuid import UUID
from collections import defaultdict
from positions.contracts import PositionProjection, PositionBucket
from positions.reconstruction import key_identity
from .economics import MarketAttribution,finite_decimal

@dataclass(frozen=True)
class MarkKey:
    subject_id: UUID
    cutoff: datetime

@dataclass(frozen=True)
class MarkRequirement:
    key: MarkKey

@dataclass(frozen=True)
class PositionLine:
    bucket: PositionBucket
    attribution: MarketAttribution
    execution_value: Decimal

@dataclass(frozen=True)
class PositionPeriodAttribution:
    lines: tuple[PositionLine,...]
    market_pnl: Decimal
    opening_value: Decimal
    closing_value: Decimal
    execution_value: Decimal

def required_marks(projection: PositionProjection):
    keys=set()
    for bucket in projection.buckets:
        if bucket.opening_quantity:
            keys.add(MarkKey(bucket.key.subject_id,projection.request.opening_cutoff))
        if bucket.closing_quantity:
            keys.add(MarkKey(bucket.key.subject_id,projection.request.closing_cutoff))
    return tuple(MarkRequirement(key) for key in sorted(keys,key=lambda k:(k.cutoff,str(k.subject_id))))

def attribute_projection(projection: PositionProjection, marks, reporting_currency_id):
    if projection.request.mode!='PERIOD': raise ValueError('Period attribution requires PERIOD projection')
    if not projection.complete_knowledge: raise ValueError('Complete information cutoff required for valuation')
    lines=[]
    execution_groups=defaultdict(list)
    for effect in projection.executions: execution_groups[effect.key].append(effect)
    with localcontext() as context:
        context.prec=512; context.traps[Inexact]=True
        for bucket in projection.buckets:
            key=bucket.key
            if key.currency_id!=reporting_currency_id:
                raise ValueError('Reporting currency requires frozen FX conversion; multi-currency is not enabled yet')
            factor=key.unit_multiplier/key.quote_factor
            values=[]
            for quantity,cutoff in [(bucket.opening_quantity,projection.request.opening_cutoff),
                                     (bucket.closing_quantity,projection.request.closing_cutoff)]:
                if quantity==0: values.append(Decimal(0)); continue
                mark=marks.get(MarkKey(key.subject_id,cutoff))
                if mark is None: raise ValueError(f'Missing required position mark for {key.subject_id}')
                finite_decimal(mark,'market price',positive=True)
                values.append(quantity*factor*mark)
            executions=sum((effect.booking.quantity*factor*effect.booking.price
                for effect in execution_groups[key]),Decimal(0))
            opening,closing=values
            pnl=closing-opening-executions
            lines.append(PositionLine(bucket,MarketAttribution(pnl,Decimal(0),Decimal(0),pnl,opening,closing),executions))
        opening=sum((line.attribution.opening_value for line in lines),Decimal(0))
        closing=sum((line.attribution.closing_value for line in lines),Decimal(0))
        executions=sum((line.execution_value for line in lines),Decimal(0))
        pnl=sum((line.attribution.market_pnl for line in lines),Decimal(0))
        if pnl!=closing-opening-executions: raise ValueError('Position bridge does not reconcile')
    return PositionPeriodAttribution(tuple(lines),pnl,opening,closing,executions)
