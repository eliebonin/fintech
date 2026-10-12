"""Supported economic position P&L from independently frozen input evidence."""
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timedelta
from uuid import UUID
from sqlalchemy import select
from security_master_schema import models as m
from security_master_schema.market_data_resolver import ResolutionRequest, resolve_market_data, persist_resolution_snapshot
from positions.contracts import PositionProjection
from .economics import evidence_hash, canonical_payload
from .positions import aware
from .position_calculation import PositionPeriodAttribution

METHOD = 'listed-equity-market-pnl-v1'
POSITION_METHOD = 'economic-position-pnl-v3'


class ValuationBlocked(ValueError):
    """A required economic or market-data input cannot safely be calculated."""
    code = 'valuation.blocked'


@dataclass(frozen=True)
class ValuationRequest:
    tenant_id: UUID
    strategy_id: UUID
    policy_id: UUID
    cut_id: UUID
    reporting_currency_id: UUID
    opening_cutoff: datetime
    closing_cutoff: datetime
    information_cutoff: datetime
    daily: bool = False
    predecessor_batch_id: UUID | None = None
    recalculation_reason: str | None = None


@dataclass(frozen=True)
class Calculation:
    request: ValuationRequest
    period: PositionPeriodAttribution
    resolution_snapshot_ids: tuple[UUID, ...]
    evidence: dict
    input_hash: str
    scope: str = 'MARKET_ONLY'
    external_comparison: str = 'NOT_COMPARED'
    projection: PositionProjection | None = None
    method: str = POSITION_METHOD

    @property
    def gross_pnl(self):
        from decimal import Decimal,localcontext
        with localcontext() as ctx:
            ctx.prec=512
            return sum((l.gross_pnl for l in self.period.lines),Decimal(0))

    @property
    def net_pnl(self):
        from decimal import Decimal,localcontext
        with localcontext() as ctx:
            ctx.prec=512
            return sum((l.net_pnl for l in self.period.lines),Decimal(0))




def _selection(c, request, subject, economic_cutoff,product='EQUITY'):
    day=economic_cutoff.date()
    selection_request=ResolutionRequest(request.tenant_id,subject,request.policy_id,day,request.cut_id,
        request.information_cutoff,'VALUATION',request.strategy_id)
    selected=resolve_market_data(c,selection_request)
    if selected.status!='SELECTED':
        from market_data.policy_compatibility import missing_input_message
        rule=c.execute(select(m.valuation_policy_rule).where(m.valuation_policy_rule.c.valuation_policy_rule_id==selected.policy_rule_id)).mappings().one_or_none()
        raise ValuationBlocked(missing_input_message(c,request.tenant_id,subject,day,rule,selected.exception_code or selected.status))
    series=c.execute(select(m.market_data_series).where(m.market_data_series.c.market_data_series_id==selected.market_data_series_id)).mappings().one()
    rule=c.execute(select(m.valuation_policy_rule).where(m.valuation_policy_rule.c.valuation_policy_rule_id==selected.policy_rule_id)).mappings().one()
    normalized = (rule.get('price_requirement')=='AS_TRADED' and selected.valuation_basis=='AS_TRADED'
        and selected.valuation_value is not None and (selected.pricing_evidence or {}).get('priceBasis'))
    permitted=('OFFICIAL_NAV','NAV') if product=='FUND' else ('CLOSE','OFFICIAL_CLOSE')
    if series['value_type']!='PRICE' or rule['series_type'] not in permitted or not (normalized or rule['value_basis']=='RAW'):
        raise ValuationBlocked('As-traded price with verified proof or explicit native RAW basis required')
    evidence=selected.pricing_evidence or {}
    convention='NAV_DATE' if product=='FUND' else rule['pricing_convention']
    sources=('TENANT_PUBLISHED_SCHEDULE','GOVERNED_SESSIONS') if product=='FUND' else ('GOVERNED_SESSIONS',)
    if (rule['pricing_convention']!=convention or (product!='FUND' and convention not in ('SESSION_CLOSE','EXPLICIT_TIME'))
        or (convention=='EXPLICIT_TIME' and product!='BOND') or evidence.get('calendarEvidence',{}).get('source') not in sources):
        raise ValuationBlocked('Explicit governed session calendar required; legacy weekday fallback is not valuation-ready')
    if not (evidence['calendarEvidence'].get('sealed') or evidence['calendarEvidence'].get('source')=='TENANT_PUBLISHED_SCHEDULE'):
        raise ValuationBlocked('A sealed reference calendar version is required for reproducible valuation')
    # Information known today must not turn a later session into a mark for an
    # earlier economic position cutoff on that same historical date.
    try:
        target=datetime.fromisoformat(evidence['pricingTargetUtc'])
        aware(target)
    except (KeyError,TypeError,ValueError) as exc:
        raise ValuationBlocked('Missing frozen session pricing target') from exc
    if target>economic_cutoff:
        raise ValuationBlocked('Session pricing target is later than the economic cutoff')
    # Flexibility does not grant freshness. Only a chosen rule's explicit,
    # bounded allowance can authorise carrying a prior expected-session mark.
    if selected.staleness_status!='CURRENT' and not (
        selected.staleness_status=='WITHIN_TOLERANCE'
        and rule['pricing_date_rule'] in ('PRIOR_AVAILABLE','FIXED_LAG')
        and rule['max_staleness_business_days'] is not None
        and selected.staleness_business_days is not None
        and 0 <= selected.staleness_business_days <= rule['max_staleness_business_days']
    ):
        raise ValuationBlocked('Current price or explicit bounded freshness allowance required')
    measure=c.scalar(select(m.series_measure_definition.c.measure_code).where(
        m.series_measure_definition.c.series_measure_definition_id==series['measure_definition_id']))
    if measure!='PRICE': raise ValuationBlocked('Governed PRICE measurement semantics required')
    return selection_request,selected




