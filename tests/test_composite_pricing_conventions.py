"""Pure temporal contracts: wrong DST/calendar branches change selected inputs."""
from datetime import date,datetime,time,timezone
import pytest


def test_local_target_tracks_london_and_new_york_dst_independently():
    from market_data.pricing_conventions import local_target
    assert local_target(date(2026,3,16),time(16),'Europe/London')==datetime(2026,3,16,16,tzinfo=timezone.utc)
    assert local_target(date(2026,3,16),time(16),'America/New_York')==datetime(2026,3,16,20,tzinfo=timezone.utc)


@pytest.mark.parametrize('day',[date(2026,3,29),date(2026,10,25)])
def test_nonexistent_and_ambiguous_london_times_are_rejected(day):
    from market_data.pricing_conventions import local_target
    with pytest.raises(ValueError): local_target(day,time(1,30),'Europe/London')


def test_session_target_uses_early_close_and_rolls_only_known_closed_dates():
    from market_data.pricing_conventions import session_target
    sessions={date(2026,11,25):time(16),date(2026,11,26):None,date(2026,11,27):time(13)}
    assert session_target(date(2026,11,27),sessions)==(date(2026,11,27),time(13))
    assert session_target(date(2026,11,26),sessions)==(date(2026,11,25),time(16))
    with pytest.raises(ValueError): session_target(date(2026,11,28),sessions)


def test_staleness_counts_open_sessions_not_generic_weekdays():
    from market_data.pricing_conventions import session_distance,session_target
    sessions={date(2026,11,25):time(16),date(2026,11,26):None,date(2026,11,27):time(13)}
    assert session_distance(date(2026,11,27),date(2026,11,25),sessions)==1
    assert session_target(date(2026,11,27),sessions,lag=1)==(date(2026,11,25),time(16))
