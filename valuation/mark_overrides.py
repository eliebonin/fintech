"""Governed manual marks fill exact missing inputs, never edit provider prices.

Caller owns the connection/transaction and audit adapter. Approval is independent
of the requester and real operator; every request/decision remains append-only.
"""
from dataclasses import replace
from datetime import date,datetime,timezone
from decimal import Decimal
from uuid import UUID
from sqlalchemy import select,func,exists
from security_master_schema import models as m
from security_master_schema.governance_clock import governance_date
from security_master_schema.strategy_access import require_strategy_action
from security_master_schema.tenant_workspace import resolve_tenant_workspace,require_tenant_action
from security_master_schema.market_data_resolver import ResolutionRequest,resolve_market_data
from market_data.closing_prices import series_filter
from market_data.entitlements import tenant_series_entitlement_clause
from market_data.display_access import assert_dataset_display
from market_data.rights import load_rights
from . import mark_override_tables as t,storage
from .economics import canonical_payload,evidence_hash,finite_decimal
from .price_inputs import gap_identity,may_continue


def _authority(c,tenant,actor,strategy,action):
    workspace=resolve_tenant_workspace(c,tenant,actor,governance_date())
    require_tenant_action(workspace,action)
    if not {'MARKET_DATA','VALUATION'}.issubset(workspace.module_codes):raise PermissionError('Market data and valuation modules required')
    require_strategy_action(c,tenant,actor,action,strategy)


def resolution_request(payload,*,asof=None):
    values=dict(payload)
    for key in ('tenant_id','subject_reference_node_id','valuation_policy_id','valuation_cut_id','strategy_id'):
        if values.get(key):values[key]=UUID(str(values[key]))
    values['valuation_date']=date.fromisoformat(str(values['valuation_date']))
    values['market_data_as_of_utc']=asof or datetime.fromisoformat(values['market_data_as_of_utc'])
    values['series_dimension_filters']=tuple(tuple(x) for x in values.get('series_dimension_filters',()))
    return ResolutionRequest(**values)


def _context(c,tenant,batch_id,input_key,actor,action):
    base=storage.batch_view(c,tenant,batch_id)
    _authority(c,tenant,actor,base['strategy_id'],action)
    from .evidence_access import assert_batch_display
    assert_batch_display(c,tenant,base)
    coverage=base['summary'].get('inputCoverage') or {}
    gaps=[g for g in coverage.get('gaps',[]) if g['inputKey']==input_key]
    if len(gaps)!=1:raise LookupError('Missing-price input not found in this candidate')
    return base,gaps[0]


def _latest(c,request_id,asof=None):
    conditions=[t.decision.c.request_id==request_id]
    if asof:conditions.append(t.decision.c.recorded_at<=asof)
    return c.execute(select(t.decision).where(*conditions).order_by(t.decision.c.recorded_at.desc(),t.decision.c.decision_id.desc()).limit(1)).mappings().one_or_none()


def _lock(c,tenant,strategy,input_key):
    storage.input_revision_lock(c,tenant,strategy)
    lock=int.from_bytes(bytes.fromhex(evidence_hash(dict(tenant=tenant,strategy=strategy,input=input_key)))[:8],'big',signed=True)
    c.execute(select(func.pg_advisory_xact_lock(lock)))


