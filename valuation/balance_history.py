"""Explicit local-stock maintenance; valuation reads exact-date retained revisions."""
from dataclasses import asdict
from datetime import date,datetime,time,timedelta,timezone
from decimal import Decimal
from types import SimpleNamespace
from sqlalchemy import select,func,or_,union_all
from security_master_schema import models as m
from security_master_schema.strategy_access import require_strategy_action
from security_master_schema.tenant_workspace import TenantActionForbidden
from security_master_schema.tenancy import assert_tenant_owns_strategy
from security_master_schema.reference_visibility import visible_clause
from security_master_schema.access_management import audit
from . import balance_history_tables as t
from uuid import UUID
from .accrued_balance import BalanceDay
from .economics import canonical_payload,evidence_hash

METHOD='maintained-local-accrued-balance-v1'


def signature_matches(proof,signature):
    return all(proof.get(key)==value for key,value in signature.items())


def authorize(c,tenant,actor,strategy,write=False):
    if not write:return require_strategy_action(c,tenant,actor,'VALUATION_READ',strategy)
    for action in ('VALUATION_RUN','VALUATION_REVIEW'):
        try:return require_strategy_action(c,tenant,actor,action,strategy)
        except TenantActionForbidden:pass
    raise TenantActionForbidden('Strategy valuation input authority required')


def source_signature(c,tenant,strategy,end,info):
    from .accrued_balance_health import _counts
    from .tables import ledger_change
    daily,coupons=c.execute(select(*_counts(tenant,strategy,end,info))).one()
    anchors=c.scalar(select(func.count()).select_from(t.balance_input).where(t.balance_input.c.tenant_id==tenant,
        t.balance_input.c.strategy_id==strategy,t.balance_input.c.value_date<=end,t.balance_input.c.recorded_at<=info))
    ledger=c.scalar(select(func.max(ledger_change.c.revision)).where(ledger_change.c.tenant_id==tenant,
        ledger_change.c.strategy_id==strategy,ledger_change.c.economic_from<=end,ledger_change.c.recorded_at<=info)) or 0
    return dict(version=1,dailyRevisionCount=daily,couponRevisionCount=coupons,balanceInputRevisionCount=anchors,ledgerRevision=ledger)


def read_inputs(c,tenant,strategy,start,end,info):
    assert_tenant_owns_strategy(c,tenant,strategy)
    a=t.balance_input
    ranked=select(a,func.row_number().over(partition_by=[a.c.instrument_id,a.c.currency_id,a.c.value_date],order_by=a.c.revision.desc()).label('rank')).where(
        a.c.tenant_id==tenant,a.c.strategy_id==strategy,a.c.value_date.between(start,end),a.c.recorded_at<=info).subquery()
    return [dict(row) for row in c.execute(select(ranked).where(ranked.c.rank==1).order_by(ranked.c.value_date,ranked.c.instrument_id)).mappings()]


def record_balance_input(c,tenant,actor,payload,key):
    authorize(c,tenant,actor,payload.strategy_id,True)
    if not c.scalar(select(m.financial_reference_node.c.reference_node_id).where(m.financial_reference_node.c.reference_node_id==payload.instrument_id,
        visible_clause(m.financial_reference_node.c.reference_node_id,tenant))):raise LookupError('Visible historical bond reference required')
    instrument=c.execute(select(m.instrument.c.base_currency_id,m.instrument_type.c.type_code).join(m.instrument_type).where(m.instrument.c.instrument_node_id==payload.instrument_id)).mappings().one()
    if instrument['type_code']!='BOND' or instrument['base_currency_id']!=payload.currency_id:raise ValueError('An assessed bond balance uses its canonical local monetary currency')
    now=datetime.now(timezone.utc)
    if payload.value_date>now.date():raise ValueError('Future balance dates are not supported')
    from .storage import input_revision_lock
    input_revision_lock(c,tenant,payload.strategy_id)
    values=payload.model_dump();digest=evidence_hash(values)
    a=t.balance_input
    prior=c.execute(select(a).where(a.c.tenant_id==tenant,a.c.submission_key==key)).mappings().one_or_none()
    if prior:
        if prior['request_hash']!=digest:raise ValueError('Balance input key reused for different content')
        return dict(prior)
    current=c.execute(select(a).where(a.c.tenant_id==tenant,a.c.strategy_id==payload.strategy_id,a.c.instrument_id==payload.instrument_id,
        a.c.currency_id==payload.currency_id,a.c.value_date==payload.value_date).order_by(a.c.revision.desc()).limit(1)).mappings().one_or_none()
    if payload.supersedes_input_id!=(current['input_id'] if current else None):raise ValueError('Balance revision changed; select the current input version')
    row=c.execute(a.insert().values(tenant_id=tenant,recorded_by=actor,recorded_at=now,revision=current['revision']+1 if current else 1,
        submission_key=key,request_hash=digest,**values).returning(a)).mappings().one()
    audit(c,actor,tenant,'ACCRUED_BALANCE_INPUT_RECORDED',dict(inputId=str(row['input_id']),strategyId=str(payload.strategy_id),instrumentId=str(payload.instrument_id),revision=row['revision'],status=row['status']))
    return dict(row)


