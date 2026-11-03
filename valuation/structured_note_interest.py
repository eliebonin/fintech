"""Optional assessed CLEAN-note interest stocks; never guess conditional coupons.

An assessed opening/closing bridge is an input, not an entitlement engine. DIRTY
and NONE quotations stay in the whole-note price bridge. Detached receivables
and generated lifecycle events are deliberately outside this adapter.
"""
from collections import defaultdict
from dataclasses import asdict,replace
from datetime import timedelta
from decimal import Decimal,localcontext
from uuid import UUID
from positions.reconstruction import reconstruct
from .accruals import read_accruals
from .accrued_balance import BalanceDay,BalanceFxDay,BalanceFxLine,optional_interest_fx
from .economics import evidence_hash,canonical_payload


def add_note_balance_fx(c,r,projection,result):
    from security_master_schema.market_data_resolver import persist_resolution_snapshot
    keys=defaultdict(set);bases=defaultdict(set)
    for bucket in projection.buckets:
        if bucket.key.product_basis!='STRUCTURED_PRODUCT':continue
        for f in projection.facts:
            if not f.booking or f.trade_id not in bucket.trade_ids:continue
            p=f.booking.product_evidence;instrument=UUID(p['instrumentId']);bases[instrument].add(p['notePriceType'])
            if p['notePriceType']=='CLEAN':keys[instrument].add(bucket.key)
    if not keys:return result
    start=r.opening_cutoff.date()+timedelta(days=1);end=r.closing_cutoff.date()
    rows={(row['instrument_id'],row['value_date']):row for row in read_accruals(c,r.tenant_id,r.strategy_id,start,end,r.information_cutoff)}
    groups=defaultdict(list);missing=list(result.coverage['missing']);warnings=list(result.coverage.get('warnings',[]))
    snapshots=list(result.snapshot_ids);assessed=result.coverage['suppliedCount'];fx_cache={};selections=defaultdict(list)
    day=start
    with localcontext() as ctx:
        ctx.prec=512
        while day<=end:
            end_cut=r.closing_cutoff.replace(year=day.year,month=day.month,day=day.day)
            daily=reconstruct(projection.facts,replace(projection.request,opening_cutoff=end_cut-timedelta(days=1),closing_cutoff=end_cut))
            for instrument,owner_keys in sorted(keys.items(),key=lambda p:str(p[0])):
                if not any(b.key in owner_keys for b in daily.buckets):continue
                row=rows.get((instrument,day));details=(row['payload'].get('inputs') or {}) if row else {}
                currency=row['currency_id'] if row else next(iter(owner_keys)).currency_id
                refs=dict(dailyInputs=[dict(inputId=str(row['input_id']),revision=row['revision'])] if row else [])
                reason='AMBIGUOUS_NOTE_INTEREST_ALLOCATION' if len(bases[instrument])>1 else None
                if not details or reason:
                    balance=BalanceDay(day,None,row['daily_earned_interest'] if row else None,None,None,None,'NOT_ASSESSED')
                    reason=reason or 'NOTE_ASSESSED_BALANCE_NOT_SUPPLIED';fx0=fx1=amount=None;proofs=[]
                else:
                    balance=BalanceDay(day,Decimal(details['openingBalance']),row['daily_earned_interest'],Decimal(details['balanceMovements']),
                        None,Decimal(details['closingBalance']),'STRUCTURED_NOTE_CLEAN_ASSESSED')
                    fx0=fx1=amount=None;proofs=[]
                    if balance.opening==0:amount=Decimal(0)
                    elif currency==r.reporting_currency_id:fx0=fx1=Decimal(1);amount=Decimal(0)
                    else:
                        values=[]
                        for target in (day-timedelta(days=1),day):
                            cache_key=(currency,target)
                            if cache_key not in fx_cache:fx_cache[cache_key]=optional_interest_fx(c,r,currency,r.reporting_currency_id,target)
                            values.append(fx_cache[cache_key])
                        if any(isinstance(v,str) for v in values):reason='ACCRUED_BALANCE_FX_UNAVAILABLE'
                        else:
                            fx0,fx1=(v.rate for v in values);amount=balance.opening*(fx1-fx0)
                            for v in values:
                                proofs.append(v.evidence)
                                if v.selection:
                                    snapshots.append(persist_resolution_snapshot(c,v.resolution_request,(v.selection,)))
                                    selections[(instrument,currency)].append(dict(asdict(v.selection),valuation_date=v.economic_date,input_role='FX',
                                        valuation_source_currency_id=v.source_currency_id,conversion=v.evidence))
                if reason:missing.append(dict(instrumentId=str(instrument),currencyId=str(currency),valueDate=day.isoformat(),reason=reason))
                else:assessed+=1
                groups[(instrument,currency)].append(BalanceFxDay(balance,fx0,fx1,amount,reason,refs,tuple(proofs)))
            day+=timedelta(days=1)
    lines=list(result.lines);catalog=list(result.source_proof.get('sources',[]))
    for (instrument,currency),days in groups.items():
        refs=dict(kind='STRUCTURED_NOTE_CLEAN_ASSESSED',instrumentId=str(instrument),
            dailyInputs=[ref for d in days for ref in d.sources['dailyInputs']],
            movements='ASSESSED_AGGREGATE_COUPON_AND_BOUGHT_SOLD_MOVEMENTS_NOT_SEPARATELY_CLASSIFIED')
        catalog.append(refs)
        selected={evidence_hash(s):s for s in selections[(instrument,currency)]}
        lines.append(BalanceFxLine(instrument,currency,tuple(days),tuple(selected.values()),refs))
    coverage=dict(status='PARTIAL' if missing and assessed else 'MISSING_INPUTS' if missing else 'INCLUDED' if assessed else 'NOT_ASSESSED',
        suppliedCount=assessed,missingCount=len(missing),missing=missing,warnings=warnings)
    return replace(result,lines=tuple(lines),coverage=coverage,source_proof=canonical_payload(result.source_proof|dict(sources=catalog)),
        snapshot_ids=tuple(dict.fromkeys(snapshots)))
