"""Daily earned interest is a flow; accumulated accrued interest is a stock.

Ops supplies assessed nominal and balance movements (coupon, bought/sold accrual,
etc.). We validate the bridge instead of guessing earnings from a stock change.
"""
from decimal import Decimal,localcontext
from dataclasses import dataclass,replace
from .economics import finite_decimal


def accrual_amounts(values):
    names=('openingBalance','dailyEarned','closingBalance','balanceMovements','openingFx','closingFx')
    for name in names:
        if name not in values: raise ValueError('Missing required daily accrual input')
        finite_decimal(values[name],name,positive=name in ('openingFx','closingFx'))
    with localcontext() as ctx:
        ctx.prec=512
        opening,daily,closing,movements,fx0,fx1=(values[n] for n in names)
        if opening+daily+movements!=closing:
            raise ValueError('Accrued balance does not reconcile; missing coupon/acquisition/disposal movements')
        return dict(dailyLocal=daily,dailyBase=daily*fx1,balanceLocal=closing,balanceBase=closing*fx1,
            openingBalanceLocal=opening,openingBalanceBase=opening*fx0,balanceMovementsLocal=movements,
            receivableFx=opening*(fx1-fx0))


def record_accrual(c,tenant,actor,payload,key,*,recorded_at=None,request_hash=None):
    from datetime import datetime,timezone
    from hashlib import sha256
    from sqlalchemy import select,func
    from security_master_schema import models as m
    from security_master_schema.tenancy import assert_tenant_owns_strategy
    from apps.reference_api.product_booking import require_visible
    from . import tables as t
    from .economics import canonical_payload,evidence_hash
    assert_tenant_owns_strategy(c,tenant,payload['strategyId'])
    require_visible(c,tenant,payload['instrumentId'])
    instrument=c.execute(select(m.instrument,m.instrument_type.c.type_code).join(m.instrument_type).where(
        m.instrument.c.instrument_node_id==payload['instrumentId'])).mappings().one()
    if instrument['type_code']!='BOND': raise ValueError('Daily interest requires a canonical bond')
    if not c.scalar(select(m.currency.c.currency_id).where(m.currency.c.currency_id==payload['currencyId'],m.currency.c.status=='ACTIVE')):
        raise ValueError('Active daily interest currency required')
    inputs=payload.get('inputs')
    daily=payload.get('dailyEarned',inputs.get('dailyEarned') if inputs else None)
    finite_decimal(daily,'daily earned interest')
    with localcontext() as ctx:
        ctx.prec=512
        if daily!=daily.quantize(Decimal('0.000000000001')) or abs(daily)>=Decimal('1e18'):
            raise ValueError('daily earned interest exceeds NUMERIC(30,12); no silent rounding')
    if inputs:
        if instrument['base_currency_id']!=payload['currencyId']: raise ValueError('Reconciled balance currency must match the canonical bond')
        expected=accrual_amounts(inputs)
        if daily!=inputs['dailyEarned'] or payload.get('amounts')!=expected:
            raise ValueError('daily accrual amounts must equal the validated local/base bridge')
        if payload['currencyId']==payload['reportingCurrencyId']:
            if inputs['openingFx']!=1 or inputs['closingFx']!=1: raise ValueError('Same-currency accrual requires identity FX')
        elif len(payload.get('fxEvidence',[]))!=2 or any(not e.get('selection') for e in payload['fxEvidence']):
            raise ValueError('Foreign accrual requires frozen opening and closing FX selections')
    elif payload.get('amounts'):
        raise ValueError('Balance amounts require reconciled inputs')
    if payload.get('eligibleNominal') is not None: finite_decimal(payload['eligibleNominal'],'eligible nominal')
    for name in ('sourceReference','eligibilityConvention'):
        if name in payload and not payload[name].strip(): raise ValueError('Provided source/eligibility description cannot be blank')
    digest=evidence_hash(payload);request_hash=request_hash or digest;table=t.accrual_input
    from .storage import input_revision_lock
    input_revision_lock(c,tenant,payload['strategyId'])
    scope=f"accrual:{tenant}:{payload['strategyId']}:{payload['instrumentId']}:{payload['valueDate']}"
    for name in (f'accrual-key:{tenant}:{key}',scope):
        c.execute(select(func.pg_advisory_xact_lock(int.from_bytes(sha256(name.encode()).digest()[:8],'big',signed=True))))
    prior_key=c.execute(select(table).where(table.c.tenant_id==tenant,table.c.submission_key==key)).mappings().one_or_none()
    if prior_key:
        if prior_key['request_hash']!=request_hash: raise ValueError('Accrual request key reused for different inputs')
        return prior_key['input_id']
    old=c.execute(select(table).where(table.c.tenant_id==tenant,table.c.strategy_id==payload['strategyId'],
        table.c.instrument_id==payload['instrumentId'],table.c.value_date==payload['valueDate'],table.c.input_type==payload['inputType'])
        .order_by(table.c.revision.desc()).limit(1)).mappings().one_or_none()
    if payload.get('supersedesInputId')!=(old['input_id'] if old else None):
        raise ValueError('Accrual revision changed; select the current input version')
    stamp=recorded_at or datetime.now(timezone.utc)
    if stamp.utcoffset() is None or old and stamp<old['recorded_at']: raise ValueError('Invalid accrual revision recording time')
    return c.scalar(table.insert().values(tenant_id=tenant,strategy_id=payload['strategyId'],recorded_by=actor,
        instrument_id=payload['instrumentId'],value_date=payload['valueDate'],input_type=payload['inputType'],
        daily_earned_interest=daily,currency_id=payload['currencyId'],
        revision=old['revision']+1 if old else 1,supersedes_input_id=payload.get('supersedesInputId'),
        submission_key=key,input_hash=digest,request_hash=request_hash,payload=canonical_payload(payload),recorded_at=stamp).returning(table.c.input_id))


