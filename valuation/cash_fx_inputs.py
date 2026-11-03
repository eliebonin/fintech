"""Scoped, information-cutoff cash snapshots and governed daily FX evidence."""
from dataclasses import asdict
from datetime import datetime,time,timedelta,timezone
from decimal import Decimal
from sqlalchemy import select,and_
from sqlalchemy.dialects.postgresql import distinct_on
from security_master_schema import models as m
from security_master_schema.market_data_resolver import persist_resolution_snapshot
from .cash_fx import CashFxDay,CashFxLine,CashFxResult,METHOD,cash_fx_amount
from .economics import canonical_payload,evidence_hash


def cash_source_state(c,request,asof):
    """Only supplied valuation-window inputs establish a cash scope.

    Old snapshots and account inventory do not establish a continuing obligation
    to upload that currency. The opening date is included because its balance
    supplies the first day's exposure.
    """
    s=m.strategy;b=m.cash_balance;a=m.cash_account
    if not c.scalar(select(s.c.strategy_id).where(s.c.strategy_id==request.strategy_id,s.c.tenant_id==request.tenant_id)):
        raise PermissionError('Strategy unavailable')
    base=and_(b.c.strategy_id==request.strategy_id,b.c.source_system_id=='TENANT_EOD',
        b.c.received_at_utc<=asof,b.c.balance_as_of_date>=request.opening_cutoff.date(),
        b.c.balance_as_of_date<=request.closing_cutoff.date())
    source=b.join(a,and_(b.c.cash_account_id==a.c.cash_account_id,b.c.strategy_id==a.c.strategy_id))
    # Reject malformed admitted EoD records rather than silently losing scopes.
    invalid=c.scalar(select(b.c.cash_balance_id).select_from(b.outerjoin(a,and_(b.c.cash_account_id==a.c.cash_account_id,
        b.c.strategy_id==a.c.strategy_id))).where(base,
        (a.c.cash_account_id.is_(None))|(a.c.custodian_organisation_id.is_(None))|(b.c.balance_type!='LEDGER')|(b.c.status!='ACTIVE')).limit(1))
    if invalid:raise ValueError('Admitted EoD cash snapshot has invalid account ownership, status or balance convention')
    invalid_currency=c.scalar(select(b.c.cash_balance_id).select_from(b.join(m.currency,
        b.c.currency_id==m.currency.c.currency_id)).where(base,m.currency.c.status!='ACTIVE').limit(1))
    if invalid_currency:raise ValueError('Admitted EoD cash snapshot requires an active currency')
    scopes=[dict(row) for row in c.execute(select(b.c.cash_account_id,b.c.currency_id)
        .select_from(source).where(base).distinct().order_by(b.c.cash_account_id,b.c.currency_id)).mappings()]
    rows=[dict(row) for row in c.execute(select(b).select_from(source).where(base)
        .ext(distinct_on(b.c.cash_account_id,b.c.currency_id,b.c.balance_as_of_date))
        .order_by(b.c.cash_account_id,b.c.currency_id,b.c.balance_as_of_date,b.c.revision.desc())).mappings()]
    payload=canonical_payload(dict(scopes=scopes,rows=rows))
    return scopes,rows,evidence_hash(payload)


