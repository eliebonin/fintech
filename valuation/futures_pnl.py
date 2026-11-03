"""Price variation is futures P&L; gross price references are not NAV assets.

The caller supplies governed exact-contract prices and economic-day closing FX.
Margin cash is separately assessed from tenant cash snapshots, never generated here.
"""
from decimal import Decimal,localcontext,Inexact
from .economics import MarketAttribution,finite_decimal


def future_mark_context(projection,subject,cutoff):
    from security_master_schema.booking_conventions import FutureConvention
    from security_master_schema.future_economics import require_linear_future
    from .economics import evidence_hash
    trades={trade for bucket in projection.buckets if bucket.key.subject_id==subject for trade in bucket.trade_ids}
    bookings=[f.booking for f in projection.facts if f.booking and f.trade_id in trades
        and (f.booking.valuation_effective_date or f.effective_at.date())<=cutoff.date()
        and (projection.request.daily or f.effective_at<=cutoff)]
    conventions=[];parents=set()
    for b in bookings:
        proof=b.product_evidence or {};cv=FutureConvention.model_validate(proof.get('futureConvention',{}))
        require_linear_future(cv)
        if (b.product_basis!='FUTURE' or b.quantity_unit!='CONTRACTS' or b.currency_id!=cv.price_currency_id
            or b.unit_multiplier!=cv.monetary_multiplier or b.quote_factor!=cv.quote_factor):
            raise ValueError('Frozen compatible linear futures quotation required')
        if cutoff.date()<cv.effective_from or cutoff.date()>cv.final_settlement_date:
            raise ValueError('Futures boundary outside active contract dates requires recorded Ops closure')
        conventions.append(cv);parents.add(proof['instrumentId'])
    if len(parents)!=1 or len({evidence_hash(cv.model_dump(mode='json',exclude={'source_reference','effective_from'})) for cv in conventions})!=1:
        raise ValueError('Unique compatible frozen futures contract required')
    return (('CONTRACT_INSTRUMENT_ID',next(iter(parents))),('FUTURE_PRICE_BASIS',conventions[0].price_basis)),conventions[0]


def attribute_future(projection,bucket,marks,executions,closing_fx):
    from .position_calculation import PositionLine,MarkKey
    key=bucket.key;r=projection.request;zero=Decimal(0)
    original=[f.booking for f in projection.facts if f.booking and f.trade_id in bucket.trade_ids]
    allow_negative=bool(original) and all((b.product_evidence or {}).get('allowNegativePrice') is True for b in original)
    def mark(quantity,cutoff):
        if not quantity:return None
        value=marks.get(MarkKey(key.subject_id,cutoff))
        if value is None:raise ValueError('Missing required futures contract price')
        finite_decimal(value,'futures price')
        if value<0 and not allow_negative:raise ValueError('Negative futures price requires frozen explicit permission')
        return value
    first=mark(bucket.opening_quantity,r.opening_cutoff);last=mark(bucket.closing_quantity,r.closing_cutoff)
    with localcontext() as ctx:
        ctx.prec=512;ctx.traps[Inexact]=True
        factor=key.unit_multiplier/key.quote_factor
        local=(bucket.closing_quantity*(last if last is not None else zero)
            -bucket.opening_quantity*(first if first is not None else zero)
            -sum((e.booking.quantity*e.booking.price for e in executions),zero))*factor
        amount=local*closing_fx
    day=dict(valueDate=r.closing_cutoff.date(),openingDate=r.opening_cutoff.date(),
        openingQuantity=bucket.opening_quantity,closingQuantity=bucket.closing_quantity,
        openingPrice=first,closingPrice=last,monetaryMultiplier=key.unit_multiplier,quoteFactor=key.quote_factor,
        executions=[dict(tradeId=e.booking.trade_id,quantity=e.booking.quantity,price=e.booking.price,effectiveAt=e.effective_at) for e in executions],
        localVariation=local,closingFx=closing_fx,reportingVariation=amount)
    proof=dict(kind='FUTURES_DAILY_VARIATION',version=1,currencyId=key.currency_id,
        valueBasis='PRICE_VARIATION_NOT_CONTRACT_MTM',fxConvention='ECONOMIC_DAY_CLOSE',days=[day])
    if original and (original[0].product_evidence or {}).get('futureConvention'):
        proof['contractConvention']=original[0].product_evidence['futureConvention']
    return PositionLine(bucket,MarketAttribution(amount,zero,zero,amount,zero,zero),zero,
        economic_evidence=(proof,),settlement_variation=amount)


def retained_variation(items):
    """Verify exact frozen daily variation before accepting a review summary."""
    total=Decimal(0)
    with localcontext() as ctx:
        ctx.prec=512
        for row in items:
            evidence=row.get('evidence') or {};identity=evidence.get('identity') or {}
            if identity.get('bucket',{}).get('key',{}).get('product_basis')!='FUTURE':continue
            proofs=[p for p in evidence.get('economicInputs',[]) if p.get('kind')=='FUTURES_DAILY_VARIATION']
            if (identity.get('valueBasis')!='PRICE_VARIATION_NOT_CONTRACT_MTM' or len(proofs)!=1
                or any(identity.get(name) is not None for name in ('openingValue','closingValue','executionValue'))):
                raise ValueError('Missing explicit futures variation evidence')
            amount=sum((Decimal(day['reportingVariation']) for day in proofs[0]['days']),Decimal(0))
            if amount!=Decimal(identity['futuresVariation']) or amount!=Decimal(evidence['storageRounding']['exact']['market']):
                raise ValueError('Futures variation differs from immutable market attribution')
            total+=amount
    return total