def refresh_history(c,tenant,actor,payload,key):
    authorize(c,tenant,actor,payload.strategy_id,True)
    now=datetime.now(timezone.utc);info=payload.information_cutoff or now
    if payload.to_date>now.date() or info>now:raise ValueError('Balance maintenance cannot use future dates or future information')
    from .storage import input_revision_lock
    input_revision_lock(c,tenant,payload.strategy_id)
    digest=evidence_hash(payload.model_dump());b=t.history_build
    prior=c.execute(select(b).where(b.c.tenant_id==tenant,b.c.submission_key==key)).mappings().one_or_none()
    if prior:
        if prior['request_hash']!=digest:raise ValueError('Balance update key reused for different content')
        return dict(prior)|dict(replayed=True)
    signature=source_signature(c,tenant,payload.strategy_id,payload.to_date,info)
    recent=c.execute(select(b).where(b.c.tenant_id==tenant,b.c.strategy_id==payload.strategy_id,b.c.from_date==payload.from_date,
        b.c.to_date==payload.to_date,b.c.information_cutoff<=info,b.c.method==METHOD).order_by(b.c.information_cutoff.desc(),b.c.recorded_at.desc()).limit(1)).mappings().one_or_none()
    if recent and signature_matches(recent['source_proof'],signature):
        reused=str(recent['source_proof'].get('reusedBuildId',recent['build_id']))
        row=c.execute(b.insert().values(tenant_id=tenant,strategy_id=payload.strategy_id,from_date=payload.from_date,to_date=payload.to_date,
            information_cutoff=info,source_proof=dict(signature,reusedBuildId=reused),method=METHOD,recorded_by=actor,recorded_at=now,
            submission_key=key,request_hash=digest).returning(b)).mappings().one()
        return dict(row)|dict(rowCount=0,reusedBuildId=reused,replayed=False)
    from positions.contracts import ProjectionRequest
    from positions.reconstruction import reconstruct
    from positions.repository import iter_ledger_facts
    close=datetime.combine(payload.to_date,time.max,timezone.utc)
    opening=datetime.combine(payload.from_date-timedelta(days=1),time.max,timezone.utc)
    request=ProjectionRequest(tenant,payload.strategy_id,close,info,opening,mode='PERIOD')
    bond_ids=select(m.instrument.c.instrument_node_id).join(m.instrument_type).where(m.instrument_type.c.type_code=='BOND')
    subjects=union_all(bond_ids,select(m.listing.c.listing_node_id).where(m.listing.c.instrument_node_id.in_(bond_ids)))
    projection=reconstruct(tuple(iter_ledger_facts(c,request,subject_ids=subjects)),request)
    from .accrued_balance_inputs import reconstruct_local_balances
    local=SimpleNamespace(tenant_id=tenant,strategy_id=payload.strategy_id,closing_cutoff=close,opening_cutoff=opening,information_cutoff=info)
    supplied=read_inputs(c,tenant,payload.strategy_id,date.min,payload.to_date,info)
    checkpoints=_verified_checkpoints(c,tenant,payload.strategy_id,payload.from_date,info)
    lines,missing=reconstruct_local_balances(c,local,projection,balance_inputs=supplied,history_checkpoints=checkpoints)
    proof=signature
    proof['missingScopes']=list(missing)
    proof['bondSources']=canonical_payload([dict(instrumentId=line.instrument_id,currencyId=line.currency_id,sourceRefs=line.source_refs) for line in lines])
    row=c.execute(b.insert().values(tenant_id=tenant,strategy_id=payload.strategy_id,from_date=payload.from_date,to_date=payload.to_date,
        information_cutoff=info,source_proof=proof,method=METHOD,recorded_by=actor,recorded_at=now,
        submission_key=key,request_hash=digest).returning(b)).mappings().one()
    days=[]
    for line in lines:
        for day in line.days:
            days.append(dict(build_id=row['build_id'],tenant_id=tenant,strategy_id=payload.strategy_id,instrument_id=line.instrument_id,
                currency_id=line.currency_id,value_date=day.value_date,opening_balance=day.opening,daily_earned=day.daily_earned,
                trade_movements=day.trade_movements,coupon_paid=day.coupon_paid,closing_balance=day.closing,basis=day.basis,
                evidence=canonical_payload(dict(warnings=day.warnings,sources=line.day_sources.get(day.value_date,{}),
                    anchorDate=line.source_refs.get('anchorDate'),openingBasis=line.source_refs.get('openingBasis')))))
    for offset in range(0,len(days),1000):c.execute(t.history_day.insert(),days[offset:offset+1000])
    audit(c,actor,tenant,'ACCRUED_BALANCE_HISTORY_UPDATED',dict(buildId=str(row['build_id']),strategyId=str(payload.strategy_id),
        fromDate=payload.from_date.isoformat(),toDate=payload.to_date.isoformat(),rowCount=len(days),missingClosingCount=sum(d['closing_balance'] is None for d in days)))
    return dict(row)|dict(rowCount=len(days),replayed=False)


