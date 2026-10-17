from datetime import date,datetime,timezone,time
from pathlib import Path
import json
import pytest

REVIEW=Path(__file__).resolve().parents[1]/'data/xpar-calendar-review-2026.json'

def draft():
    from market_data.reference_calendar_import import build_reviewed_schedule
    return build_reviewed_schedule(json.loads(REVIEW.read_text()))

def test_import_covers_every_day_and_distinguishes_holidays_half_days():
    result=draft(); rows={r['session_date']:r for r in result['sessions']}
    assert len(rows)==365
    assert rows[date(2026,4,3)]['session_status']=='CLOSED'
    assert rows[date(2026,10,10)]['session_status']=='CLOSED'
    assert rows[date(2026,12,24)]['session_status']=='HALF_DAY'
    assert rows[date(2026,12,24)]['close_local_time']==time(14,5)
    assert rows[date(2026,10,8)]['close_local_time']==time(17,30)
    assert result['provenance']['sourceKind']=='REVIEWED_LIBRARY_SCHEDULE'
    assert result['provenance']['exchangeCertified'] is False
    assert result['provenance']['packageVersion']
    assert len(result['provenance']['scheduleSha256'])==64

def test_disagreement_with_review_refuses_publication():
    from market_data.reference_calendar_import import build_reviewed_schedule
    review=json.loads(REVIEW.read_text()); review['closedWeekdays']['2026-10-08']='Incorrect closure'
    with pytest.raises(ValueError,match='disagrees'):
        build_reviewed_schedule(review)

def test_review_without_source_is_rejected():
    from market_data.reference_calendar_import import build_reviewed_schedule
    review=json.loads(REVIEW.read_text()); review['sourceReference']=''
    with pytest.raises(ValueError,match='source'):
        build_reviewed_schedule(review)

def test_snapshot_can_be_sealed_without_claiming_exchange_review():
    from market_data.reference_calendar_import import build_reviewed_schedule
    review={'mode':'LIBRARY_SNAPSHOT','mic':'XNYS','calendarName':'NYSE','year':2026,
        'reviewedOn':'2026-10-13','sourceReference':'https://pandas-market-calendars.readthedocs.io/en/latest/',
        'reviewScope':'Pinned regular equities only','publicationStatus':'ACTIVE'}
    result=build_reviewed_schedule(review)
    rows={r['session_date']:r for r in result['sessions']}
    assert rows[date(2026,11,27)]['session_status']=='HALF_DAY'
    assert rows[date(2026,11,27)]['close_local_time']==time(13)
    assert result['provenance']['sourceKind']=='LIBRARY_SNAPSHOT'
    assert not result['provenance']['exchangeCertified']

def test_snapshot_boundaries_do_not_invent_unreviewed_future_sessions():
    from market_data.reference_calendar_import import build_reviewed_schedule
    result=build_reviewed_schedule({'mode':'LIBRARY_SNAPSHOT','mic':'XNSE','calendarName':'NSE','year':2026,
        'coverageTo':'2026-10-13','reviewedOn':'2026-10-13','sourceReference':'library',
        'reviewScope':'Future special sessions not included','publicationStatus':'ACTIVE'})
    assert result['end']==date(2026,10,13)
    assert len(result['sessions'])==286

def test_review_required_calendar_cannot_be_activated():
    from apps.reference_api.db import get_engine
    from security_master_schema.demo_data import DEMO_IDS as ids
    from market_data.reference_calendar_import import publish_reviewed_schedule,activate_calendar
    with get_engine().connect() as c:
        tx=c.begin()
        try:
            review={'mode':'LIBRARY_SNAPSHOT','mic':'XLON','calendarName':'LSE','year':2026,
                'reviewedOn':'2026-10-13','sourceReference':'library','reviewScope':'Unresolved source check',
                'publicationStatus':'REVIEW_REQUIRED'}
            cid=publish_reviewed_schedule(c,ids['platform_admin_user_account'],review)
            with pytest.raises(ValueError,match='active sealed'):
                activate_calendar(c,ids['platform_admin_user_account'],cid,'XLON')
        finally: tx.rollback()

def test_published_import_replays_and_exposes_provenance():
    from apps.reference_api.db import get_engine
    from sqlalchemy import select
    from security_master_schema import models as m
    from security_master_schema.demo_data import DEMO_IDS as ids
    from market_data.reference_calendar_import import publish_reviewed_schedule
    from market_data.policy_selection import calendar_context
    with get_engine().connect() as c:
        tx=c.begin()
        try:
            review=json.loads(REVIEW.read_text())
            cid=publish_reviewed_schedule(c,ids['platform_admin_user_account'],review)
            assert publish_reviewed_schedule(c,ids['platform_admin_user_account'],review)==cid
            row=c.execute(select(m.market_calendar).where(m.market_calendar.c.market_calendar_id==cid)).mappings().one()
            assert row['sealed'] and row['coverage_from']==date(2026,1,1)
            assert row['definition_json']['provenance']['sourceReference']==review['sourceReference']
            sessions,zone,evidence=calendar_context(c,cid,None,date(2026,10,8),asof=datetime.now(timezone.utc))
            assert sessions[date(2026,10,8)]==time(17,30) and zone=='Europe/Paris'
            assert evidence['provenance']['scheduleSha256']==row['definition_json']['provenance']['scheduleSha256']
            with pytest.raises(PermissionError):
                publish_reviewed_schedule(c,ids['demo_user_account'],review)
        finally: tx.rollback()
