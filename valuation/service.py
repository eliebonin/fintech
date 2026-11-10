"""Supported economic position P&L from independently frozen input evidence."""
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID
from sqlalchemy import select
from security_master_schema import models as m
from security_master_schema.market_data_resolver import ResolutionRequest, resolve_market_data, persist_resolution_snapshot
from positions.contracts import PositionProjection
from .economics import evidence_hash, canonical_payload
from .positions import aware
from .position_calculation import PositionPeriodAttribution
from .cash_fx import CashFxResult
from security_master_schema.cash_products import QUOTED_WRAPPERS

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
    require_complete_accruals: bool = False


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
    cash: CashFxResult | None = None
    accrued_balance: object | None = None
    receivables: tuple = ()

    @property
    def gross_pnl(self):
        from decimal import Decimal,localcontext
        with localcontext() as ctx:
            ctx.prec=512
            return sum((l.gross_pnl for l in self.period.lines),Decimal(0)) + (self.cash.amount if self.cash else Decimal(0)) + sum((l.amount for l in self.receivables),Decimal(0))

    @property
    def net_pnl(self):
        from decimal import Decimal,localcontext
        with localcontext() as ctx:
            ctx.prec=512
            return sum((l.net_pnl for l in self.period.lines),Decimal(0)) + (self.cash.amount if self.cash else Decimal(0)) + sum((l.amount for l in self.receivables),Decimal(0))




