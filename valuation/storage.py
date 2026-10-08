"""Transaction-bound immutable attribution and separate durable run attempts."""
from dataclasses import asdict
from datetime import datetime, timezone
from decimal import Decimal, localcontext
from hashlib import sha256
from uuid import uuid4
from sqlalchemy import select, func
from security_master_schema import models as m  # registers dedicated table metadata
from . import tables as t
from .economics import canonical_payload, evidence_hash, validate_totals
from .service import METHOD


def _lock(c, tenant, strategy, day):
    scope=f'valuation:{tenant}:{strategy}:{day}'
    lock_id=int.from_bytes(sha256(scope.encode()).digest()[:8],'big',signed=True)
    c.execute(select(func.pg_advisory_xact_lock(lock_id)))


def population_hash(rows):
    return evidence_hash({'population':sorted([(str(row.get('position_key') or row['trade_id']),str(row['attribution_id'])) for row in rows])})


def _event(c, attempt_id, event_code, stage, details):
    c.execute(t.run_event.insert().values(attempt_id=attempt_id,event_code=event_code,stage=stage,details=canonical_payload(details)))


def begin_attempt(engine, request, actor, key, correlation_id=None, *, configure_transaction=None):
    """Commit operational STARTED independently of any financial transaction."""
    if not isinstance(key,str) or not key.strip() or len(key)>255: raise ValueError('Request key required')
    digest=evidence_hash(dict(request=asdict(request),actor=actor))
    with engine.begin() as c:
        if configure_transaction: configure_transaction(c)
        # Serialize identical keys without taking unrelated strategy/date locks.
        lock_id=int.from_bytes(sha256(f'valuation-request:{request.tenant_id}:{key}'.encode()).digest()[:8],'big',signed=True)
        c.execute(select(func.pg_advisory_xact_lock(lock_id)))
        old=c.execute(select(t.attempt).where(t.attempt.c.tenant_id==request.tenant_id,t.attempt.c.request_key==key)).mappings().one_or_none()
        if old:
            if old['request_hash']!=digest: raise ValueError('Idempotency key already used for different valuation inputs')
            return old['attempt_id']
        attempt=c.execute(t.attempt.insert().values(tenant_id=request.tenant_id,strategy_id=request.strategy_id,
            initiated_by=actor,request_key=key,request_hash=digest,request_payload=canonical_payload(asdict(request)),
            correlation_id=correlation_id or str(uuid4()),status='RUNNING').returning(t.attempt.c.attempt_id)).scalar_one()
        _event(c,attempt,'STARTED','REQUEST',{})
        return attempt


def fail_attempt(engine, tenant, attempt_id, code, *, reason=None, configure_transaction=None):
    """Retain safe failure evidence after the financial transaction has rolled back."""
    if code not in {'INPUT_MISSING','VALUATION_BLOCKED','CALCULATION_FAILED'}: code='CALCULATION_FAILED'
    with engine.begin() as c:
        if configure_transaction: configure_transaction(c)
        # Financial rollback releases the worker lock before diagnostics commit.
        # A retry may already own that same attempt; never fail its active work.
        lock_id=int.from_bytes(attempt_id.bytes[:8],'big',signed=True)
        if not c.scalar(select(func.pg_try_advisory_xact_lock(lock_id))):
            return
        changed=c.execute(t.attempt.update().where(t.attempt.c.attempt_id==attempt_id,t.attempt.c.tenant_id==tenant,
            t.attempt.c.status=='RUNNING').values(status='FAILED',error_code=code,completed_at=datetime.now(timezone.utc))).rowcount
        if changed: _event(c,attempt_id,'FAILED','CALCULATION',{'errorCode':code,'reason':reason or 'Required calculation inputs are unavailable.'})


def published(c, tenant, strategy, day):
    return [dict(row) for row in c.execute(select(t.attribution).join(t.item,t.item.c.attribution_id==t.attribution.c.attribution_id)
        .join(t.batch,t.batch.c.batch_id==t.item.c.batch_id).where(t.batch.c.tenant_id==tenant,t.batch.c.strategy_id==strategy,
            t.batch.c.value_date==day,t.batch.c.status=='PUBLISHED').order_by(t.attribution.c.trade_id)).mappings()]