def load_cash_fx(c,request,*,missing_inputs=None):
    scopes,rows,state_hash=cash_source_state(c,request,request.information_cutoff)
    latest={(r['cash_account_id'],r['currency_id'],r['balance_as_of_date']):r for r in rows}
    cache={};snapshot_ids=[];lines=[];missing=[];supplied=0;unpriced=[]
    from .fx import resolve_fx
    from .price_inputs import MissingPriceInput,retain_gap
    def rate(currency,day):
        key=(currency,day)
        if key not in cache:
            conversion=resolve_fx(c,request,currency,request.reporting_currency_id,day,allow_partial=missing_inputs is not None)
            if conversion.selection:
                target=datetime.fromisoformat(conversion.selection.pricing_evidence['pricingTargetUtc'])
                if target>datetime.combine(day,time.max,timezone.utc):raise ValueError('Cash FX pricing target is later than its daily boundary')
                snapshot_ids.append(persist_resolution_snapshot(c,conversion.resolution_request,(conversion.selection,)))
            cache[key]=conversion
        return cache[key]
    for scope in scopes:
        account,currency=scope['cash_account_id'],scope['currency_id']
        days=[];selections={};omitted=[];input_keys=set();day=request.opening_cutoff.date()+timedelta(days=1)
        while day<=request.closing_cutoff.date():
            opening=latest.get((account,currency,day-timedelta(days=1)));closing=latest.get((account,currency,day))
            # No snapshot at either boundary means no supplied daily scope,
            # not a perpetual missing-data obligation inferred from history.
            if opening is None and closing is None:
                day+=timedelta(days=1);continue
            if opening is None or closing is None:
                item=dict(accountId=str(account),currencyId=str(currency),valueDate=day.isoformat(),
                    missingOpening=opening is None,missingClosing=closing is None)
                omitted.append(item);missing.append(item);day+=timedelta(days=1);continue
            # Missing cash never blocks. Supplied EoD pairs cannot be used at
            # an intraday boundary that precedes their economic date end.
            if any(cut.time()!=time.max for cut in (request.opening_cutoff,request.closing_cutoff)):
                raise ValueError('Supplied EoD cash requires daily EoD valuation boundaries')
            if any(row['balance_as_of_datetime_utc']!=datetime.combine(row['balance_as_of_date'],time.max,timezone.utc) for row in (opening,closing)):
                raise ValueError('Cash snapshot is not an exact-date TENANT_EOD boundary')
            conversions=[]
            if currency==request.reporting_currency_id:
                first=last=Decimal(1);mode='IDENTITY'
            elif opening['amount']==0:
                first=last=None;mode='ZERO_OPENING_EXPOSURE'
            else:
                rates=[]
                for pricing_day in (day-timedelta(days=1),day):
                    try:
                        conversion=rate(currency,pricing_day);rates.append(conversion)
                        if conversion.selection:
                            selections[(currency,pricing_day)]=canonical_payload(dict(asdict(conversion.selection),
                                input_role='CASH_FX',valuation_date=pricing_day,valuation_source_currency_id=currency,conversion=conversion.evidence))
                    except MissingPriceInput as unavailable:
                        gap=retain_gap(missing_inputs,unavailable,[],role='CASH_FX')
                        input_keys.add(gap['inputKey'])
                if len(rates)!=2:day+=timedelta(days=1);continue
                before,after=rates
                first,last=before.rate,after.rate;mode='POLICY_FX';conversions=[before,after]
            for fx in conversions:
                if fx.selection:
                    selections[(currency,fx.economic_date)]=canonical_payload(dict(asdict(fx.selection),
                        input_role='CASH_FX',valuation_date=fx.economic_date,valuation_source_currency_id=currency,conversion=fx.evidence))
            amount=cash_fx_amount(opening['amount'],first,last)
            days.append(CashFxDay(day,canonical_payload(opening),canonical_payload(closing),first,last,amount,mode,
                tuple(fx.evidence for fx in conversions)))
            supplied+=1;day+=timedelta(days=1)
        if input_keys:
            unpriced.append(canonical_payload(dict(accountId=account,currencyId=currency,pnl=None,status='UNPRICED',inputKeys=sorted(input_keys),
                snapshots=[row for row in rows if row['cash_account_id']==account and row['currency_id']==currency],selections=list(selections.values()))))
        elif days:lines.append(CashFxLine(account,currency,tuple(days),tuple(selections.values()),tuple(omitted)))
    status=('PARTIAL' if lines else 'MISSING_INPUTS') if missing or unpriced else 'NOT_ASSESSED' if not scopes else 'INCLUDED'
    coverage=canonical_payload(dict(version=1,method=METHOD,convention='OPENING_BALANCE_EOD_MOVEMENTS',
        status=status,knownScopeCount=len(scopes),suppliedCount=supplied,missingCount=len(missing),missing=missing,
        missingFxCount=len({key for row in unpriced for key in row['inputKeys']}),unpricedCashAccounts=unpriced,
        scopes=[dict(accountId=s['cash_account_id'],currencyId=s['currency_id']) for s in scopes],
        sourceState=dict(version=1,inputHash=state_hash,
            informationCutoff=request.information_cutoff,openingDate=request.opening_cutoff.date(),closingDate=request.closing_cutoff.date())))
    return CashFxResult(tuple(lines),coverage,tuple(snapshot_ids))


def assert_cash_source_current(c,tenant,batch):
    """Snapshot correction or newly supplied missing data requires recalculation."""
    from types import SimpleNamespace
    summary=batch.get('summary') or {};coverage=summary.get('cashCoverage')
    if not coverage or not coverage.get('sourceState'):raise ValueError('Cash source evidence is missing; recalculate')
    source=coverage['sourceState']
    r=SimpleNamespace(tenant_id=tenant,strategy_id=batch['strategy_id'],
        opening_cutoff=datetime.fromisoformat(summary['request']['opening_cutoff']),
        closing_cutoff=datetime.fromisoformat(summary['request']['closing_cutoff']))
    current=cash_source_state(c,r,datetime.now(timezone.utc))[-1]
    if current!=source['inputHash']:raise ValueError('Cash snapshots or coverage changed; recalculate before review or publication')