def read_accruals(c,tenant,strategy,start,end,asof):
    from sqlalchemy import select,func
    from . import tables as t
    from security_master_schema.tenancy import assert_tenant_owns_strategy
    assert_tenant_owns_strategy(c,tenant,strategy)
    table=t.accrual_input
    query=select(table,func.row_number().over(partition_by=[table.c.instrument_id,table.c.value_date,table.c.input_type],
        order_by=table.c.revision.desc()).label('rank')).where(table.c.tenant_id==tenant,table.c.strategy_id==strategy,
        table.c.value_date.between(start,end),table.c.recorded_at<=asof).subquery()
    return [dict(row) for row in c.execute(select(query).where(query.c.rank==1).order_by(query.c.value_date,query.c.instrument_id)).mappings()]


@dataclass(frozen=True)
class AccrualInput:
    input_id: object
    instrument_id: object
    value_date: object
    revision: int
    payload: dict
    position_key: object


@dataclass(frozen=True)
class MissingAccrualInput:
    instrument_id: object
    value_date: object
    position_keys: tuple


@dataclass(frozen=True)
class AccrualCoverage:
    inputs: tuple = ()
    missing: tuple = ()

    def evidence(self,required):
        return dict(mode='REQUIRED' if required else 'OPTIONAL',suppliedCount=len(self.inputs),
            missingCount=len(self.missing),missing=[dict(instrumentId=str(i.instrument_id),
                valueDate=i.value_date.isoformat()) for i in self.missing])


