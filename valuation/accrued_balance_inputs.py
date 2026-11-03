"""Original tenant-scoped interest sources; no changes to shared FX selection.

Integration cases live in tests/test_accrued_balance_integration.py. Optional
absence classification is isolated in the tested optional_interest_fx helper.
"""
from collections import defaultdict
from dataclasses import asdict,replace,dataclass
from datetime import date,timedelta
from decimal import Decimal,localcontext
from uuid import UUID
from sqlalchemy import select,func
from positions.reconstruction import booking_removed
from lifecycle import coupon_tables as ct
from .accruals import read_accruals
from .accrued_balance import replay_balances,BalanceFxDay,BalanceFxLine,BalanceFxResult,optional_interest_fx
from .economics import canonical_payload,evidence_hash


def _facts(projection):
    groups=defaultdict(list)
    for fact in projection.facts:groups[fact.trade_id].append(fact)
    return [f for chain in groups.values() if not booking_removed(chain,projection.request)
            for f in chain if f.booking and f.booking.product_basis=='BOND']


def _read_sources(c,r):
    rows=read_accruals(c,r.tenant_id,r.strategy_id,date.min,r.closing_cutoff.date(),r.information_cutoff)
    # CLEAN note stocks use assessed anchors in their own adapter; never send
    # note inputs through the bond coupon-receipt/reconstruction assumptions.
    from security_master_schema import models as m
    bond_ids=set(c.scalars(select(m.instrument.c.instrument_node_id).join(m.instrument_type).where(
        m.instrument_type.c.type_code=='BOND',m.instrument.c.instrument_node_id.in_({row['instrument_id'] for row in rows})))) if rows else set()
    rows=[row for row in rows if row['instrument_id'] in bond_ids]
    latest=select(ct.payment,func.row_number().over(partition_by=ct.payment.c.logical_payment_id,
        order_by=ct.payment.c.revision.desc()).label('rank')).where(ct.payment.c.tenant_id==r.tenant_id,
        ct.payment.c.strategy_id==r.strategy_id,ct.payment.c.recorded_at<=r.information_cutoff).subquery()
    payments=[dict(row) for row in c.execute(select(latest,ct.schedule.c.instrument_id,
        ct.cashflow.c.cashflow_key,ct.cashflow.c.payment_date.label('scheduled_date'))
        .join(ct.cashflow,latest.c.period_id==ct.cashflow.c.cashflow_id)
        .join(ct.schedule,ct.cashflow.c.schedule_id==ct.schedule.c.schedule_id)
        .where(latest.c.rank==1,latest.c.payment_date<=r.closing_cutoff.date(),ct.schedule.c.tenant_id==r.tenant_id)).mappings()]
    return rows,payments


@dataclass(frozen=True)
class LocalBalanceLine:
    instrument_id:object
    currency_id:object
    days:tuple
    source_refs:dict
    day_sources:dict


