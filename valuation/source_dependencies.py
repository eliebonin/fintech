"""Frozen, scoped non-ledger source fingerprints; never a financial recalculator.

SQL expressions are shared by detail/history and the pre-pagination worklist.
Hashes detect changes to relevant candidate populations, including unselected
eligible candidates; they do not assert that a changed input changes the result.
"""
from datetime import date, timedelta
from contextlib import contextmanager
from uuid import UUID
from sqlalchemy import select, func, cast, literal, Text, Date, column, and_, or_, exists
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID, aggregate_order_by
from security_master_schema import models as m
from security_master_schema.governance_clock import governance_date
from market_data.entitlements import tenant_series_entitlement_clause
from . import tables as t

KINDS=('MARKET_DATA','POLICY','CALENDAR','CORPORATE_ACTION')


@contextmanager
def metadata_query(c):
    """Avoid measured JIT setup overhead for scoped metadata aggregates only.

    Financial queries keep their caller's setting. SET LOCAL restores itself on
    rollback; an aborted PostgreSQL transaction cannot execute a restoration SQL.
    """
    from psycopg.pq import TransactionStatus
    previous=c.scalar(select(func.current_setting('jit')))
    if previous=='off':
        yield
        return
    c.execute(select(func.set_config('jit','off',True)))
    try:yield
    finally:
        if not c.closed and not c.invalidated and c.connection.driver_connection.info.transaction_status!=TransactionStatus.INERROR:
            c.execute(select(func.set_config('jit',previous,True)))



def _value(scope,name):
    # Explicit extraction also supports JSONB bind parameters on PostgreSQL.
    return scope.op('->')(name)


def _text(scope,name):
    return scope.op('->>')(name)


def _ids(scope,name):
    # Scope can reference a batch several nested SELECTs above this one.
    # Explicit correlation prevents accidentally scanning other batches' scopes.
    return select(cast(func.jsonb_array_elements_text(_value(scope,name)),PGUUID)).correlate(t.batch)


def _digest(value):
    return func.encode(func.sha256(func.convert_to(value,'UTF8')),'hex')


def _hash(table,where,*,joined=None,correlate=(),snapshot=None):
    row=_digest(cast(snapshot if snapshot is not None else func.to_jsonb(table.table_valued()),Text))
    return select(_digest(func.coalesce(func.string_agg(row,aggregate_order_by(literal(''),row)),literal('')))).select_from(
        joined if joined is not None else table).where(where).correlate_except(table,*correlate).scalar_subquery()


def _combined(*parts):
    return _digest(func.concat(*parts))