def load_accrual_inputs(c,request,position_projection):
    """Include assessed daily interest; disclose absent inputs unless required.

    Missing is never a confirmed zero. Invalid supplied evidence still fails.
    Coverage counts canonical bond/dates, not the number of traded listings.
    """
    from datetime import timedelta,date
    from uuid import UUID
    from positions.reconstruction import reconstruct
    bonds={}
    for bucket in position_projection.buckets:
        if bucket.key.product_basis!='BOND': continue
        for fact in position_projection.facts:
            if fact.trade_id in bucket.trade_ids and fact.booking:
                proof=fact.booking.product_evidence or {}
                instrument=UUID(proof['instrumentId'])
                maturity=proof.get('maturityDate')
                if not maturity: raise ValueError('Frozen bond maturity required')
                if bucket.closing_quantity and request.closing_cutoff.date()>=date.fromisoformat(maturity):
                    raise ValueError('Mature bond requires recorded supported redemption; no inferred final marks or cash')
                bonds.setdefault(instrument,[])
                if bucket.key not in bonds[instrument]: bonds[instrument].append(bucket.key)
    if not bonds: return AccrualCoverage()
    start=request.opening_cutoff.date()+timedelta(days=1);end=request.closing_cutoff.date()
    if start>end: raise ValueError('Daily bond accrual requires an economic date interval')
    rows=read_accruals(c,request.tenant_id,request.strategy_id,start,end,request.information_cutoff)
    known={(row['instrument_id'],row['value_date']):row for row in rows};results=[];missing=[]
    day=start
    while day<=end:
        # Coverage follows actual daily exposure, not every historical bond ever
        # booked in the strategy. Eligibility itself is assessed by Ops.
        boundary=request.closing_cutoff.replace(year=day.year,month=day.month,day=day.day)
        daily=reconstruct(position_projection.facts,replace(position_projection.request,
            opening_cutoff=boundary-timedelta(days=1),closing_cutoff=boundary))
        for instrument,keys in sorted(bonds.items(),key=lambda item:str(item[0])):
            active=[b for b in daily.buckets if b.key in keys]
            if not active: continue
            row=known.get((instrument,day))
            if row is None:
                if request.require_complete_accruals:
                    raise ValueError(f'Missing assessed daily accrued-interest input for {instrument} on {day}')
                missing.append(MissingAccrualInput(instrument,day,tuple(b.key for b in active)))
                continue
            payload=dict(row['payload']);daily_amount=row['daily_earned_interest'];currency=row['currency_id']
            finite_decimal(daily_amount,'stored daily earned interest')
            source_amount=payload.get('dailyEarned',(payload.get('amounts') or {}).get('dailyLocal'))
            if source_amount is None or Decimal(source_amount)!=daily_amount or UUID(payload['currencyId'])!=currency:
                raise ValueError('Typed daily interest differs from retained source evidence')
            if not payload.get('inputs'):
                from .fx import resolve_fx
                fx=resolve_fx(c,request,currency,request.reporting_currency_id,day)
                with localcontext() as ctx:
                    ctx.prec=512
                    amounts=dict(dailyLocal=str(daily_amount),dailyBase=str(daily_amount*fx.rate))
                payload.update(amounts=amounts,reportingCurrencyId=str(request.reporting_currency_id),
                    fxEvidence=[fx.evidence],balanceReconciliation='NOT_PROVIDED')
                results.append(AccrualInput(row['input_id'],instrument,day,row['revision'],payload,active[0].key))
                continue
            inputs={k:Decimal(v) for k,v in payload['inputs'].items()}
            expected=accrual_amounts(inputs)
            if {k:Decimal(v) for k,v in payload['amounts'].items()}!=expected:
                raise ValueError('Stored accrued-interest bridge is inconsistent')
            currencies={b.key.currency_id for b in active}
            if currencies!={UUID(payload['currencyId'])} or UUID(payload['reportingCurrencyId'])!=request.reporting_currency_id:
                raise ValueError('Accrued-interest currency differs from position/reporting currency')
            if UUID(payload['currencyId'])!=request.reporting_currency_id and (
                payload.get('policyId')!=str(request.policy_id) or payload.get('cutId')!=str(request.cut_id)):
                raise ValueError('Foreign accrued-interest inputs require matching frozen valuation policy/cut')
            results.append(AccrualInput(row['input_id'],instrument,day,row['revision'],payload,active[0].key))
        day+=timedelta(days=1)
    return AccrualCoverage(tuple(results),tuple(missing))