def candidate_series(c,rr,selected):
    """Quotation definitions remain entitled and rule/dimension-compatible."""
    rule=c.execute(select(m.valuation_policy_rule).where(m.valuation_policy_rule.c.valuation_policy_rule_id==selected.policy_rule_id)).mappings().one()
    if not may_continue(rule['missing_data_action'],selected.exception_code):raise ValueError('This rule does not permit reviewed missing-price inputs')
    if rule['value_basis'] not in (None,'RAW') and rule.get('price_requirement')!='AS_TRADED':
        raise ValueError('Reviewed manual marks require an explicit RAW/as-traded quotation rule')
    s=m.market_data_series;conditions=[s.c.reference_node_id==rr.subject_reference_node_id,s.c.status=='ACTIVE',series_filter(s,rule)]
    if rule['market_data_series_id']:conditions.append(s.c.market_data_series_id==rule['market_data_series_id'])
    for code,value in rr.series_dimension_filters:
        d=m.market_data_series_dimension
        conditions.append(exists(select(1).where(d.c.market_data_series_id==s.c.market_data_series_id,d.c.dimension_code==code,d.c.dimension_value==value)))
    priority=(selected.pricing_evidence or {}).get('sourcePriority',{}).get('datasetIds')
    result=[]
    for row in c.execute(select(s).where(*conditions).order_by(s.c.market_data_series_id)).mappings():
        dataset=rule['dataset_id'] or row['default_dataset_id']
        if dataset is None or priority is not None and str(dataset) not in {str(x) for x in priority}:continue
        if not all(c.scalar(select(tenant_series_entitlement_clause(dataset,row['market_data_series_id'],rr.tenant_id,'VALUATION',day)))
                   for day in (rr.valuation_date,governance_date())):continue
        if not load_rights(c,dataset,'NON_DISPLAY',governance_date()).allowed:continue
        try:assert_dataset_display(c,rr.tenant_id,{dataset},series_contexts=[(dataset,row['market_data_series_id'])])
        except PermissionError:continue
        dimensions={}
        for code,value in c.execute(select(m.market_data_series_dimension.c.dimension_code,m.market_data_series_dimension.c.dimension_value).where(
            m.market_data_series_dimension.c.market_data_series_id==row['market_data_series_id'])):dimensions.setdefault(code,set()).add(value)
        result.append(dict(row)|dict(dataset_id=dataset,dimensions=dimensions))
    return result


def _fresh_gap(c,gap):
    rr=resolution_request(gap['request'],asof=c.scalar(select(func.clock_timestamp())))
    selected=resolve_market_data(c,rr)
    if selected.status=='SELECTED':raise ValueError('A policy-eligible source mark is now available; recalculate instead')
    if evidence_hash(gap_identity(rr,selected))!=gap['inputKey']:raise ValueError('Required input scope changed; recalculate before requesting a mark')
    return rr,selected


def quotation_evidence(series):
    """Canonical JSON records dimension values; validation keeps native sets."""
    return canonical_payload(dict(series,dimensions={code:sorted(values) for code,values in series['dimensions'].items()}))


def _validate_quote(series,value,product,quoted_accrual=None,settlement=None,pricing_date=None):
    finite_decimal(value,'manual mark')
    if series['currency_id'] is None:raise ValueError('A governed quote currency is required')
    if series['value_type']=='RATE' and value<=0:raise ValueError('Manual rates must be positive')
    if series['value_type']!='RATE' and (value<0 and product!='SWAP' or value==0 and product not in {'SWAP','OPTION','STRUCTURED_PRODUCT','DIGITAL_ASSET'}):
        raise ValueError('Manual mark sign is incompatible with the product quotation')
    quote=series['dimensions'].get('BOND_PRICE_TYPE',set())
    if product=='BOND' and quote=={'DIRTY'}:
        if quoted_accrual is None or settlement is None or settlement<pricing_date:raise ValueError('DIRTY manual mark requires paired quoted accrual per 100 and a valid quote settlement date')
        finite_decimal(quoted_accrual,'quoted accrual')
        from market_data.bond_quotes import clean_quote,per_100_quote
        if not per_100_quote(series['dimensions'].get('QUOTE_FACTOR',set())):raise ValueError('DIRTY override requires a per-100 quote')
        clean_quote(value,quoted_accrual)
    elif quoted_accrual is not None or settlement is not None:raise ValueError('Quoted accrual is only valid with a DIRTY bond quotation')


