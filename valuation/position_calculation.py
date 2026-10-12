"""Position-owned market bridge; no market mark for a zero value boundary."""
from dataclasses import dataclass,field
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
    economic_components: dict = field(default_factory=dict)
    economic_evidence: tuple = ()

    def components(self):
        return self.attribution.components() | self.economic_components

    @property
    def gross_pnl(self):
        from .economics import INCOME
        with localcontext() as ctx:
            ctx.prec=512
            return self.attribution.market_pnl+sum((v for k,v in self.economic_components.items() if k in INCOME),Decimal(0))

    @property
    def net_pnl(self):
        from .economics import COSTS
        with localcontext() as ctx:
            ctx.prec=512
            return self.gross_pnl+sum((v for k,v in self.economic_components.items() if k in COSTS),Decimal(0))

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

def attribute_projection(projection: PositionProjection, marks, reporting_currency_id, fx_inputs=None):
    if projection.request.mode!='PERIOD': raise ValueError('Period attribution requires PERIOD projection')
    if not projection.complete_knowledge: raise ValueError('Complete information cutoff required for valuation')
    lines=[]
    execution_groups=defaultdict(list)
    for effect in projection.executions: execution_groups[effect.key].append(effect)
    with localcontext() as context:
        context.prec=512; context.traps[Inexact]=True
        for bucket in projection.buckets:
            key=bucket.key
            def fx(cutoff):
                if key.currency_id==reporting_currency_id: return Decimal(1)
                value=(fx_inputs or {}).get((key.currency_id,cutoff))
                if value is None: raise ValueError('Missing frozen FX conversion for reporting currency')
                return finite_decimal(value,'FX conversion',positive=True)
            closing_fx=fx(projection.request.closing_cutoff)
            opening_fx=fx(projection.request.opening_cutoff) if bucket.opening_quantity else closing_fx
            factor=key.unit_multiplier/key.quote_factor
            values=[]
            for quantity,cutoff in [(bucket.opening_quantity,projection.request.opening_cutoff),
                                     (bucket.closing_quantity,projection.request.closing_cutoff)]:
                if quantity==0: values.append(Decimal(0)); continue
                mark=marks.get(MarkKey(key.subject_id,cutoff))
                if mark is None: raise ValueError(f'Missing required position mark for {key.subject_id}')
                finite_decimal(mark,'market price',positive=True)
                values.append(quantity*factor*mark)
            execution_local=sum((effect.booking.quantity*factor*effect.booking.price
                for effect in execution_groups[key]),Decimal(0))
            opening_local,closing_local=values
            # Daily end-date execution FX: new trades do not acquire overnight FX
            # P&L. Multi-day orchestration sums daily bridges, not one end-rate bridge.
            executions=execution_local*closing_fx
            opening,closing=opening_local*opening_fx,closing_local*closing_fx
            local_pnl=closing_local-opening_local-execution_local
            price=local_pnl*opening_fx
            fx_pnl=opening_local*(closing_fx-opening_fx)
            cross=local_pnl*(closing_fx-opening_fx)
            pnl=price+fx_pnl+cross
            if pnl!=closing-opening-executions: raise ValueError('FX position bridge does not reconcile')
            lines.append(PositionLine(bucket,MarketAttribution(price,fx_pnl,cross,pnl,opening,closing),executions))
        opening=sum((line.attribution.opening_value for line in lines),Decimal(0))
        closing=sum((line.attribution.closing_value for line in lines),Decimal(0))
        executions=sum((line.execution_value for line in lines),Decimal(0))
        pnl=sum((line.attribution.market_pnl for line in lines),Decimal(0))
        if pnl!=closing-opening-executions: raise ValueError('Position bridge does not reconcile')
    return PositionPeriodAttribution(tuple(lines),pnl,opening,closing,executions)
