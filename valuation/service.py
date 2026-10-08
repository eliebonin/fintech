"""Bounded single-currency listed-equity valuation from authoritative evidence."""
from dataclasses import asdict, dataclass
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
POSITION_METHOD = 'listed-equity-position-market-pnl-v2'


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




def _selection(c, request, subject, economic_cutoff):
    day=economic_cutoff.date()
    selection_request=ResolutionRequest(request.tenant_id,subject,request.policy_id,day,request.cut_id,
        request.information_cutoff,'VALUATION',request.strategy_id)
    selected=resolve_market_data(c,selection_request)
    if selected.status!='SELECTED':
        raise ValuationBlocked(f'Input selection blocked: {selected.exception_code or selected.status}')
    if selected.currency_id!=request.reporting_currency_id:
        raise ValuationBlocked('Reporting currency requires frozen FX conversion; multi-currency is not enabled yet')
    series=c.execute(select(m.market_data_series).where(m.market_data_series.c.market_data_series_id==selected.market_data_series_id)).mappings().one()
    rule=c.execute(select(m.valuation_policy_rule).where(m.valuation_policy_rule.c.valuation_policy_rule_id==selected.policy_rule_id)).mappings().one()
    if series['value_type']!='PRICE' or rule['series_type']!='OFFICIAL_CLOSE' or rule['value_basis']!='RAW':
        raise ValuationBlocked('Explicit RAW price basis required; adjusted/total-return marks are not interchangeable')
    evidence=selected.pricing_evidence or {}
    if rule['pricing_convention']!='SESSION_CLOSE' or evidence.get('calendarEvidence',{}).get('source')!='GOVERNED_SESSIONS':
        raise ValuationBlocked('Explicit governed session calendar required; legacy weekday fallback is not valuation-ready')
    if not evidence['calendarEvidence'].get('sealed'):
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
    if selected.staleness_status!='CURRENT':
        raise ValuationBlocked('Current-date price required for the first valuation alpha')
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
    projection_request=ProjectionRequest(request.tenant_id,request.strategy_id,request.closing_cutoff,
        request.information_cutoff,request.opening_cutoff,'PERIOD')
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
    marks={}; selected_evidence=[]; snapshot_ids=[]
    requirements=required_marks(projection)
    for cutoff in sorted({r.key.cutoff for r in requirements}):
        selections=[]; first=None
        for requirement in (r for r in requirements if r.key.cutoff==cutoff):
            selection_request,selected=_selection(c,request,requirement.key.subject_id,cutoff)
            first=first or selection_request; selections.append(selected)
            marks[requirement.key]=selected.selected_value
            selected_evidence.append(dict(asdict(selected),valuation_date=cutoff.date()))
        snapshot_ids.append(persist_resolution_snapshot(c,first,tuple(selections)))
    try: period=attribute_projection(projection,marks,request.reporting_currency_id)
    except ValueError as exc: raise ValuationBlocked(str(exc)) from exc
    evidence=canonical_payload(dict(request=asdict(request),method=POSITION_METHOD,resultFormat='POSITION_V2',
        projection=asdict(projection),events=[asdict(fact) for fact in projection.facts],selections=selected_evidence,
        requiredMarkCount=len(requirements),scope='MARKET_ONLY',limitations=['INCOME_NOT_INCLUDED',
        'CORPORATE_ACTIONS_NOT_REPLAYED','CASH_NOT_VALUED','NOT_FULL_NAV'],externalComparison='NOT_COMPARED'))
    return Calculation(request,period,tuple(snapshot_ids),evidence,evidence_hash(evidence),
        projection=projection,method=POSITION_METHOD)


# One authoritative execution path; historical v1 calculation is test-only.
calculate = calculate_position