def _amount(value):
    # Storage precision is a contract, not permission to round silently.
    with localcontext() as context:
        context.prec=512
        if abs(value)>=Decimal('1e18') or value!=value.quantize(Decimal('0.000000000001')):
            raise ValueError('Calculated amount exceeds exact NUMERIC(30,12) storage precision')
    return value


def selection_identity(row):
    """Financially relevant input provenance, without mere query-time changes."""
    identity={key:row.get(key) for key in ('market_data_observation_id','market_data_series_id','policy_rule_id',
        'market_data_vintage_id','dataset_id','acquisition_licence_id','selected_value','currency_id',
        'pricing_date_requested','pricing_date_used')}
    pricing=row.get('pricing_evidence')
    identity['pricing_evidence']={key:value for key,value in pricing.items() if key!='informationCutoffUtc'} if pricing else None
    return identity


def stage(c, attempt_id, actor, calculation, *, mode='AUTHORITATIVE'):
    """Select immutable versions without modifying the official population."""
    if mode!='AUTHORITATIVE':
        raise ValueError('This alpha requires a complete authoritative population; incremental staging is deferred')
    request=calculation.request;day=request.closing_cutoff.date()
    _lock(c,request.tenant_id,request.strategy_id,day)
    attempt=c.execute(select(t.attempt).where(t.attempt.c.attempt_id==attempt_id,t.attempt.c.tenant_id==request.tenant_id).with_for_update()).mappings().one_or_none()
    if not attempt or attempt['strategy_id']!=request.strategy_id or attempt['initiated_by']!=actor:
        raise ValueError('Valuation attempt scope mismatch')
    if attempt['request_hash']!=evidence_hash(dict(request=asdict(request),actor=actor)):
        raise ValueError('Calculation does not match the attempted request')
    if attempt['status']=='FAILED': raise ValueError('Failed attempt needs a new request key')
    prior=c.execute(select(t.batch).where(t.batch.c.tenant_id==request.tenant_id,t.batch.c.strategy_id==request.strategy_id,
        t.batch.c.value_date==day,t.batch.c.input_hash==calculation.input_hash,t.batch.c.mode==mode)).mappings().one_or_none()
    if prior:
        if prior['status'] in {'CANCELLED','SUPERSEDED'}: raise ValueError('This historical batch is no longer publishable; create a fresh calculation')
        c.execute(t.attempt.update().where(t.attempt.c.attempt_id==attempt_id).values(status='COMPLETED',completed_at=datetime.now(timezone.utc)))
        if attempt['status']!='COMPLETED':
            _event(c,attempt_id,'COMPLETED','STAGING',{'batchId':prior['batch_id'],'reused':True})
        return prior['batch_id']
    official=published(c,request.tenant_id,request.strategy_id,day)
    selected={}
    from collections import defaultdict
    facts_by_trade=defaultdict(list); selections_by_subject=defaultdict(list)
    if calculation.projection is not None:
        for fact in calculation.projection.facts: facts_by_trade[fact.trade_id].append(fact)
        for selection in calculation.evidence['selections']:
            selections_by_subject[selection['subject_reference_node_id']].append(selection)
    for line in calculation.period.lines:
        components=line.attribution.components();total=line.attribution.market_pnl
        validate_totals(components,market=total,gross=total,net=total)
        for amount in [*components.values(),total]: _amount(amount)
        if calculation.projection is not None:
            from .position_storage import stage_line
            position,attribution=stage_line(c,attempt_id,calculation,line,
                facts=[fact for trade in line.bucket.trade_ids for fact in facts_by_trade[trade]],
                selections=selections_by_subject[str(line.bucket.key.subject_id)])
            selected[position]=attribution
            continue
        # Unrelated trade changes must not manufacture a new version of this lot.
        selections=[row for row in calculation.evidence['selections'] if row['subject_reference_node_id']==str(line.lot.subject_id)]
        identity=dict(method=METHOD,lot=asdict(line.lot),basis=line.basis,components=components,
            openingCutoff=request.opening_cutoff,closingCutoff=request.closing_cutoff,
            policyId=request.policy_id,reportingCurrency=request.reporting_currency_id,
            selections=[selection_identity(row) for row in selections])
        digest=evidence_hash(identity)
        previous=c.execute(select(t.attribution).where(t.attribution.c.tenant_id==request.tenant_id,t.attribution.c.strategy_id==request.strategy_id,
            t.attribution.c.value_date==day,t.attribution.c.trade_id==line.lot.trade_id).order_by(t.attribution.c.version.desc()).limit(1)).mappings().one_or_none()
        if previous and previous['input_hash']==digest:
            selected[line.lot.trade_id]=previous['attribution_id'];continue
        evidence=canonical_payload(dict(identity=identity,informationCutoff=request.information_cutoff,
            resolutionSnapshotIds=calculation.resolution_snapshot_ids,events=[event for event in calculation.evidence['events'] if event['trade_id']==str(line.lot.trade_id)],
            selections=selections,scope=calculation.scope))
        selected[line.lot.trade_id]=c.execute(t.attribution.insert().values(tenant_id=request.tenant_id,strategy_id=request.strategy_id,
            attempt_id=attempt_id,trade_id=line.lot.trade_id,value_date=day,version=previous['version']+1 if previous else 1,
            supersedes_attribution_id=previous['attribution_id'] if previous else None,method=METHOD,input_hash=digest,
            currency_id=request.reporting_currency_id,market_pnl=total,gross_pnl=total,net_pnl=total,
            components=canonical_payload(components),evidence=evidence).returning(t.attribution.c.attribution_id)).scalar_one()
    old_staged=c.execute(select(t.batch.c.batch_id).where(t.batch.c.tenant_id==request.tenant_id,t.batch.c.strategy_id==request.strategy_id,
        t.batch.c.value_date==day,t.batch.c.status=='STAGED')).scalars().all()
    for old in old_staged:
        c.execute(t.batch.update().where(t.batch.c.batch_id==old).values(status='CANCELLED'))
        c.execute(t.review_event.insert().values(batch_id=old,actor_id=actor,action='CANCELLED',comment='Replaced by a new staged calculation'))
    summary=canonical_payload(dict(scope=calculation.scope,externalComparison=calculation.external_comparison,
        marketPnl=calculation.period.market_pnl,openingValue=calculation.period.opening_value,closingValue=calculation.period.closing_value,
        executionValue=calculation.period.execution_value,reportingCurrencyId=request.reporting_currency_id,
        request=asdict(request),limitations=calculation.evidence['limitations'],blockingValidation=[],inputHash=calculation.input_hash,
        resultFormat='POSITION_V2' if calculation.projection is not None else 'TRADE_V1',
        positionEvidence=({ 'engine':calculation.projection.engine_version,'inputHash':calculation.projection.input_hash,
            'completeKnowledge':calculation.projection.complete_knowledge,'factsScanned':calculation.projection.facts_scanned,
            'bucketCount':len(calculation.projection.buckets),'executionCount':len(calculation.projection.executions),
            'requiredMarkCount':calculation.evidence['requiredMarkCount']} if calculation.projection is not None else None)))
    batch=c.execute(t.batch.insert().values(tenant_id=request.tenant_id,strategy_id=request.strategy_id,staged_by=actor,attempt_id=attempt_id,
        value_date=day,status='STAGED',mode=mode,input_hash=calculation.input_hash,base_population_hash=population_hash(official),summary=summary)
        .returning(t.batch.c.batch_id)).scalar_one()
    for owner,attribution in selected.items():
        ownership={'position_key':owner} if calculation.projection is not None else {'trade_id':owner}
        c.execute(t.item.insert().values(tenant_id=request.tenant_id,batch_id=batch,attribution_id=attribution,**ownership))
    c.execute(t.review_event.insert().values(batch_id=batch,actor_id=actor,action='STAGED',comment='Calculated market-only attribution staged for review'))
    c.execute(t.attempt.update().where(t.attempt.c.attempt_id==attempt_id).values(status='COMPLETED',completed_at=datetime.now(timezone.utc)))
    _event(c,attempt_id,'COMPLETED','STAGING',{'batchId':batch,'attributionCount':len(selected)})
    return batch