def _selection(c, request, subject, economic_cutoff,product='EQUITY',*,dimension_filters=()):
    day=economic_cutoff.date()
    selection_request=ResolutionRequest(request.tenant_id,subject,request.policy_id,day,request.cut_id,
        request.information_cutoff,'VALUATION',request.strategy_id,dimension_filters)
    from .price_inputs import resolve_input
    selected=resolve_input(c,selection_request,resolve_market_data)
    if selected.status!='SELECTED':
        from market_data.policy_compatibility import missing_input_message
        rule=c.execute(select(m.valuation_policy_rule).where(m.valuation_policy_rule.c.valuation_policy_rule_id==selected.policy_rule_id)).mappings().one_or_none()
        raise ValuationBlocked(missing_input_message(c,request.tenant_id,subject,day,rule,selected.exception_code or selected.status))
    series=c.execute(select(m.market_data_series).where(m.market_data_series.c.market_data_series_id==selected.market_data_series_id)).mappings().one()
    rule=c.execute(select(m.valuation_policy_rule).where(m.valuation_policy_rule.c.valuation_policy_rule_id==selected.policy_rule_id)).mappings().one()
    normalized = (rule.get('price_requirement')=='AS_TRADED' and selected.valuation_basis=='AS_TRADED'
        and selected.valuation_value is not None and (selected.pricing_evidence or {}).get('priceBasis'))
    permitted=('OFFICIAL_NAV','NAV') if product=='FUND' else ('CLOSE','OFFICIAL_CLOSE')
    if product in QUOTED_WRAPPERS|{'DIGITAL_ASSET'}:permitted=(*permitted,'MARK')
    if product=='DIGITAL_ASSET':
        proof=(selected.pricing_evidence or {}).get('priceBasis')
        # The resolver filters native basis directly, or freezes the actual
        # source basis in AS_TRADED proof. No per-mark observation reread.
        source_basis=proof.get('sourceBasis') if proof else rule['value_basis']
        if source_basis!='RAW' or proof and proof.get('method')!='NATIVE_RAW':
            raise ValuationBlocked('Native RAW spot-crypto quotation required; share-split conversion is not token-unit evidence')
    if product in ('SWAP','OPTION','STRUCTURED_PRODUCT'):
        permitted=(*permitted,'MARK')
        if product=='OPTION':permitted=(*permitted,'SETTLEMENT')
        if rule['value_basis']!='RAW' or rule.get('price_requirement'):
            raise ValuationBlocked('Native RAW derivative contract marks required; share-price normalization is not applicable')
        dimensions={}
        for code,value in c.execute(select(m.market_data_series_dimension.c.dimension_code,m.market_data_series_dimension.c.dimension_value)
            .where(m.market_data_series_dimension.c.market_data_series_id==selected.market_data_series_id)):
            dimensions.setdefault(code,set()).add(value)
        if not dimension_filters or any(dimensions.get(code)!={value} for code,value in dimension_filters):
            raise ValuationBlocked('Unambiguous derivative contract mark units and quote divisor required')
    if product=='FUTURE':
        permitted=(*permitted,'SETTLEMENT')
        if rule['value_basis']!='RAW' or rule.get('price_requirement'):
            raise ValuationBlocked('Exact-contract native RAW futures prices required; share-price normalization is not applicable')
        dims={}
        for code,value in c.execute(select(m.market_data_series_dimension.c.dimension_code,m.market_data_series_dimension.c.dimension_value)
                .where(m.market_data_series_dimension.c.market_data_series_id==selected.market_data_series_id)):
            dims.setdefault(code,set()).add(value)
        if not dimension_filters or any(dims.get(code)!={value} for code,value in dimension_filters):
            raise ValuationBlocked('Exact futures contract and quotation dimensions required')
    index_level=(product=='INDEX' and series['series_type']=='INDEX_LEVEL' and series['value_type']=='INDEX_LEVEL'
        and rule['series_type']=='INDEX_LEVEL' and rule['value_basis']=='INDEX_LEVEL')
    if not index_level and (series['value_type']!='PRICE' or rule['series_type'] not in permitted or not (normalized or rule['value_basis']=='RAW')):
        raise ValuationBlocked('As-traded price with verified proof or explicit native RAW basis required')
    evidence=selected.pricing_evidence or {}
    convention='NAV_DATE' if product=='FUND' else rule['pricing_convention']
    sources=('TENANT_PUBLISHED_SCHEDULE','GOVERNED_SESSIONS') if product=='FUND' else ('GOVERNED_SESSIONS',)
    if (rule['pricing_convention']!=convention or (product!='FUND' and convention not in ('SESSION_CLOSE','EXPLICIT_TIME'))
        or (convention=='EXPLICIT_TIME' and product not in {'BOND','SWAP','OPTION','INDEX','FUTURE','STRUCTURED_PRODUCT','DIGITAL_ASSET','ACTIVELY_MANAGED_CERTIFICATE'}|QUOTED_WRAPPERS) or evidence.get('calendarEvidence',{}).get('source') not in sources):
        raise ValuationBlocked('Explicit governed session calendar required; legacy weekday fallback is not valuation-ready')
    if not (evidence['calendarEvidence'].get('sealed') or evidence['calendarEvidence'].get('source')=='TENANT_PUBLISHED_SCHEDULE'):
        raise ValuationBlocked('A sealed reference calendar version is required for reproducible valuation')
    if product=='DIGITAL_ASSET':
        # A bank/exchange weekend must not silently redefine a continuous
        # asset's Saturday as Friday. Explicit lag/freshness remains supported
        # on a calendar that actually assesses the requested economic day.
        from market_data.policy_selection import calendar_context
        try:
            sessions,_,_=calendar_context(c,UUID(evidence['calendarEvidence']['calendarId']),None,day,
                request.tenant_id,request.information_cutoff)
        except (ValueError,KeyError) as exc:raise ValuationBlocked('Assessed daily crypto pricing calendar required') from exc
        if sessions.get(day) is None:raise ValuationBlocked('Daily crypto pricing calendar must explicitly cover the valuation day as open; use a continuous pricing calendar')
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
    if measure!=('INDEX_LEVEL' if index_level else 'PRICE'): raise ValuationBlocked('Governed PRICE or native INDEX_LEVEL measurement semantics required')
    return selection_request,selected




