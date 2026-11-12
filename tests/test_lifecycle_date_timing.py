"""Date proximity is presentation only, with explicit holiday/coverage evidence."""
from datetime import date,datetime,timedelta,timezone
from uuid import uuid4
import pytest

def event(day,**changes):
 return dict(eventDate=day,maturityDate=day,status='UPCOMING',attention='INFORMATION',eventAtUtc=None)|changes

def source(states=None,**changes):
 return dict(name='Synthetic London calendar',timezone='Europe/London',basis='CALENDAR',reason='Listing venue calendar',days=states or {})|changes

def test_weekends_and_holiday_count_business_days_not_elapsed_days():
 from lifecycle.date_timing import timing_for_event
 now=datetime(2026,8,28,12,tzinfo=timezone.utc)
 states={date(2026,8,29):'CLOSED',date(2026,8,30):'CLOSED',date(2026,8,31):'CLOSED',date(2026,9,1):'OPEN',date(2026,9,2):'OPEN'}
 result=timing_for_event(event(date(2026,9,2)),now,source(states))
 assert result['tone']=='SOON' and result['businessDays']==2 and result['label']=='In 2 business days'

@pytest.mark.parametrize('count,tone',[(1,'SOON'),(2,'SOON'),(3,'WEEK'),(5,'WEEK'),(6,'LATER')])
def test_band_boundaries(count,tone):
 from lifecycle.date_timing import timing_for_event
 now=datetime(2026,11,2,12,tzinfo=timezone.utc);day=now.date()+timedelta(days=count)
 states={now.date()+timedelta(days=n):'OPEN' for n in range(1,count+1)}
 assert timing_for_event(event(day),now,source(states))['tone']==tone

def test_unknown_day_never_assumed_open_and_known_long_range_stops_at_six():
 from lifecycle.date_timing import timing_for_event
 now=datetime(2026,11,2,12,tzinfo=timezone.utc);day=now.date()+timedelta(days=25)
 states={now.date()+timedelta(days=n):'OPEN' for n in range(1,7)}
 assert timing_for_event(event(day),now,source(states))['tone']=='LATER'
 states.pop(date(2026,11,4))
 assert timing_for_event(event(day),now,source(states))['tone']=='NEUTRAL'

def test_today_is_calendar_local_but_earlier_timed_cutoff_is_overdue():
 from lifecycle.date_timing import timing_for_event
 now=datetime(2026,11,12,0,30,tzinfo=timezone.utc)
 us=source(timezone='America/New_York')
 assert timing_for_event(event(date(2026,11,11)),now,us)['tone']=='TODAY'
 expired=event(date(2026,11,11),eventAtUtc=now-timedelta(hours=1),status='OVERDUE',attention='ACTIONABLE')
 assert timing_for_event(expired,now,us)['tone']=='OVERDUE'

@pytest.mark.parametrize('status',['BOOKED','CONFIRMATION_RECORDED'])
def test_completed_and_informational_past_are_neutral(status):
 from lifecycle.date_timing import timing_for_event
 now=datetime(2026,11,11,12,tzinfo=timezone.utc)
 assert timing_for_event(event(now.date(),status=status),now,source())['tone']=='NEUTRAL'
 assert timing_for_event(event(date(2026,11,10)),now,source())['label']=='Date passed'

def test_unconfigured_weekday_estimate_is_explicit_and_skips_weekend():
 from lifecycle.date_timing import timing_for_event
 now=datetime(2026,11,6,12,tzinfo=timezone.utc)
 result=timing_for_event(event(date(2026,11,10)),now,None)
 assert result['tone']=='SOON' and result['businessDays']==2
 assert result['basis']=='WEEKDAYS' and result['label']=='Est. 2 weekdays'
 assert 'holidays' in result['explanation'].lower()

def test_unavailable_calendar_is_not_replaced_with_weekdays_or_assumed_utc():
 from lifecycle.date_timing import timing_for_event
 now=datetime(2026,11,11,12,tzinfo=timezone.utc)
 result=timing_for_event(event(date(2026,11,12)),now,source(basis='UNKNOWN',timezone='not/a/zone'))
 assert result['tone']=='NEUTRAL' and result['basis']=='UNKNOWN' and result['businessDays'] is None

