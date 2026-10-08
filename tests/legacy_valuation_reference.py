# Test-only frozen v1 reference for equivalence and historical storage fixtures.
"""Bounded single-currency listed-equity valuation from authoritative evidence."""
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from decimal import Decimal
import json
from uuid import UUID
from sqlalchemy import select
from security_master_schema import models as m
from security_master_schema.market_data_resolver import ResolutionRequest, resolve_market_data, persist_resolution_snapshot
from security_master_schema.tenancy import assert_tenant_owns_strategy
from valuation.economics import evidence_hash, canonical_payload
from tests.legacy_valuation_positions import BookedLot, BookingEvent, PeriodMarks, PeriodAttribution, attribute_period, aware, replay_bookings
from valuation.corporate_actions import assert_no_unreplayed_actions

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
    period: PeriodAttribution
    resolution_snapshot_ids: tuple[UUID, ...]
    evidence: dict
    input_hash: str
    scope: str = 'MARKET_ONLY'
    external_comparison: str = 'NOT_COMPARED'
    projection: object | None = None
    method: str = METHOD


def _booked_lot(c, row, snapshot, conventions=None):
    if snapshot.get('kind') != 'CASH_BOOKING' or row['price_basis'] != 'UNIT_PRICE':
        raise ValuationBlocked('Unsupported booking economics; only plain equities/ETFs are enabled')
    try:
        definition=UUID(snapshot['instrumentDefinitionId'])
        parent=UUID(snapshot['instrumentId'])
        currency=UUID(snapshot['priceCurrencyId'])
        factor=Decimal(snapshot['quoteFactor'])
        multiplier=Decimal(snapshot['unitMultiplier'])
    except (KeyError,ValueError,TypeError) as exc:
        raise ValuationBlocked('Missing frozen BOOKED conventions') from exc
    conventions={} if conventions is None else conventions
    product_key=('product',definition,parent)
    if product_key not in conventions:
        conventions[product_key]=c.execute(select(m.instrument_type.c.type_code).join(m.instrument_definition_version,
        m.instrument_definition_version.c.instrument_type_id==m.instrument_type.c.instrument_type_id).where(
        m.instrument_definition_version.c.instrument_definition_version_id==definition,
        m.instrument_definition_version.c.instrument_node_id==parent)).scalar_one_or_none()
    product=conventions[product_key]
    if product not in {'EQUITY','ETP'}:
        raise ValuationBlocked('Unsupported booking product')
    if product=='ETP':
        etp_key=('etp',parent,row['trade_datetime_utc'].date())
        if etp_key not in conventions:
            conventions[etp_key]=c.scalar(select(m.etp_terms.c.etp_kind).where(m.etp_terms.c.instrument_node_id==parent,
                m.etp_terms.c.effective_from<=row['trade_datetime_utc'].date()).order_by(m.etp_terms.c.sequence_no.desc()).limit(1))
        kind=conventions[etp_key]
        if kind!='ETF': raise ValuationBlocked('Only ETF exchange-traded products are enabled')
    if currency!=row['price_currency_id']:
        raise ValuationBlocked('Frozen booking price currency is inconsistent')
    return BookedLot(row['trade_id'],row['trade_subject_reference_node_id'],row['quantity'],row['execution_price'],
                     currency,row['quantity_unit'],multiplier,factor,row['trade_datetime_utc'])


