"""Two-stage, strategy/day Ops review. Financial changes occur only at validation."""
from datetime import date,datetime,time,timedelta,timezone
from decimal import Decimal,localcontext
from types import SimpleNamespace
from uuid import UUID
from sqlalchemy import select,func
from security_master_schema import models as m
from security_master_schema.reference_visibility import visible_clause
from security_master_schema.access_management import audit
from security_master_schema.strategy_access import require_strategy_action
from . import interest_review_tables as t
from . import balance_history as balances
from .accruals import read_accruals,record_accrual,accrual_amounts
from .economics import canonical_payload,evidence_hash
from .interest_review_model import benchmark,covered_days,review_warning


def _latest(c,tenant,strategy,day,stage):
    return c.execute(select(t.review).where(t.review.c.tenant_id==tenant,t.review.c.strategy_id==strategy,
        t.review.c.value_date==day,t.review.c.stage==stage).order_by(t.review.c.revision.desc()).limit(1)).mappings().one_or_none()


def _items(c,review):
    return [dict(r) for r in c.execute(select(t.item).where(t.item.c.review_id==review['review_id'])).mappings()] if review else []


def _sources(c,tenant,strategy,day):
    from positions.contracts import ProjectionRequest
    from positions.repository import iter_ledger_facts
    from positions.reconstruction import reconstruct
    now=datetime.now(timezone.utc)
    if day>=date.max or day<=date.min+timedelta(days=40) or day>now.date():raise ValueError('Choose a past or current value date with preceding benchmark history')
    close=datetime.combine(day,time.max,timezone.utc);opening=close-timedelta(days=1)
    request=ProjectionRequest(tenant,strategy,close,now,opening,mode='PERIOD')
    bond_ids=select(m.instrument.c.instrument_node_id).join(m.instrument_type).where(m.instrument_type.c.type_code=='BOND')
    from sqlalchemy import union_all
    subjects=union_all(bond_ids,select(m.listing.c.listing_node_id).where(m.listing.c.instrument_node_id.in_(bond_ids)))
    projection=reconstruct(tuple(iter_ledger_facts(c,request,subject_ids=subjects)),request)
    inputs=read_accruals(c,tenant,strategy,day-timedelta(days=40),day,now)
    nodes={row['instrument_id'] for row in inputs if row['value_date']==day}
    relevant={trade for bucket in projection.buckets for trade in bucket.trade_ids}
    for fact in projection.facts:
        if fact.trade_id in relevant and fact.booking and fact.booking.product_evidence:
            key=fact.booking.product_evidence.get('instrumentId')
            if key and fact.booking.product_evidence.get('couponType')!='ZERO':nodes.add(UUID(str(key)))
    instruments=[dict(row) for row in c.execute(select(m.instrument.c.instrument_node_id,m.instrument.c.base_currency_id,
        m.financial_reference_node.c.canonical_name,m.currency.c.currency_code).join(m.instrument_type).join(m.financial_reference_node,
        m.financial_reference_node.c.reference_node_id==m.instrument.c.instrument_node_id).join(m.currency,m.currency.c.currency_id==m.instrument.c.base_currency_id)
        .where(m.instrument_type.c.type_code=='BOND',m.instrument.c.instrument_node_id.in_(nodes),visible_clause(m.instrument.c.instrument_node_id,tenant))
        .order_by(m.financial_reference_node.c.canonical_name,m.instrument.c.instrument_node_id)).mappings()]
    allowed={row['instrument_node_id'] for row in instruments};inputs=[row for row in inputs if row['instrument_id'] in allowed]
    from lifecycle import coupon_tables as ct
    latest=select(ct.schedule.c.schedule_id,ct.schedule.c.instrument_id,func.row_number().over(partition_by=ct.schedule.c.instrument_id,
        order_by=ct.schedule.c.revision.desc()).label('rank')).where(ct.schedule.c.tenant_id==tenant,ct.schedule.c.instrument_id.in_(allowed)).subquery()
    schedules=[dict(row) for row in c.execute(select(ct.cashflow,latest.c.instrument_id).join(latest,ct.cashflow.c.schedule_id==latest.c.schedule_id)
        .where(latest.c.rank==1,ct.cashflow.c.payment_date==day)).mappings()]
    signature=balances.source_signature(c,tenant,strategy,day,now)
    # A stock decision must not invalidate its own daily prerequisite. Prior
    # balance versions are pinned separately by the balance-stage proof below.
    signature.pop('balanceInputRevisionCount',None)
    prior_review_ids=list(c.scalars(select(t.review.c.review_id).where(t.review.c.tenant_id==tenant,t.review.c.strategy_id==strategy,
        t.review.c.stage=='DAILY',t.review.c.state=='VALIDATED',t.review.c.value_date<day,t.review.c.value_date>=day-timedelta(days=40)).order_by(t.review.c.review_id)))
    proof=dict(sources=signature,projection=[str(f.event_id) for f in projection.facts],priorCoverageReviews=list(map(str,prior_review_ids)),
        inputs=[str(row['input_id']) for row in inputs],schedules=[str(row['cashflow_id']) for row in schedules],
        population=[str(row['instrument_node_id']) for row in instruments])
    return now,projection,inputs,instruments,schedules,proof