def _history_query(tenant,strategy,start,end,info,*,instrument_id=None,compact_sources=False):
    h=t.history_day;b=t.history_build
    proof=b.c.source_proof.op('-')('bondSources').label('source_proof') if compact_sources else b.c.source_proof
    ranked=select(h,b.c.recorded_at,b.c.information_cutoff,proof,b.c.to_date,
        func.row_number().over(partition_by=[h.c.instrument_id,h.c.currency_id,h.c.value_date],order_by=[b.c.information_cutoff.desc(),b.c.recorded_at.desc(),b.c.build_id.desc()]).label('rank')).join(b,
        (h.c.build_id==b.c.build_id)&(h.c.tenant_id==b.c.tenant_id)&(h.c.strategy_id==b.c.strategy_id)).where(
        h.c.tenant_id==tenant,h.c.strategy_id==strategy,h.c.value_date.between(start,end),b.c.information_cutoff<=info,
        visible_clause(h.c.instrument_id,tenant))
    if instrument_id is not None:ranked=ranked.where(h.c.instrument_id==instrument_id)
    ranked=ranked.subquery()
    return select(ranked).where(ranked.c.rank==1)


def _history_rows(c,tenant,strategy,start,end,info):
    return [dict(row) for row in c.execute(_history_query(tenant,strategy,start,end,info)).mappings()]


def _verified_checkpoints(c,tenant,strategy,start,info):
    """Reuse a derived closing stock only while its original source set agrees."""
    h=t.history_day;b=t.history_build
    latest=select(h,b.c.source_proof,b.c.to_date,func.row_number().over(
        partition_by=[h.c.instrument_id,h.c.currency_id],order_by=[h.c.value_date.desc(),
            b.c.information_cutoff.desc(),b.c.recorded_at.desc(),b.c.build_id.desc()]).label('rank')).join(b,h.c.build_id==b.c.build_id).where(
        h.c.tenant_id==tenant,h.c.strategy_id==strategy,h.c.value_date<start,
        b.c.information_cutoff<=info,visible_clause(h.c.instrument_id,tenant)).subquery()
    rows=c.execute(select(latest).where(latest.c.rank==1,latest.c.closing_balance.is_not(None))).mappings()
    verified=[];states={}
    for row in rows:
        build=row['build_id']
        if build not in states:states[build]=signature_matches(row['source_proof'],source_signature(c,tenant,strategy,row['to_date'],info))
        if states[build]:verified.append(dict(row))
    return tuple(verified)


def stored_balance_day(day,current,previous):
    if current:
        return BalanceDay(day,current['opening_balance'],current['daily_earned'],current['trade_movements'],current['coupon_paid'],current['closing_balance'],current['basis'],tuple(current['evidence'].get('warnings',())))
    opening=previous['closing_balance'] if previous and previous['value_date']==day-timedelta(days=1) else None
    return BalanceDay(day,opening,None,None,None,None,'MAINTAINED_HISTORY',('CLOSING_BALANCE_NOT_UPDATED',) if opening is not None else ('ACCRUED_BALANCE_HISTORY_NOT_UPDATED',))


