"""Coupon facts only: no trade, accrued-interest, cash or valuation mutations."""
from datetime import datetime,timezone
from hashlib import sha256
from uuid import uuid4
from sqlalchemy import select,func
from security_master_schema import models as m
from security_master_schema.strategy_access import require_strategy_action
from security_master_schema.reference_visibility import require_visible
from security_master_schema.reference_authority import require_reference_action
from security_master_schema.evidence import evidence_hash,canonical_payload
from . import coupon_tables as t
from .coupon_contracts import PaymentCreate


def _lock(c,key):
    c.execute(select(func.pg_advisory_xact_lock(int.from_bytes(sha256(key.encode()).digest()[:8],'big',signed=True))))


def _bond(c,tenant,instrument):
    node=require_visible(c,tenant,instrument)
    kind=c.scalar(select(m.instrument_type.c.type_code).join(m.instrument).where(m.instrument.c.instrument_node_id==instrument))
    if kind!='BOND': raise ValueError('A canonical bond is required')
    terms=c.execute(select(m.bond_terms).where(m.bond_terms.c.instrument_node_id==instrument,m.bond_terms.c.is_current)
        .order_by(m.bond_terms.c.sequence_no.desc()).limit(1)).mappings().one_or_none()
    if terms is None: raise ValueError('Sourced bond terms required')
    return node,terms


def _existing(c,table,tenant,key,digest,actor,operator):
    row=c.execute(select(table).where(table.c.tenant_id==tenant,table.c.request_key==key)).mappings().one_or_none()
    if row:
        if row['request_hash']!=digest: raise ValueError('Request key reused for different coupon facts')
        if row['actor_id']!=actor or row['real_operator_id']!=operator: raise PermissionError('Request key belongs to a different operator')
    return dict(row) if row else None


def _schedule_view(c,header):
    cashflows=[dict(r) for r in c.execute(select(t.cashflow).where(t.cashflow.c.schedule_id==header['schedule_id'])
        .order_by(t.cashflow.c.payment_date,t.cashflow.c.cashflow_type,t.cashflow.c.cashflow_key)).mappings()]
    currency=c.scalar(select(m.currency.c.currency_code).where(m.currency.c.currency_id==header['currency_id']))
    return dict(header)|dict(cashflows=cashflows,currencyCode=currency,amountBasis='PER_100_ORIGINAL_NOMINAL',
        coverage='EXPLICIT_SOURCED_ROWS_ONLY',scope='INFORMATIVE_CONTRACT_NOT_PAYMENT')


def save_schedule(c,tenant,actor,payload,key,*,operator=None):
    require_reference_action(c,tenant,actor,'REFERENCE_APPROVE');operator=operator or actor
    _,terms=_bond(c,tenant,payload.instrument_id)
    if terms['coupon_type']=='ZERO' and any(r.cashflow_type=='COUPON' for r in payload.cashflows):
        raise ValueError('Zero-coupon bonds permit principal cashflows only')
    approved=c.scalar(select(m.instrument_definition_version.c.instrument_definition_version_id).where(
        m.instrument_definition_version.c.instrument_node_id==payload.instrument_id,m.instrument_definition_version.c.is_current,
        m.instrument_definition_version.c.status=='APPROVED'))
    if not approved: raise ValueError('Approved bond definition required')
    digest=evidence_hash(payload.model_dump(by_alias=True))
    _lock(c,f'coupon-schedule:{tenant}:{payload.instrument_id}')
    _lock(c,f'coupon-schedule-key:{tenant}:{key}')
    old_key=_existing(c,t.schedule,tenant,key,digest,actor,operator)
    if old_key:return _schedule_view(c,old_key)
    old=c.execute(select(t.schedule).where(t.schedule.c.tenant_id==tenant,t.schedule.c.instrument_id==payload.instrument_id)
        .order_by(t.schedule.c.revision.desc()).limit(1)).mappings().one_or_none()
    revision=old['revision'] if old else 0
    if payload.expected_revision!=revision: raise ValueError('Schedule revision changed; reload before saving')
    if payload.calendar_id:
        from market_data.calendar_store import visible_calendar
        if visible_calendar(c,tenant,payload.calendar_id) is None: raise ValueError('Calendar unavailable')
    if payload.day_count_convention_id and not c.scalar(select(m.day_count_convention.c.day_count_convention_id).where(
        m.day_count_convention.c.day_count_convention_id==payload.day_count_convention_id)):
        raise ValueError('Known day-count convention required')
    header=c.execute(t.schedule.insert().values(tenant_id=tenant,instrument_id=payload.instrument_id,bond_terms_id=terms['bond_terms_id'],
        terms_snapshot=canonical_payload(dict(terms)|dict(instrumentDefinitionId=approved)),revision=revision+1,
        supersedes_schedule_id=old['schedule_id'] if old else None,currency_id=terms['issue_currency_id'],
        calendar_id=payload.calendar_id,day_count_convention_id=payload.day_count_convention_id,
        business_day_convention=payload.business_day_convention,source_reference=payload.source_reference,reason=payload.reason,
        request_key=key,request_hash=digest,actor_id=actor,real_operator_id=operator).returning(t.schedule)).mappings().one()
    c.execute(t.cashflow.insert(),[p.model_dump()|dict(schedule_id=header['schedule_id']) for p in payload.cashflows])
    return _schedule_view(c,header)


