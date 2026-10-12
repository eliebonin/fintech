"""New conventions exercise real resolver/SQL without modifying operating data."""
from dataclasses import replace
from datetime import date,datetime,time,timedelta,timezone
from uuid import uuid4
import pytest
from sqlalchemy import select
from apps.reference_api.db import get_engine
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS
from security_master_schema.market_data_resolver import ResolutionRequest,resolve_market_data,persist_resolution_snapshot


@pytest.fixture
def composite():
    with get_engine().connect() as c:
        tx=c.begin()
        try:
            calendar=uuid4()
            c.execute(m.market_calendar.insert().values(market_calendar_id=calendar,calendar_code='SYNTHETIC_COMPOSITE_'+calendar.hex,
                display_name='Synthetic test sessions',timezone_name='Europe/London',calendar_kind='TRADING',
                created_at_utc=datetime(2026,8,1,tzinfo=timezone.utc)))
            for offset in range(8):
                day=date(2026,8,24)+timedelta(days=offset)
                closed=day.weekday()>4
                c.execute(m.market_calendar_session.insert().values(market_calendar_id=calendar,session_date=day,
                    session_status='CLOSED' if closed else 'HALF_DAY' if day==date(2026,8,28) else 'OPEN',
                    open_local_time=None if closed else time(8),close_local_time=None if closed else time(13) if day==date(2026,8,28) else time(16),
                    created_at_utc=datetime(2026,8,1,tzinfo=timezone.utc)))
            venue=c.scalar(select(m.listing.c.market_venue_id).where(m.listing.c.listing_node_id==DEMO_IDS['hsbc_xlon_listing_node']))
            rule=m.valuation_policy_rule
            c.execute(rule.update().where(rule.c.valuation_policy_rule_id==DEMO_IDS['valuation_policy_rule']).values(
                pricing_convention='SESSION_CLOSE',market_venue_id=venue,market_calendar_id=calendar,value_basis=None))
            observation=m.market_data_observation
            c.execute(observation.update().where(observation.c.market_data_observation_id==DEMO_IDS['market_data_observation']).values(
                market_date=date(2026,8,28),received_at_utc=datetime(2026,8,28,14,tzinfo=timezone.utc),
                source_published_at_utc=datetime(2026,8,28,14,tzinfo=timezone.utc),market_data_vintage_id=None))
            request=ResolutionRequest(tenant_id=DEMO_IDS['tenant'],subject_reference_node_id=DEMO_IDS['hsbc_xlon_listing_node'],
                valuation_policy_id=DEMO_IDS['valuation_policy'],valuation_date=date(2026,8,28),valuation_cut_id=DEMO_IDS['valuation_cut'],
                market_data_as_of_utc=datetime(2026,8,31,18,tzinfo=timezone.utc),use_purpose='VALUATION')
            yield c,request,venue
        finally:
            tx.rollback()


def test_exchange_close_freezes_actual_early_close_not_global_cut(composite):
    c,request,_=composite
    result=resolve_market_data(c,request)
    assert result.status=='SELECTED'
    assert result.pricing_evidence['pricingTargetUtc']=='2026-08-28T12:00:00+00:00'
    snapshot=persist_resolution_snapshot(c,request,(result,))
    evidence=c.scalar(select(m.market_data_resolution_snapshot_item.c.pricing_evidence).where(
        m.market_data_resolution_snapshot_item.c.market_data_resolution_snapshot_id==snapshot))
    assert evidence['convention']=='SESSION_CLOSE' and evidence['calendarEvidence']['source']=='GOVERNED_SESSIONS'


def test_known_closed_day_uses_previous_session_without_stale_warning(composite):
    c,request,_=composite
    result=resolve_market_data(c,replace(request,valuation_date=date(2026,8,29)))
    assert result.status=='SELECTED' and result.pricing_date_requested==date(2026,8,28)
    assert result.staleness_business_days==0


