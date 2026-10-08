"""Fail closed on unrepresented unit/security changes; never mutate trades.

Corporate-action replay is not implemented. This guard therefore checks the
entire life of each retained booking, not merely the requested P&L period.
"""
from zoneinfo import ZoneInfo,ZoneInfoNotFoundError
from sqlalchemy import select,and_
from security_master_schema import models as m
from .positions import aware


UNIT_CHANGING_ACTIONS=('STOCK_SPLIT','BONUS_ISSUE','SPIN_OFF','MERGER','SECURITY_REPLACEMENT')


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


def assert_no_unreplayed_actions(c,lots,closing_cutoff,information_cutoff,error_type):
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
    if subjects-parents.keys():
        raise error_type('Corporate action safety requires an explicit canonical listing parent')
    actions=m.corporate_action;dates=m.corporate_action_date
    rows=c.execute(select(actions,dates.c.date_value,dates.c.timestamp_value_utc,dates.c.timezone_name)
        .select_from(actions.outerjoin(dates,and_(dates.c.corporate_action_id==actions.c.corporate_action_id,
            dates.c.date_role.in_(['EX','EFFECTIVE'])))).where(
                actions.c.affected_instrument_node_id.in_({parent for parent,_ in parents.values()}),
                actions.c.recorded_at_utc<=information_cutoff,actions.c.status!='CANCELLED',
                actions.c.event_type.in_(UNIT_CHANGING_ACTIONS))
        .order_by(actions.c.corporate_action_id,dates.c.corporate_action_date_id)).mappings().all()
    by_parent={}
    for row in rows:
        by_parent.setdefault(row['affected_instrument_node_id'],{}).setdefault(row['corporate_action_id'],[]).append(row)
    for lot in lots:
        parent,zone=parents[lot.subject_id]
        for action_id,action_dates in by_parent.get(parent,{}).items():
            if action_requires_replay(lot.executed_at,getattr(lot,'ended_at',closing_cutoff),action_dates,zone):
                first=action_dates[0]
                effective=first['timestamp_value_utc'] or first['date_value'] or 'UNKNOWN'
                raise error_type(f"Corporate action {action_id} ({first['event_type']}, date {effective}) "
                    f"affects instrument {parent}, trade {lot.trade_id}; unit/identity changes may occur "
                    'between execution and close. Corporate-action replay or unambiguous date evidence is required.')


def assert_projection_actions(c,projection,error_type):
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
            projection.request.information_cutoff,error_type)