def read_schedule(c,tenant,actor,strategy,instrument,schedule_id=None):
    require_strategy_action(c,tenant,actor,'LIFECYCLE_READ',strategy)
    node,_=_bond(c,tenant,instrument)
    query=select(t.schedule).where(t.schedule.c.tenant_id==tenant,t.schedule.c.instrument_id==instrument)
    header=c.execute(query.where(t.schedule.c.schedule_id==schedule_id) if schedule_id else query.order_by(t.schedule.c.revision.desc()).limit(1)).mappings().one_or_none()
    if schedule_id and not header: raise LookupError('Schedule unavailable')
    history=[dict(r) for r in c.execute(select(t.schedule.c.schedule_id,t.schedule.c.revision,t.schedule.c.recorded_at,t.schedule.c.source_reference)
        .where(t.schedule.c.tenant_id==tenant,t.schedule.c.instrument_id==instrument).order_by(t.schedule.c.revision.desc()).limit(25)).mappings()]
    return dict(instrumentId=instrument,label=node['canonical_name'],schedule=_schedule_view(c,header) if header else None,history=history)


def _period(c,tenant,period_id):
    row=c.execute(select(t.cashflow,t.schedule.c.instrument_id,t.schedule.c.revision.label('schedule_revision'),t.schedule.c.currency_id.label('contract_currency_id'))
        .join(t.schedule).where(t.cashflow.c.cashflow_id==period_id,t.schedule.c.tenant_id==tenant)).mappings().one_or_none()
    if not row: raise LookupError('Coupon period unavailable')
    _bond(c,tenant,row['instrument_id'])
    if row['cashflow_type']!='COUPON': raise ValueError('Principal cashflows cannot be confirmed as coupons')
    return row


def _latest_payments(tenant,strategy):
    return select(t.payment,func.row_number().over(partition_by=t.payment.c.logical_payment_id,
        order_by=t.payment.c.revision.desc()).label('rank')).where(t.payment.c.tenant_id==tenant,t.payment.c.strategy_id==strategy).subquery()


