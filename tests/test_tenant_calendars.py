"""Real HTTP and database calendar governance; disposable runner only."""
from uuid import UUID, uuid4
from datetime import date, datetime, timezone
import pytest
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError
from tests.test_composite_policy_api import call
from apps.reference_api.db import get_engine
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS

ROOT='/v1/market-data/calendars'
STRATEGY=None

@pytest.fixture(autouse=True)
def isolated_strategy():
    global STRATEGY
    STRATEGY=uuid4()
    with get_engine().begin() as c:
        c.execute(m.strategy.insert().values(strategy_id=STRATEGY,tenant_id=DEMO_IDS['tenant'],strategy_code='CAL_'+uuid4().hex,
            display_name='Synthetic calendar strategy',strategy_type='FUND',status='ACTIVE',effective_from=date(2020,1,1)))

def payload(**changes):
    return dict(calendarCode='FUND_'+uuid4().hex[:12],displayName='Fund valuation days',purpose='VALUATION',
        timezoneName='Europe/Dublin',decisionTime='16:00:00',coverageFrom='2026-08-28',coverageTo='2026-09-01',
        mode='WEEKDAYS',weekdays=[0,1,2,3,4],sourceReference='Synthetic administrator notice',
        exceptions=[dict(date='2026-08-31',status='CLOSED',reason='UK and Irish rule',sourceReference='Notice 1')],**changes)

def created(data=None):
    result=call('POST',ROOT,data or payload())
    assert result.status_code==201,result.text
    return result.json()

def test_publication_replay_and_version_history():
    data=payload(); key=str(uuid4()); first=call('POST',ROOT,data,key)
    assert first.status_code==201,first.text
    assert first.json()['versionNo']==1
    assert call('POST',ROOT,data,key).json()==first.json()
    data['displayName']='Revised'
    assert call('POST',ROOT,data,key).status_code==409
    second=created(data)
    assert second['versionNo']==2
    assert call('GET',ROOT+'/'+first.json()['calendarId']).json()['displayName']=='Fund valuation days'
    days=call('GET',ROOT+'/'+second['calendarId']+'/days?fromDate=2026-08-28&toDate=2026-09-02').json()['days']
    assert [d['status'] for d in days]==['OPEN','CLOSED','CLOSED','CLOSED','OPEN','UNKNOWN']

def test_explicit_schedule_never_implies_coverage():
    data=payload(); data['mode']='EXPLICIT'
    value=created(data)
    days=call('GET',ROOT+'/'+value['calendarId']+'/days?fromDate=2026-08-28&toDate=2026-08-31').json()['days']
    assert days[0]['status']=='UNKNOWN' and days[-1]['status']=='CLOSED'

def test_published_calendar_and_sessions_cannot_be_changed():
    value=created(); cal_id=UUID(value['calendarId'])
    with get_engine().begin() as c:
        with pytest.raises(DBAPIError),c.begin_nested():
            c.execute(m.market_calendar.update().where(m.market_calendar.c.market_calendar_id==cal_id).values(display_name='Rewrite'))
        with pytest.raises(DBAPIError),c.begin_nested():
            c.execute(m.market_calendar_session.delete().where(m.market_calendar_session.c.market_calendar_id==cal_id))