def _last_assessed_stocks(c,tenant,strategy,end,info):
    """An uncollected receivable outlives investment exposure and exact-day rows."""
    h=t.history_day;b=t.history_build
    latest=select(h.c.instrument_id,h.c.currency_id,h.c.closing_balance,func.row_number().over(
        partition_by=[h.c.instrument_id,h.c.currency_id],order_by=[h.c.value_date.desc(),b.c.information_cutoff.desc(),b.c.recorded_at.desc(),b.c.build_id.desc()]).label('rank')).join(b,h.c.build_id==b.c.build_id).where(
        h.c.tenant_id==tenant,h.c.strategy_id==strategy,h.c.value_date<=end,h.c.closing_balance.is_not(None),
        b.c.information_cutoff<=info,visible_clause(h.c.instrument_id,tenant)).subquery()
    return c.execute(select(latest).where(latest.c.rank==1,latest.c.closing_balance!=0)).mappings().all()


def read_balance_lines(c,r,projection):
    from .accrued_balance_inputs import LocalBalanceLine,_facts
    start=r.opening_cutoff.date()+timedelta(days=1);end=r.closing_cutoff.date()
    rows=_history_rows(c,r.tenant_id,r.strategy_id,start-timedelta(days=1),end,r.information_cutoff)
    lookup={};freshness={}
    for row in rows:
        build=row['build_id']
        if build not in freshness:
            freshness[build]=signature_matches(row['source_proof'],source_signature(c,r.tenant_id,r.strategy_id,row['to_date'],r.information_cutoff))
        lookup[(row['instrument_id'],row['currency_id'],row['value_date'])]=row
    active={b.key.subject_id for b in projection.buckets if b.key.product_basis=='BOND'}
    facts=_facts(projection);expected={}
    for fact in facts:
        booking=fact.booking;instrument=UUID(booking.product_evidence['instrumentId'])
        if booking.product_evidence.get('couponType')!='ZERO' and booking.subject_id in active:expected[instrument]=booking.currency_id
    for row in _last_assessed_stocks(c,r.tenant_id,r.strategy_id,end,r.information_cutoff):expected[row['instrument_id']]=row['currency_id']
    for row in rows:
        if row['opening_balance'] not in (None,0) or row['closing_balance'] not in (None,0) or row['instrument_id'] in expected:
            expected[row['instrument_id']]=row['currency_id']
    lines=[]
    for instrument,currency in sorted(expected.items(),key=lambda item:str(item[0])):
        days=[];sources={};refs=[];day=start
        while day<=end:
            current=lookup.get((instrument,currency,day));previous=lookup.get((instrument,currency,day-timedelta(days=1)))
            valid_current=current if current and freshness[current['build_id']] else None
            valid_previous=previous if previous and freshness[previous['build_id']] else None
            if (current or previous) and not(valid_current or valid_previous):
                value=BalanceDay(day,None,None,None,None,None,'STALE_HISTORY',('STALE_ACCRUED_BALANCE_HISTORY',))
            else:value=stored_balance_day(day,valid_current,valid_previous)
            days.append(value)
            for row in (current,previous):
                if row:
                    ref=dict(historyId=str(row['history_id']),buildId=str(row['build_id']),valueDate=row['value_date'].isoformat())
                    refs.append(ref);sources.setdefault(day,{}).setdefault('balanceHistory',[]).append(ref)
            day+=timedelta(days=1)
        lines.append(LocalBalanceLine(instrument,currency,tuple(days),dict(method=METHOD,balanceHistory=refs),sources))
    return tuple(lines),()


def list_history(c,tenant,actor,strategy,start,end,info,*,limit=None,offset=0,instrument_id=None,compact_sources=False):
    authorize(c,tenant,actor,strategy)
    statement=_history_query(tenant,strategy,start,end,info,instrument_id=instrument_id,compact_sources=compact_sources)
    table=statement.subquery()
    total=c.scalar(select(func.count()).select_from(table)) if limit is not None else None
    statement=select(table).order_by(table.c.value_date,table.c.instrument_id,table.c.currency_id)
    if limit is not None:statement=statement.limit(limit).offset(offset)
    rows=[dict(row) for row in c.execute(statement).mappings()];states={}
    for row in rows:
        key=row['build_id']
        if key not in states:states[key]=signature_matches(row['source_proof'],source_signature(c,tenant,strategy,row['to_date'],info))
        row['source_status']='CURRENT' if states[key] else 'STALE'
    return (rows,total) if limit is not None else rows