def test_future_nonbusiness_date_is_not_rolled_or_called_today():
 from lifecycle.date_timing import timing_for_event
 now=datetime(2026,11,6,12,tzinfo=timezone.utc)
 result=timing_for_event(event(date(2026,11,7)),now,None)
 assert result['tone']=='SOON' and result['businessDays']==0 and 'Today' not in result['label']


from tests.test_valuation_service import valued

def calendar_fixture(c,tenant,states):
 from security_master_schema import models as m
 identity=uuid4()
 c.execute(m.market_calendar.insert().values(market_calendar_id=identity,calendar_code='TIMING_'+identity.hex,display_name='Synthetic Ops settlement calendar',timezone_name='Europe/London',calendar_kind='SETTLEMENT',tenant_id=tenant,coverage_from=date(2027,1,1),coverage_to=date(2027,12,31),definition_json={'days':{d.isoformat():{'status':s} for d,s in states.items()}},created_at_utc=datetime(2026,1,1,tzinfo=timezone.utc),sealed=False))
 c.execute(m.market_calendar.update().where(m.market_calendar.c.market_calendar_id==identity).values(sealed=True))
 return identity

def assign_fixture(c,r,identity):
 from security_master_schema import models as m
 from security_master_schema.demo_data import DEMO_IDS as ids
 c.execute(m.calendar_assignment.insert().values(tenant_id=r.tenant_id,market_calendar_id=identity,target_kind='STRATEGY',target_id=r.strategy_id,purpose='SETTLEMENT',valid_from=date(2027,1,1),valid_to=date(2027,12,31),reason='Synthetic display calendar',submission_key=str(uuid4()),submission_fingerprint='f'*64,created_by_user_account_id=ids['demo_user_account'],created_at_utc=datetime(2026,1,1,tzinfo=timezone.utc)))

def test_batch_uses_sealed_strategy_calendar_and_fixed_query_budget(valued):
 from lifecycle.date_timing_store import add_date_timing
 from tests.test_structured_batch_reads import QueryCounter
 c,r,_=valued;now=datetime(2027,1,8,12,tzinfo=timezone.utc)
 states={date(2027,1,9):'CLOSED',date(2027,1,10):'CLOSED',date(2027,1,11):'CLOSED',date(2027,1,12):'HALF_DAY',date(2027,1,13):'OPEN'}
 # Frozen tenant days normally contain OPEN/CLOSED; HALF_DAY is open for proximity.
 calendar=calendar_fixture(c,r.tenant_id,states);assign_fixture(c,r,calendar)
 def rows(n):return [event(date(2027,1,13),strategyId=r.strategy_id,instrumentId=uuid4(),eventType='BOND_MATURITY') for _ in range(n)]
 first=rows(1)
 with QueryCounter(c) as small:add_date_timing(c,r.tenant_id,first,now)
 many=rows(30)
 with QueryCounter(c) as large:add_date_timing(c,r.tenant_id,many,now)
 assert small.count==large.count and large.count<=5
 assert all(item['dateTiming']['basis']=='CALENDAR' and item['dateTiming']['businessDays']==2 for item in many)
 assert first[0]['status']=='UPCOMING' and first[0]['eventDate']==date(2027,1,13)

def test_inaccessible_calendar_never_leaks_name_or_falls_back(valued):
 from lifecycle.date_timing_store import add_date_timing
 from security_master_schema.demo_data import DEMO_IDS as ids
 c,r,_=valued;identity=calendar_fixture(c,ids['second_tenant'],{})
 assign_fixture(c,r,identity)
 row=event(date(2027,1,11),strategyId=r.strategy_id,instrumentId=uuid4(),eventType='BOND_MATURITY')
 add_date_timing(c,r.tenant_id,[row],datetime(2027,1,8,12,tzinfo=timezone.utc))
 assert row['dateTiming']['tone']=='NEUTRAL' and row['dateTiming']['basis']=='UNKNOWN'
 assert row['dateTiming']['calendarName'] is None

