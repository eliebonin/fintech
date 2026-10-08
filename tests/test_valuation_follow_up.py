"""Focused regressions for the reviewed valuation safety gaps."""
from dataclasses import replace
from datetime import date, datetime, time, timedelta, timezone
from uuid import uuid4
from decimal import Decimal
import pytest
from sqlalchemy import select, text
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from tests.test_composite_policy_resolution import composite
from tests.test_valuation_service import valued, service


def test_yahoo_daily_bar_cannot_satisfy_intraday_policy(composite):
    c, request, _ = composite
    c.execute(m.valuation_policy_rule.update().where(
        m.valuation_policy_rule.c.valuation_policy_rule_id == ids['valuation_policy_rule']).values(
            pricing_convention='EXPLICIT_TIME', pricing_cut_id=ids['valuation_cut']))
    c.execute(m.market_data_observation.update().where(
        m.market_data_observation.c.market_data_observation_id == ids['market_data_observation']).values(
            observed_at_utc=datetime(2026,8,28,8,tzinfo=timezone.utc)))
    assert service().resolve_market_data(c,request).status=='SELECTED'
    c.execute(m.market_data_series_dimension.insert().values(
        market_data_series_id=ids['market_data_series'], dimension_code='TIMESTAMP_SEMANTICS',
        dimension_value='PROVIDER_DAILY_BAR_TIMESTAMP'))
    assert service().resolve_market_data(c, request).status == 'MISSING'


def test_new_execution_does_not_require_opening_price(valued):
    c, request, _ = valued
    c.execute(m.market_data_observation.delete().where(
        m.market_data_observation.c.market_data_series_id == ids['market_data_series'],
        m.market_data_observation.c.market_date == request.opening_cutoff.date()))
    result = service().calculate(c, request)
    assert result.period.market_pnl == Decimal('109.877')
    assert len(result.resolution_snapshot_ids) == 1
    assert len(result.evidence['selections']) == 1


def test_calendar_recorded_after_cutoff_is_unavailable(composite):
    c, request, _ = composite
    calendar = c.scalar(select(m.valuation_policy_rule.c.market_calendar_id).where(
        m.valuation_policy_rule.c.valuation_policy_rule_id == ids['valuation_policy_rule']))
    c.execute(m.market_calendar.update().where(m.market_calendar.c.market_calendar_id == calendar).values(
        created_at_utc=request.market_data_as_of_utc+timedelta(days=1)))
    result = service().resolve_market_data(c, request)
    assert result.exception_code == 'CALENDAR_VERSION_NOT_AVAILABLE_AT_CUTOFF'


def test_late_session_cannot_enter_historical_calendar(composite):
    c, request, _ = composite
    calendar = c.scalar(select(m.valuation_policy_rule.c.market_calendar_id).where(
        m.valuation_policy_rule.c.valuation_policy_rule_id == ids['valuation_policy_rule']))
    c.execute(m.market_calendar_session.update().where(m.market_calendar_session.c.market_calendar_id == calendar,
        m.market_calendar_session.c.session_date == request.valuation_date).values(
            created_at_utc=request.market_data_as_of_utc+timedelta(days=1)))
    assert service().resolve_market_data(c, request).status == 'MISSING'


def test_valuation_rejects_mutable_reference_calendar(valued):
    c, request, _ = valued
    calendar = uuid4()
    c.execute(m.market_calendar.insert().values(market_calendar_id=calendar, calendar_code='UNSEALED_'+calendar.hex,
        display_name='Mutable fixture',timezone_name='Europe/London',calendar_kind='TRADING'))
    c.execute(m.market_calendar_session.insert().values(market_calendar_id=calendar,session_date=request.closing_cutoff.date(),
        session_status='OPEN',open_local_time=time(8),close_local_time=time(16)))
    c.execute(m.valuation_policy_rule.update().where(m.valuation_policy_rule.c.valuation_policy_rule_id==ids['valuation_policy_rule']).values(market_calendar_id=calendar))
    with pytest.raises(service().ValuationBlocked, match='sealed'):
        service().calculate(c, request)


def test_published_reference_copy_is_immutable_and_not_backdated(composite):
    from market_data.calendar_store import publish_reference_calendar
    c, request, _ = composite
    source = c.scalar(select(m.valuation_policy_rule.c.market_calendar_id).where(
        m.valuation_policy_rule.c.valuation_policy_rule_id == ids['valuation_policy_rule']))
    published = publish_reference_calendar(c, source, ids['platform_admin_user_account'], 'Synthetic publication')
    row = c.execute(select(m.market_calendar).where(m.market_calendar.c.market_calendar_id == published)).mappings().one()
    assert row['sealed'] and row['created_at_utc'] > request.market_data_as_of_utc
    with pytest.raises(Exception, match='immutable'):
        with c.begin_nested():
            c.execute(m.market_calendar_session.update().where(m.market_calendar_session.c.market_calendar_id == published).values(close_local_time=time(12)))


