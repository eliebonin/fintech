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


def input_revision_lock(c, tenant, strategy):
    """Serialize source revisions with review across every date in a strategy."""
    c.execute(select(m.strategy.c.strategy_id).where(m.strategy.c.tenant_id==tenant,
        m.strategy.c.strategy_id==strategy).with_for_update(key_share=True))
    scope=f'valuation-inputs:{tenant}:{strategy}'
    c.execute(select(func.pg_advisory_xact_lock(int.from_bytes(sha256(scope.encode()).digest()[:8],'big',signed=True))))


def _lock(c, tenant, strategy, day):
    input_revision_lock(c,tenant,strategy)
    scope=f'valuation:{tenant}:{strategy}:{day}'
    lock_id=int.from_bytes(sha256(scope.encode()).digest()[:8],'big',signed=True)
    c.execute(select(func.pg_advisory_xact_lock(lock_id)))


def population_hash(rows):
    from .cash_fx_storage import cash_owner
    return evidence_hash({'population':sorted([(cash_owner(row) if row.get('cash_account_id') else str(row.get('position_key') or row['trade_id']),str(row['attribution_id'])) for row in rows])})


def _event(c, attempt_id, event_code, stage, details):
    c.execute(t.run_event.insert().values(attempt_id=attempt_id,event_code=event_code,stage=stage,details=canonical_payload(details)))


def request_identity(request):
    """Version execution semantics, including valuation-window cash coverage."""
    values = dict(asdict(request),calculation_contract='economic-pnl-bond-clean-v1')
    if not values.get('daily'): values.pop('daily', None)
    if not values.get('require_complete_accruals'): values.pop('require_complete_accruals',None)
    for key in ('predecessor_batch_id','recalculation_reason'):
        if values.get(key) is None: values.pop(key,None)
    return values