def test_no_assigned_calendar_is_explicit_weekday_estimate(valued):
 from lifecycle.date_timing_store import add_date_timing
 c,r,_=valued
 row=event(date(2027,1,11),strategyId=r.strategy_id,instrumentId=uuid4(),eventType='BOND_MATURITY')
 add_date_timing(c,r.tenant_id,[row],datetime(2027,1,8,12,tzinfo=timezone.utc))
 assert row['dateTiming']['label']=='Est. 1 weekday' and row['dateTiming']['basis']=='WEEKDAYS'


def test_reference_sessions_holidays_and_conflicts_are_not_weekday_assumptions(valued):
 from datetime import time
 from sqlalchemy import select
 from lifecycle.date_timing_store import add_date_timing
 from security_master_schema import models as m
 c,r,_=valued;identity=uuid4();now=datetime(2027,1,8,12,tzinfo=timezone.utc)
 c.execute(m.market_calendar.insert().values(market_calendar_id=identity,calendar_code='TIMING_PUBLIC_'+identity.hex,display_name='Synthetic reference sessions',timezone_name='Europe/London',calendar_kind='SETTLEMENT',coverage_from=date(2027,1,1),coverage_to=date(2027,12,31),created_at_utc=datetime(2026,1,1,tzinfo=timezone.utc),sealed=False))
 for day,state in [(date(2027,1,9),'CLOSED'),(date(2027,1,10),'CLOSED'),(date(2027,1,12),'HALF_DAY'),(date(2027,1,13),'OPEN')]:
  c.execute(m.market_calendar_session.insert().values(market_calendar_id=identity,session_date=day,session_status=state,open_local_time=time(8) if state!='CLOSED' else None,close_local_time=time(16) if state!='CLOSED' else None,source_reference='Synthetic source'))
 c.execute(m.market_calendar_holiday.insert().values(market_calendar_id=identity,holiday_date=date(2027,1,11),holiday_name='Synthetic bank closure',source_reference='Synthetic source'))
 c.execute(m.market_calendar.update().where(m.market_calendar.c.market_calendar_id==identity).values(sealed=True))
 assign_fixture(c,r,identity)
 row=event(date(2027,1,13),strategyId=r.strategy_id,instrumentId=uuid4(),eventType='BOND_MATURITY')
 add_date_timing(c,r.tenant_id,[row],now)
 assert row['dateTiming']['businessDays']==2 and row['dateTiming']['basis']=='CALENDAR'

def test_coupon_calendar_precedes_strategy_calendar_and_never_rolls_date(valued):
 from sqlalchemy import select
 from tests.test_coupon_worklist import setup
 from lifecycle import coupon_tables as ct
 from security_master_schema import models as m
 from lifecycle.date_timing_store import add_date_timing
 c,r,trade=valued;schedule=setup(c,r,trade);period=schedule['cashflows'][0]['cashflow_id']
 now=datetime(2027,1,8,12,tzinfo=timezone.utc)
 days={date(2027,1,9):'CLOSED',date(2027,1,10):'CLOSED',date(2027,1,11):'CLOSED',date(2027,1,12):'OPEN'}
 calendar=calendar_fixture(c,r.tenant_id,days)
 # Clone a new retained schedule version rather than rewriting a schedule row.
 header=dict(c.execute(select(ct.schedule).where(ct.schedule.c.schedule_id==schedule['schedule_id'])).mappings().one())
 header.update(schedule_id=uuid4(),revision=2,supersedes_schedule_id=schedule['schedule_id'],calendar_id=calendar,request_key=str(uuid4()))
 c.execute(ct.schedule.insert().values(**header))
 flow=dict(c.execute(select(ct.cashflow).where(ct.cashflow.c.cashflow_id==period)).mappings().one());flow.update(cashflow_id=uuid4(),schedule_id=header['schedule_id']);c.execute(ct.cashflow.insert().values(**flow))
 weekday=calendar_fixture(c,r.tenant_id,{d:'OPEN' for d in days});assign_fixture(c,r,weekday)
 row=event(date(2027,1,12),strategyId=r.strategy_id,instrumentId=header['instrument_id'],eventType='BOND_COUPON',couponPeriodId=flow['cashflow_id'])
 add_date_timing(c,r.tenant_id,[row],now)
 assert row['dateTiming']['businessDays']==1 and 'Coupon schedule calendar' in row['dateTiming']['explanation']
 assert row['eventDate']==date(2027,1,12)