def test_retained_evidence_checks_current_entitlement_before_display(valued):
    from valuation import storage
    from valuation.evidence_access import assert_batch_display
    c, request, _ = valued
    result = service().calculate(c, request)
    batch = {'items': [{'evidence': {'selections': result.evidence['selections']}}]}
    assert_batch_display(c, request.tenant_id, batch)
    c.execute(m.tenant_dataset_entitlement.update().where(
        m.tenant_dataset_entitlement.c.tenant_id == request.tenant_id,
        m.tenant_dataset_entitlement.c.dataset_id == ids['dataset']).values(status='SUSPENDED'))
    with pytest.raises(PermissionError):
        assert_batch_display(c, request.tenant_id, batch)


def test_non_display_permission_does_not_disclose_preview_prices(valued):
    from apps.reference_api import valuation_policies
    from apps.reference_api.contracts import MarketDataResolutionSnapshotCreate
    c,request,_=valued
    assignment=c.execute(select(m.dataset_licence_assignment.c.dataset_licence_assignment_id,
        m.data_licence.c.licensee_organisation_id).join(m.data_licence).where(
        m.dataset_licence_assignment.c.dataset_id==ids['dataset'])).mappings().first()
    c.execute(m.dataset_access_profile.insert().values(dataset_id=ids['dataset'],
        licensee_organisation_id=assignment['licensee_organisation_id'],permitted_tenant_id=ids['tenant'],
        usage_scope='PERSONAL',provider_enabled=True,activation_reference='Synthetic calculation only',status='ACTIVE'))
    c.execute(m.dataset_right_requirement.insert().values(dataset_id=ids['dataset'],activity='NON_DISPLAY',
        requirement_code='SYNTHETIC_CALCULATION',dataset_licence_assignment_id=assignment['dataset_licence_assignment_id']))
    c.execute(m.licence_activity_grant.insert().values(dataset_licence_assignment_id=assignment['dataset_licence_assignment_id'],
        activity='NON_DISPLAY',usage_scope='PERSONAL',evidence_basis='PERSONAL_DECLARATION',
        evidence_reference='Synthetic calculation right only',valid_from=date(2026,1,1),status='ACTIVE'))
    payload=MarketDataResolutionSnapshotCreate(subjectReferenceNodeIds=[str(ids['hsbc_xlon_listing_node'])],
        valuationPolicyId=str(request.policy_id),valuationDate=request.closing_cutoff.date(),
        valuationCutId=str(request.cut_id),marketDataAsOfUtc=request.information_cutoff,usePurpose='VALUATION')
    # Control: calculation remains authorised; disclosure is a separate right.
    selected=service().resolve_market_data(c,service().ResolutionRequest(request.tenant_id,
        ids['hsbc_xlon_listing_node'],request.policy_id,request.closing_cutoff.date(),request.cut_id,
        request.information_cutoff,'VALUATION'))
    assert selected.status=='SELECTED'
    with pytest.raises(PermissionError):
        valuation_policies.preview(c,request.tenant_id,ids['demo_user_account'],payload)


def test_runner_uses_consistent_input_snapshot():
    from valuation.runner import calculation_transaction
    from apps.reference_api.db import get_engine
    with calculation_transaction(get_engine()) as c:
        assert c.scalar(text('SHOW transaction_isolation')) == 'repeatable read'


def test_input_reads_do_not_mix_concurrent_database_versions():
    from valuation.runner import calculation_transaction
    from apps.reference_api.db import get_engine
    engine=get_engine()
    assert engine.url.database.startswith('fortem_isolated_tests_')
    actor=uuid4()
    with engine.begin() as c:
        c.execute(m.user_account.insert().values(user_account_id=actor,account_type='HUMAN',status='ACTIVE'))
    with calculation_transaction(engine) as c:
        statement=select(m.user_account.c.status).where(m.user_account.c.user_account_id==actor)
        assert c.scalar(statement)=='ACTIVE'
        with engine.begin() as concurrent:
            concurrent.execute(m.user_account.update().where(m.user_account.c.user_account_id==actor).values(status='SUSPENDED'))
        assert c.scalar(statement)=='ACTIVE'
    with engine.connect() as fresh:
        assert fresh.scalar(statement)=='SUSPENDED'


