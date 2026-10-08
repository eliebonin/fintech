"""Exchange holidays, missing bars and uncertain history are different issues."""
from datetime import date


def test_reconciliation_detects_omitted_session_without_calling_holiday_missing():
    from market_data.coverage import reconcile_dates
    expected={date(2026,7,1),date(2026,7,2),date(2026,7,6)}
    report=reconcile_dates({date(2026,7,1),date(2026,7,6)},expected)
    assert report['missingSessions']==['2026-07-02']
    assert report['unavailableLeadingSessions']==[]
    assert report['status']=='GAPS'


def test_short_history_is_not_assumed_to_be_listing_inception():
    from market_data.coverage import reconcile_dates
    report=reconcile_dates({date(2026,7,6)},{date(2026,7,1),date(2026,7,2),date(2026,7,6)})
    assert report['missingSessions']==[]
    assert report['unavailableLeadingSessions']==['2026-07-01','2026-07-02']
    assert report['status']=='SHORT_HISTORY'


def test_versioned_calendars_distinguish_known_us_and_paris_holidays():
    from market_data.coverage import calendar_sessions
    days,evidence=calendar_sessions('XNYS',date(2026,7,1),date(2026,7,6))
    assert days=={date(2026,7,1),date(2026,7,2),date(2026,7,6)}
    assert evidence['calendar']=='NYSE' and evidence['packageVersion']
    days,_=calendar_sessions('XPAR',date(2026,4,2),date(2026,4,7))
    assert days=={date(2026,4,2),date(2026,4,7)}
    assert calendar_sessions('UNSUPPORTED',date(2026,1,1),date(2026,1,2))[0] is None