def test_information_cut_before_session_close_cannot_use_early_claimed_close(composite):
    c,request,_=composite
    c.execute(m.market_data_observation.update().where(m.market_data_observation.c.market_data_observation_id==DEMO_IDS['market_data_observation']).values(
        received_at_utc=datetime(2026,8,28,10,tzinfo=timezone.utc),source_published_at_utc=datetime(2026,8,28,10,tzinfo=timezone.utc)))
    result=resolve_market_data(c,replace(request,market_data_as_of_utc=datetime(2026,8,28,11,tzinfo=timezone.utc)))
    assert result.status=='MISSING' and result.exception_code=='PRICING_TARGET_NOT_AVAILABLE'


def test_missing_specific_exchange_rule_does_not_fall_through_to_default(composite):
    c,request,venue=composite
    rule=m.valuation_policy_rule
    c.execute(rule.update().where(rule.c.valuation_policy_rule_id==DEMO_IDS['valuation_policy_rule']).values(
        market_data_series_id=None,subject_reference_node_id=None,instrument_type_id=None,market_venue_id=None,pricing_convention='LEGACY',rule_sequence=900))
    exact=c.execute(rule.insert().values(valuation_policy_id=DEMO_IDS['valuation_policy'],rule_sequence=800,
        market_venue_id=venue,series_type='NO_SUCH_CLOSE',selection_method='OFFICIAL').returning(rule.c.valuation_policy_rule_id)).scalar_one()
    result=resolve_market_data(c,request)
    assert result.status=='MISSING' and result.policy_rule_id==exact


def test_premature_reported_closing_mark_is_not_a_completed_close(composite):
    c,request,_=composite
    c.execute(m.market_data_observation.update().where(m.market_data_observation.c.market_data_observation_id==DEMO_IDS['market_data_observation']).values(
        received_at_utc=datetime(2026,8,28,10,tzinfo=timezone.utc),source_published_at_utc=datetime(2026,8,28,10,tzinfo=timezone.utc)))
    result=resolve_market_data(c,request)
    assert result.status=='MISSING'


def test_unknown_explicit_calendar_cannot_borrow_venue_calendar(composite):
    c,request,_=composite
    calendar=uuid4()
    c.execute(m.market_calendar.insert().values(market_calendar_id=calendar,calendar_code='UNKNOWN_'+calendar.hex,
        display_name='Not governed',timezone_name='Europe/London',calendar_kind='TRADING',created_at_utc=datetime(2026,8,1,tzinfo=timezone.utc)))
    c.execute(m.valuation_policy_rule.update().where(m.valuation_policy_rule.c.valuation_policy_rule_id==DEMO_IDS['valuation_policy_rule']).values(market_calendar_id=calendar))
    result=resolve_market_data(c,request)
    assert result.status=='MISSING' and result.exception_code=='CALENDAR_NOT_ASSESSED'