def state_expression(tenant,scope,asof):
    """One statement snapshot, exact reference/date scope and no financial row cap."""
    opening=cast(_text(scope,'fromDate'),Date);closing=cast(_text(scope,'toDate'),Date)
    policy=cast(_text(scope,'policyId'),PGUUID);strategy=cast(_text(scope,'strategyId'),PGUUID)
    s=m.market_data_series;o=m.market_data_observation
    markets=func.jsonb_array_elements(_value(scope,'markets')).table_valued(column('value',JSONB)).alias('dependency_market_scope')
    v=markets.c.value
    market_match=exists(select(1).select_from(markets).where(
        s.c.reference_node_id==cast(v['subject'].astext,PGUUID),s.c.series_type==v['seriesType'].astext,
        or_(v['currencyId'].astext.is_(None),s.c.currency_id==cast(v['currencyId'].astext,PGUUID)))).correlate_except(markets)
    selected=s.c.market_data_series_id.in_(_ids(scope,'seriesIds'))
    def market_window(day,dataset=None):
        conditions=[s.c.reference_node_id==cast(v['subject'].astext,PGUUID),s.c.series_type==v['seriesType'].astext,
            or_(v['currencyId'].astext.is_(None),s.c.currency_id==cast(v['currencyId'].astext,PGUUID)),
            day.between(cast(v['fromDate'].astext,Date),cast(v['toDate'].astext,Date))]
        if dataset is not None:
            conditions.append(tenant_series_entitlement_clause(dataset,s.c.market_data_series_id,tenant,'VALUATION',cast(v['valuationDate'].astext,Date)))
        return exists(select(1).select_from(markets).where(*conditions)).correlate_except(markets)
    def current_access(table):
        return tenant_series_entitlement_clause(table.c.dataset_id,table.c.market_data_series_id,tenant,'VALUATION',governance_date())
    def known(table):
        return and_(table.c.quality_status=='ACCEPTED',table.c.received_at_utc<=asof,
            or_(table.c.source_published_at_utc.is_(None),table.c.source_published_at_utc<=asof))
    candidate=o.alias('dependency_candidate_observation')
    actual_source=exists(select(1).select_from(candidate).where(candidate.c.market_data_series_id==s.c.market_data_series_id,
        known(candidate),market_window(candidate.c.market_date,candidate.c.dataset_id),current_access(candidate))).correlate_except(candidate)
    eligible=and_(market_match,or_(selected,and_(s.c.status=='ACTIVE',actual_source)))
    # Materialize these small scoped populations once. Repeating rights joins
    # through every aggregate otherwise produces expensive PostgreSQL plans.
    candidates=select(s.c.market_data_series_id).where(eligible).correlate_except(s).cte('dependency_series',nesting=True).prefix_with('MATERIALIZED')
    series_ids=select(candidates.c.market_data_series_id)
    visible=or_(o.c.market_data_observation_id.in_(_ids(scope,'observationIds')),
        and_(market_window(o.c.market_date,o.c.dataset_id),current_access(o)))
    roots=select(o.c.market_data_observation_id).select_from(o.join(s)).where(
        o.c.market_data_series_id.in_(series_ids),known(o),market_window(o.c.market_date),visible).correlate_except(o,s).cte(
            'dependency_observation_roots',nesting=True).prefix_with('MATERIALIZED')
    root_ids=select(roots.c.market_data_observation_id)
    # A moved correction can suppress a previously eligible observation even
    # when the successor itself lies outside the original price-date window.
    observation_scope=or_(o.c.market_data_observation_id.in_(root_ids),and_(o.c.supersedes_observation_id.in_(root_ids),known(o)))
    vintage_ids=select(o.c.market_data_vintage_id).where(observation_scope).correlate_except(o)
    market=_combined(_hash(s,s.c.market_data_series_id.in_(series_ids)),
        _hash(o,observation_scope,joined=o.join(s),correlate=(s,),snapshot=func.jsonb_build_object(
            'observation',func.to_jsonb(o.table_valued()),'historicalValuationEligible',market_window(o.c.market_date,o.c.dataset_id),
            'currentValuationEligible',current_access(o))),
        _hash(m.market_data_vintage,m.market_data_vintage.c.market_data_vintage_id.in_(vintage_ids)),
        _hash(m.market_data_series_dimension,m.market_data_series_dimension.c.market_data_series_id.in_(series_ids)))
    rules=m.valuation_policy_rule
    cuts=m.valuation_cut
    cut_ids=select(rules.c.pricing_cut_id).where(rules.c.valuation_policy_id==policy).correlate_except(rules)
    priority=m.source_priority_version
    priorities=select(priority.c.source_priority_version_id).where(
        or_(priority.c.tenant_id.is_(None),priority.c.tenant_id==tenant),priority.c.use_purpose=='VALUATION',
        or_(priority.c.instrument_type_id.is_(None),priority.c.instrument_type_id.in_(_ids(scope,'instrumentTypeIds'))),
        priority.c.created_at_utc<=asof).correlate_except(priority)
    policy_state=_combined(_hash(m.valuation_policy,m.valuation_policy.c.valuation_policy_id==policy),
        _hash(rules,rules.c.valuation_policy_id==policy),
        _hash(cuts,or_(cuts.c.valuation_cut_id==cast(_text(scope,'cutId'),PGUUID),cuts.c.valuation_cut_id.in_(cut_ids))),
        _hash(priority,priority.c.source_priority_version_id.in_(priorities)),
        _hash(m.source_priority_entry,m.source_priority_entry.c.source_priority_version_id.in_(priorities)))
    assignment=m.calendar_assignment
    assignment_scope=and_(assignment.c.tenant_id==tenant,assignment.c.purpose=='VALUATION',
        assignment.c.valid_from<=closing,assignment.c.valid_to>=opening,assignment.c.created_at_utc<=asof,
        or_(and_(assignment.c.target_kind=='STRATEGY',assignment.c.target_id==strategy),
            and_(assignment.c.target_kind=='FUND_REFERENCE',assignment.c.target_id.in_(_ids(scope,'calendarTargets')))))
    calendar_ids=_ids(scope,'calendarIds')
    calendar_state=_combined(_hash(m.market_calendar,m.market_calendar.c.market_calendar_id.in_(calendar_ids)),
        _hash(m.market_calendar_session,and_(m.market_calendar_session.c.market_calendar_id.in_(calendar_ids),m.market_calendar_session.c.session_date.between(opening,closing))),
        _hash(m.market_calendar_holiday,and_(m.market_calendar_holiday.c.market_calendar_id.in_(calendar_ids),m.market_calendar_holiday.c.holiday_date.between(opening,closing))),
        _hash(assignment,assignment_scope),_hash(m.market_venue,m.market_venue.c.market_venue_id.in_(_ids(scope,'venueIds'))))
    from market_data.split_replay import action_query
    from .corporate_actions import UNIT_CHANGING_ACTIONS
    action=m.corporate_action;dates=m.corporate_action_date
    # Reuse the exact ownership checks used by the native replay guard.
    visible=action_query(_ids(scope,'instrumentIds'),asof,tenant).with_only_columns(action.c.corporate_action_id)
    prior=action.alias('dependency_prior_action')
    prior_dates=select(dates.c.corporate_action_id).where(dates.c.date_role.in_(['EX','EFFECTIVE']),
        dates.c.date_value.between(cast(_text(scope,'actionFrom'),Date),closing)).correlate_except(dates)
    prior_unknown=~exists(select(1).where(dates.c.corporate_action_id==prior.c.corporate_action_id,
        dates.c.date_role.in_(['EX','EFFECTIVE']))).correlate_except(dates)
    related=exists(select(1).select_from(prior).where(prior.c.corporate_action_id.in_(visible),
        prior.c.event_type.in_(UNIT_CHANGING_ACTIONS),or_(prior.c.corporate_action_id.in_(prior_dates),prior_unknown),
        prior.c.affected_instrument_node_id==action.c.affected_instrument_node_id,
        or_(prior.c.corporate_action_id==action.c.corporate_action_id,
            and_(prior.c.external_event_reference.is_not(None),prior.c.external_event_reference==action.c.external_event_reference)))).correlate_except(prior)
    actions=select(action.c.corporate_action_id).where(action.c.corporate_action_id.in_(visible),related).correlate_except(action)
    action_state=_combined(_hash(action,action.c.corporate_action_id.in_(actions)),
        _hash(dates,dates.c.corporate_action_id.in_(actions)),
        _hash(m.corporate_action_effect,m.corporate_action_effect.c.corporate_action_id.in_(actions)),
        _hash(m.corporate_action_replay_decision,and_(m.corporate_action_replay_decision.c.corporate_action_id.in_(actions),
            m.corporate_action_replay_decision.c.recorded_at_utc<=asof)))
    return select(func.jsonb_build_object('MARKET_DATA',market,'POLICY',policy_state,'CALENDAR',calendar_state,'CORPORATE_ACTION',action_state)).add_cte(candidates,roots,nest_here=True).correlate(t.batch).scalar_subquery()