def batch_view(c, tenant, batch_id):
    header=c.execute(select(t.batch).where(t.batch.c.batch_id==batch_id,t.batch.c.tenant_id==tenant)).mappings().one_or_none()
    if header is None: raise LookupError('Review batch not found')
    items=[dict(row) for row in c.execute(select(t.attribution).join(t.item,t.item.c.attribution_id==t.attribution.c.attribution_id)
        .where(t.item.c.batch_id==batch_id,t.item.c.tenant_id==tenant).order_by(t.attribution.c.trade_id)).mappings()]
    links={}
    for row in c.execute(select(t.lineage).join(t.item,t.item.c.attribution_id==t.lineage.c.attribution_id)
            .where(t.item.c.batch_id==batch_id,t.item.c.tenant_id==tenant).order_by(t.lineage.c.trade_id,t.lineage.c.event_id)).mappings():
        links.setdefault(row['attribution_id'],[]).append(dict(row))
    for row in items:
        row['lineage']=links.get(row['attribution_id'],[])
    reviews=[dict(row) for row in c.execute(select(t.review_event).where(t.review_event.c.batch_id==batch_id)
        .order_by(t.review_event.c.recorded_at,t.review_event.c.review_event_id)).mappings()]
    return dict(header)|dict(items=items,reviews=reviews)