def test_named_fixing_requires_identity_cut_time_and_non_daily_timestamp(composite):
    from market_data.pricing_conventions import local_target
    c,request,_=composite
    cut=c.execute(select(m.valuation_cut).where(m.valuation_cut.c.valuation_cut_id==DEMO_IDS['valuation_cut'])).mappings().one()
    target=local_target(request.valuation_date,time.fromisoformat(cut['local_time']),cut['timezone_name'])
    c.execute(m.valuation_policy_rule.update().where(m.valuation_policy_rule.c.valuation_policy_rule_id==DEMO_IDS['valuation_policy_rule']).values(
        pricing_convention='NAMED_FIXING',pricing_cut_id=DEMO_IDS['valuation_cut'],fixing_code='SYNTHETIC_LONDON_FIX'))
    c.execute(m.market_data_series.update().where(m.market_data_series.c.market_data_series_id==DEMO_IDS['market_data_series']).values(valuation_cut_id=DEMO_IDS['valuation_cut']))
    c.execute(m.market_data_observation.update().where(m.market_data_observation.c.market_data_observation_id==DEMO_IDS['market_data_observation']).values(
        observed_at_utc=target,received_at_utc=target+timedelta(minutes=2),source_published_at_utc=target))
    assert resolve_market_data(c,request).status=='MISSING'
    c.execute(m.market_data_series_dimension.insert().values(market_data_series_id=DEMO_IDS['market_data_series'],dimension_code='FIXING_CODE',dimension_value='SYNTHETIC_LONDON_FIX'))
    assert resolve_market_data(c,request).status=='SELECTED'
    c.execute(m.market_data_observation.update().where(m.market_data_observation.c.market_data_observation_id==DEMO_IDS['market_data_observation']).values(valuation_cut_id=DEMO_IDS['uk_fx_cut']))
    assert resolve_market_data(c,request).status=='MISSING'
    c.execute(m.market_data_observation.update().where(m.market_data_observation.c.market_data_observation_id==DEMO_IDS['market_data_observation']).values(valuation_cut_id=None))
    c.execute(m.market_data_series_dimension.insert().values(market_data_series_id=DEMO_IDS['market_data_series'],dimension_code='TIMESTAMP_SEMANTICS',dimension_value='SOURCE_DAILY_BAR'))
    assert resolve_market_data(c,request).status=='MISSING'


def test_basis_mismatch_is_missing_not_permission_denial(composite):
    c,request,_=composite
    c.execute(m.valuation_policy_rule.update().where(m.valuation_policy_rule.c.valuation_policy_rule_id==DEMO_IDS['valuation_policy_rule']).values(value_basis='NONEXISTENT_BASIS'))
    result=resolve_market_data(c,request)
    assert result.status=='MISSING' and result.entitlement_decision=='ALLOWED'