def test_calendar_permissions_and_missing_ids():
    assert call('GET',ROOT+'/'+str(uuid4())).status_code==404
    membership=m.tenant_user_account
    where=(membership.c.tenant_id==DEMO_IDS['tenant']) & (membership.c.user_account_id==DEMO_IDS['demo_user_account'])
    with get_engine().begin() as c:
        rows=c.execute(select(membership.c.tenant_user_account_id,membership.c.membership_role).where(where)).all()
        c.execute(membership.update().where(where).values(membership_role='READ_ONLY'))
        group=c.execute(m.access_group.insert().values(tenant_id=DEMO_IDS['tenant'],code=uuid4().hex,display_name='Calendar reader').returning(m.access_group.c.group_id)).scalar_one()
        c.execute(m.access_group_member.insert().values(tenant_id=DEMO_IDS['tenant'],group_id=group,user_account_id=DEMO_IDS['demo_user_account']))
        c.execute(m.access_group_grant.insert().values(tenant_id=DEMO_IDS['tenant'],group_id=group,action_code='CALENDAR_READ'))
    try:
        assert call('GET',ROOT+'/options').json()['canManage'] is False
        assert call('POST',ROOT,payload()).status_code==403
    finally:
        with get_engine().begin() as c:
            c.execute(m.access_group_member.delete().where(m.access_group_member.c.group_id==group))
            c.execute(m.access_group_grant.delete().where(m.access_group_grant.c.group_id==group))
            c.execute(m.access_group.delete().where(m.access_group.c.group_id==group))
            for rid,role in rows:
                c.execute(membership.update().where(membership.c.tenant_user_account_id==rid).values(membership_role=role))

def test_composition_freezes_governed_holidays_and_unknowns():
    with get_engine().begin() as c:
        cid=c.execute(m.market_calendar.insert().values(calendar_code='REF_'+uuid4().hex,display_name='Irish bank days',timezone_name='Europe/Dublin',calendar_kind='HOLIDAY').returning(m.market_calendar.c.market_calendar_id)).scalar_one()
        c.execute(m.market_calendar_holiday.insert().values(market_calendar_id=cid,holiday_date=date(2026,8,31),holiday_name='Published closure',source_reference='Synthetic source'))
    data=payload(); data.update(mode='ALL_OPEN',baseCalendarIds=[str(cid)],exceptions=[])
    value=created(data)
    with get_engine().begin() as c:
        c.execute(m.market_calendar_holiday.delete().where(m.market_calendar_holiday.c.market_calendar_id==cid))
    days=call('GET',ROOT+'/'+value['calendarId']+'/days?fromDate=2026-08-28&toDate=2026-08-31').json()['days']
    assert days[0]['status']=='UNKNOWN' and days[-1]['status']=='CLOSED'

def assign(value,kind='STRATEGY',target=None,**changes):
    data=dict(calendarId=value['calendarId'],targetKind=kind,targetId=str(target or STRATEGY),
        validFrom='2026-08-28',validTo='2026-09-01',reason='Synthetic acceptance',**changes)
    result=call('POST',ROOT+'/assignments',data)
    assert result.status_code==201,result.text
    return result.json()

def resolve(subject=None,strategy=None,day='2026-08-31',asof='2099-01-01T22:00:00Z'):
    from security_master_schema.market_data_resolver import ResolutionRequest,resolve_market_data
    request=ResolutionRequest(tenant_id=DEMO_IDS['tenant'],subject_reference_node_id=subject or DEMO_IDS['hsbc_xlon_listing_node'],
        valuation_policy_id=DEMO_IDS['valuation_policy'],valuation_date=date.fromisoformat(day),
        valuation_cut_id=DEMO_IDS['valuation_cut'],market_data_as_of_utc=datetime.fromisoformat(asof.replace('Z','+00:00')),
        use_purpose='VALUATION',strategy_id=strategy)
    with get_engine().connect() as c: return resolve_market_data(c,request)

def test_strategy_calendar_closed_is_not_missing_price_and_cutoff_hides_later_assignment():
    value=created(); decision=assign(value)
    item=resolve(strategy=STRATEGY)
    assert item.status=='NOT_EXPECTED' and item.exception_code=='STRATEGY_VALUATION_CLOSED'
    assert item.selected_value is None and item.pricing_evidence['calendarDecisions'][0]['assignmentId']==decision['assignmentId']
    historical=resolve(strategy=STRATEGY,asof='2026-09-01T22:00:00Z')
    assert historical.status!='NOT_EXPECTED'