def request_mark(c,tenant,actor,payload,key,*,real_operator_id=None):
    base,gap=_context(c,tenant,payload.base_batch_id,payload.input_key,actor,'VALUATION_RUN')
    if not isinstance(key,str) or not key.strip() or len(key)>255:raise ValueError('Request key required')
    if base['status']!='STAGED':raise ValueError('Manual marks require a staged candidate; recalculate this historical result')
    _lock(c,tenant,base['strategy_id'],gap['inputKey'])
    digest=evidence_hash(dict(payload=payload.model_dump(mode='json',by_alias=True),actor=actor,realOperator=real_operator_id or actor))
    old=c.execute(select(t.request).where(t.request.c.tenant_id==tenant,t.request.c.submission_key==key)).mappings().one_or_none()
    if old:
        if old['request_hash']!=digest:raise ValueError('Manual mark request key reused for different inputs or operator')
        return old['request_id']
    rr,selected=_fresh_gap(c,gap)
    series=next((s for s in candidate_series(c,rr,selected) if s['market_data_series_id']==payload.series_id),None)
    if series is None:raise PermissionError('Quoted series is unavailable, unentitled or incompatible with this required input')
    positions=[p for p in base['summary']['inputCoverage']['unpricedPositions'] if gap['inputKey'] in p['inputKeys']]
    if gap['role']=='PRICE' and {p['currencyId'] for p in positions}!={str(series['currency_id'])}:
        raise ValueError('Manual quote currency must match frozen trade-price currency')
    products={p['product'] for p in positions};product='FX' if gap['role'] in {'FX','CASH_FX'} else next(iter(products))
    _validate_quote(series,payload.value,product,payload.quoted_accrual_per_100,payload.quote_settlement_date,selected.pricing_date_requested)
    context=canonical_payload(dict(gap=gap,product=product,series=quotation_evidence(series),quoteBasisAcknowledged=True))
    identity=c.scalar(t.request.insert().values(tenant_id=tenant,strategy_id=base['strategy_id'],base_batch_id=payload.base_batch_id,
        input_key=gap['inputKey'],series_id=payload.series_id,currency_id=series['currency_id'],value_date=selected.pricing_date_requested,
        value=payload.value,quoted_accrual_per_100=payload.quoted_accrual_per_100,quote_settlement_date=payload.quote_settlement_date,
        reason=payload.reason,source_reference=payload.source_reference,requested_by=actor,real_operator_id=real_operator_id or actor,
        request_context=context,request_hash=digest,submission_key=key).returning(t.request.c.request_id))
    storage._event(c,base['attempt_id'],'MARK_OVERRIDE_REQUESTED','INPUT_REVIEW',dict(requestId=identity,realOperatorId=real_operator_id or actor))
    return identity


def decide_mark(c,tenant,request_id,actor,action,comment,*,real_operator_id=None):
    row=c.execute(select(t.request).where(t.request.c.request_id==request_id,t.request.c.tenant_id==tenant)).mappings().one_or_none()
    if row is None:raise LookupError('Manual mark request not found')
    _authority(c,tenant,actor,row['strategy_id'],'VALUATION_REVIEW')
    if action not in {'APPROVED','REJECTED','WITHDRAWN'} or not isinstance(comment,str) or not comment.strip() or len(comment)>2000:raise ValueError('A valid review decision and explanation are required')
    if actor==row['requested_by']:raise PermissionError('An independent manual-mark reviewer is required')
    from .review_authority import assert_independent,OperatorLineage
    assert_independent(OperatorLineage(frozenset({row['real_operator_id']}),True),actor,real_operator_id)
    _lock(c,tenant,row['strategy_id'],row['input_key']);old=_latest(c,request_id)
    if old and old['action']==action:
        if old['reviewed_by']!=actor or old['real_operator_id']!=(real_operator_id or actor) or old['comment']!=comment.strip():raise ValueError('Decision already recorded by another review or explanation')
        return old['decision_id']
    if old and (action!='WITHDRAWN' or old['action']!='APPROVED') or not old and action=='WITHDRAWN':raise ValueError('This request is no longer pending or withdrawable')
    if action=='APPROVED':
        base,gap=_context(c,tenant,row['base_batch_id'],row['input_key'],actor,'VALUATION_REVIEW')
        from .ledger_impacts import assert_batch_ledger_current
        assert_batch_ledger_current(c,tenant,row['base_batch_id'])
        rr,selected=_fresh_gap(c,gap)
        series=next((s for s in candidate_series(c,rr,selected) if s['market_data_series_id']==row['series_id']),None)
        if series is None or quotation_evidence(series)!=row['request_context']['series']:raise ValueError('Manual quote definition or its authority changed; submit a new request')
        _validate_quote(series,row['value'],row['request_context']['product'],row['quoted_accrual_per_100'],row['quote_settlement_date'],row['value_date'])
    decision=c.scalar(t.decision.insert().values(request_id=request_id,tenant_id=tenant,action=action,reviewed_by=actor,
        real_operator_id=real_operator_id or actor,comment=comment.strip()).returning(t.decision.c.decision_id))
    attempt=c.scalar(select(storage.t.batch.c.attempt_id).where(storage.t.batch.c.batch_id==row['base_batch_id']))
    storage._event(c,attempt,'MARK_OVERRIDE_'+action,'INPUT_REVIEW',dict(requestId=request_id,decisionId=decision,reviewerId=actor,realOperatorId=real_operator_id or actor))
    return decision


