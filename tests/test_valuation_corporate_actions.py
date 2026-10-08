"""Temporal corporate-action safety, not position transformation."""
from datetime import date,datetime,timezone
import importlib
import pytest


def guard():
    try: return importlib.import_module('valuation.corporate_actions')
    except ModuleNotFoundError: pytest.fail('Corporate-action historical guard is missing')


def stamp(day,hour=10):
    return datetime(2026,9,day,hour,tzinfo=timezone.utc)


def dated(day=None,timestamp=None,zone=None):
    return dict(date_value=day,timestamp_value_utc=timestamp,timezone_name=zone)


@pytest.mark.parametrize('rows,expected',[
    ([dated(timestamp=stamp(15))],False),
    ([dated(timestamp=stamp(21))],True),
    ([dated(timestamp=stamp(25))],True),
    ([dated(timestamp=stamp(30))],False),
    ([dated(timestamp=stamp(20))],True),
    ([dated(date(2026,9,19))],False),
    ([dated(date(2026,9,20))],True),
    ([dated(date(2026,9,28))],True),
    ([dated(date(2026,9,29))],False),
    ([],True),
    ([dated()],True),
    ([dated(date(2026,9,15),stamp(21))],True),
])
def test_action_interval_from_execution_through_close(rows,expected):
    assert guard().action_requires_replay(stamp(20),stamp(28),rows,'UTC') is expected


def test_business_date_uses_venue_timezone_not_utc_date():
    # 00:30 UTC is still the prior business date in New York.
    executed=datetime(2026,9,21,0,30,tzinfo=timezone.utc)
    assert guard().action_requires_replay(executed,stamp(28),[dated(date(2026,9,20))],'America/New_York')


def test_source_timezone_precedes_venue_timezone():
    executed=datetime(2026,9,21,0,30,tzinfo=timezone.utc)
    assert not guard().action_requires_replay(executed,stamp(28),[dated(date(2026,9,20),zone='UTC')],'America/New_York')


@pytest.mark.parametrize('zone',[None,'Invalid/Zone'])
def test_unknown_business_date_timezone_requires_replay(zone):
    assert guard().action_requires_replay(stamp(20),stamp(28),[dated(date(2026,9,15))],zone)