def calculate_position(c, request: ValuationRequest) -> Calculation:
    """V2 consumes position state and movements; historical executions are lineage."""
    from positions.contracts import ProjectionRequest,PositionError
    from positions.repository import iter_ledger_facts
    from positions.reconstruction import reconstruct
    from .position_calculation import required_marks,attribute_projection
    from .corporate_actions import assert_projection_actions
    for cutoff in (request.opening_cutoff,request.closing_cutoff,request.information_cutoff):
        aware(cutoff)
        if cutoff.utcoffset()!=timedelta(0): raise ValuationBlocked('UTC cutoffs required')
    if request.closing_cutoff<=request.opening_cutoff or request.information_cutoff<request.closing_cutoff:
        raise ValuationBlocked('Invalid economic/information cutoff ordering')
    if bool(request.predecessor_batch_id)!=bool(request.recalculation_reason):
        raise ValuationBlocked('Corrected-input calculation requires predecessor and reason together')
    if request.predecessor_batch_id:
        from .storage import batch_view
        from .evidence_access import assert_batch_display
        prior=batch_view(c,request.tenant_id,request.predecessor_batch_id)
        assert_batch_display(c,request.tenant_id,prior)
        if prior['strategy_id']!=request.strategy_id or prior['value_date']!=request.closing_cutoff.date():
            raise ValuationBlocked('Corrected-input predecessor scope differs from requested strategy/date')
        if prior['summary']['request']['opening_cutoff']!=request.opening_cutoff.isoformat():
            raise ValuationBlocked('Corrected-input predecessor period differs from requested period')
    projection_request=ProjectionRequest(request.tenant_id,request.strategy_id,request.closing_cutoff,
        request.information_cutoff,request.opening_cutoff,'PERIOD',request.daily)
    # A zero/no-mark result does not bypass request governance. Resolver checks
    # still govern actual price inputs; this validates the unpriced request too.
    policy=c.execute(select(m.valuation_policy).where(m.valuation_policy.c.valuation_policy_id==request.policy_id,
        m.valuation_policy.c.tenant_id==request.tenant_id)).mappings().one_or_none()
    if (policy is None or policy['status']!='ACTIVE' or policy['valid_from']>request.closing_cutoff.date()
        or (policy['valid_to'] is not None and policy['valid_to']<request.closing_cutoff.date())
        or (policy['strategy_id'] is not None and policy['strategy_id']!=request.strategy_id)
        or policy['created_at_utc']>request.information_cutoff):
        raise ValuationBlocked('Active tenant pricing policy valid at the requested cutoffs required')
    if not c.scalar(select(m.valuation_cut.c.valuation_cut_id).where(m.valuation_cut.c.valuation_cut_id==request.cut_id)):
        raise ValuationBlocked('Known valuation cut required')
    if not c.scalar(select(m.currency.c.currency_id).where(m.currency.c.currency_id==request.reporting_currency_id,m.currency.c.status=='ACTIVE')):
        raise ValuationBlocked('Active reporting currency required')
    try: projection=reconstruct(iter_ledger_facts(c,projection_request),projection_request)
    except PositionError as exc: raise ValuationBlocked(str(exc)) from exc
    assert_projection_actions(c,projection,ValuationBlocked)
    marks={}; selected_evidence=[]; snapshot_ids=[]; conversions={};fx_inputs={}
    # Foreign multi-day calculations aggregate daily bridges so each execution
    # is translated at its own economic day's end-rate, not the period end.
    daily_projections=[projection]
    foreign=any(b.key.currency_id!=request.reporting_currency_id for b in projection.buckets)
    if foreign and (request.closing_cutoff-request.opening_cutoff)>timedelta(days=1):
        daily_projections=[];boundary=request.opening_cutoff
        while boundary<request.closing_cutoff:
            end=min(boundary+timedelta(days=1),request.closing_cutoff)
            daily_projections.append(reconstruct(projection.facts,replace(projection_request,opening_cutoff=boundary,closing_cutoff=end)))
            boundary=end
    requirements=tuple({r.key:r for p in daily_projections for r in required_marks(p)}.values())
    for cutoff in sorted({r.key.cutoff for r in requirements}):
        selections={}; first=None
        for requirement in (r for r in requirements if r.key.cutoff==cutoff):
            products={b.key.product_basis for b in projection.buckets if b.key.subject_id==requirement.key.subject_id}
            if len(products)!=1: raise ValuationBlocked('Incompatible product valuation conventions on the same subject')
            product=next(iter(products))
            subject=requirement.key.subject_id
            if product=='FUND':
                parents={UUID(f.booking.product_evidence['instrumentId']) for f in projection.facts
                    if f.booking and f.booking.subject_id==subject and f.booking.product_evidence}
                if len(parents)!=1: raise ValuationBlocked('Unique frozen canonical fund NAV identity required')
                subject=next(iter(parents))
                from .product_inputs import prepare_product_inputs
                for bucket in (b for b in projection.buckets if b.key.subject_id==requirement.key.subject_id):
                    try: prepare_product_inputs(c,request,bucket,{})
                    except ValueError as exc: raise ValuationBlocked(str(exc)) from exc
            cached=selections.get(subject)
            selection_request,selected=cached if cached else _selection(c,request,subject,cutoff,product)
            if product=='BOND':
                dims=m.market_data_series_dimension
                quote_types=set(c.scalars(select(dims.c.dimension_value).where(dims.c.market_data_series_id==selected.market_data_series_id,
                    dims.c.dimension_code=='BOND_PRICE_TYPE')))
                from .product_inputs import prepare_product_inputs
                for bucket in (b for b in projection.buckets if b.key.subject_id==requirement.key.subject_id):
                    try: prepare_product_inputs(c,request,bucket,{'bondPriceType':next(iter(quote_types)) if len(quote_types)==1 else None})
                    except ValueError as exc: raise ValuationBlocked(str(exc)) from exc
            first=first or selection_request; selections[subject]=(selection_request,selected)
            expected={b.key.currency_id for b in projection.buckets if b.key.subject_id==requirement.key.subject_id}
            if expected!={selected.currency_id}:
                raise ValuationBlocked('Selected market price currency differs from frozen trade currency; explicit normalization required')
            marks[requirement.key]=selected.valuation_value if selected.valuation_value is not None else selected.selected_value
            selected_evidence.append(dict(asdict(selected),valuation_date=cutoff.date(),
                valuation_position_subject_id=requirement.key.subject_id))
        snapshot_ids.append(persist_resolution_snapshot(c,first,tuple(s[1] for s in selections.values())))
    from .fx import resolve_fx
    try:
        for p in daily_projections:
            for bucket in p.buckets:
                cutoffs=[p.request.closing_cutoff]
                if bucket.opening_quantity: cutoffs.append(p.request.opening_cutoff)
                for cutoff in cutoffs:
                    key=(bucket.key.currency_id,cutoff)
                    if key in conversions: continue
                    conversion=resolve_fx(c,request,bucket.key.currency_id,request.reporting_currency_id,cutoff.date())
                    conversions[key]=conversion;fx_inputs[key]=conversion.rate
                    if conversion.selection:
                        proof=conversion.selection.pricing_evidence or {}
                        if datetime.fromisoformat(proof['pricingTargetUtc'])>cutoff:
                            raise ValueError('FX pricing target is later than economic cutoff')
                        snapshot_ids.append(persist_resolution_snapshot(c,conversion.resolution_request,(conversion.selection,)))
                        selected_evidence.append(dict(asdict(conversion.selection),valuation_date=cutoff.date(),input_role='FX',
                            valuation_source_currency_id=bucket.key.currency_id,conversion=conversion.evidence))
        periods=[attribute_projection(p,marks,request.reporting_currency_id,fx_inputs) for p in daily_projections]
        period=periods[0] if len(periods)==1 else aggregate_daily_periods(projection,periods)
    except ValueError as exc: raise ValuationBlocked(str(exc)) from exc
    from .flows import load_economic_flows,attach_flows
    try: flows=load_economic_flows(c,request)
    except ValueError as exc: raise ValuationBlocked(str(exc)) from exc
    from .accruals import load_accrual_inputs,attach_accruals
    try:
        accruals=load_accrual_inputs(c,request,projection)
        period=attach_accruals(period,accruals)
    except ValueError as exc: raise ValuationBlocked(str(exc)) from exc
    # Interest coverage reconstructs actual investment exposure. Monetary flows
    # are appended afterwards solely for result ownership/ledger lineage.
    projection,period=attach_flows(projection,period,flows)
    for flow in flows:
        if flow.fx.selection:
            snapshot_ids.append(persist_resolution_snapshot(c,flow.fx.resolution_request,(flow.fx.selection,)))
            selected_evidence.append(dict(asdict(flow.fx.selection),valuation_date=flow.economic_date,input_role='FX',
                valuation_source_currency_id=flow.currency_id,conversion=flow.fx.evidence))
    for accrual in accruals:
        for proof in accrual.payload.get('fxEvidence',[]):
            if proof.get('selection'):
                selected_evidence.append(dict(proof['selection'],valuation_date=accrual.value_date,input_role='FX',
                    valuation_source_currency_id=accrual.payload['currencyId'],conversion=proof))
    scope='ECONOMIC_RECORDED_INPUTS' if accruals else 'ECONOMIC_RECORDED_FLOWS' if flows else 'MARKET_ONLY'
    evidence=canonical_payload(dict(request=asdict(request),method=POSITION_METHOD,resultFormat='POSITION_V2',
        projection=asdict(projection),events=[asdict(fact) for fact in projection.facts],selections=selected_evidence,
        fxConversions=[dict(sourceCurrencyId=fx.source_currency_id,targetCurrencyId=fx.target_currency_id,
            rate=fx.rate,economicDate=fx.economic_date,observationDate=fx.observation_date,evidence=fx.evidence) for fx in conversions.values()],
        economicFlows=[f.evidence for f in flows],
        dailyAccrualInputs=[dict(inputId=a.input_id,revision=a.revision,payload=a.payload) for a in accruals],
        executionFxConvention='ECONOMIC_DAY_END',dailyBridgeCount=len(periods),requiredMarkCount=len(requirements),scope=scope,limitations=['UNBOOKED_INCOME_NOT_INCLUDED',
        'CORPORATE_ACTIONS_NOT_REPLAYED','CASH_NOT_VALUED','NOT_FULL_NAV'],externalComparison='NOT_COMPARED'))
    return Calculation(request,period,tuple(snapshot_ids),evidence,evidence_hash(evidence),
        projection=projection,method=POSITION_METHOD,scope=scope)


