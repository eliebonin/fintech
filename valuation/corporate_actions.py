"""Fail closed on unrepresented unit/security changes; never mutate trades.

Only reviewed basic share-ratio replay is implemented. This guard checks the
entire retained exposure life, not merely the requested P&L period.
"""
from zoneinfo import ZoneInfo,ZoneInfoNotFoundError
from sqlalchemy import select,and_
from security_master_schema import models as m
from .positions import aware


UNIT_CHANGING_ACTIONS=('STOCK_SPLIT','BONUS_ISSUE','SPIN_OFF','MERGER','SECURITY_REPLACEMENT')


def assert_native_mark_units(events,subject,cutoff,price_date,*,daily=False):
    """Freshness permission is not permission to mix pre/post-action units."""
    for event in events:
        if event.subject_id!=subject: continue
        post_action=cutoff.date()>=event.effective_date if daily else cutoff>=event.effective_at
        if post_action and (price_date is None or price_date<event.effective_date):
            raise ValueError(f'Corporate action {event.action_id}: pre-action price dated {price_date} '
                f'cannot value post-action units on {cutoff.date()}; a compatible post-action RAW mark is required')


def action_requires_replay(executed_at,closing_cutoff,date_rows,venue_timezone):
    """True if a relevant action may have occurred during this booking's life.

    Date-only evidence cannot establish ordering on the execution/closing day.
    Exact timestamps can; equality with execution is still unresolved ordering.
    Either EX or EFFECTIVE may affect quote/quantity compatibility, so neither
    date is silently preferred over the other. Incomplete evidence fails closed.
    """
    aware(executed_at);aware(closing_cutoff)
    if not date_rows: return True
    for row in date_rows:
        day=row.get('date_value');instant=row.get('timestamp_value_utc')
        zone_name=row.get('timezone_name') or venue_timezone
        if instant is not None:
            try:
                aware(instant)
                if day is not None and instant.astimezone(ZoneInfo(zone_name)).date()!=day:
                    return True  # Contradictory source date/time, not a safe exclusion.
            except (ValueError,TypeError,ZoneInfoNotFoundError):
                return True
            if executed_at<=instant<=closing_cutoff: return True
        elif day is not None:
            try: zone=ZoneInfo(zone_name)
            except (ValueError,TypeError,ZoneInfoNotFoundError): return True
            if executed_at.astimezone(zone).date()<=day<=closing_cutoff.astimezone(zone).date():
                return True
        else:
            return True
    return False


def assert_no_unreplayed_actions(c,lots,closing_cutoff,information_cutoff,error_type,*,represented=(),tenant_id=...,reviewed_events=()):
    """Batch-load canonical actions, then apply per-booking temporal safety.

    The existing operational runner persists this safe diagnostic on rollback.
    Date rows have no independent recorded timestamp in the current schema;
    historical date-version governance is a separate prerequisite for replay.
    """
    subjects={lot.subject_id for lot in lots}
    parents={row.listing_node_id:(row.instrument_node_id,row.timezone_name)
        for row in c.execute(select(m.listing.c.listing_node_id,m.listing.c.instrument_node_id,
            m.market_venue.c.timezone_name).select_from(m.listing.outerjoin(m.market_venue)).where(
                m.listing.c.listing_node_id.in_(subjects)))}
    canonical=set(c.scalars(select(m.instrument.c.instrument_node_id).where(m.instrument.c.instrument_node_id.in_(subjects-parents.keys()))))
    # No venue timezone is fabricated for OTC instruments. Timestamped action
    # evidence can be ordered; date-only actions without a timezone fail closed.
    parents.update({subject:(subject,None) for subject in canonical})
    if subjects-parents.keys():
        raise error_type('Corporate action safety requires an explicit canonical listing parent')
    from market_data.split_replay import current_actions,historical_guard_ids
    current=current_actions(c,{parent for parent,_ in parents.values()},information_cutoff,scope_tenant=tenant_id)
    identities={r['corporate_action_id'] for r in current if r['status']!='CANCELLED' and r['event_type'] in UNIT_CHANGING_ACTIONS}
    identities.update(historical_guard_ids(c,current,information_cutoff,reviewed_events,tenant_id))
    actions=m.corporate_action;dates=m.corporate_action_date
    rows=c.execute(select(actions,dates.c.date_value,dates.c.timestamp_value_utc,dates.c.timezone_name)
        .select_from(actions.outerjoin(dates,and_(dates.c.corporate_action_id==actions.c.corporate_action_id,
            dates.c.date_role.in_(['EX','EFFECTIVE'])))).where(
                actions.c.corporate_action_id.in_(identities))
        .order_by(actions.c.corporate_action_id,dates.c.corporate_action_date_id)).mappings().all()
    by_parent={}
    for row in rows:
        by_parent.setdefault(row['affected_instrument_node_id'],{}).setdefault(row['corporate_action_id'],[]).append(row)
    for lot in lots:
        parent,zone=parents[lot.subject_id]
        for action_id,action_dates in by_parent.get(parent,{}).items():
            if (lot.subject_id,action_id) in represented: continue
            if action_requires_replay(lot.executed_at,getattr(lot,'ended_at',closing_cutoff),action_dates,zone):
                first=action_dates[0]
                effective=first['timestamp_value_utc'] or first['date_value'] or 'UNKNOWN'
                raise error_type(f"Corporate action {action_id} ({first['event_type']}, date {effective}) "
                    f"affects instrument {parent}, trade {lot.trade_id}; unit/identity changes may occur "
                    'between execution and close. Corporate-action replay or unambiguous date evidence is required.')


def assert_projection_actions(c,projection,error_type,*,reviewed_events=None):
    """Guard actual exposure intervals, including round trips with no closing mark."""
    from dataclasses import dataclass
    @dataclass(frozen=True)
    class GuardExposure:
        subject_id: object
        trade_id: object
        executed_at: object
        ended_at: object
    exposures=[GuardExposure(interval.key.subject_id,interval.trade_ids[0],interval.started_at,interval.ended_at)
        for interval in projection.exposures]
    if exposures:
        assert_no_unreplayed_actions(c,exposures,projection.request.closing_cutoff,
            projection.request.information_cutoff,error_type,
            represented={(event.subject_id,event.action_id) for event in projection.split_events},tenant_id=projection.request.tenant_id,
            reviewed_events=projection.split_events if reviewed_events is None else reviewed_events)