def _market_dates(c,request,item,row,rule):
    target=date.fromisoformat(str(item.get('pricing_date_requested') or item.get('pricing_date_used') or request.closing_cutoff.date()))
    first=min(target,date.fromisoformat(str(item.get('pricing_date_used') or target)))
    if rule:
        allowance=rule['max_staleness_business_days']
        if allowance is None:
            first=date.min if rule['pricing_convention']=='LEGACY' else target-timedelta(days=1100)
        elif allowance:
            from market_data.policy_selection import calendar_context,listing_venue
            provenance=(item.get('pricing_evidence') or {}).get('calendarEvidence') or {}
            identity=rule['market_calendar_id'] or provenance.get('calendarId') or (row or {}).get('expected_market_calendar_id')
            try:
                sessions,_,_=calendar_context(c,identity,listing_venue(c,UUID(str(item['subject_reference_node_id']))),target,
                    request.tenant_id,request.information_cutoff,rule['pricing_convention']=='NAV_DATE')
                permitted=sorted(day for day,close in sessions.items() if day<=target and close is not None)
                if permitted:first=min(first,permitted[max(0,len(permitted)-1-allowance)])
            except ValueError:
                # Widen tracking only. No price, holiday or financial fallback is
                # invented when a partially staged input lacks an assessed calendar.
                first=min(first,target-timedelta(days=1100))
    return first,target


