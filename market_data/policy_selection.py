"""Composite input selection. No ingestion, valuation or permission grants."""
from datetime import datetime, date, time, timedelta
from importlib.metadata import version
from zoneinfo import ZoneInfo
from sqlalchemy import select
from security_master_schema import models as m
from .pricing_conventions import local_target, session_target, session_distance


def is_daily_bar(dimensions):
    """Both historical and Yahoo labels mean a day bucket, not a price instant."""
    return bool({'SOURCE_DAILY_BAR', 'PROVIDER_DAILY_BAR_TIMESTAMP'} &
                dimensions.get('TIMESTAMP_SEMANTICS', set()))


def listing_venue(c, subject):
    return c.execute(select(m.market_venue).select_from(m.listing.join(m.market_venue)).where(
        m.listing.c.listing_node_id == subject)).mappings().one_or_none()


def calendar_context(c, calendar_id, venue, end, tenant=None, asof=None, fund_nav=False):
    start = end - timedelta(days=1100)
    calendar = c.execute(select(m.market_calendar).where(
        m.market_calendar.c.market_calendar_id == calendar_id,
        m.market_calendar.c.status == 'ACTIVE')).mappings().one_or_none() if calendar_id else None
    if calendar_id and not calendar:
        raise ValueError('CALENDAR_NOT_ASSESSED')
    if calendar and asof and calendar['created_at_utc'] > asof:
        raise ValueError('CALENDAR_VERSION_NOT_AVAILABLE_AT_CUTOFF')
    if calendar and calendar['tenant_id']:
        if not fund_nav or calendar['tenant_id']!=tenant or calendar['calendar_kind']!='VALUATION' or not calendar['sealed']:
            raise ValueError('CALENDAR_NOT_ASSESSED')
        if not asof or calendar['created_at_utc']>asof:
            raise ValueError('CALENDAR_VERSION_NOT_AVAILABLE_AT_CUTOFF')
        config=calendar['definition_json']['configuration']
        sessions={date.fromisoformat(day): None if item['status']=='CLOSED' else time.fromisoformat(config['decisionTime'])
                  for day,item in calendar['definition_json']['days'].items() if item['status']!='UNKNOWN'}
        return sessions,calendar['timezone_name'],dict(source='TENANT_PUBLISHED_SCHEDULE',calendarId=str(calendar_id),versionNo=calendar['version_no'],
            sourceReference=config['sourceReference'],recordedAtUtc=calendar['created_at_utc'].isoformat(),
            days=calendar['definition_json']['days'])
    rows = c.execute(select(m.market_calendar_session).where(
        m.market_calendar_session.c.market_calendar_id == calendar_id,
        m.market_calendar_session.c.session_date.between(start, end))).mappings().all() if calendar else []
    holidays=c.execute(select(m.market_calendar_holiday).where(m.market_calendar_holiday.c.market_calendar_id==calendar_id,
        m.market_calendar_holiday.c.holiday_date.between(start,end))).mappings().all() if calendar else []
    # Do not switch to a generated exchange schedule when all governed records
    # were published after the information cutoff. Unknown is not a holiday.
    governed = bool(rows or holidays)
    if asof:
        rows = [r for r in rows if r['created_at_utc'] <= asof]
        holidays = [r for r in holidays if r['created_at_utc'] <= asof]
    if governed and not rows and not holidays:
        raise ValueError('CALENDAR_VERSION_NOT_AVAILABLE_AT_CUTOFF')
    if rows or holidays:
        sessions = {r['session_date']: None if r['session_status'] == 'CLOSED' else r['close_local_time'] for r in rows}
        if any(r['session_status'] != 'CLOSED' and not r['close_local_time'] for r in rows):
            raise ValueError('CALENDAR_NOT_ASSESSED')
        for holiday in holidays:
            day=holiday['holiday_date']
            if day in sessions and sessions[day] is not None:
                sessions.pop(day)  # Conflicting records provide no assessed decision.
            else:
                sessions[day]=None
        return sessions, calendar['timezone_name'], {
            'source': 'GOVERNED_SESSIONS', 'calendarId': str(calendar_id),
            'sealed': calendar['sealed'], 'versionNo': calendar['version_no'],
            'recordedAtUtc': calendar['created_at_utc'].isoformat(),
            'holidays':[dict(date=h['holiday_date'].isoformat(),name=h['holiday_name'],sourceReference=h['source_reference'],recordedAtUtc=h['created_at_utc'].isoformat()) for h in holidays],
            'sessions': [{'date': r['session_date'].isoformat(), 'status': r['session_status'],
                          'closeLocalTime': r['close_local_time'].isoformat() if r['close_local_time'] else None,
                          'sourceReference': r['source_reference'], 'recordedAtUtc': r['created_at_utc'].isoformat()} for r in rows],
        }
    if calendar and (not venue or calendar_id != venue['market_calendar_id']):
        raise ValueError('CALENDAR_NOT_ASSESSED')
    mic = c.scalar(select(m.market_venue_identifier.c.identifier_value).where(
        m.market_venue_identifier.c.market_venue_id == venue['market_venue_id'],
        m.market_venue_identifier.c.identifier_scheme == 'ISO_10383_MIC',
        m.market_venue_identifier.c.is_primary.is_(True))) if venue else None
    name = {'XNYS':'NYSE','XNAS':'NASDAQ','XLON':'LSE','XPAR':'XPAR','XAMS':'XAMS'}.get(mic)
    if not name:
        raise ValueError('CALENDAR_NOT_ASSESSED')
    import pandas_market_calendars as calendars
    exchange = calendars.get_calendar(name)
    zone = str(exchange.tz)
    schedule = exchange.schedule(start_date=start, end_date=end)
    sessions = {start + timedelta(days=n): None for n in range((end-start).days+1)}
    for day, r in schedule.iterrows():
        sessions[day.date()] = r['market_close'].to_pydatetime().astimezone(ZoneInfo(zone)).time()
    return sessions, zone, {'source':'VERSIONED_EXCHANGE_SCHEDULE','calendar':name,'mic':mic,
        'package':'pandas_market_calendars','packageVersion':version('pandas_market_calendars'), 'authoritative':False}