def _load_events(c, request):
    trades=c.execute(select(m.trade).where(m.trade.c.strategy_id==request.strategy_id,
        m.trade.c.trade_datetime_utc<=request.closing_cutoff,m.trade.c.created_at_utc<=request.information_cutoff)
        .order_by(m.trade.c.trade_id)).mappings().all()
    # One lifecycle query, not one per lot. Join instead of an unbounded IN
    # parameter list so this does not introduce another hidden population cap.
    chains={}
    events=c.execute(select(m.trade_lifecycle_event).join(m.trade,
        m.trade.c.trade_id==m.trade_lifecycle_event.c.trade_id).where(
        m.trade.c.strategy_id==request.strategy_id,m.trade.c.trade_datetime_utc<=request.closing_cutoff,
        m.trade.c.created_at_utc<=request.information_cutoff,
        m.trade_lifecycle_event.c.recorded_at_utc<=request.information_cutoff).order_by(
            m.trade_lifecycle_event.c.trade_id,m.trade_lifecycle_event.c.sequence_no)).mappings()
    for event in events:
        chains.setdefault(event['trade_id'],[]).append(event)
    result=[]; conventions={}
    for row in trades:
        events=chains.get(row['trade_id'],[])
        if not events: raise ValuationBlocked('Missing original BOOKED evidence for historical position')
        for event in events:
            lot=None
            if event['event_type']=='BOOKED':
                try: snapshot=json.loads(event['event_payload'] or '{}')
                except (json.JSONDecodeError,TypeError) as exc: raise ValuationBlocked('Invalid BOOKED evidence') from exc
                lot=_booked_lot(c,row,snapshot,conventions)
            result.append(BookingEvent(event['trade_lifecycle_event_id'],row['trade_id'],event['sequence_no'],
                event['event_type'],event['event_datetime_utc'],event['recorded_at_utc'],lot))
    return result


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


def calculate(c, request: ValuationRequest) -> Calculation:
    """Calculate a market-only period; caller owns the financial transaction.

    No data rights are granted here. Income/corporate actions, cash and complete
    NAV are explicitly not claimed by this first calculation scope.
    """
    for cutoff in (request.opening_cutoff,request.closing_cutoff,request.information_cutoff):
        aware(cutoff)
        if cutoff.utcoffset()!=timedelta(0): raise ValuationBlocked('UTC cutoffs required')
    if request.closing_cutoff<=request.opening_cutoff or request.information_cutoff<request.closing_cutoff:
        raise ValuationBlocked('Invalid economic/information cutoff ordering')
    assert_tenant_owns_strategy(c,request.tenant_id,request.strategy_id)
    events=_load_events(c,request)
    try:
        lots=replay_bookings(events,request.closing_cutoff,request.information_cutoff)
        opening_lots=replay_bookings(events,request.opening_cutoff,request.information_cutoff)
    except ValueError as exc: raise ValuationBlocked(str(exc)) from exc
    if not lots: raise ValuationBlocked('No active evidenced equity bookings; empty-population review is not enabled yet')
    assert_no_unreplayed_actions(c,lots,request.closing_cutoff,request.information_cutoff,ValuationBlocked)
    marks={}; selected_evidence=[]; snapshot_ids=[]
    for cutoff in (request.opening_cutoff,request.closing_cutoff):
        selections=[]; first_request=None
        population=opening_lots if cutoff==request.opening_cutoff else lots
        for subject in sorted({lot.subject_id for lot in population},key=str):
            selection_request,selected=_selection(c,request,subject,cutoff)
            selections.append(selected);first_request=first_request or selection_request
            selected_evidence.append(dict(asdict(selected),valuation_date=cutoff.date()))
            if cutoff==request.opening_cutoff:
                marks[subject]=PeriodMarks(selected.selected_value,selected.selected_value,Decimal('1'),Decimal('1'))
            else:
                old=marks.get(subject)
                marks[subject]=PeriodMarks(old.opening_price if old else None,selected.selected_value,Decimal('1'),Decimal('1'))
        if selections:
            snapshot_ids.append(persist_resolution_snapshot(c,first_request,tuple(selections)))
    if any(lot.currency_id!=request.reporting_currency_id for lot in lots):
        raise ValuationBlocked('Execution currency differs from reporting currency')
    try:
        period=attribute_period(events,request.opening_cutoff,request.closing_cutoff,request.information_cutoff,marks,
            execution_fx={lot.trade_id:Decimal('1') for lot in lots})
    except ValueError as exc: raise ValuationBlocked(str(exc)) from exc
    evidence=canonical_payload(dict(request=asdict(request),method=METHOD,events=[asdict(event) for event in events],
        selections=selected_evidence,scope='MARKET_ONLY',limitations=['INCOME_NOT_INCLUDED','CORPORATE_ACTIONS_NOT_REPLAYED',
        'CASH_NOT_VALUED','NOT_FULL_NAV'],externalComparison='NOT_COMPARED'))
    return Calculation(request,period,tuple(snapshot_ids),evidence,evidence_hash(evidence))