def capture_sources(c,request,projection,selections):
    """Capture selected identities plus alternative candidates within the same scope."""
    subjects={str(b.key.subject_id) for b in projection.buckets}
    selected_series={UUID(str(s['market_data_series_id'])) for s in selections if s.get('market_data_series_id')}
    series={r['market_data_series_id']:r for r in c.execute(select(m.market_data_series).where(m.market_data_series.c.market_data_series_id.in_(selected_series))).mappings()}
    rules=list(c.execute(select(m.valuation_policy_rule).where(m.valuation_policy_rule.c.valuation_policy_id==request.policy_id)).mappings())
    by_rule={r['valuation_policy_rule_id']:r for r in rules}
    markets=[];days=[request.opening_cutoff.date()]
    calendars=set();targets=set(subjects)
    def collect(value):
        if isinstance(value,dict):
            for key,item in value.items():
                if key in ('calendarId','marketCalendarId','market_calendar_id') and item:
                    try:calendars.add(str(UUID(str(item))))
                    except (ValueError,TypeError):pass
                collect(item)
        elif isinstance(value,(list,tuple)):
            for item in value:collect(item)
    for item in selections:
        collect(item.get('pricing_evidence') or {})
        if item.get('pricing_date_used'):days.append(date.fromisoformat(str(item['pricing_date_used'])))
        subject=str(item['subject_reference_node_id']);subjects.add(subject);targets.add(subject)
        sid=UUID(str(item['market_data_series_id'])) if item.get('market_data_series_id') else None
        row=series.get(sid)
        rule=by_rule.get(UUID(str(item['policy_rule_id']))) if item.get('policy_rule_id') else None
        if row or rule:
            first,last=_market_dates(c,request,item,row,rule);days.append(first)
            markets.append(dict(subject=subject,seriesType=row['series_type'] if row else rule['series_type'],
                currencyId=str(row['currency_id']) if row and row['currency_id'] else None,fromDate=first.isoformat(),toDate=last.isoformat(),valuationDate=str(item.get('valuation_date') or request.closing_cutoff.date())))
            if row and row['expected_market_calendar_id']:calendars.add(str(row['expected_market_calendar_id']))
    for rule in rules:
        if rule['market_calendar_id']:calendars.add(str(rule['market_calendar_id']))
    cut_ids={request.cut_id}|{r['pricing_cut_id'] for r in rules if r['pricing_cut_id']}
    for calendar in c.scalars(select(m.valuation_cut.c.market_calendar_id).where(m.valuation_cut.c.valuation_cut_id.in_(cut_ids))):
        if calendar:calendars.add(str(calendar))
    listings=list(c.execute(select(m.listing).where(m.listing.c.listing_node_id.in_([UUID(s) for s in subjects]))).mappings())
    instruments={str(r['instrument_node_id']) for r in listings}
    for fact in projection.facts:
        if fact.booking:
            proof=fact.booking.product_evidence or {}
            if proof.get('instrumentId'):instruments.add(str(proof['instrumentId']))
    instruments.update(str(x) for x in c.scalars(select(m.instrument.c.instrument_node_id).where(m.instrument.c.instrument_node_id.in_([UUID(s) for s in subjects]))))
    targets.update(instruments)
    targets.update(str(x) for x in c.scalars(select(m.fund_share_class_terms.c.fund_reference_node_id).where(m.fund_share_class_terms.c.instrument_node_id.in_([UUID(s) for s in instruments]))) if x)
    venues={r['market_venue_id'] for r in listings}
    for calendar in c.scalars(select(m.market_venue.c.market_calendar_id).where(m.market_venue.c.market_venue_id.in_(venues))):
        if calendar:calendars.add(str(calendar))
    for calendar in c.scalars(select(m.calendar_assignment.c.market_calendar_id).where(m.calendar_assignment.c.tenant_id==request.tenant_id,
        m.calendar_assignment.c.purpose=='VALUATION',m.calendar_assignment.c.target_id.in_([request.strategy_id]+[UUID(x) for x in targets]),
        m.calendar_assignment.c.valid_from<=request.closing_cutoff.date(),m.calendar_assignment.c.valid_to>=min(days),m.calendar_assignment.c.created_at_utc<=request.information_cutoff)):
        calendars.add(str(calendar))
    kinds=list(map(str,c.scalars(select(m.instrument.c.instrument_type_id).where(m.instrument.c.instrument_node_id.in_([UUID(x) for x in instruments])))))
    # Missing marks also need a dependency window so newly supplied inputs can
    # make partial calculations eligible for explicit reassessment.
    known={x['subject'] for x in markets}
    for subject in subjects-known:
        for rule in rules:
            if rule['status']=='ACTIVE' and rule['series_type']:
                markets.append(dict(subject=subject,seriesType=rule['series_type'],currencyId=None,fromDate=min(days).isoformat(),toDate=request.closing_cutoff.date().isoformat(),valuationDate=request.closing_cutoff.date().isoformat()))
    scope=dict(policyId=str(request.policy_id),strategyId=str(request.strategy_id),cutId=str(request.cut_id),
        fromDate=min(days).isoformat(),toDate=request.closing_cutoff.date().isoformat(),
        actionFrom=min([f.effective_at.date() for f in projection.facts]+[request.opening_cutoff.date()]).isoformat(),
        markets=list({(x['subject'],x['seriesType'],x['currencyId'],x['fromDate'],x['toDate'],x['valuationDate']):x for x in markets}.values()),
        seriesIds=sorted(map(str,selected_series)),datasetIds=sorted({str(x['dataset_id']) for x in selections if x.get('dataset_id')}),observationIds=sorted({str(x['market_data_observation_id']) for x in selections if x.get('market_data_observation_id')}),calendarIds=sorted(calendars),calendarTargets=sorted(targets),
        instrumentIds=sorted(instruments),venueIds=sorted(map(str,venues)),instrumentTypeIds=sorted(set(kinds)))
    with metadata_query(c):
        state=c.scalar(select(state_expression(request.tenant_id,literal(scope,type_=JSONB),request.information_cutoff)))
    return dict(version=1,scope=scope,fingerprints=state)