def review_view(c,tenant,actor,strategy,day,stage):
    balances.authorize(c,tenant,actor,strategy)
    if stage not in ('DAILY','BALANCE'):raise ValueError('Unknown review stage')
    now,projection,inputs,instruments,schedules,proof=_sources(c,tenant,strategy,day)
    current=_latest(c,tenant,strategy,day,stage);daily_review=_latest(c,tenant,strategy,day,'DAILY')
    daily_hash=evidence_hash(proof)
    daily_valid=bool(daily_review and daily_review['state']=='VALIDATED' and daily_review['source_hash']==daily_hash)
    if stage=='BALANCE' and not daily_valid:raise ValueError('Validate the current daily accruals before reviewing balances')
    current_inputs={row['instrument_id']:row for row in inputs if row['value_date']==day}
    prior_reviews=c.execute(select(t.item.c.instrument_id,t.item.c.value_date,t.item.c.covered_days,t.item.c.source_input_id,t.review.c.revision).join(t.review,t.item.c.review_id==t.review.c.review_id)
        .where(t.review.c.tenant_id==tenant,t.review.c.strategy_id==strategy,t.review.c.stage=='DAILY',t.review.c.state=='VALIDATED',
            t.review.c.value_date<day,t.review.c.value_date>=day-timedelta(days=40)).order_by(t.review.c.revision)).all()
    current_ids={(row['instrument_id'],row['value_date']):row['input_id'] for row in inputs}
    coverage={(row.instrument_id,row.value_date):row.covered_days for row in prior_reviews if current_ids.get((row.instrument_id,row.value_date))==row.source_input_id}
    local={}
    current_stocks={}
    if stage=='BALANCE':
        from .accrued_balance_inputs import reconstruct_local_balances
        r=SimpleNamespace(tenant_id=tenant,strategy_id=strategy,opening_cutoff=projection.request.opening_cutoff,
            closing_cutoff=projection.request.closing_cutoff,information_cutoff=now)
        anchors=balances.read_inputs(c,tenant,strategy,date.min,day-timedelta(days=1),now)
        checkpoints=balances._verified_checkpoints(c,tenant,strategy,day,now)
        current_stocks={(row['instrument_id'],row['currency_id']):row for row in balances.read_inputs(c,tenant,strategy,day,day,now) if row['status']=='ACTIVE'}
        lines,missing=reconstruct_local_balances(c,r,projection,balance_inputs=anchors,history_checkpoints=checkpoints)
        for line in lines:
            for value in line.days:
                if value.value_date==day:local[(line.instrument_id,line.currency_id)]=(value,line.source_refs)
        proof.update(dailyReviewId=str(daily_review['review_id']),anchors=[str(row['input_id']) for row in anchors],
            checkpoints=[str(row['history_id']) for row in checkpoints],currentStocks=[str(row['input_id']) for row in current_stocks.values()],missing=missing)
    source_hash=evidence_hash(proof)
    retained_items=_items(c,current)
    saved={(row['instrument_id'],row['currency_id']):row for row in retained_items} if current and current['source_hash']==source_hash else {}
    rows=[]
    for instrument in instruments:
        identity=instrument['instrument_node_id'];currency=instrument['base_currency_id'];source=current_inputs.get(identity)
        foreign=bool(source and source['currency_id']!=currency)
        history=[row for row in inputs if row['instrument_id']==identity and row['currency_id']==currency and row['value_date']<day]
        dates={row['value_date'] for row in inputs if row['instrument_id']==identity}
        count=covered_days(day,dates);retained=saved.get((identity,currency));count=retained['covered_days'] if retained else count
        samples=[dict(valueDate=str(row['value_date']),amount=str(row['daily_earned_interest']),coveredDays=coverage.get((identity,row['value_date']),covered_days(row['value_date'],dates)),inputId=str(row['input_id'])) for row in history]
        baseline=benchmark([(date.fromisoformat(row['valueDate']),Decimal(row['amount']),row['coveredDays']) for row in samples],day,count)
        amount=source['daily_earned_interest'] if source and not foreign else None;before=None;increment=amount;details={};notes=[]
        if foreign:notes.append('The supplied source uses another currency. Provide a sourced local-currency assessment; no FX conversion is assumed.')
        if stage=='BALANCE':
            item=local.get((identity,currency))
            if item:
                value,refs=item;before=value.opening;amount=value.closing
                details=dict(tradeMovements=value.trade_movements,couponReceipts=value.coupon_paid,basis=value.basis,sources=refs)
            else:amount=None
            existing=current_stocks.get((identity,currency))
            if existing:
                details.update(existingClosingBalance=str(existing['closing_balance']),existingBalanceInputId=str(existing['input_id']))
                if amount is None:
                    amount=existing['closing_balance']
                    notes.append('An existing sourced closing stock is available, but the daily bridge is incomplete. Its amount is not inferred daily income.')
            if before is None:notes.append('Opening balance is not assessed. Supply a sourced closing balance; unknown is not zero.')
        due=[row for row in schedules if row['instrument_id']==identity]
        if any(row['cashflow_type']=='COUPON' for row in due):notes.append('Coupon scheduled today: review the accrued-balance reset and preserve any new-period interest. The schedule does not confirm payment.')
        if any(row['cashflow_type']=='PRINCIPAL' for row in due):notes.append('Principal scheduled today: check maturity and remaining accrued balance.')
        proposed=retained['proposed_amount'] if retained else amount
        warning=review_warning(proposed,count,baseline) if stage=='DAILY' and proposed is not None else None
        if stage=='BALANCE' and before is not None and proposed is not None:
            warning=review_warning(proposed,1,dict(average=before,coveredDays=5))
        rows.append(dict(instrumentId=str(identity),instrumentName=instrument['canonical_name'],currencyId=str(currency),currency=instrument['currency_code'],
            inputId=str(source['input_id']) if source else None,amount=proposed,sourceAmount=amount,decision=retained['decision'] if retained else 'ASSESSED',coveredDays=count,openingBalance=before,
            dailyIncrement=increment,benchmark=baseline,warning=warning,notes=notes,details=details,
            sourceReference=retained['source_reference'] if retained else source['payload'].get('sourceReference','') if source else '',
            reason=retained['reason'] if retained else '',benchmarkSamples=samples,
            reconciliation=retained['evidence'].get('proposedReconciliation') if retained and retained['evidence'].get('proposedReconciliation') else source['payload'].get('inputs') if source else None))
    from security_master_schema.tenant_workspace import TenantActionForbidden
    writable=True
    try:require_strategy_action(c,tenant,actor,'VALUATION_REVIEW',strategy)
    except TenantActionForbidden:writable=False
    name=c.scalar(select(m.strategy.c.display_name).where(m.strategy.c.strategy_id==strategy,m.strategy.c.tenant_id==tenant))
    return canonical_payload(dict(strategyId=strategy,strategyLabel=name,canWrite=writable,valueDate=day,stage=stage,sourceHash=source_hash,sourceProof=proof,rows=rows,
        review=dict(current,items=retained_items) if current else None,reviewCurrent=bool(current and current['source_hash']==source_hash),dailyValidated=daily_valid,
        dailyReviewId=str(daily_review['review_id']) if daily_valid else None,dailyGapCount=daily_review['gap_count'] if daily_valid else 0))