def test_late_holiday_does_not_change_known_open_day(composite):
    c,request,_=composite
    calendar=c.scalar(select(m.valuation_policy_rule.c.market_calendar_id).where(
        m.valuation_policy_rule.c.valuation_policy_rule_id==ids['valuation_policy_rule']))
    c.execute(m.market_calendar_holiday.insert().values(market_calendar_id=calendar,
        holiday_date=request.valuation_date,holiday_name='Late announcement',
        created_at_utc=request.market_data_as_of_utc+timedelta(days=1)))
    assert service().resolve_market_data(c,request).status=='SELECTED'


def test_existing_holding_still_requires_opening_price(valued):
    c,request,_=valued
    request=replace(request,opening_cutoff=datetime(2026,9,30,22,tzinfo=timezone.utc))
    with pytest.raises(service().ValuationBlocked,match='Input selection blocked'):
        service().calculate(c,request)


def test_reference_publication_denied_to_tenant_admin(composite):
    from market_data.calendar_store import publish_reference_calendar
    c,_,_=composite
    source=c.scalar(select(m.valuation_policy_rule.c.market_calendar_id).where(
        m.valuation_policy_rule.c.valuation_policy_rule_id==ids['valuation_policy_rule']))
    with pytest.raises(PermissionError):
        publish_reference_calendar(c,source,ids['demo_user_account'],'Tenant cannot publish shared references')


def test_stale_recovery_does_not_interrupt_locked_attempt(valued):
    from valuation import storage, tables as t
    from valuation.runner import recover_attempt
    from apps.reference_api.db import get_engine
    c, request, _ = valued
    engine = get_engine()
    attempt = storage.begin_attempt(engine, request, ids['demo_user_account'], str(uuid4()))
    with engine.begin() as setup:
        setup.execute(t.attempt.update().where(t.attempt.c.attempt_id == attempt).values(
            started_at=datetime.now(timezone.utc)-timedelta(hours=1)))
    c.execute(text('SELECT pg_advisory_xact_lock(:lock)').bindparams(lock=int.from_bytes(attempt.bytes[:8],'big',signed=True)))
    with pytest.raises(ValueError, match='active'):
        recover_attempt(engine,request.tenant_id,attempt,ids['demo_user_account'],'Worker stopped and checked',confirmed_worker_stopped=True)


def test_failing_duplicate_cannot_mark_active_worker_failed(valued):
    from valuation import storage,tables as t
    from apps.reference_api.db import get_engine
    c,request,_=valued
    engine=get_engine()
    attempt=storage.begin_attempt(engine,request,ids['demo_user_account'],str(uuid4()))
    c.execute(text('SELECT pg_advisory_xact_lock(:lock)').bindparams(lock=int.from_bytes(attempt.bytes[:8],'big',signed=True)))
    storage.fail_attempt(engine,request.tenant_id,attempt,'CALCULATION_FAILED')
    with engine.connect() as fresh:
        assert fresh.scalar(select(t.attempt.c.status).where(t.attempt.c.attempt_id==attempt))=='RUNNING'


def test_stale_recovery_records_failure_and_reason(valued):
    from valuation import storage, tables as t
    from valuation.runner import recover_attempt
    from apps.reference_api.db import get_engine
    _, request, _ = valued
    engine = get_engine()
    attempt = storage.begin_attempt(engine, request, ids['demo_user_account'], str(uuid4()))
    with pytest.raises(ValueError, match='stale'):
        recover_attempt(engine,request.tenant_id,attempt,ids['demo_user_account'],'Worker stopped and checked',confirmed_worker_stopped=True)
    with engine.begin() as c:
        c.execute(t.attempt.update().where(t.attempt.c.attempt_id == attempt).values(
            started_at=datetime.now(timezone.utc)-timedelta(hours=1)))
    recover_attempt(engine,request.tenant_id,attempt,ids['demo_user_account'],'Worker stopped and checked',confirmed_worker_stopped=True)
    with engine.connect() as c:
        assert c.scalar(select(t.attempt.c.status).where(t.attempt.c.attempt_id==attempt))=='FAILED'
        event=c.execute(select(t.run_event).where(t.run_event.c.attempt_id==attempt,t.run_event.c.event_code=='FAILED')).mappings().one()
        assert event['details']['actorId']==str(ids['demo_user_account'])
        assert event['details']['reason']=='Worker stopped and checked'