def test_fund_calendar_applies_to_nav_not_exchange_price():
    assign(created(),'FUND_REFERENCE',DEMO_IDS['demo_fund_node'])
    nav=resolve(subject=DEMO_IDS['demo_share_class_instrument_node'])
    assert nav.status=='NOT_EXPECTED' and nav.exception_code=='FUND_VALUATION_CLOSED'
    assert resolve().exception_code!='FUND_VALUATION_CLOSED'

def test_assignment_purposes_and_overlap_validation():
    data=payload(); data['purpose']='DEALING'; assign(created(data))
    assert resolve(strategy=STRATEGY).exception_code!='STRATEGY_VALUATION_CLOSED'
    value=created(); assign(value)
    overlap=dict(calendarId=value['calendarId'],targetKind='STRATEGY',targetId=str(STRATEGY),
        validFrom='2026-08-29',validTo='2026-09-01',reason='Overlapping different interval')
    assert call('POST',ROOT+'/assignments',overlap).status_code==422

def test_unknown_assigned_day_is_unresolved_not_an_open_day():
    data=payload(); data['mode']='EXPLICIT'; assign(created(data))
    result=resolve(strategy=STRATEGY,day='2026-08-28')
    assert result.status=='MISSING' and result.exception_code=='CALENDAR_NOT_ASSESSED'

def test_nav_session_lag_uses_fund_days_not_weekdays():
    data=payload(); data.update(coverageFrom='2026-08-24',exceptions=[dict(date='2026-08-27',status='CLOSED',reason='Fund closure',sourceReference='Administrator')])
    value=created(data)
    policy=dict(policyCode='NAV_CAL_'+uuid4().hex,displayName='NAV calendar lag',valuationCutId=str(DEMO_IDS['valuation_cut']),validFrom='2026-08-24',
        rules=[dict(ruleSequence=1,seriesType='OFFICIAL_NAV',pricingConvention='NAV_DATE',marketCalendarId=value['calendarId'],
            subjectReferenceNodeId=str(DEMO_IDS['demo_share_class_instrument_node']),pricingDateRule='FIXED_LAG',lagBusinessDays=1)])
    response=call('POST','/v1/market-data/valuation-policies',policy)
    assert response.status_code==201,response.text
    preview=call('POST','/v1/market-data/resolution-preview',dict(subjectReferenceNodeIds=[str(DEMO_IDS['demo_share_class_instrument_node'])],
        valuationPolicyId=response.json()['valuationPolicyId'],valuationDate='2026-08-28',valuationCutId=str(DEMO_IDS['valuation_cut']),
        marketDataAsOfUtc='2099-01-01T22:00:00Z',usePurpose='VALUATION'))
    assert preview.status_code==200,preview.text
    assert preview.json()['items'][0]['pricingDateRequested']=='2026-08-26'

def test_exchange_holiday_cannot_be_ignored_when_session_claims_open():
    with get_engine().begin() as c:
        cid=c.execute(m.market_calendar.insert().values(calendar_code='CONFLICT_'+uuid4().hex,display_name='Conflicting reference',timezone_name='Europe/London',calendar_kind='TRADING').returning(m.market_calendar.c.market_calendar_id)).scalar_one()
        from datetime import time
        c.execute(m.market_calendar_session.insert().values(market_calendar_id=cid,session_date=date(2026,8,28),session_status='OPEN',open_local_time=time(8),close_local_time=time(16,30)))
        c.execute(m.market_calendar_holiday.insert().values(market_calendar_id=cid,holiday_date=date(2026,8,28),holiday_name='Conflicting closure'))
    from tests.test_composite_policy_api import policy_payload
    policy=policy_payload(); policy['rules'][0]['marketCalendarId']=str(cid)
    response=call('POST','/v1/market-data/valuation-policies',policy)
    assert response.status_code==201,response.text
    result=call('POST','/v1/market-data/resolution-preview',dict(subjectReferenceNodeIds=[str(DEMO_IDS['hsbc_xlon_listing_node'])],
        valuationPolicyId=response.json()['valuationPolicyId'],valuationDate='2026-08-28',valuationCutId=str(DEMO_IDS['valuation_cut']),
        marketDataAsOfUtc='2099-01-01T22:00:00Z',usePurpose='VALUATION')).json()['items'][0]
    assert result['status']=='MISSING' and result['exceptionCode']=='CALENDAR_NOT_ASSESSED'

