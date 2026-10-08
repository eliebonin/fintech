"""Deterministic local targets and explicitly covered trading-session arithmetic."""
from datetime import datetime,timedelta,timezone
from zoneinfo import ZoneInfo


def local_target(day,local_time,timezone_name):
    zone=ZoneInfo(timezone_name)
    naive=datetime.combine(day,local_time)
    first=naive.replace(tzinfo=zone,fold=0)
    second=naive.replace(tzinfo=zone,fold=1)
    if first.astimezone(timezone.utc).astimezone(zone).replace(tzinfo=None)!=naive:
        raise ValueError('Nonexistent local pricing time')
    if first.utcoffset()!=second.utcoffset():
        raise ValueError('Ambiguous local pricing time')
    return first.astimezone(timezone.utc)


def session_target(day,sessions,lag=0):
    if not isinstance(lag,int) or isinstance(lag,bool) or lag<0:
        raise ValueError('Nonnegative session lag required')
    while True:
        if day not in sessions:
            raise ValueError('Calendar coverage is not assessed for the target')
        close=sessions[day]
        if close is not None:
            if lag==0:
                return day,close
            lag-=1
        day-=timedelta(days=1)


def session_distance(requested,used,sessions):
    if used>requested:
        raise ValueError('Future session cannot be used')
    distance=0
    while used<requested:
        used+=timedelta(days=1)
        if used not in sessions:
            raise ValueError('Calendar coverage is not assessed for staleness')
        distance+=sessions[used] is not None
    return distance