def begin_attempt(engine, request, actor, key, correlation_id=None, *, configure_transaction=None,real_operator_id=None):
    """Commit operational STARTED independently of any financial transaction."""
    if not isinstance(key,str) or not key.strip() or len(key)>255: raise ValueError('Request key required')
    digest=evidence_hash(dict(request=request_identity(request),actor=actor))
    with engine.begin() as c:
        if configure_transaction: configure_transaction(c)
        # Serialize identical keys without taking unrelated strategy/date locks.
        lock_id=int.from_bytes(sha256(f'valuation-request:{request.tenant_id}:{key}'.encode()).digest()[:8],'big',signed=True)
        c.execute(select(func.pg_advisory_xact_lock(lock_id)))
        old=c.execute(select(t.attempt).where(t.attempt.c.tenant_id==request.tenant_id,t.attempt.c.request_key==key)).mappings().one_or_none()
        if old:
            if old['request_hash']!=digest: raise ValueError('Idempotency key already used for different valuation inputs')
            operators=c.scalars(select(t.run_event.c.details).where(t.run_event.c.attempt_id==old['attempt_id'],
                t.run_event.c.event_code=='STARTED')).all()
            if any(e.get('realOperatorId') and e['realOperatorId']!=str(real_operator_id or actor) for e in operators):
                raise ValueError('Valuation request key belongs to a different real operator')
            if not any(e.get('realOperatorId') for e in operators):
                from .review_authority import _legacy
                lineage=_legacy(c,request.tenant_id,old['attempt_id'],actor)
                if (lineage.complete and (real_operator_id or actor) not in lineage.operators
                    or not lineage.complete and real_operator_id and real_operator_id!=actor):
                    raise ValueError('Legacy request real operator cannot be verified; use a new request key')
            from security_master_schema.command_audit import retain_command_audit
            retain_command_audit(c, resources=[old['attempt_id']], phase='REQUEST_ACCEPTED')
            return old['attempt_id']
        attempt=c.execute(t.attempt.insert().values(tenant_id=request.tenant_id,strategy_id=request.strategy_id,
            initiated_by=actor,request_key=key,request_hash=digest,request_payload=canonical_payload(asdict(request)),
            correlation_id=correlation_id or str(uuid4()),status='RUNNING').returning(t.attempt.c.attempt_id)).scalar_one()
        _event(c,attempt,'STARTED','REQUEST',{'realOperatorId':str(real_operator_id or actor)})
        from security_master_schema.command_audit import retain_command_audit
        retain_command_audit(c, resources=[attempt], phase='REQUEST_ACCEPTED')
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
    from .rounding import rounded_result
    request=calculation.request;day=request.closing_cutoff.date()
    cash=calculation.cash if calculation.projection is not None else None
    _lock(c,request.tenant_id,request.strategy_id,day)
    attempt=c.execute(select(t.attempt).where(t.attempt.c.attempt_id==attempt_id,t.attempt.c.tenant_id==request.tenant_id).with_for_update()).mappings().one_or_none()
    if not attempt or attempt['strategy_id']!=request.strategy_id or attempt['initiated_by']!=actor:
        raise ValueError('Valuation attempt scope mismatch')
    if attempt['request_hash']!=evidence_hash(dict(request=request_identity(request),actor=actor)):
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
    from .accrued_balance_storage import retain_balances,stage_receivable
    if calculation.projection is not None:retain_balances(c,attempt_id,calculation)
    selected={}
    cash_owners={}
    stored_totals={'market':Decimal(0),'gross':Decimal(0),'net':Decimal(0)}
    from collections import defaultdict
    facts_by_trade=defaultdict(list); selections_by_subject=defaultdict(list); executions_by_key=defaultdict(list)
    fx_by_currency=defaultdict(list);accrued_fx_by_instrument=defaultdict(list)
    if calculation.projection is not None:
        for fact in calculation.projection.facts: facts_by_trade[fact.trade_id].append(fact)
        for selection in calculation.evidence['selections']:
            selections_by_subject[selection.get('valuation_position_subject_id',selection['subject_reference_node_id'])].append(selection)
            if selection.get('input_role')=='FX':fx_by_currency[selection.get('valuation_source_currency_id')].append(selection)
            if selection.get('valuation_accrued_instrument_id'):accrued_fx_by_instrument[selection['valuation_accrued_instrument_id']].append(selection)
        for execution in calculation.projection.executions:
            executions_by_key[execution.key].append(execution)
    for line in calculation.period.lines:
        total=line.attribution.market_pnl
        components=line.components() if calculation.projection is not None else line.attribution.components()
        gross=line.gross_pnl if calculation.projection is not None else total
        net=line.net_pnl if calculation.projection is not None else total
        validate_totals(components,market=total,gross=gross,net=net)
        from .rounding import rounded_result
        rounded=rounded_result(components,market=total,gross=gross,net=net)
        with localcontext() as ctx:
            ctx.prec=512
            for name in stored_totals: stored_totals[name]+=rounded[name]
        if calculation.projection is not None:
            from .position_storage import stage_line
            instruments={p.get('instrumentId') or p.get('payload',{}).get('instrumentId') for p in line.economic_evidence}
            source_selections=selections_by_subject[str(line.bucket.key.subject_id)]+fx_by_currency[str(line.bucket.key.currency_id)]
            for instrument in instruments:source_selections+=accrued_fx_by_instrument[instrument]
            source_selections=list({evidence_hash(s):s for s in source_selections}.values())
            position,attribution=stage_line(c,attempt_id,calculation,line,
                facts=[fact for trade in line.bucket.trade_ids for fact in facts_by_trade[trade]],
                selections=source_selections,
                executions=executions_by_key[line.bucket.key],rounded=rounded)
            selected[position]=attribution
            continue
        # Unrelated trade changes must not manufacture a new version of this lot.
        selections=[row for row in calculation.evidence['selections'] if row['subject_reference_node_id']==str(line.lot.subject_id)]
        identity=dict(method=METHOD,lot=asdict(line.lot),basis=line.basis,components=components,storageRounding=rounded['evidence'],
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
            selections=selections,scope=calculation.scope,storageRounding=rounded['evidence']))
        selected[line.lot.trade_id]=c.execute(t.attribution.insert().values(tenant_id=request.tenant_id,strategy_id=request.strategy_id,
            attempt_id=attempt_id,trade_id=line.lot.trade_id,value_date=day,version=previous['version']+1 if previous else 1,
            supersedes_attribution_id=previous['attribution_id'] if previous else None,method=METHOD,input_hash=digest,
            currency_id=request.reporting_currency_id,market_pnl=rounded['market'],gross_pnl=rounded['gross'],net_pnl=rounded['net'],
            components=canonical_payload(rounded['components']),evidence=evidence).returning(t.attribution.c.attribution_id)).scalar_one()
    for line in calculation.receivables if calculation.projection is not None else ():
        if not any(day.amount is not None for day in line.days):continue
        rounded=rounded_result({'CARRY':line.amount},market=Decimal(0),gross=line.amount,net=line.amount)
        owner,identity=stage_receivable(c,attempt_id,calculation,line,rounded)
        selected[owner]=identity
        with localcontext() as ctx:
            ctx.prec=512
            for name in stored_totals:stored_totals[name]+=rounded[name]
    cash_total=None
    if cash is not None:
        from .cash_fx_storage import stage_cash_line,cash_owner
        cash_total=Decimal(0) if cash.lines else None
        for line in cash.lines:
            rounded=rounded_result(line.components(),market=Decimal(0),gross=line.amount,net=line.amount)
            owner=dict(cash_account_id=line.account_id,cash_currency_id=line.currency_id)
            key=cash_owner(owner)
            selected[key]=stage_cash_line(c,attempt_id,calculation,line,rounded)
            cash_owners[key]=owner
            with localcontext() as ctx:
                ctx.prec=512
                cash_total+=rounded['components']['CASH_FX']
                for name in stored_totals:stored_totals[name]+=rounded[name]
    old_staged=c.execute(select(t.batch.c.batch_id).where(t.batch.c.tenant_id==request.tenant_id,t.batch.c.strategy_id==request.strategy_id,
        t.batch.c.value_date==day,t.batch.c.status=='STAGED')).scalars().all()
    for old in old_staged:
        c.execute(t.batch.update().where(t.batch.c.batch_id==old).values(status='CANCELLED'))
        c.execute(t.amendment.update().where(t.amendment.c.base_batch_id==old,t.amendment.c.status=='PENDING').values(
            status='STALE',reviewed_by=actor,reviewed_at=datetime.now(timezone.utc),
            review_comment='Base candidate replaced by a new staged calculation'))
        c.execute(t.review_event.insert().values(batch_id=old,actor_id=actor,action='CANCELLED',comment='Replaced by a new staged calculation'))
    with localcontext() as ctx:
        ctx.prec=512
        market_rounding=stored_totals['market']-calculation.period.market_pnl
    summary=canonical_payload(dict(scope=calculation.scope,externalComparison=calculation.external_comparison,
        marketPnl=stored_totals['market'],openingValue=calculation.period.opening_value,closingValue=calculation.period.closing_value,
        grossPnl=stored_totals['gross'],netPnl=stored_totals['net'],marketRoundingAdjustment=market_rounding,
        executionValue=calculation.period.execution_value,reportingCurrencyId=request.reporting_currency_id,
        request=asdict(request),ledgerSource=calculation.evidence.get('ledgerSource'),limitations=calculation.evidence['limitations'],
        blockingValidation=['REQUIRED_PRICE_INPUTS_MISSING'] if calculation.evidence.get('requiredInputsComplete') is False else [],inputHash=calculation.input_hash,
        inputCoverage=calculation.evidence.get('inputCoverage'),requiredInputsComplete=calculation.evidence.get('requiredInputsComplete',True),
        markOverrideInputs=list({proof['requestId']:proof for s in calculation.evidence.get('selections',[])
            if (proof:=(s.get('pricing_evidence') or {}).get('manualOverride'))}.values()),
        totalsBasis='PRICED_POSITIONS_SUBTOTAL' if calculation.evidence.get('requiredInputsComplete') is False else 'RECORDED_COMPONENTS',
        hasCalculatedContributions=bool(selected),
        accrualCoverage=calculation.evidence.get('accrualCoverage'),
        accruedBalanceCoverage=calculation.evidence.get('accruedBalanceCoverage'),
        accruedBalanceSource=calculation.evidence.get('accruedBalanceSource'),pnlCompleteness=calculation.evidence.get('pnlCompleteness'),
        cashCoverage=cash.coverage if cash else None,cashFxPnl=cash_total,
        resultFormat='POSITION_V2' if calculation.projection is not None else 'TRADE_V1',
        positionEvidence=({ 'engine':calculation.projection.engine_version,'inputHash':calculation.projection.input_hash,
            'completeKnowledge':calculation.projection.complete_knowledge,'factsScanned':calculation.projection.facts_scanned,
            'bucketCount':len(calculation.projection.buckets),'executionCount':len(calculation.projection.executions),
            'requiredMarkCount':calculation.evidence['requiredMarkCount']} if calculation.projection is not None else None)))
    if calculation.projection is not None and any(b.key.product_basis=='FUTURE' for b in calculation.projection.buckets):
        summary.update(futuresVariationPnl=canonical_payload(calculation.period.settlement_variation),
            investmentValueScope='EXCLUDES_FUTURES_NOTIONAL_AND_UNASSESSED_MTM')
    batch=c.execute(t.batch.insert().values(tenant_id=request.tenant_id,strategy_id=request.strategy_id,staged_by=actor,attempt_id=attempt_id,
        value_date=day,status='STAGED',mode=mode,input_hash=calculation.input_hash,base_population_hash=population_hash(official),summary=summary)
        .returning(t.batch.c.batch_id)).scalar_one()
    for owner,attribution in selected.items():
        ownership=cash_owners.get(owner) or ({'position_key':owner} if calculation.projection is not None else {'trade_id':owner})
        c.execute(t.item.insert().values(tenant_id=request.tenant_id,batch_id=batch,attribution_id=attribution,**ownership))
    c.execute(t.review_event.insert().values(batch_id=batch,actor_id=actor,action='STAGED',comment='Calculated P&L attribution staged for review'))
    mark_makers={s['pricing_evidence']['manualOverride']['requestedOperatorId'] for s in calculation.evidence.get('selections',[])
        if (s.get('pricing_evidence') or {}).get('manualOverride')}
    if mark_makers:
        _event(c,attempt_id,'MARK_OVERRIDE_INPUTS','CALCULATION',dict(contributorOperatorIds=sorted(mark_makers)))
    c.execute(t.attempt.update().where(t.attempt.c.attempt_id==attempt_id).values(status='COMPLETED',completed_at=datetime.now(timezone.utc)))
    _event(c,attempt_id,'COMPLETED','STAGING',{'batchId':batch,'attributionCount':len(selected)})
    return batch


