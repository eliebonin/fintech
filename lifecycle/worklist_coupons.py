"""Coupon notices and source inspection only; never infer payment or income.

Visibility follows the existing strategy bond notification selection. Position
context is trade-ledger relevance, not settled entitlement or a coupon amount.
"""
from collections import defaultdict
from datetime import datetime,time,timedelta,timezone
from sqlalchemy import select,func
from security_master_schema import models as m
from security_master_schema.evidence import canonical_payload,evidence_hash
from security_master_schema.reference_visibility import visible_clause
from security_master_schema.strategy_access import require_strategy_action
from positions.contracts import ProjectionRequest
from positions.repository import iter_ledger_facts
from positions.allocations import reconstruct_allocations
from trading.allocation_policy import load_allocation_policy
from trading.annotation_snapshots import load_trade_annotations
from . import coupon_tables as ct
from .worklist_repository import candidate_pairs


def latest_payments(tenant,strategies,now):
    return select(ct.payment,func.row_number().over(partition_by=ct.payment.c.logical_payment_id,order_by=ct.payment.c.revision.desc()).label('latest_rank')).where(ct.payment.c.tenant_id==tenant,ct.payment.c.strategy_id.in_(strategies),ct.payment.c.recorded_at<=now).subquery()


def reference_cutoff(flow,now):
    day=flow['record_date'] or (flow['ex_date']-timedelta(days=1) if flow['ex_date'] else flow['payment_date'])
    return min(datetime.combine(day,time.max,timezone.utc),now)


def coupon_events(c,tenant,actor,query,now,subscription,*,period_id=None):
    from .worklist import _quantities
    pairs=candidate_pairs(c,tenant,actor,query.model_copy(update={'eventType':'BOND_MATURITY'}),now,coupon_visibility=True)
    if not pairs:return []
    instruments={p['instrument_id'] for p in pairs};strategies={p['strategy_id'] for p in pairs}
    latest=select(ct.schedule.c.instrument_id,func.max(ct.schedule.c.revision).label('revision')).where(ct.schedule.c.tenant_id==tenant,ct.schedule.c.instrument_id.in_(instruments),ct.schedule.c.recorded_at<=now).group_by(ct.schedule.c.instrument_id).subquery()
    headers={r['instrument_id']:dict(r) for r in c.execute(select(ct.schedule).join(latest,(latest.c.instrument_id==ct.schedule.c.instrument_id)&(latest.c.revision==ct.schedule.c.revision)).where(ct.schedule.c.tenant_id==tenant)).mappings()}
    flows=defaultdict(list)
    flow_query=select(ct.cashflow).where(ct.cashflow.c.schedule_id.in_([h['schedule_id'] for h in headers.values()]),ct.cashflow.c.cashflow_type=='COUPON',ct.cashflow.c.payment_date.between(query.fromDate,query.toDate))
    if period_id is not None:flow_query=flow_query.where(ct.cashflow.c.cashflow_id==period_id)
    for row in c.execute(flow_query).mappings():flows[row['schedule_id']].append(dict(row))
    if not flows:return []
    periods={f['cashflow_id'] for rows in flows.values() for f in rows};payments=latest_payments(tenant,strategies,now)
    confirmed={(r['strategy_id'],r['period_id']):r['count'] for r in c.execute(select(payments.c.strategy_id,payments.c.period_id,func.count().label('count')).where(payments.c.latest_rank==1,payments.c.status=='CONFIRMED',payments.c.period_id.in_(periods)).group_by(payments.c.strategy_id,payments.c.period_id)).mappings()}
    subjects={i:i for i in instruments}
    subjects.update(dict(c.execute(select(m.listing.c.listing_node_id,m.listing.c.instrument_node_id).where(m.listing.c.instrument_node_id.in_(instruments),visible_clause(m.listing.c.listing_node_id,tenant))).all()))
    currencies=dict(c.execute(select(m.currency.c.currency_id,m.currency.c.currency_code)).all())
    current_terms=defaultdict(set)
    for instrument,term in c.execute(select(m.bond_terms.c.instrument_node_id,m.bond_terms.c.bond_terms_id).where(m.bond_terms.c.instrument_node_id.in_(instruments),m.bond_terms.c.is_current)):current_terms[instrument].add(term)
    by_strategy=defaultdict(list)
    for row in pairs:by_strategy[row['strategy_id']].append(row)
    events=[]
    for strategy,rows in by_strategy.items():
        eligible={r['instrument_id'] for r in rows};grouped=defaultdict(list);error=None
        try:
            request=ProjectionRequest(tenant,strategy,now,now)
            facts=tuple(iter_ledger_facts(c,request,subject_ids=[s for s,i in subjects.items() if i in eligible]))
            allocation=load_allocation_policy(c,tenant,strategy)
            annotations=load_trade_annotations(c,tenant,[f.trade_id for f in facts],allocation)
            parents={f.trade_id:subjects.get(f.booking.subject_id) for f in facts if f.booking}
            for fact in facts:
                if parents.get(fact.trade_id):grouped[parents[fact.trade_id]].append(fact)
        except (ValueError,LookupError) as exc:error=str(exc)
        for row in rows:
            identity=row['instrument_id'];header=headers.get(identity)
            if not header:continue
            for flow in flows.get(header['schedule_id'],[]):
                cutoff=reference_cutoff(flow,now);known=error is None;buckets=[];reasons=[]
                if error:reasons.append('Position context could not be assessed: '+error)
                else:
                    try:buckets=[b for b in reconstruct_allocations(tuple(grouped.get(identity,[])),ProjectionRequest(tenant,strategy,cutoff,now),allocation,annotations).buckets if b.closing_quantity]
                    except (ValueError,LookupError) as exc:known=False;reasons.append('Position context could not be assessed: '+str(exc))
                has_confirmation=bool(confirmed.get((strategy,flow['cashflow_id'])))
                if known and not buckets and not has_confirmation:continue
                blocked=not known or row['selected_tier']>subscription['maximumTier'] or row['reference_status']!='ACTIVE' or current_terms[identity]!={header['bond_terms_id']}
                if row['selected_tier']>subscription['maximumTier']:reasons.append('Bond lifecycle assistance exceeds the current subscription; review strategy settings.')
                if current_terms[identity]!={header['bond_terms_id']}:reasons.append('Schedule terms are no longer the single current term set; review the source.')
                if row['reference_status']!='ACTIVE':reasons.append('Held reference is inactive or retired; the schedule is retained source evidence.')
                state='BLOCKED' if blocked else 'CONFIRMATION_RECORDED' if has_confirmation else 'UPCOMING' if flow['payment_date']>now.date() else 'REVIEW_DUE'
                attention='ACTIONABLE' if state in ('BLOCKED','REVIEW_DUE') and flow['payment_date']<=now.date() else 'INFORMATION'
                reasons.extend(['Coupon schedule notice only. Review due does not mean unpaid.', 'Cash-flow booking, EoD cash representation and income treatment have not been assessed.'])
                events.append(dict(eventKey=evidence_hash(dict(tenantId=tenant,strategyId=strategy,eventType='BOND_COUPON',periodId=flow['cashflow_id'])),eventType='BOND_COUPON',instrumentType='BOND',strategyId=strategy,strategyName=row['strategy_name'],instrumentId=identity,instrumentName=row['instrument_name'],maturityDate=row['maturity_date'],eventDate=flow['payment_date'],couponPeriodId=flow['cashflow_id'],positionDate=cutoff.date(),status=state,attention=attention,quantities=_quantities(buckets,currencies) if known else [],remainingEntries=len(buckets) if known else None,selectedTier=row['selected_tier'],maximumTier=subscription['maximumTier'],processingMode='MANUAL',reasons=reasons,actionLabel='Inspect coupon',actionHref=f'/instruments/{identity}',positionAssessed=known))
    return events