def test_snapshot_calendar_evidence_remains_pinned_after_reassignment():
    first=created(); decision=assign(first)
    data=dict(subjectReferenceNodeIds=[str(DEMO_IDS['hsbc_xlon_listing_node'])],valuationPolicyId=str(DEMO_IDS['valuation_policy']),
        valuationDate='2026-08-31',valuationCutId=str(DEMO_IDS['valuation_cut']),marketDataAsOfUtc='2099-01-01T22:00:00Z',
        usePurpose='VALUATION',strategyId=str(STRATEGY))
    response=call('POST','/v1/market-data-resolution-snapshots',data)
    assert response.status_code==201,response.text
    frozen=response.json()
    revised=payload(); revised['exceptions']=[]; assign(created(revised))
    replay=call('GET','/v1/market-data-resolution-snapshots/'+frozen['marketDataResolutionSnapshotId']).json()
    assert replay==frozen
    assert replay['items'][0]['pricingEvidence']['calendarDecisions'][0]['assignmentId']==decision['assignmentId']

def test_foreign_calendar_is_hidden_from_all_configuration_paths():
    tenant=uuid4()
    with get_engine().begin() as c:
        c.execute(m.tenant.insert().values(tenant_id=tenant,owning_organisation_id=DEMO_IDS['fortem_organisation'],tenant_code='CAL_'+uuid4().hex,display_name='Other calendar tenant',status='ACTIVE'))
        cid=c.execute(m.market_calendar.insert().values(calendar_code='FOREIGN_'+uuid4().hex,display_name='Foreign calendar',timezone_name='UTC',calendar_kind='VALUATION',tenant_id=tenant).returning(m.market_calendar.c.market_calendar_id)).scalar_one()
    assert call('GET',ROOT+'/'+str(cid)).status_code==404
    assert str(cid) not in [str(row['calendarId']) for row in call('GET',ROOT+'/options').json()['calendars']]
    assert str(cid) not in [str(row['id']) for row in call('GET','/v1/market-data/valuation-policy-options').json()['calendars']]
    data=payload();data.update(mode='ALL_OPEN',baseCalendarIds=[str(cid)])
    assert call('POST',ROOT,data).status_code==404

def test_assignment_replay_conflict_and_immutability():
    value=created(); key=str(uuid4())
    data=dict(calendarId=value['calendarId'],targetKind='STRATEGY',targetId=str(STRATEGY),validFrom='2026-08-28',validTo='2026-09-01',reason='Original')
    first=call('POST',ROOT+'/assignments',data,key)
    assert first.status_code==201,first.text
    assert call('POST',ROOT+'/assignments',data,key).json()==first.json()
    data['reason']='Changed'
    assert call('POST',ROOT+'/assignments',data,key).status_code==409
    with get_engine().begin() as c:
        with pytest.raises(DBAPIError),c.begin_nested():
            c.execute(m.calendar_assignment.delete().where(m.calendar_assignment.c.calendar_assignment_id==UUID(first.json()['assignmentId'])))

def test_calendar_inventory_does_not_duplicate_full_schedule_payloads():
    value=created()
    inventory=call('GET',ROOT+'/options').json()['calendars']
    assert next(row for row in inventory if row['calendarId']==value['calendarId'])['configuration'] is None
    assert call('GET',ROOT+'/'+value['calendarId']).json()['configuration']['exceptions'][0]['date']=='2026-08-31'

def test_closed_strategy_does_not_need_a_matching_price_rule():
    assign(created())
    result=resolve(subject=DEMO_IDS['gbpusd_fx_pair_node'],strategy=STRATEGY)
    assert result.status=='NOT_EXPECTED' and result.exception_code=='STRATEGY_VALUATION_CLOSED'