def batch_disclosure_views(c,tenant,batch_ids,*,include_evidence=True):
    """Minimal batched history projection; NOT a publication/review view.

    Keep exact evidence consumed by assert_batch_display (including empty/flat
    population proof). Do not fetch financial lines, lineage or review events
    just to authorize a headline. Missing/foreign headers remain absent.
    """
    if not batch_ids: return {}
    headers={row['batch_id']:dict(row,items=[]) for row in c.execute(select(t.batch).where(
        t.batch.c.tenant_id==tenant,t.batch.c.batch_id.in_(set(batch_ids)))).mappings()}
    if headers and include_evidence:
        for row in c.execute(select(t.item.c.batch_id,t.attribution.c.position_key,t.attribution.c.evidence,
                t.attribution.c.cash_account_id,t.attribution.c.cash_currency_id,t.attribution.c.method,t.attribution.c.currency_id)
                .join(t.attribution,t.attribution.c.attribution_id==t.item.c.attribution_id)
                .where(t.item.c.tenant_id==tenant,t.item.c.batch_id.in_(headers))
                .order_by(t.attribution.c.trade_id)).mappings():
            headers[row['batch_id']]['items'].append({key:row[key] for key in ('position_key','evidence','cash_account_id','cash_currency_id','method','currency_id')})
    return headers


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
    mode=c.scalar(select(t.run_event.c.details['reviewMode'].astext).where(t.run_event.c.event_code=='PUBLISHED',
        t.run_event.c.details['batchId'].astext==str(batch_id),t.run_event.c.attempt_id==header['attempt_id'])
        .order_by(t.run_event.c.recorded_at.desc(),t.run_event.c.event_id.desc()).limit(1))
    from .ledger_impacts import source_health
    return dict(header)|dict(items=items,reviews=reviews,publicationReviewMode=mode,sourceHealth=source_health(c,header))