def publish(c, tenant, batch_id, actor, comment):
    header=c.execute(select(t.batch).where(t.batch.c.batch_id==batch_id,t.batch.c.tenant_id==tenant)).mappings().one_or_none()
    if header is None: raise LookupError('Review batch not found')
    _lock(c,tenant,header['strategy_id'],header['value_date'])
    header=c.execute(select(t.batch).where(t.batch.c.batch_id==batch_id).with_for_update()).mappings().one()
    if actor==header['staged_by']: raise ValueError('Publication requires an independent reviewer')
    if not isinstance(comment,str) or not comment.strip() or len(comment)>2000: raise ValueError('Review explanation required')
    if header['status']=='PUBLISHED': return batch_id
    if header['status']!='STAGED': raise ValueError('Batch is no longer staged')
    if header['summary'].get('blockingValidation'): raise ValueError('Blocking validation must be resolved before publication')
    # Review the exact selected versions, not just a stored UI summary. This is
    # also a guard against incomplete population edits before publication.
    candidate=batch_view(c,tenant,batch_id)['items']
    if not candidate:
        from .position_storage import valid_empty_summary
        if not valid_empty_summary(header['summary']): raise ValueError('Empty-population publication is not enabled')
    try:
        with localcontext() as context:
            context.prec=512
            selected_total=sum((row['market_pnl'] for row in candidate),Decimal('0'))
            summary=header['summary']
            values={key:Decimal(summary[key]) for key in ('marketPnl','openingValue','closingValue','executionValue')}
            if not all(value.is_finite() for value in values.values()): raise ValueError('Nonfinite review summary')
            if any(str(row['currency_id'])!=summary['reportingCurrencyId'] for row in candidate):
                raise ValueError('Review currency mismatch')
            if selected_total!=values['marketPnl'] or selected_total!=values['closingValue']-values['openingValue']-values['executionValue']:
                raise ValueError('Review summary and selected attribution do not reconcile')
    except (KeyError,TypeError,ArithmeticError) as exc:
        raise ValueError('Review summary and selected attribution do not reconcile') from exc
    current=published(c,tenant,header['strategy_id'],header['value_date'])
    if population_hash(current)!=header['base_population_hash']:
        raise ValueError('Published population changed after staging; calculate again')
    old=c.execute(select(t.batch.c.batch_id).where(t.batch.c.tenant_id==tenant,t.batch.c.strategy_id==header['strategy_id'],
        t.batch.c.value_date==header['value_date'],t.batch.c.status=='PUBLISHED')).scalars().all()
    for prior in old:
        c.execute(t.batch.update().where(t.batch.c.batch_id==prior).values(status='SUPERSEDED'))
        c.execute(t.review_event.insert().values(batch_id=prior,actor_id=actor,action='SUPERSEDED',comment='Superseded by a reviewed publication'))
    c.execute(t.batch.update().where(t.batch.c.batch_id==batch_id).values(status='PUBLISHED'))
    c.execute(t.review_event.insert().values(batch_id=batch_id,actor_id=actor,action='PUBLISHED',comment=comment.strip()))
    return batch_id