def attach_accruals(period,inputs,*,missing=()):
    """One deterministic owner per canonical bond; never multiply by listing count."""
    lines=list(period.lines)
    for source in inputs:
        index=next((i for i,l in enumerate(lines) if l.bucket.key==source.position_key),None)
        if index is None: raise ValueError('Daily accrual has no real position owner')
        line=lines[index];components=dict(line.economic_components)
        with localcontext() as ctx:
            ctx.prec=512
            for name,field in [('ACCRUAL','dailyBase'),('CARRY','receivableFx')]:
                if field in source.payload['amounts']:
                    components[name]=components.get(name,Decimal(0))+Decimal(source.payload['amounts'][field])
        proof=dict(kind='DAILY_ACCRUAL',inputId=str(source.input_id),revision=source.revision,
            valueDate=source.value_date.isoformat(),payload=source.payload,
            receivableFxComponent='CARRY' if 'receivableFx' in source.payload['amounts'] else None,
            allocation='ONCE_PER_CANONICAL_INSTRUMENT')
        lines[index]=replace(line,economic_components=components,economic_evidence=line.economic_evidence+(proof,))
    for source in missing:
        for key in source.position_keys:
            index=next((i for i,l in enumerate(lines) if l.bucket.key==key),None)
            if index is None: raise ValueError('Missing accrual coverage has no real position owner')
            line=lines[index]
            proof=dict(kind='MISSING_DAILY_ACCRUAL',instrumentId=str(source.instrument_id),
                valueDate=source.value_date.isoformat(),status='NOT_SUPPLIED_NOT_INCLUDED')
            lines[index]=replace(line,economic_evidence=line.economic_evidence+(proof,))
    return replace(period,lines=tuple(lines))


def assert_current_accrual_versions(c,tenant,items):
    """A known corrected source cannot be published from an older candidate."""
    from datetime import date,datetime,timezone
    from uuid import UUID
    from sqlalchemy import select
    from . import tables as t
    for item in items:
        for evidence in item['evidence'].get('economicInputs',[]):
            if evidence.get('kind')=='MISSING_DAILY_ACCRUAL':
                supplied=c.scalar(select(t.accrual_input.c.input_id).where(t.accrual_input.c.tenant_id==tenant,
                    t.accrual_input.c.strategy_id==item['strategy_id'],
                    t.accrual_input.c.instrument_id==UUID(evidence['instrumentId']),
                    t.accrual_input.c.value_date==date.fromisoformat(evidence['valueDate']),
                    t.accrual_input.c.input_type=='DAILY_INTEREST',
                    t.accrual_input.c.recorded_at<=datetime.now(timezone.utc)).limit(1))
                if supplied: raise ValueError('A previously missing daily accrued-interest input is now supplied; recalculate before publication')
                continue
            if evidence.get('kind')!='DAILY_ACCRUAL': continue
            payload=evidence['payload']
            row=c.execute(select(t.accrual_input.c.input_id).where(t.accrual_input.c.tenant_id==tenant,
                t.accrual_input.c.strategy_id==item['strategy_id'],t.accrual_input.c.instrument_id==UUID(payload['instrumentId']),
                t.accrual_input.c.value_date==date.fromisoformat(payload['valueDate']),t.accrual_input.c.input_type=='DAILY_INTEREST',
                t.accrual_input.c.recorded_at<=datetime.now(timezone.utc)).order_by(t.accrual_input.c.revision.desc()).limit(1)).scalar_one_or_none()
            if row!=UUID(evidence['inputId']): raise ValueError('Accrued-interest source revision changed; correct inputs and recalculate')