def inspect_coupon(c,tenant,actor,strategy,period):
    from .worklist import list_worklist
    from .worklist_contracts import WorklistQuery
    from .recording_clock import recording_now
    require_strategy_action(c,tenant,actor,'LIFECYCLE_READ',strategy)
    row=c.execute(select(ct.cashflow,ct.schedule.c.instrument_id).join(ct.schedule).where(ct.cashflow.c.cashflow_id==period,ct.cashflow.c.cashflow_type=='COUPON',ct.schedule.c.tenant_id==tenant)).mappings().one_or_none()
    if row is None:raise LookupError('Coupon schedule unavailable')
    now=recording_now(c)
    result=list_worklist(c,tenant,actor,WorklistQuery(fromDate=row['payment_date'],toDate=row['payment_date'],strategyId=strategy,instrumentId=row['instrument_id'],eventType='BOND_COUPON'),now=now,coupon_period_id=period)
    event=next((r for r in result['items'] if r['couponPeriodId']==period),None)
    if event is None:raise LookupError('Coupon schedule or notification visibility changed; refresh Lifecycle')
    header=c.execute(select(ct.schedule).where(ct.schedule.c.schedule_id==row['schedule_id'],ct.schedule.c.tenant_id==tenant)).mappings().one()
    currencies=dict(c.execute(select(m.currency.c.currency_id,m.currency.c.currency_code)).all())
    latest=latest_payments(tenant,[strategy],now)
    confirmations=[]
    for receipt in c.execute(select(latest,ct.schedule.c.revision.label('schedule_revision')).join(ct.cashflow,ct.cashflow.c.cashflow_id==latest.c.period_id).join(ct.schedule,ct.schedule.c.schedule_id==ct.cashflow.c.schedule_id).where(latest.c.latest_rank==1,ct.schedule.c.tenant_id==tenant,ct.schedule.c.instrument_id==row['instrument_id'],ct.cashflow.c.cashflow_key==row['cashflow_key']).order_by(latest.c.payment_date.desc(),latest.c.payment_id)).mappings():
        confirmations.append(dict(paymentId=receipt['payment_id'],status=receipt['status'],paymentDate=receipt['payment_date'],amount=receipt['amount'],currency=currencies.get(receipt['currency_id'],'Unknown currency'),sourceReference=receipt['source_reference'],note=receipt['note'],recordedAt=receipt['recorded_at'],scheduleRevision=receipt['schedule_revision'],currentSchedule=receipt['period_id']==period))
    return canonical_payload(dict(eventKey=event['eventKey'],strategyId=strategy,instrumentId=row['instrument_id'],periodId=period,scheduleId=header['schedule_id'],scheduleRevision=header['revision'],cashflowKey=row['cashflow_key'],paymentDate=row['payment_date'],accrualStart=row['accrual_start'],accrualEnd=row['accrual_end'],recordDate=row['record_date'],exDate=row['ex_date'],currency=currencies.get(header['currency_id'],'Unknown currency'),couponRate=row['coupon_rate'],amountPer100=row['amount_per_100'],amountFormula=row['amount_formula'],sourceReference=header['source_reference'],sourceRecordedAt=header['recorded_at'],positionDate=event['positionDate'],positionAssessed=event['positionAssessed'],quantities=event['quantities'],confirmations=confirmations,financialTreatment='NOT_ASSESSED'))