def select_composite(c, request, rule, rows):
    """Return frozen target/result evidence, rejecting unknown semantics explicitly."""
    convention = rule['pricing_convention']
    evidence = {'convention':convention, 'informationCutoffUtc':request.market_data_as_of_utc.isoformat(),
        'valueBasis':rule['value_basis'], 'fixingCode':rule['fixing_code'],
        'pricingCutId':str(rule['pricing_cut_id']) if rule['pricing_cut_id'] else None,
        'strategyId':str(request.strategy_id) if request.strategy_id else None}
    result = dict(status='MISSING', row=None, requested=None, used=None, staleness=None,
                  exception='NO_ELIGIBLE_OBSERVATION', evidence=evidence)
    venue = listing_venue(c, request.subject_reference_node_id)
    evidence['listingId'] = str(request.subject_reference_node_id) if venue else None
    evidence['venueId'] = str(venue['market_venue_id']) if venue else None
    try:
        cut = None
        if convention == 'NAV_DATE':
            calendar_id=rule['market_calendar_id']
        elif convention == 'SESSION_CLOSE':
            if not venue:
                raise ValueError('EXPLICIT_PRICING_LISTING_REQUIRED')
            calendar_id = rule['market_calendar_id'] or venue['market_calendar_id']
        elif convention in ('NAMED_FIXING','EXPLICIT_TIME'):
            cut = c.execute(select(m.valuation_cut).where(m.valuation_cut.c.valuation_cut_id == rule['pricing_cut_id'],
                m.valuation_cut.c.status == 'ACTIVE')).mappings().one_or_none()
            if not cut:
                raise ValueError('PRICING_CUT_REQUIRED')
            if convention == 'NAMED_FIXING' and not rule['fixing_code']:
                raise ValueError('FIXING_CODE_REQUIRED')
            calendar_id = rule['market_calendar_id'] or cut['market_calendar_id']
        else:
            raise ValueError('UNSUPPORTED_PRICING_CONVENTION')
        sessions, zone, provenance = calendar_context(c, calendar_id, venue, request.valuation_date,
            request.tenant_id,request.market_data_as_of_utc,convention=='NAV_DATE')
        evidence['calendarEvidence'] = provenance
        lag = rule['lag_business_days'] if rule['pricing_date_rule'] == 'FIXED_LAG' else 0
        requested, close = session_target(request.valuation_date, sessions, lag)
        zone = cut['timezone_name'] if cut else zone
        target = local_target(requested, time.fromisoformat(cut['local_time']) if cut else close, zone)
        result['requested'] = requested
        evidence.update(pricingTargetUtc=target.isoformat(), pricingDate=requested.isoformat(), timezone=zone)
        if target > request.market_data_as_of_utc:
            raise ValueError('PRICING_TARGET_NOT_AVAILABLE')
        ids = {r['market_data_series_id'] for r in rows}
        dimensions = {}
        if ids:
            for sid, code, value in c.execute(select(m.market_data_series_dimension.c.market_data_series_id,
                m.market_data_series_dimension.c.dimension_code, m.market_data_series_dimension.c.dimension_value).where(
                    m.market_data_series_dimension.c.market_data_series_id.in_(ids))):
                dimensions.setdefault(sid, {}).setdefault(code, set()).add(value)
        eligible = []
        for row in rows:
            if rule['value_basis'] and row['value_basis'] != rule['value_basis']:
                continue
            day = row['market_date']
            if day > requested or day not in sessions or sessions[day] is None:
                continue
            if rule['pricing_date_rule'] == 'SAME_DAY' and day != requested:
                continue
            dims = dimensions.get(row['market_data_series_id'], {})
            if convention in ('SESSION_CLOSE','NAV_DATE'):
                completed = local_target(day, sessions[day], zone)
                if row['received_at_utc'] < completed or (row['source_published_at_utc'] and row['source_published_at_utc'] < completed):
                    continue
            if convention == 'NAMED_FIXING':
                if dims.get('FIXING_CODE') != {rule['fixing_code']} or row['series_cut_id'] != rule['pricing_cut_id'] or row['observation_cut_id'] not in (None,rule['pricing_cut_id']):
                    continue
            if convention in ('EXPLICIT_TIME', 'NAMED_FIXING'):
                if is_daily_bar(dims):
                    continue
                row_target = local_target(day, time.fromisoformat(cut['local_time']), zone)
                if row['observed_at_utc'] > row_target:
                    continue
                if convention == 'NAMED_FIXING' and row['observed_at_utc'] != row_target:
                    continue
                if convention == 'NAMED_FIXING' and row['received_at_utc'] < row_target:
                    continue
            eligible.append(row)
        if eligible:
            row = max(eligible, key=lambda r: (r['market_date'], r['observed_at_utc'] if convention == 'EXPLICIT_TIME' else r['received_at_utc'], r['received_at_utc'], str(r['market_data_observation_id'])))
            stale = session_distance(requested, row['market_date'], sessions)
            result.update(row=row, used=row['market_date'], staleness=stale, status='SELECTED', exception=None)
            if rule['max_staleness_business_days'] is not None and stale > rule['max_staleness_business_days']:
                result.update(status='STALE', exception='MAX_STALENESS_EXCEEDED')
    except (ValueError, KeyError) as exc:
        result['exception'] = 'CALENDAR_NOT_ASSESSED' if str(exc).startswith('Calendar coverage') else str(exc) if str(exc).isupper() else 'CALENDAR_OR_LOCAL_TIME_NOT_ASSESSED'
    if result['status'] != 'SELECTED' and rule['missing_data_action'] == 'MANUAL_OVERRIDE':
        result['status'] = 'NEEDS_OVERRIDE'
    if evidence.get('calendarEvidence', {}).get('sessions'):
        earliest = result['used'] or result['requested'] or request.valuation_date
        evidence['calendarEvidence']['sessions'] = [s for s in evidence['calendarEvidence']['sessions']
            if earliest.isoformat() <= s['date'] <= request.valuation_date.isoformat()]
    if evidence.get('calendarEvidence',{}).get('days'):
        earliest=result['used'] or result['requested'] or request.valuation_date
        evidence['calendarEvidence']['days']={day:item for day,item in evidence['calendarEvidence']['days'].items()
            if earliest.isoformat()<=day<=request.valuation_date.isoformat()}
    return result