@pytest.mark.parametrize('mode', ['STRICT', 'FLEXIBLE'])
def test_mixed_us_uk_paris_closes_and_separate_london_fixing(composite, mode):
    from security_master_schema.market_data_resolver import resolve_market_data_batch
    c,request,_=composite
    policy=c.execute(m.valuation_policy.insert().values(tenant_id=request.tenant_id,policy_code='MIXED_'+uuid4().hex,
        display_name='Synthetic mixed market',valuation_cut_id=request.valuation_cut_id,selection_mode=mode,status='ACTIVE',valid_from=date(2026,8,1)).returning(m.valuation_policy.c.valuation_policy_id)).scalar_one()
    original_listing=dict(c.execute(select(m.listing).where(m.listing.c.listing_node_id==request.subject_reference_node_id)).mappings().one())
    original_node=dict(c.execute(select(m.financial_reference_node).where(m.financial_reference_node.c.reference_node_id==request.subject_reference_node_id)).mappings().one())
    subjects=[]
    for seq,(zone,close,convention) in enumerate([('Europe/London',time(16,30),'SESSION_CLOSE'),
            ('America/New_York',time(16),'SESSION_CLOSE'),('Europe/Paris',time(17,30),'SESSION_CLOSE'),
            ('Europe/London',time(16),'NAMED_FIXING')],1):
        calendar=uuid4()
        c.execute(m.market_calendar.insert().values(market_calendar_id=calendar,calendar_code='MIXED_'+calendar.hex,
            display_name='Synthetic calendar',timezone_name=zone,calendar_kind='FIXING' if seq==4 else 'TRADING',created_at_utc=datetime(2026,8,1,tzinfo=timezone.utc)))
        c.execute(m.market_calendar_session.insert().values(market_calendar_id=calendar,session_date=request.valuation_date,
            session_status='OPEN',open_local_time=time(8),close_local_time=close,created_at_utc=datetime(2026,8,1,tzinfo=timezone.utc)))
        if seq==4:
            subject=DEMO_IDS['gbpusd_fx_pair_node']; venue=None
            cut=c.execute(m.valuation_cut.insert().values(cut_code='SYNTHETIC_FIX_'+calendar.hex,display_name='Synthetic London fixing',
                timezone_name=zone,local_time='16:00:00',market_calendar_id=calendar).returning(m.valuation_cut.c.valuation_cut_id)).scalar_one()
        else:
            subject=uuid4(); venue=uuid4();cut=None
            c.execute(m.market_venue.insert().values(market_venue_id=venue,venue_type='EXCHANGE',display_name='Synthetic '+zone,
                timezone_name=zone,market_calendar_id=calendar))
            c.execute(m.financial_reference_node.insert().values(**{**original_node,'reference_node_id':subject,'internal_code':None}))
            c.execute(m.listing.insert().values(**{**original_listing,'listing_node_id':subject,'market_venue_id':venue,'is_primary_listing':False}))
        series=c.execute(m.market_data_series.insert().values(reference_node_id=subject,series_type='SYNTHETIC_FIX' if seq==4 else 'SYNTHETIC_CLOSE',
            value_type='RATE' if seq==4 else 'PRICE',default_dataset_id=DEMO_IDS['dataset'],valuation_cut_id=cut,source_system_id='SYNTHETIC').returning(m.market_data_series.c.market_data_series_id)).scalar_one()
        if seq==4:
            c.execute(m.market_data_series_dimension.insert().values(market_data_series_id=series,dimension_code='FIXING_CODE',dimension_value='TEST_LONDON_4PM'))
        from market_data.pricing_conventions import local_target
        target=local_target(request.valuation_date,close,zone)
        c.execute(m.market_data_observation.insert().values(market_data_series_id=series,dataset_id=DEMO_IDS['dataset'],
            market_date=request.valuation_date,observed_at_utc=target if seq==4 else datetime(2026,8,28,8,tzinfo=timezone.utc),
            received_at_utc=target+timedelta(minutes=1),source_published_at_utc=target,value='1.250000000001' if seq==4 else '100.123456789012',quality_status='ACCEPTED'))
        if mode == 'STRICT' or seq == 4:
            c.execute(m.valuation_policy_rule.insert().values(valuation_policy_id=policy,rule_sequence=seq,
                subject_reference_node_id=subject if seq==4 else None,market_venue_id=venue,pricing_convention=convention,
                market_calendar_id=calendar,pricing_cut_id=cut,fixing_code='TEST_LONDON_4PM' if seq==4 else None,
                series_type='SYNTHETIC_FIX' if seq==4 else 'SYNTHETIC_CLOSE',selection_method='OFFICIAL',max_staleness_business_days=0))
        subjects.append(subject)
    if mode == 'FLEXIBLE':
        c.execute(m.valuation_policy_rule.insert().values(valuation_policy_id=policy,rule_sequence=10,
            subject_type='LISTING',is_default=True,pricing_convention='SESSION_CLOSE',series_type='SYNTHETIC_CLOSE',
            selection_method='OFFICIAL',max_staleness_business_days=0))
    coherent=replace(request,valuation_policy_id=policy,market_data_as_of_utc=datetime(2026,8,28,22,tzinfo=timezone.utc))
    results=resolve_market_data_batch(c,coherent,tuple(subjects))
    assert [r.status for r in results]==['SELECTED']*4
    assert [r.pricing_evidence['pricingTargetUtc'] for r in results]==[
        '2026-08-28T15:30:00+00:00','2026-08-28T20:00:00+00:00','2026-08-28T15:30:00+00:00','2026-08-28T15:00:00+00:00']
    assert str(results[0].selected_value)=='100.123456789012'
    assert [r.pricing_evidence['ruleOrigin'] for r in results] == (['DEFAULT']*3+['EXPLICIT'] if mode == 'FLEXIBLE' else ['EXPLICIT']*4)
    if mode == 'FLEXIBLE':
        assert len({r.policy_rule_id for r in results[:3]}) == 1
    before_us_close=resolve_market_data_batch(c,replace(coherent,market_data_as_of_utc=datetime(2026,8,28,16,tzinfo=timezone.utc)),tuple(subjects))
    assert [r.status for r in before_us_close]==['SELECTED','MISSING','SELECTED','SELECTED']