def reconstruct_local_balances(c,r,projection,*,balance_inputs=(),history_checkpoints=()):
    """Explicit balance-update stage. Valuation never calls this reconstruction."""
    from security_master_schema.market_data_resolver import persist_resolution_snapshot
    rows,payments=_read_sources(c,r)
    by_bond=defaultdict(lambda:dict(facts=[],rows=[],payments=[]))
    for f in _facts(projection):by_bond[UUID(f.booking.product_evidence['instrumentId'])]['facts'].append(f)
    for row in rows:by_bond[row['instrument_id']]['rows'].append(row)
    for row in payments:by_bond[row['instrument_id']]['payments'].append(row)
    for row in balance_inputs:by_bond[row['instrument_id']].setdefault('balanceInputs',[]).append(row)
    for row in history_checkpoints:by_bond[row['instrument_id']].setdefault('checkpoints',[]).append(row)
    lines=[];missing=[];warnings=[];snapshots={};fx_cache={};source_catalog=[];assessed=0
    start=r.opening_cutoff.date()+timedelta(days=1);end=r.closing_cutoff.date()
    def conversion(source,target,day):
        if not getattr(r,'policy_id',None):return 'TRADE_ACCRUAL_CURRENCY_CONVERSION_NOT_CONFIGURED'
        key=(source,target,day)
        if key not in fx_cache:fx_cache[key]=optional_interest_fx(c,r,source,target,day)
        return fx_cache[key]
    def retain_fx(value,selections):
        if value.selection:
            key=evidence_hash(value.evidence)
            if key not in snapshots:snapshots[key]=persist_resolution_snapshot(c,value.resolution_request,(value.selection,))
            selections.append(dict(asdict(value.selection),valuation_date=value.economic_date,input_role='FX',
                valuation_source_currency_id=value.source_currency_id,conversion=value.evidence))
    with localcontext() as ctx:
        ctx.prec=512
        for instrument,data in sorted(by_bond.items(),key=lambda pair:str(pair[0])):
            local_rows=data['rows'];bookings=data['facts'];receipts=data['payments']
            supplied=data.get('balanceInputs',[]);checkpoints=data.get('checkpoints',[])
            currencies={row['currency_id'] for row in local_rows+supplied+checkpoints}
            if len(currencies)>1:
                missing.append(dict(instrumentId=str(instrument),valueDate=start.isoformat(),reason='ACCRUAL_CURRENCY_CHANGED_WITHOUT_SINGLE_BASIS'))
                continue
            currency=next(iter(currencies),bookings[0].booking.currency_id if bookings else receipts[0]['currency_id'] if receipts else None)
            if currency is None:continue
            zero=bool(bookings) and all(f.booking.product_evidence.get('couponType')=='ZERO' for f in bookings)
            if zero and not local_rows and not supplied and not any(p['status']=='CONFIRMED' for p in receipts):continue
            earned={row['value_date']:row['daily_earned_interest'] for row in local_rows}
            anchors={};opening_anchors={};movements=defaultdict(lambda:Decimal(0));paid=defaultdict(lambda:Decimal(0));qty=defaultdict(lambda:Decimal(0));selections=[]
            day_sources=defaultdict(lambda:dict(dailyInputs=[],trades=[],payments=[]));refs=dict(dailyInputs=[],trades=[],payments=[]);first=[]
            for row in local_rows:
                day=row['value_date'];first.append(day)
                ref=dict(inputId=str(row['input_id']),revision=row['revision'],valueDate=day.isoformat())
                refs['dailyInputs'].append(ref);day_sources[day]['dailyInputs'].append(ref)
                detail=row['payload'].get('inputs') or {}
                if detail:
                    anchors[day]=Decimal(detail['closingBalance']);opening_anchors[day]=Decimal(detail['openingBalance'])
            for row in supplied:
                if row['status']!='ACTIVE':continue
                day=row['value_date'];first.append(day);anchors[day]=row['closing_balance']
                ref=dict(balanceInputId=str(row['input_id']),revision=row['revision'],valueDate=day.isoformat())
                refs.setdefault('balanceInputs',[]).append(ref);day_sources[day].setdefault('balanceInputs',[]).append(ref)
            for row in checkpoints:
                day=row['value_date'];first.append(day)
                # Explicit assessed facts win if both refer to the same date.
                anchors.setdefault(day,row['closing_balance'])
                refs.setdefault('checkpoints',[]).append(dict(historyId=str(row['history_id']),buildId=str(row['build_id']),valueDate=day.isoformat()))
            for f in bookings:
                b=f.booking;day=b.valuation_effective_date or f.effective_at.date();first.append(day);qty[day]+=b.quantity
                details=b.product_evidence.get('bondDetails') or {}
                amount=Decimal(details['accruedInterestAmount']) if 'accruedInterestAmount' in details else None
                if b.product_evidence.get('redemptionEvidence'):amount=Decimal(0)
                if amount is not None and b.quantity<0:amount=-amount
                fx=conversion(b.currency_id,currency,day) if amount and b.currency_id!=currency else None
                if amount is None or isinstance(fx,str):movements[day]=None
                elif movements[day] is not None:movements[day]+=amount*(fx.rate if fx else Decimal(1))
                if fx and not isinstance(fx,str):retain_fx(fx,selections)
                ref=dict(tradeId=str(f.trade_id),eventId=str(f.event_id),valueDate=day.isoformat(),accruedAmount=str(amount) if amount is not None else None,
                    currencyId=str(b.currency_id),conversion=fx.evidence if fx and not isinstance(fx,str) else None)
                refs['trades'].append(ref);day_sources[day]['trades'].append(ref)
            for payment in receipts:
                day=payment['payment_date'];first.append(day)
                ref=dict(paymentId=str(payment['payment_id']),revision=payment['revision'],status=payment['status'],valueDate=day.isoformat(),amount=str(payment['amount']),
                    currencyId=str(payment['currency_id']),scheduledDate=payment['scheduled_date'].isoformat(),couponKey=payment['cashflow_key'])
                refs['payments'].append(ref);day_sources[day]['payments'].append(ref)
                if payment['status']!='CONFIRMED':continue
                if payment['currency_id']!=currency:paid[day]=None
                elif paid[day] is not None:paid[day]+=payment['amount']
            if not first:continue
            prior=[day for day in anchors if day<=r.opening_cutoff.date()]
            anchor=max(prior) if prior else None
            replay_start=anchor+timedelta(days=1) if anchor else min(first)
            opening=anchors[anchor] if anchor else Decimal(0) if bookings and replay_start==min((f.booking.valuation_effective_date or f.effective_at.date()) for f in bookings) else None
            nominal=sum((q for day,q in qty.items() if day<replay_start),Decimal(0));cursor=replay_start
            while cursor<=end:
                before=nominal;nominal+=qty.get(cursor,Decimal(0))
                if cursor not in earned and (zero or before==nominal==0):earned[cursor]=Decimal(0)
                cursor+=timedelta(days=1)
            history=replay_balances(replay_start,end,earnings=earned,movements=movements,payments=paid,
                opening=opening,anchors=anchors,opening_anchors=opening_anchors)
            requested=[day for day in history if start<=day.value_date<=end]
            active=any(b.key.product_basis=='BOND' and any(f.trade_id in b.trade_ids for f in bookings) for b in projection.buckets)
            if not active and requested and all(day.opening==day.closing==0 for day in requested):continue
            known_stock=any(day.opening not in (None,0) or day.closing not in (None,0) for day in history)
            if not active and not known_stock and not any(start<=row['value_date']<=end for row in local_rows):continue
            source_catalog.append(dict(instrumentId=str(instrument),currencyId=str(currency),anchorDate=anchor.isoformat() if anchor else None,
                openingBasis=('VERIFIED_HISTORY_CHECKPOINT' if any(row['value_date']==anchor for row in checkpoints) and not any(row['value_date']==anchor and row['status']=='ACTIVE' for row in supplied) else 'SUPPLIED_CLOSING_ANCHOR') if anchor else 'FIRST_RECORDED_LEDGER_ACQUISITION' if opening==0 else 'UNKNOWN',sources=refs))
            lines.append(LocalBalanceLine(instrument,currency,tuple(requested),source_catalog[-1],dict(day_sources)))
    return tuple(lines),tuple(missing)


