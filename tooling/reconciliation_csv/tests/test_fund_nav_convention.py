"""Fund NAV lag is explicit policy/calendar configuration; FX dates stay current."""
from datetime import date,time
from uuid import uuid4
from tooling.reconciliation_csv.reconciliation_eligibility import build_policy


def test_fund_nav_uses_one_valuation_session_lag_and_fx_stays_same_day():
    strategy,cut,calendar,prices,fx,nav_calendar=[uuid4() for _ in range(6)]
    types={kind:uuid4() for kind in ('BOND','ACTIVELY_MANAGED_CERTIFICATE','OPTION','SWAP','FX_FORWARD','FUND_SHARE_CLASS')}
    policy=build_policy(strategy,cut,calendar,prices,fx,date(2026,9,21),types,
        include_fund_nav=True,fund_nav_calendar_id=nav_calendar)
    nav=next(rule for rule in policy.rules if rule.series_type=='NAV')
    assert nav.pricing_convention=='NAV_DATE' and nav.market_calendar_id==nav_calendar
    assert nav.pricing_date_rule=='FIXED_LAG' and nav.lag_business_days==1
    assert nav.max_staleness_business_days==0
    for rule in policy.rules:
        if rule.series_type!='NAV':assert rule.pricing_date_rule=='SAME_DAY' and rule.lag_business_days==0


def test_reconciliation_nav_calendar_excludes_weekends_without_inventing_holidays():
    from tooling.reconciliation_csv.reconciliation_eligibility import fund_nav_calendar_payload
    payload=fund_nav_calendar_payload(uuid4(),date(2026,9,21),date(2026,10,20))
    assert payload.purpose=='VALUATION' and payload.mode=='WEEKDAYS'
    assert payload.weekdays==[0,1,2,3,4] and payload.base_calendar_ids==[]
    assert payload.exceptions==[]


def test_previous_nav_boundaries_use_the_fund_calendar_including_weekends_and_closures():
    from market_data.pricing_conventions import session_target
    sessions={date(2026,10,15):time(23,59,59),date(2026,10,16):time(23,59,59),
        date(2026,10,17):None,date(2026,10,18):None,date(2026,10,19):time(23,59,59),date(2026,10,20):time(23,59,59)}
    assert session_target(date(2026,10,20),sessions,lag=1)[0]==date(2026,10,19)
    assert session_target(date(2026,10,19),sessions,lag=1)[0]==date(2026,10,16)
    sessions[date(2026,10,16)]=None
    assert session_target(date(2026,10,19),sessions,lag=1)[0]==date(2026,10,15)