def source_reassessment_predicate(batch):
    proof=batch.c.summary['sourceDependencies']
    return or_(proof['version'].as_integer().is_distinct_from(1),
        state_expression(batch.c.tenant_id,proof['scope'],func.clock_timestamp()).is_distinct_from(proof['fingerprints']))


def dependency_health(c,headers):
    valid={h['batch_id']:h for h in headers if (h['summary'].get('sourceDependencies') or {}).get('version')==1}
    result={h['batch_id']:dict(status='UNKNOWN_LEGACY',kinds=[]) for h in headers}
    if not valid:return result
    b=t.batch;proof=b.c.summary['sourceDependencies']
    with metadata_query(c):
        rows=c.execute(select(b.c.batch_id,state_expression(b.c.tenant_id,proof['scope'],func.clock_timestamp())).where(
            b.c.batch_id.in_(valid),b.c.tenant_id.in_({h['tenant_id'] for h in valid.values()}))).all()
    for identity,current in rows:
        frozen=valid[identity]['summary']['sourceDependencies']['fingerprints']
        changed=[kind for kind in KINDS if current.get(kind)!=frozen.get(kind)]
        result[identity]=dict(status='REASSESSMENT_REQUIRED' if changed else 'CURRENT',kinds=changed)
    return result


def assert_current_source_rights(c,tenant,header):
    """Publication is a new use; current non-display rights remain mandatory."""
    proof=header['summary'].get('sourceDependencies') or {}
    datasets={UUID(value) for value in proof.get('scope',{}).get('datasetIds',[])}
    if not datasets:return
    from market_data.rights import denied_activity_datasets
    if denied_activity_datasets(c,tenant,governance_date(),['NON_DISPLAY'],datasets=datasets):
        raise ValueError('Current non-display source rights are unavailable; restore appropriate access before publication')