def load_accrued_balance_fx(c,r,projection):
    """FX stage reads maintained local stocks; it cannot rebuild missing history."""
    from security_master_schema.market_data_resolver import persist_resolution_snapshot
    from .balance_history import read_balance_lines
    local_lines,missing=read_balance_lines(c,r,projection)
    missing=list(missing);warnings=[];lines=[];snapshots={};fx_cache={};assessed=0
    def conversion(source,target,day):
        key=(source,target,day)
        if key not in fx_cache:fx_cache[key]=optional_interest_fx(c,r,source,target,day)
        return fx_cache[key]
    with localcontext() as ctx:
        ctx.prec=512
        for source in local_lines:
            result_days=[];selections=[]
            for day in source.days:
                fx0=fx1=None;reason=None;amount=None;evidence=[]
                if day.opening is None:
                    reason='STALE_ACCRUED_BALANCE_HISTORY' if 'STALE_ACCRUED_BALANCE_HISTORY' in day.warnings else 'OPENING_ACCRUED_BALANCE_UNAVAILABLE'
                elif day.opening==0:amount=Decimal(0)
                else:
                    values=[conversion(source.currency_id,r.reporting_currency_id,at) for at in (day.value_date-timedelta(days=1),day.value_date)]
                    if any(isinstance(value,str) for value in values):reason='ACCRUED_BALANCE_FX_UNAVAILABLE'
                    else:
                        fx0,fx1=(value.rate for value in values);amount=day.opening*(fx1-fx0)
                        for value in values:
                            evidence.append(value.evidence)
                            if value.selection:
                                key=evidence_hash(value.evidence)
                                if key not in snapshots:snapshots[key]=persist_resolution_snapshot(c,value.resolution_request,(value.selection,))
                                selections.append(dict(asdict(value.selection),valuation_date=value.economic_date,input_role='FX',valuation_source_currency_id=value.source_currency_id,conversion=value.evidence))
                if reason:missing.append(dict(instrumentId=str(source.instrument_id),currencyId=str(source.currency_id),valueDate=day.value_date.isoformat(),reason=reason))
                else:assessed+=1
                for warning in day.warnings:warnings.append(dict(instrumentId=str(source.instrument_id),valueDate=day.value_date.isoformat(),reason=warning))
                result_days.append(BalanceFxDay(day,fx0,fx1,amount,reason,source.day_sources.get(day.value_date,{}),tuple(evidence)))
            unique={evidence_hash(row):row for row in selections}
            lines.append(BalanceFxLine(source.instrument_id,source.currency_id,tuple(result_days),tuple(unique.values()),source.source_refs))
    from .accrued_balance_health import capture_balance_sources
    proof=canonical_payload(capture_balance_sources(c,r)|dict(sources=[line.source_refs for line in local_lines]))
    return BalanceFxResult(tuple(lines),dict(status='PARTIAL' if missing and assessed else 'MISSING_INPUTS' if missing else 'INCLUDED' if assessed else 'NOT_ASSESSED',
        suppliedCount=assessed,missingCount=len(missing),missing=missing,warnings=warnings),proof,tuple(snapshots.values()))