def publish(c, tenant, batch_id, actor, comment,*,real_operator_id=None,self_publication=False):
    header=c.execute(select(t.batch).where(t.batch.c.batch_id==batch_id,t.batch.c.tenant_id==tenant)).mappings().one_or_none()
    if header is None: raise LookupError('Review batch not found')
    _lock(c,tenant,header['strategy_id'],header['value_date'])
    header=c.execute(select(t.batch).where(t.batch.c.batch_id==batch_id).with_for_update()).mappings().one()
    if self_publication:
        from .self_publication import authorize_self_publication
        publication_evidence=authorize_self_publication(c,tenant,header,actor,real_operator_id,lock=True)
    else:
        if actor==header['staged_by']: raise ValueError('Publication requires an independent reviewer')
        from .review_authority import assert_batch_independent
        assert_batch_independent(c,tenant,batch_id,actor,real_operator_id)
        publication_evidence={'reviewMode':'INDEPENDENT'}
    if not isinstance(comment,str) or not comment.strip() or len(comment)>2000: raise ValueError('Review explanation required')
    if header['status']=='PUBLISHED': return batch_id
    if header['status']!='STAGED': raise ValueError('Batch is no longer staged')
    from .price_inputs import assert_complete_prices
    assert_complete_prices(header['summary'])
    from .mark_overrides import assert_current_marks
    assert_current_marks(c,tenant,batch_view(c,tenant,batch_id))
    # Preserve precise per-input diagnostics before the broader source-state
    # check, which also covers coupon revisions and reconstructed history.
    candidate=batch_view(c,tenant,batch_id)['items']
    from .accruals import assert_current_accrual_versions
    assert_current_accrual_versions(c,tenant,candidate)
    from .bond_quote_review import assert_current_normalized_bond_quotes
    assert_current_normalized_bond_quotes(c,tenant,header,candidate)
    from .ledger_impacts import assert_batch_ledger_current
    assert_batch_ledger_current(c,tenant,batch_id)
    if c.scalar(select(t.amendment.c.request_id).where(t.amendment.c.base_batch_id==batch_id,t.amendment.c.status=='PENDING').limit(1)):
        raise ValueError('Resolve pending amendment requests before publication')
    if header['summary'].get('blockingValidation'): raise ValueError('Blocking validation must be resolved before publication')
    # Review the exact selected versions, not just a stored UI summary. This is
    # also a guard against incomplete population edits before publication.
    from .cash_fx_inputs import assert_cash_source_current
    assert_cash_source_current(c,tenant,header)
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
            rounding=sum((Decimal(row['evidence'].get('storageRounding',{}).get('adjustments',{}).get('market','0')) for row in candidate),Decimal(0))
            if rounding!=Decimal(summary.get('marketRoundingAdjustment','0')):
                raise ValueError('Review rounding adjustment and immutable evidence do not reconcile')
            from .futures_pnl import retained_variation
            variation=retained_variation(candidate)
            if variation!=Decimal(summary.get('futuresVariationPnl','0')):
                raise ValueError('Review futures variation and retained inputs do not reconcile')
            if selected_total!=values['marketPnl'] or selected_total!=values['closingValue']-values['openingValue']-values['executionValue']+variation+rounding:
                raise ValueError('Review summary and selected attribution do not reconcile')
            for column,label in [('gross_pnl','grossPnl'),('net_pnl','netPnl')]:
                expected=sum((row[column] for row in candidate),Decimal(0))
                if Decimal(summary.get(label,summary['marketPnl']))!=expected:
                    raise ValueError('Economic review totals do not reconcile')
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
    c.execute(t.review_event.insert().values(batch_id=batch_id,actor_id=actor,action='SELF_PUBLISHED' if self_publication else 'PUBLISHED',comment=comment.strip()))
    _event(c,header['attempt_id'],'PUBLISHED','REVIEW',{'batchId':batch_id,
        'reviewerId':actor,'realOperatorId':real_operator_id or actor,'reason':comment.strip(),**publication_evidence})
    return batch_id