def save_review(c,tenant,actor,operator,payload,key):
    require_strategy_action(c,tenant,actor,'VALUATION_REVIEW',payload.strategy_id)
    from .storage import input_revision_lock
    input_revision_lock(c,tenant,payload.strategy_id)
    digest=evidence_hash(payload.model_dump())
    old=c.execute(select(t.review).where(t.review.c.tenant_id==tenant,t.review.c.request_key==key)).mappings().one_or_none()
    if old:
        if old['request_hash']!=digest or old['actor_id']!=actor or old['real_operator_id']!=operator:raise ValueError('Review request key belongs to different content or operator')
        return dict(old)
    view=review_view(c,tenant,actor,payload.strategy_id,payload.value_date,payload.stage)
    if view['sourceHash']!=payload.source_hash:raise ValueError('Interest sources changed; refresh and review the current data')
    current=_latest(c,tenant,payload.strategy_id,payload.value_date,payload.stage)
    if payload.supersedes_review_id!=(current['review_id'] if current else None):raise ValueError('Review revision changed; refresh current state')
    actual={(row['instrumentId'],row['currencyId']):row for row in view['rows']}
    if set(actual)!={(str(row.instrument_id),str(row.currency_id)) for row in payload.rows}:raise ValueError('Bulk review must include the complete current population')
    if not actual:raise ValueError('There are no daily values to validate')
    from .balance_history_contracts import BalanceInputCreate,BalanceHistoryRefresh
    recorded=[]
    # Caller owns the outer audited transaction; the savepoint protects direct
    # command callers too if any later row, audit or history projection fails.
    with c.begin_nested():
        current_stocks=balances.read_inputs(c,tenant,payload.strategy_id,payload.value_date,payload.value_date,datetime.now(timezone.utc)) if payload.stage=='BALANCE' else []
        stocks={(row['instrument_id'],row['currency_id']):row for row in current_stocks}
        for row in payload.rows:
            source=actual[(str(row.instrument_id),str(row.currency_id))]
            original=Decimal(source['sourceAmount']) if source['sourceAmount'] is not None else None
            gap=row.decision=='NOT_SUPPLIED'
            if gap and (original is not None or row.amount is not None or not row.reason):raise ValueError('A missing-input acknowledgement needs an unknown amount and a reason; known amounts cannot be hidden')
            changed=row.amount!=original
            detail_changed=bool(row.reconciliation and source.get('reconciliation') and any(value!=Decimal(source['reconciliation'][key]) for key,value in row.reconciliation.model_dump(by_alias=True).items()))
            if not gap and (changed or detail_changed or row.covered_days!=source['coveredDays']) and (not row.reason or not row.source_reference):raise ValueError('Manual changes require a source reference and a reason')
            if payload.state=='VALIDATED' and row.amount is None and not gap:raise ValueError('Every row needs an assessed amount or an explicit missing-input acknowledgement')
            daily_id=UUID(source['inputId']) if source['inputId'] else None;stock_id=None
            if payload.state=='VALIDATED' and payload.stage=='DAILY' and not gap and (changed or detail_changed):
                from . import tables as vt
                prior=c.execute(select(vt.accrual_input).where(vt.accrual_input.c.input_id==daily_id)).mappings().one_or_none() if daily_id else None
                data=dict(prior['payload']) if prior else {}
                data.update(strategyId=payload.strategy_id,instrumentId=row.instrument_id,currencyId=row.currency_id,valueDate=payload.value_date,
                    inputType='DAILY_INTEREST',dailyEarned=row.amount,sourceReference=row.source_reference,supersedesInputId=daily_id)
                if data.get('inputs'):
                    if row.reconciliation is None:raise ValueError('Update the retained detailed reconciliation with the corrected daily value')
                    pricing=c.execute(select(m.valuation_policy).where(m.valuation_policy.c.valuation_policy_id==UUID(data['policyId']),
                        m.valuation_policy.c.tenant_id==tenant,m.valuation_policy.c.status=='ACTIVE')).mappings().one_or_none()
                    if not pricing or pricing['strategy_id'] not in (None,payload.strategy_id):raise ValueError('Active scoped pricing context required for detailed correction')
                    values={k:Decimal(v) for k,v in data['inputs'].items()}
                    values.update(row.reconciliation.model_dump(by_alias=True),dailyEarned=row.amount)
                    data.update(inputs=values,amounts=accrual_amounts(values))
                    for field in ('policyId','cutId','reportingCurrencyId'):data[field]=UUID(data[field])
                daily_id=record_accrual(c,tenant,actor,data,f'{key}:daily:{row.instrument_id}',request_hash=digest)
            if payload.state=='VALIDATED' and payload.stage=='BALANCE' and not gap:
                previous=stocks.get((row.instrument_id,row.currency_id))
                stock=balances.record_balance_input(c,tenant,actor,BalanceInputCreate(strategyId=payload.strategy_id,instrumentId=row.instrument_id,currencyId=row.currency_id,
                    valueDate=payload.value_date,closingBalance=str(row.amount),sourceReference=row.source_reference or 'Validated daily balance review',
                    reason=row.reason or 'Daily balance bridge reviewed',supersedesInputId=previous['input_id'] if previous else None),f'{key}:balance:{row.instrument_id}')
                stock_id=stock['input_id']
            evidence=dict(source,proposedAmount=str(row.amount) if row.amount is not None else None,
                proposedReconciliation=row.reconciliation.model_dump(mode='json',by_alias=True) if row.reconciliation else None)
            if payload.stage=='DAILY':
                checked=benchmark([(date.fromisoformat(r['valueDate']),Decimal(r['amount']),r['coveredDays']) for r in source['benchmarkSamples']],payload.value_date,row.covered_days)
                evidence.update(benchmark=canonical_payload(checked),warning=canonical_payload(review_warning(row.amount,row.covered_days,checked)) if row.amount is not None else None)
            recorded.append(dict(instrument_id=row.instrument_id,currency_id=row.currency_id,source_amount=original,proposed_amount=row.amount,
                opening_balance=source['openingBalance'],daily_increment=source['dailyIncrement'],benchmark_daily=source['benchmark']['average'],
                covered_days=row.covered_days,decision=row.decision,source_input_id=daily_id if not gap else None,balance_input_id=stock_id,source_reference=row.source_reference,reason=row.reason,
                evidence=evidence))
        if payload.state=='VALIDATED' and payload.stage=='BALANCE':
            balances.refresh_history(c,tenant,actor,BalanceHistoryRefresh(strategyId=payload.strategy_id,fromDate=payload.value_date,toDate=payload.value_date),f'{key}:history')
        if payload.stage=='DAILY' and payload.state=='VALIDATED':
            _,_,_,_,_,proof=_sources(c,tenant,payload.strategy_id,payload.value_date)
            after_hash=evidence_hash(proof)
        elif payload.stage=='BALANCE' and payload.state=='VALIDATED':
            refreshed=review_view(c,tenant,actor,payload.strategy_id,payload.value_date,'BALANCE')
            proof=refreshed['sourceProof'];after_hash=refreshed['sourceHash']
        else:proof=view['sourceProof'];after_hash=view['sourceHash']
        # Only this command's own daily revisions / stock sources may change
        # while validating. Never bless a concurrent position/schedule change
        # merely by recording its newer hash after the user reviewed old data.
        before=view['sourceProof']
        for field in ('projection','schedules','population','priorCoverageReviews'):
            if proof[field]!=before[field]:raise ValueError('Position, schedule or comparison sources changed during review; refresh and review again')
        expected=set(before['inputs'])
        for row in recorded:
            prior=actual[(str(row['instrument_id']),str(row['currency_id']))]['inputId']
            new=str(row['source_input_id']) if row['source_input_id'] else None
            if new and new!=prior:
                if prior:expected.discard(prior)
                expected.add(new)
        if set(proof['inputs'])!=expected:raise ValueError('Daily sources changed during review; refresh and review again')
        header=c.execute(t.review.insert().values(tenant_id=tenant,strategy_id=payload.strategy_id,value_date=payload.value_date,stage=payload.stage,state=payload.state,
            revision=current['revision']+1 if current else 1,row_count=len(recorded),gap_count=sum(row.decision=='NOT_SUPPLIED' for row in payload.rows),supersedes_review_id=payload.supersedes_review_id,
            daily_review_id=UUID(view['dailyReviewId']) if payload.stage=='BALANCE' else None,source_hash=after_hash,source_proof=proof,
            actor_id=actor,real_operator_id=operator,request_key=key,request_hash=digest).returning(t.review)).mappings().one()
        for row in recorded:c.execute(t.item.insert().values(review_id=header['review_id'],tenant_id=tenant,strategy_id=payload.strategy_id,value_date=payload.value_date,
            **{k:v for k,v in row.items() if k!='evidence'},evidence=canonical_payload(row['evidence'])))
        audit(c,operator,tenant,'INTEREST_REVIEW_'+payload.state,dict(reviewId=str(header['review_id']),strategyId=str(payload.strategy_id),valueDate=str(payload.value_date),stage=payload.stage,rows=len(recorded)),actor)
        return dict(header)