def balance_proof(line):
    return canonical_payload(dict(kind='ACCRUED_BALANCE_FX',version=1,instrumentId=line.instrument_id,currencyId=line.currency_id,
        convention='OPENING_STOCK_CLOSING_FX_MOVEMENTS',days=[asdict(day) for day in line.days],sourceRefs=line.source_refs))


def attach_balance_fx(period,result):
    lines=list(period.lines);detached=[]
    for source in result.lines:
        owner=next((i for i,line in enumerate(lines) if any(value.get('instrumentId')==str(source.instrument_id)
            for value in line.economic_evidence if value.get('kind') in ('MISSING_DAILY_ACCRUAL','MISSING_DAILY_ACCRUAL_FX','DAILY_ACCRUAL_NOT_APPLICABLE'))
            or any(value.get('payload',{}).get('instrumentId')==str(source.instrument_id) for value in line.economic_evidence if value.get('kind')=='DAILY_ACCRUAL')),None)
        if owner is None:detached.append(source);continue
        line=lines[owner];components=dict(line.economic_components)
        if any(day.amount is not None for day in source.days):components['CARRY']=source.amount
        lines[owner]=replace(line,economic_components=components,economic_evidence=line.economic_evidence+(balance_proof(source),))
    return replace(period,lines=tuple(lines)),tuple(detached)