def approved_mark(c,rr,selected):
    """Use only a currently entitled exact-scope approval known by this cutoff."""
    key=evidence_hash(gap_identity(rr,selected));asof=rr.market_data_as_of_utc
    last_approval=c.execute(select(t.decision).join(t.request).where(t.request.c.tenant_id==rr.tenant_id,
        t.request.c.strategy_id==rr.strategy_id,t.request.c.input_key==key,t.request.c.recorded_at<=asof,
        t.decision.c.recorded_at<=asof,t.decision.c.action=='APPROVED')
        .order_by(t.decision.c.recorded_at.desc(),t.decision.c.decision_id.desc()).limit(1)).mappings().one_or_none()
    if last_approval is None:return None
    row=c.execute(select(t.request).where(t.request.c.request_id==last_approval['request_id'])).mappings().one()
    decision=_latest(c,row['request_id'],asof)
    # Withdrawal never silently revives a superseded older approved price.
    if decision is None or decision['action']!='APPROVED':return None
    series=next((s for s in candidate_series(c,rr,selected) if s['market_data_series_id']==row['series_id']),None)
    if series is None:raise PermissionError('Reviewed manual mark quotation or current source rights are unavailable')
    if quotation_evidence(series)!=row['request_context']['series']:raise ValueError('Reviewed manual mark quotation changed; reassessment required')
    _validate_quote(series,row['value'],row['request_context']['product'],row['quoted_accrual_per_100'],row['quote_settlement_date'],row['value_date'])
    proof=canonical_payload(dict(requestId=row['request_id'],decisionId=decision['decision_id'],inputKey=key,
        origin='TENANT_REVIEWED_MARK',value=row['value'],currencyId=row['currency_id'],valueDate=row['value_date'],
        requestedBy=row['requested_by'],requestedOperatorId=row['real_operator_id'],reviewedBy=decision['reviewed_by'],
        reviewedOperatorId=decision['real_operator_id'],reviewedAt=decision['recorded_at'],reason=row['reason'],sourceReference=row['source_reference'],
        quotedAccrualPer100=row['quoted_accrual_per_100'],quoteSettlementDate=row['quote_settlement_date']))
    rule=c.execute(select(m.valuation_policy_rule).where(m.valuation_policy_rule.c.valuation_policy_rule_id==selected.policy_rule_id)).mappings().one()
    pricing=dict(selected.pricing_evidence or {},manualOverride=proof)
    if rule.get('price_requirement')=='AS_TRADED':
        pricing['priceBasis']=dict(method='REVIEWED_MANUAL_AS_TRADED',sourceBasis='RAW',overrideId=str(row['request_id']))
    return replace(selected,status='SELECTED',market_data_series_id=row['series_id'],market_data_observation_id=None,
        market_data_vintage_id=None,dataset_id=series['dataset_id'],acquisition_licence_id=None,currency_id=row['currency_id'],
        selected_value=row['value'],source_published_at_utc=decision['recorded_at'],received_at_utc=decision['recorded_at'],
        pricing_date_used=row['value_date'],staleness_business_days=0,staleness_status='CURRENT',
        selection_reason='REVIEWED_MANUAL_OVERRIDE',entitlement_decision='ALLOWED',exception_code=None,
        pricing_evidence=pricing,valuation_value=row['value'] if rule.get('price_requirement')=='AS_TRADED' else None,
        valuation_basis='AS_TRADED' if rule.get('price_requirement')=='AS_TRADED' else None,price_basis_evidence=pricing.get('priceBasis'))