def record_payment(c,tenant,actor,payload,key,*,operator=None,correction=False,reverse=False):
    action='TRADE_CORRECT' if correction or reverse else 'LIFECYCLE_BOOK'
    require_strategy_action(c,tenant,actor,action,payload.strategy_id);operator=operator or actor
    from valuation.storage import input_revision_lock
    input_revision_lock(c,tenant,payload.strategy_id)
    if correction and not payload.note.strip(): raise ValueError('A correction reason is required')
    period=_period(c,tenant,payload.period_id)
    if payload.payment_date>datetime.now(timezone.utc).date(): raise ValueError('Future dates are expected payments, not confirmed receipts')
    if not c.scalar(select(m.currency.c.currency_id).where(m.currency.c.currency_id==payload.currency_id,m.currency.c.status=='ACTIVE')):
        raise ValueError('Active payment currency required')
    if payload.cash_account_id and not c.scalar(select(m.cash_account.c.cash_account_id).where(
        m.cash_account.c.cash_account_id==payload.cash_account_id,m.cash_account.c.strategy_id==payload.strategy_id,m.cash_account.c.status=='ACTIVE')):
        raise ValueError('Cash account unavailable in this strategy')
    digest=evidence_hash(dict(payload=payload.model_dump(by_alias=True),correction=correction,reverse=reverse))
    _lock(c,f'coupon-payment:{tenant}:{payload.strategy_id}')
    _lock(c,f'coupon-payment-key:{tenant}:{key}')
    replay=_existing(c,t.payment,tenant,key,digest,actor,operator)
    if replay:return replay
    previous=None
    if correction or reverse:
        previous=c.execute(select(t.payment).where(t.payment.c.tenant_id==tenant,t.payment.c.strategy_id==payload.strategy_id,
            t.payment.c.payment_id==payload.supersedes_payment_id)).mappings().one_or_none()
        if not previous or previous['period_id']!=payload.period_id: raise LookupError('Payment revision unavailable')
        latest=c.scalar(select(func.max(t.payment.c.revision)).where(t.payment.c.logical_payment_id==previous['logical_payment_id']))
        if latest!=previous['revision']: raise ValueError('Payment revision changed; reload before correcting')
        if reverse and previous['status']=='REVERSED': raise ValueError('Payment already reversed')
    elif payload.supersedes_payment_id: raise ValueError('Use the correction action for a previous payment')
    logical=previous['logical_payment_id'] if previous else uuid4()
    latest=_latest_payments(tenant,payload.strategy_id)
    if not reverse and c.scalar(select(latest.c.payment_id).where(latest.c.rank==1,latest.c.status=='CONFIRMED',
        latest.c.period_id==payload.period_id,latest.c.payment_date==payload.payment_date,latest.c.amount==payload.amount,
        latest.c.currency_id==payload.currency_id,latest.c.source_reference==payload.source_reference,latest.c.logical_payment_id!=logical).limit(1)):
        raise ValueError('Matching payment already recorded; reuse or correct the existing receipt')
    return dict(c.execute(t.payment.insert().values(logical_payment_id=logical,tenant_id=tenant,strategy_id=payload.strategy_id,
        period_id=payload.period_id,revision=previous['revision']+1 if previous else 1,supersedes_payment_id=previous['payment_id'] if previous else None,
        status='REVERSED' if reverse else 'CONFIRMED',payment_date=payload.payment_date,amount=payload.amount,currency_id=payload.currency_id,
        cash_account_id=payload.cash_account_id,source_reference=payload.source_reference,note=payload.note,
        request_key=key,request_hash=digest,actor_id=actor,real_operator_id=operator).returning(t.payment)).mappings().one())


def reverse_payment(c,tenant,actor,strategy,payment_id,reason,key,*,operator=None):
    require_strategy_action(c,tenant,actor,'TRADE_CORRECT',strategy)
    prior=c.execute(select(t.payment).where(t.payment.c.tenant_id==tenant,t.payment.c.strategy_id==strategy,t.payment.c.payment_id==payment_id)).mappings().one_or_none()
    if not prior:raise LookupError('Payment unavailable')
    payload=PaymentCreate(strategyId=strategy,periodId=prior['period_id'],paymentDate=prior['payment_date'],amount=str(prior['amount']),
        currencyId=prior['currency_id'],cashAccountId=prior['cash_account_id'],sourceReference=prior['source_reference'],
        note=reason,supersedesPaymentId=payment_id,confirmPayment=True)
    return record_payment(c,tenant,actor,payload,key,operator=operator,reverse=True)


def payment_report(c,tenant,actor,strategy,start,end,limit,offset):
    require_strategy_action(c,tenant,actor,'LIFECYCLE_READ',strategy)
    if end<start or (end-start).days>3660 or not 1<=limit<=100 or not 0<=offset<=100000: raise ValueError('Use an ordered date window and bounded page')
    latest=_latest_payments(tenant,strategy)
    where=[latest.c.rank==1,latest.c.payment_date.between(start,end)]
    total=c.scalar(select(func.count()).select_from(latest).where(*where))
    rows=[dict(r) for r in c.execute(select(latest,t.cashflow.c.cashflow_key,t.schedule.c.instrument_id,t.schedule.c.revision.label('schedule_revision'))
        .join(t.cashflow,latest.c.period_id==t.cashflow.c.cashflow_id).join(t.schedule,t.cashflow.c.schedule_id==t.schedule.c.schedule_id)
        .where(*where).order_by(latest.c.payment_date.desc(),latest.c.payment_id).limit(limit).offset(offset)).mappings()]
    return rows,total


def payment_history(c,tenant,actor,strategy,payment_id):
    require_strategy_action(c,tenant,actor,'LIFECYCLE_READ',strategy)
    group=c.scalar(select(t.payment.c.logical_payment_id).where(t.payment.c.tenant_id==tenant,t.payment.c.strategy_id==strategy,t.payment.c.payment_id==payment_id))
    if not group: raise LookupError('Payment unavailable')
    return [dict(r) for r in c.execute(select(t.payment).where(t.payment.c.tenant_id==tenant,t.payment.c.strategy_id==strategy,
        t.payment.c.logical_payment_id==group).order_by(t.payment.c.revision)).mappings()]