# One authoritative execution path; historical v1 calculation is test-only.
calculate = calculate_position


def aggregate_daily_periods(projection,periods):
    """Reconcile daily attribution against the original period boundaries."""
    from collections import defaultdict
    from decimal import Decimal,localcontext
    from .position_calculation import PositionLine
    from .economics import MarketAttribution
    groups=defaultdict(list)
    for period in periods:
        for line in period.lines: groups[line.bucket.key].append(line)
    lines=[]
    with localcontext() as ctx:
        ctx.prec=512
        for bucket in projection.buckets:
            rows=groups[bucket.key]
            amounts=[sum((getattr(row.attribution,name) for row in rows),Decimal(0)) for name in ('price','fx','cross','market_pnl')]
            opening=rows[0].attribution.opening_value if bucket.opening_quantity else Decimal(0)
            closing=rows[-1].attribution.closing_value if bucket.closing_quantity else Decimal(0)
            execution=sum((row.execution_value for row in rows),Decimal(0))
            if amounts[3]!=closing-opening-execution: raise ValuationBlocked('Daily FX bridges do not reconcile')
            lines.append(PositionLine(bucket,MarketAttribution(*amounts,opening,closing),execution))
        return PositionPeriodAttribution(tuple(lines),sum((l.attribution.market_pnl for l in lines),Decimal(0)),
            sum((l.attribution.opening_value for l in lines),Decimal(0)),sum((l.attribution.closing_value for l in lines),Decimal(0)),
            sum((l.execution_value for l in lines),Decimal(0)))