def assert_current_marks(c,tenant,batch):
    for item in batch['items']:
        for selection in item['evidence'].get('selections',[]):
            proof=(selection.get('pricing_evidence') or {}).get('manualOverride')
            if not proof:continue
            row=c.execute(select(t.request).where(t.request.c.request_id==UUID(proof['requestId']),t.request.c.tenant_id==tenant)).mappings().one_or_none()
            if row is None:raise ValueError('Reviewed manual mark evidence is unavailable')
            decision=_latest(c,row['request_id'])
            if not decision or decision['action']!='APPROVED' or str(decision['decision_id'])!=proof['decisionId']:
                raise ValueError('Reviewed manual mark override changed or was withdrawn; recalculate')
            rr,missing=_fresh_gap(c,row['request_context']['gap'])
            current=approved_mark(c,rr,missing)
            if current is None or current.pricing_evidence['manualOverride']!=proof:
                raise ValueError('Reviewed manual mark override changed; recalculate')


def review_view(c,tenant,actor,batch_id,*,real_operator_id=None):
    base=storage.batch_view(c,tenant,batch_id)
    _authority(c,tenant,actor,base['strategy_id'],'VALUATION_READ')
    from .evidence_access import assert_batch_display
    assert_batch_display(c,tenant,base)
    def allowed(action):
        try:_authority(c,tenant,actor,base['strategy_id'],action);return True
        except PermissionError:return False
    can_request=allowed('VALUATION_RUN');can_review=allowed('VALUATION_REVIEW')
    gaps=[]
    for gap in (base['summary'].get('inputCoverage') or {}).get('gaps',[]):
        options=[];notice=None
        try:
            rr,selected=_fresh_gap(c,gap)
            for s in candidate_series(c,rr,selected):
                currency=c.scalar(select(m.currency.c.currency_code).where(m.currency.c.currency_id==s['currency_id']))
                dataset=c.scalar(select(m.dataset.c.display_name).where(m.dataset.c.dataset_id==s['dataset_id']))
                options.append(dict(seriesId=s['market_data_series_id'],label=f'{dataset} · {s["series_type"]} · {currency}',
                    currency=currency,dirtyBond=s['dimensions'].get('BOND_PRICE_TYPE')=={'DIRTY'}))
        except (ValueError,PermissionError) as exc:notice=str(exc)
        gaps.append(dict(inputKey=gap['inputKey'],subjectId=gap['request']['subject_reference_node_id'],
            valueDate=gap['selection']['pricing_date_requested'],role=gap['role'],options=options,notice=notice))
    keys={g['inputKey'] for g in gaps};used=set()
    for item in base['items']:
        for selection in item['evidence'].get('selections',[]):
            proof=(selection.get('pricing_evidence') or {}).get('manualOverride')
            if proof:used.add(UUID(proof['requestId']))
    rows=c.execute(select(t.request).where(t.request.c.tenant_id==tenant,t.request.c.strategy_id==base['strategy_id'],
        (t.request.c.base_batch_id==batch_id)|(t.request.c.input_key.in_(keys))|(t.request.c.request_id.in_(used))).order_by(t.request.c.recorded_at.desc())).mappings().all()
    requests=[]
    for row in rows:
        s=row['request_context']['series'];dataset=UUID(s['dataset_id'])
        assert_dataset_display(c,tenant,{dataset},series_contexts=[(dataset,row['series_id'])])
        last=_latest(c,row['request_id']);status=last['action'] if last else 'PENDING'
        independent=actor!=row['requested_by'] and (real_operator_id or actor)!=row['real_operator_id']
        currency=c.scalar(select(m.currency.c.currency_code).where(m.currency.c.currency_id==row['currency_id']))
        requests.append(dict(requestId=row['request_id'],inputKey=row['input_key'],valueDate=row['value_date'],value=row['value'],currency=currency,
            subjectId=row['request_context']['gap']['request']['subject_reference_node_id'],reason=row['reason'],sourceReference=row['source_reference'],
            requestedBy=row['requested_by'],reviewedBy=last['reviewed_by'] if last else None,reviewComment=last['comment'] if last else None,
            status=status,canReview=can_review and independent and status=='PENDING',canWithdraw=can_review and independent and status=='APPROVED'))
    return canonical_payload(dict(gaps=gaps,requests=requests,canRequest=can_request and base['status']=='STAGED',canReview=can_review))