def calculate_position(c, request: ValuationRequest) -> Calculation:
    """V2 consumes position state and movements; historical executions are lineage."""
    from positions.contracts import ProjectionRequest,PositionError
    from positions.repository import iter_ledger_facts
    from positions.reconstruction import reconstruct
    from .position_calculation import required_marks,attribute_projection
    from .corporate_actions import assert_projection_actions
    from market_data.split_replay import load_reviewed_splits
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
    from .ledger_impacts import capture_ledger_state
    ledger_source=capture_ledger_state(c,request)
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
    try:
        facts=tuple(iter_ledger_facts(c,projection_request))
        splits=load_reviewed_splits(c,{f.booking.subject_id for f in facts if f.booking},request.information_cutoff,tenant_id=request.tenant_id)
        projection=reconstruct(facts,projection_request,splits=splits)
    except PositionError as exc: raise ValuationBlocked(str(exc)) from exc
    assert_projection_actions(c,projection,ValuationBlocked,reviewed_events=splits)
    from .price_inputs import MissingPriceInput,retain_gap,priced_projection,price_coverage
    from positions.reconstruction import key_identity
    gaps={}
    marks={}; selected_evidence=[]; snapshot_ids=[]; conversions={};fx_inputs={}
    # Foreign multi-day calculations aggregate daily bridges so each execution
    # is translated at its own economic day's end-rate, not the period end.
    daily_projections=[projection]
    foreign=any(b.key.currency_id!=request.reporting_currency_id for b in projection.buckets)
    has_movements=any((e.booking.product_evidence or {}).get('quantityMovement') for e in projection.executions)
    if (foreign or has_movements) and (request.closing_cutoff-request.opening_cutoff)>timedelta(days=1):
        daily_projections=[];boundary=request.opening_cutoff
        while boundary<request.closing_cutoff:
            end=min(boundary+timedelta(days=1),request.closing_cutoff)
            try:
                daily_projections.append(reconstruct(projection.facts,replace(projection_request,opening_cutoff=boundary,closing_cutoff=end),splits=splits))
            except PositionError as exc: raise ValuationBlocked(str(exc)) from exc
            boundary=end
    requirements=tuple({r.key:r for p in daily_projections for r in required_marks(p)}.values())
    for cutoff in sorted({r.key.cutoff for r in requirements}):
        selections={}; first=None
        for requirement in (r for r in requirements if r.key.cutoff==cutoff):
            try:
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
                if product=='OPTION':
                    from .product_inputs import option_mark_context
                    try:premium_subject,dimensions=option_mark_context(projection,subject,cutoff)
                    except ValueError as exc:raise ValuationBlocked(str(exc)) from exc
                    # Premiums belong to the canonical contract; the ledger retains
                    # its exact listing. Never substitute the performance underlying.
                    selection_request,selected=_selection(c,request,premium_subject,cutoff,product,dimension_filters=dimensions)
                elif product=='FX_FORWARD':
                    conventions=[f.booking.product_evidence for f in projection.facts if f.booking and f.booking.subject_id==subject]
                    if not conventions:raise ValuationBlocked('Frozen forward conventions required')
                    if any((Decimal(p['agreedRate']),p['maturityDate'],p['baseCurrencyId'],p['priceCurrencyId'])!=(Decimal(conventions[0]['agreedRate']),conventions[0]['maturityDate'],conventions[0]['baseCurrencyId'],conventions[0]['priceCurrencyId']) for p in conventions):
                        raise ValuationBlocked('Incompatible frozen forward terms on the same contract')
                    if cutoff.date()>datetime.fromisoformat(conventions[0]['maturityDate']).date():raise ValuationBlocked('Unclosed forward exposure after maturity requires Ops closure')
                    from .forward_inputs import select_forward_rate
                    try:selection_request,selected=cached if cached else select_forward_rate(c,request,subject,cutoff,conventions[0])
                    except ValueError as exc:raise ValuationBlocked(str(exc)) from exc
                elif product=='SWAP':
                    from .product_inputs import swap_mark_dimensions
                    try:dimensions=swap_mark_dimensions(projection,subject,cutoff)
                    except ValueError as exc:raise ValuationBlocked(str(exc)) from exc
                    selection_request,selected=cached if cached else _selection(c,request,subject,cutoff,product,dimension_filters=dimensions)
                elif product=='FUTURE':
                    from .futures_pnl import future_mark_context
                    try:
                        dimensions,convention=future_mark_context(projection,subject,cutoff)
                        selection_request,selected=cached if cached else _selection(c,request,subject,cutoff,product,dimension_filters=dimensions)
                        factors=list(c.scalars(select(m.market_data_series_dimension.c.dimension_value).where(
                            m.market_data_series_dimension.c.market_data_series_id==selected.market_data_series_id,
                            m.market_data_series_dimension.c.dimension_code=='QUOTE_FACTOR')))
                        if len(factors)!=1 or Decimal(factors[0])!=convention.quote_factor:
                            raise ValueError('Selected futures price divisor differs from frozen contract')
                    except ValueError as exc:raise ValuationBlocked(str(exc)) from exc
                elif product=='STRUCTURED_PRODUCT':
                    from .structured_note_inputs import note_mark_context,validate_note_divisor
                    try:dimensions,factor=note_mark_context(projection,subject,cutoff)
                    except ValueError as exc:raise ValuationBlocked(str(exc)) from exc
                    selection_request,selected=cached if cached else _selection(c,request,subject,cutoff,product,dimension_filters=dimensions)
                    factors=list(c.scalars(select(m.market_data_series_dimension.c.dimension_value).where(
                        m.market_data_series_dimension.c.market_data_series_id==selected.market_data_series_id,
                        m.market_data_series_dimension.c.dimension_code=='QUOTE_FACTOR')))
                    try:validate_note_divisor(factors,factor)
                    except ValueError as exc:raise ValuationBlocked(str(exc)) from exc
                elif product=='ACTIVELY_MANAGED_CERTIFICATE':
                    from security_master_schema.amc_quotation import matching_quotation
                    bases=set()
                    for fact in projection.facts:
                        booking=fact.booking
                        if booking and booking.subject_id==subject:
                            proof=booking.product_evidence or {}
                            try:bases.add(matching_quotation([proof['amcConvention']],booking.quantity_unit,booking.unit_multiplier,booking.quote_factor))
                            except (KeyError,ValueError) as exc:raise ValuationBlocked('Frozen compatible AMC quotation required') from exc
                    if len(bases)!=1:raise ValuationBlocked('Incompatible AMC price quotation bases on the same subject')
                    selection_request,selected=cached if cached else _selection(c,request,subject,cutoff,product,
                        dimension_filters=(('AMC_PRICE_BASIS',next(iter(bases))),))
                else:selection_request,selected=cached if cached else _selection(c,request,subject,cutoff,product)
                from .corporate_actions import assert_native_mark_units
                try:
                    assert_native_mark_units(projection.split_events,subject,cutoff,selected.pricing_date_used,daily=request.daily)
                except ValueError as exc: raise ValuationBlocked(str(exc)) from exc
                if product=='BOND':
                    from .bond_prices import normalize_bond_selection
                    try:selected=normalize_bond_selection(c,selected,request.information_cutoff)
                    except ValueError as exc:raise ValuationBlocked(str(exc)) from exc
                    from .product_inputs import prepare_product_inputs
                    for bucket in (b for b in projection.buckets if b.key.subject_id==requirement.key.subject_id):
                        try: prepare_product_inputs(c,request,bucket,{'bondPriceType':'CLEAN'})
                        except ValueError as exc: raise ValuationBlocked(str(exc)) from exc
                first=first or selection_request; selections[subject]=(selection_request,selected)
                expected={b.key.currency_id for b in projection.buckets if b.key.subject_id==requirement.key.subject_id}
                if expected!={selected.currency_id}:
                    raise ValuationBlocked('Selected market price currency differs from frozen trade currency; explicit normalization required')
                marks[requirement.key]=selected.valuation_value if selected.valuation_value is not None else selected.selected_value
                selected_evidence.append(dict(asdict(selected),valuation_date=cutoff.date(),
                    valuation_position_subject_id=requirement.key.subject_id,**({'input_role':'FORWARD_RATE'} if product=='FX_FORWARD' else {}),
                    **({'valuation_cutoff_utc':cutoff} if product=='BOND' else {})))
            except MissingPriceInput as missing:
                affected=[key_identity(b.key) for b in projection.buckets if b.key.subject_id==requirement.key.subject_id]
                retain_gap(gaps,missing,affected)
                first=first or missing.request
                selections[missing.request.subject_reference_node_id]=(missing.request,missing.selection)
        snapshot_ids.append(persist_resolution_snapshot(c,first,tuple(s[1] for s in selections.values())))
    from .fx import resolve_fx
    for fact in projection.facts:
        if not fact.booking or fact.booking.product_basis!='FX_FORWARD':continue
        closing=(fact.booking.product_evidence or {}).get('maturityEvidence')
        proof=(closing or {}).get('fxEvidence') or {}
        if proof.get('selection'):
            selected_evidence.append(proof['selection']|dict(valuation_date=closing['valueDate'],input_role='FX_MATURITY_SUGGESTION',
                valuation_position_subject_id=fact.booking.subject_id,bookedClosingRate=closing['price']))
    try:
        for p in daily_projections:
            for bucket in p.buckets:
                cutoffs=[p.request.closing_cutoff]
                if bucket.opening_quantity and bucket.key.product_basis!='FUTURE': cutoffs.append(p.request.opening_cutoff)
                for cutoff in cutoffs:
                    key=(bucket.key.currency_id,cutoff)
                    if key in conversions: continue
                    try:conversion=resolve_fx(c,request,bucket.key.currency_id,request.reporting_currency_id,cutoff.date(),allow_partial=True)
                    except MissingPriceInput as missing:
                        retain_gap(gaps,missing,[key_identity(bucket.key)],role='FX')
                        continue
                    conversions[key]=conversion;fx_inputs[key]=conversion.rate
                    if conversion.selection:
                        proof=conversion.selection.pricing_evidence or {}
                        if datetime.fromisoformat(proof['pricingTargetUtc'])>cutoff:
                            raise ValueError('FX pricing target is later than economic cutoff')
                        snapshot_ids.append(persist_resolution_snapshot(c,conversion.resolution_request,(conversion.selection,)))
                        selected_evidence.append(dict(asdict(conversion.selection),valuation_date=cutoff.date(),input_role='FX',
                            valuation_source_currency_id=bucket.key.currency_id,conversion=conversion.evidence))
        unpriced={key for gap in gaps.values() for key in gap['positionKeys']}
        priced=priced_projection(projection,unpriced)
        periods=[attribute_projection(priced_projection(p,unpriced),marks,request.reporting_currency_id,fx_inputs) for p in daily_projections]
        period=periods[0] if len(periods)==1 else aggregate_daily_periods(priced,periods)
    except ValueError as exc: raise ValuationBlocked(str(exc)) from exc
    from .flows import load_economic_flows,attach_flows
    try: flows=load_economic_flows(c,request)
    except ValueError as exc: raise ValuationBlocked(str(exc)) from exc
    from .accruals import load_accrual_inputs,attach_accruals
    try:
        coverage=load_accrual_inputs(c,request,priced)
        accruals=coverage.inputs
        earned_scope={(a.instrument_id,a.value_date) for a in accruals}
        if any(f.component=='COUPON' and (f.instrument_id,f.economic_date) in earned_scope
               and f.evidence.get('booking',{}).get('instrumentType')=='STRUCTURED_PRODUCT' for f in flows):
            raise ValueError('CLEAN note has both daily earned interest and coupon income for the same date; classify settlement as PAYMENT_ONLY when that income is already accrued')
        period=attach_accruals(period,accruals,missing=coverage.missing,not_applicable=coverage.not_applicable,include_balance_fx=False)
        from .accrued_balance_inputs import load_accrued_balance_fx,attach_balance_fx
        accrued_balance=load_accrued_balance_fx(c,request,priced)
        from .structured_note_interest import add_note_balance_fx
        accrued_balance=add_note_balance_fx(c,request,priced,accrued_balance)
        period,receivables=attach_balance_fx(period,accrued_balance)
    except ValueError as exc: raise ValuationBlocked(str(exc)) from exc
    # Interest coverage reconstructs actual investment exposure. Monetary flows
    # are appended afterwards solely for result ownership/ledger lineage.
    investment_projection=projection
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
                    valuation_source_currency_id=accrual.payload['currencyId'],conversion=proof,
                    valuation_accrued_instrument_id=str(accrual.instrument_id)))
    from .cash_fx_inputs import load_cash_fx
    try:cash=load_cash_fx(c,request,missing_inputs=gaps)
    except ValueError as exc:raise ValuationBlocked(str(exc)) from exc
    snapshot_ids.extend(cash.snapshot_ids)
    for line in cash.lines:selected_evidence.extend(line.selections)
    input_coverage=price_coverage(investment_projection,gaps,selected_evidence)
    input_coverage['unpricedCashAccounts']=cash.coverage.get('unpricedCashAccounts',[])
    snapshot_ids.extend(accrued_balance.snapshot_ids)
    for line in accrued_balance.lines:selected_evidence.extend(dict(s,valuation_accrued_instrument_id=str(line.instrument_id)) for s in line.selections)
    scope='ECONOMIC_WITH_CASH_FX' if cash.lines else 'ECONOMIC_RECORDED_INPUTS' if accruals or accrued_balance.lines else 'ECONOMIC_RECORDED_FLOWS' if flows else 'MARKET_ONLY'
    from .review_coverage import pnl_completeness
    evidence=canonical_payload(dict(request=asdict(request),method=POSITION_METHOD,resultFormat='POSITION_V2',
        projection=asdict(projection),events=[asdict(fact) for fact in projection.facts],selections=selected_evidence,
        fxConversions=[dict(sourceCurrencyId=fx.source_currency_id,targetCurrencyId=fx.target_currency_id,
            rate=fx.rate,economicDate=fx.economic_date,observationDate=fx.observation_date,evidence=fx.evidence) for fx in conversions.values()],
        economicFlows=[f.evidence for f in flows],
        dailyAccrualInputs=[dict(inputId=a.input_id,revision=a.revision,payload=a.payload) for a in accruals],
        accrualCoverage=coverage.evidence(request.require_complete_accruals),
        accruedBalanceCoverage=accrued_balance.coverage,accruedBalanceSource=accrued_balance.source_proof,
        inputCoverage=input_coverage,requiredInputsComplete=not gaps,
        pnlCompleteness='PARTIAL' if gaps or any(e.get('kind')=='REINVESTMENT_INCOME_NOT_ASSESSED' for line in period.lines for e in line.economic_evidence) else pnl_completeness(coverage.evidence(request.require_complete_accruals),accrued_balance.coverage,cash.coverage),
        executionFxConvention='ECONOMIC_DAY_END',dailyBridgeCount=len(periods),requiredMarkCount=len(requirements),scope=scope,limitations=['UNBOOKED_INCOME_NOT_INCLUDED',
        'ONLY_REVIEWED_BASIC_SHARE_RATIOS_REPLAYED','NOT_FULL_NAV',
        'CASH_OPENING_BALANCE_EOD_MOVEMENTS','CASH_COVERAGE_KNOWN_UPLOADED_SCOPES_ONLY']+
        (['FX_FORWARD_UNDISCOUNTED_RATE_DIFFERENCE_NOT_MODEL_MTM'] if any(b.key.product_basis=='FX_FORWARD' for b in projection.buckets) else [])+
        (['ACCRUED_BALANCE_NOT_ASSESSED'] if accrued_balance.coverage['missingCount'] else []),externalComparison='NOT_COMPARED'))
    if any(b.key.product_basis=='FUTURE' for b in projection.buckets):
        evidence['limitations'].append('FUTURES_PRICE_VARIATION_NOT_CONTRACT_MTM_NO_MARGIN_CASH_POSTING')
    if any(b.key.product_basis=='STRUCTURED_PRODUCT' for b in projection.buckets):
        evidence['limitations'].extend(['STRUCTURED_NOTE_SUPPLIED_WHOLE_MARK_NO_AUTOMATIC_LIFECYCLE',
            'NOTE_DIRTY_OR_NONE_INTEREST_EMBEDDED_NO_SEPARATE_ACCRUAL',
            'NOTE_DETACHED_COUPON_RECEIVABLES_NOT_GENERATED'])
    if any(b.key.product_basis=='DIGITAL_ASSET' for b in projection.buckets):
        evidence['limitations'].append('SPOT_CRYPTO_NO_STAKING_FORK_MARGIN_OR_ASSUMED_STABLECOIN_PEG')
    if coverage.missing:
        evidence['limitations'].append('DAILY_ACCRUAL_NOT_SUPPLIED_NOT_INCLUDED')
    if accrued_balance.coverage['missingCount']:evidence['limitations'].append('ACCRUED_BALANCE_FX_PARTIAL_NOT_ZERO')
    evidence['cashCoverage']=cash.coverage
    evidence['cashFxInputs']=[dict(accountId=line.account_id,currencyId=line.currency_id,days=[asdict(day) for day in line.days]) for line in cash.lines]
    if cash.coverage['status']!='INCLUDED':evidence['limitations'].append('CASH_INPUTS_PARTIAL_OR_UNASSESSED')
    from .decisions import applied_decisions
    evidence['appliedRules']=applied_decisions(evidence | dict(
        executionInputs=[asdict(e) for e in projection.executions],
        splitAdjustments=[asdict(a) for a in projection.split_adjustments],
        economicInputs=[item for line in period.lines for item in line.economic_evidence]))
    evidence['ledgerSource']=ledger_source
    from .source_dependencies import capture_sources
    evidence['sourceDependencies']=capture_sources(c,request,investment_projection,selected_evidence)
    return Calculation(request,period,tuple(snapshot_ids),evidence,evidence_hash(evidence),
        projection=projection,method=POSITION_METHOD,scope=scope,cash=cash,accrued_balance=accrued_balance,receivables=receivables)


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
            variation=sum((row.settlement_variation for row in rows),Decimal(0))
            if amounts[3]!=closing-opening-execution+variation: raise ValuationBlocked('Daily FX bridges do not reconcile')
            economic=tuple(value for row in rows for value in row.economic_evidence)
            if bucket.key.product_basis=='FUTURE':
                economic=(dict(economic[0],days=[day for value in economic for day in value['days']]),)
            lines.append(PositionLine(bucket,MarketAttribution(*amounts,opening,closing),execution,
                economic_evidence=economic,settlement_variation=variation))
        return PositionPeriodAttribution(tuple(lines),sum((l.attribution.market_pnl for l in lines),Decimal(0)),
            sum((l.attribution.opening_value for l in lines),Decimal(0)),sum((l.attribution.closing_value for l in lines),Decimal(0)),
            sum((l.execution_value for l in lines),Decimal(0)),sum((l.settlement_variation for l in lines),Decimal(0)))
