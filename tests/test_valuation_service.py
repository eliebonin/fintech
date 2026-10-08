"""Real resolver and booking evidence; disposable database runner only."""
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal as D
from uuid import uuid4
import importlib
import pytest
from sqlalchemy import select
from apps.reference_api.db import get_engine
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids

def service():
    try: return importlib.import_module('valuation.service')
    except ModuleNotFoundError: pytest.fail('Frozen-input valuation orchestration is not implemented')

@pytest.fixture
def valued():
    engine=get_engine()
    assert engine.url.database.startswith('fortem_isolated_tests_')
    strategy=uuid4()
    # Earlier integration tests legitimately book other product families in the
    # demo strategy. Own a fresh population instead of weakening product guards.
    # Commit only this synthetic parent so independent attempt FK checks do not
    # wait for the financial fixture transaction. The owned database is disposable.
    with engine.begin() as setup:
        original=dict(setup.execute(select(m.strategy).where(m.strategy.c.strategy_id==ids['strategy'])).mappings().one())
        setup.execute(m.strategy.insert().values(**(original|dict(strategy_id=strategy,strategy_code='VAL_'+strategy.hex,
            display_name='Isolated valuation fixture',effective_from=date(2026,9,1),effective_to=None,status='ACTIVE'))))
    with engine.connect() as c:
        tx=c.begin()
        try:
            # Insert complete immutable booking evidence without holding the
            # booking workflow's FOR UPDATE lock throughout the test. That lock
            # would artificially block an independent operational attempt's FK.
            import json
            booked=uuid4()
            c.execute(m.trade.insert().values(trade_id=booked,trade_subject_reference_node_id=ids['hsbc_xlon_listing_node'],
                strategy_id=strategy,trade_type='INVESTMENT',quantity=D('10'),quantity_unit='UNITS',
                execution_price=D('1.23'),price_basis='UNIT_PRICE',price_currency_id=ids['gbp_currency'],
                trade_datetime_utc=datetime(2026,9,30,10,tzinfo=timezone.utc),booked_by_user_account_id=ids['demo_user_account'],
                created_by_user_account_id=ids['demo_user_account'],execution_channel='API'))
            definition=c.scalar(select(m.instrument_definition_version.c.instrument_definition_version_id).where(
                m.instrument_definition_version.c.instrument_node_id==ids['hsbc_instrument_node'],m.instrument_definition_version.c.is_current))
            c.execute(m.trade_lifecycle_event.insert().values(trade_id=booked,sequence_no=1,event_type='BOOKED',
                event_datetime_utc=datetime(2026,9,30,10,tzinfo=timezone.utc),recorded_by_user_account_id=ids['demo_user_account'],
                event_payload=json.dumps(dict(schemaVersion=1,kind='CASH_BOOKING',instrumentDefinitionId=str(definition),
                    instrumentId=str(ids['hsbc_instrument_node']),quoteFactor='100',unitMultiplier='1',priceCurrencyId=str(ids['gbp_currency'])))))
            calendar=uuid4()
            c.execute(m.market_calendar.insert().values(market_calendar_id=calendar,calendar_code='VAL_'+calendar.hex,
                display_name='Synthetic valuation fixture',timezone_name='Europe/London',calendar_kind='TRADING'))
            for day in [date(2026,9,29),date(2026,9,30),date(2026,10,1)]:
                c.execute(m.market_calendar_session.insert().values(market_calendar_id=calendar,session_date=day,
                    session_status='OPEN',open_local_time=time(8),close_local_time=time(16)))
            c.execute(m.market_calendar.update().where(m.market_calendar.c.market_calendar_id==calendar).values(sealed=True))
            c.execute(m.valuation_policy_rule.update().where(m.valuation_policy_rule.c.valuation_policy_rule_id==ids['valuation_policy_rule']).values(
                pricing_convention='SESSION_CLOSE',market_calendar_id=calendar,value_basis='RAW',max_staleness_business_days=0))
            source=dict(c.execute(select(m.market_data_observation).where(m.market_data_observation.c.market_data_observation_id==ids['market_data_observation'])).mappings().one())
            for day,price in [(date(2026,9,29),'1000'),(date(2026,10,1),'1100')]:
                c.execute(m.market_data_observation.insert().values(**(source | dict(market_data_observation_id=uuid4(),market_date=day,
                    value=D(price),market_data_vintage_id=None,received_at_utc=datetime.combine(day,time(16),timezone.utc),
                    observed_at_utc=datetime.combine(day,time(16),timezone.utc),source_published_at_utc=datetime.combine(day,time(16),timezone.utc),
                    source_observation_key='VAL_'+uuid4().hex))))
            request=service().ValuationRequest(tenant_id=ids['tenant'],strategy_id=strategy,policy_id=ids['valuation_policy'],
                cut_id=ids['valuation_cut'],reporting_currency_id=ids['gbp_currency'],
                opening_cutoff=datetime(2026,9,29,22,tzinfo=timezone.utc),closing_cutoff=datetime(2026,10,1,22,tzinfo=timezone.utc),
                information_cutoff=datetime.now(timezone.utc)+timedelta(minutes=1))
            yield c,request,booked
        finally:
            if tx.is_active: tx.rollback()

def test_frozen_input_execution_bridge_uses_booking_factors(valued):
    c,request,trade=valued
    result=service().calculate(c,request)
    assert result.period.market_pnl == D('109.877')
    assert result.period.closing_value == D('110')
    assert result.period.execution_value == D('0.123')
    assert result.period.lines[0].bucket.trade_ids == (trade,)
    assert len(result.resolution_snapshot_ids)==1
    assert result.scope=='MARKET_ONLY'
    assert result.external_comparison=='NOT_COMPARED'

def test_unsupported_product_snapshot_is_not_share_valued(valued):
    c,request,trade=valued
    import json
    row=dict(c.execute(select(m.trade).where(m.trade.c.trade_id==trade)).mappings().one())
    original=dict(c.execute(select(m.trade_lifecycle_event).where(m.trade_lifecycle_event.c.trade_id==trade)).mappings().one())
    identity=uuid4(); c.execute(m.trade.insert().values(**(row|dict(trade_id=identity))))
    c.execute(m.trade_lifecycle_event.insert().values(**(original|dict(trade_id=identity,
        trade_lifecycle_event_id=uuid4(),event_payload=json.dumps({'kind':'OPTION_BOOKING'})))))
    with pytest.raises(service().ValuationBlocked,match='unsupported booking'):
        service().calculate(c,request)

def test_reporting_currency_requires_real_frozen_fx_not_one(valued):
    from dataclasses import replace
    c,request,_=valued
    with pytest.raises(service().ValuationBlocked,match='currency'):
        service().calculate(c,replace(request,reporting_currency_id=ids['usd_currency']))

def test_missing_calendar_coverage_blocks_calculation(valued):
    c,request,_=valued
    # Published reference dates cannot be deleted. Missing observations still
    # exercise the safe missing-input path without modifying sealed evidence.
    c.execute(m.market_data_observation.delete().where(m.market_data_observation.c.market_date==date(2026,10,1)))
    with pytest.raises(service().ValuationBlocked): service().calculate(c,request)

def test_ambiguous_adjustment_basis_and_missing_input_block(valued):
    c,request,_=valued
    c.execute(m.valuation_policy_rule.update().where(m.valuation_policy_rule.c.valuation_policy_rule_id==ids['valuation_policy_rule']).values(value_basis=None))
    with pytest.raises(service().ValuationBlocked,match='basis'): service().calculate(c,request)

def test_cross_tenant_strategy_is_opaque_and_rejected(valued):
    from dataclasses import replace
    c,request,_=valued
    with pytest.raises((PermissionError,ValueError)):
        service().calculate(c,replace(request,tenant_id=ids['second_tenant']))

def test_known_stock_split_blocks_unadjusted_holding_bridge(valued):
    c,request,_=valued
    action=uuid4()
    c.execute(m.corporate_action.insert().values(corporate_action_id=action,affected_instrument_node_id=ids['hsbc_instrument_node'],
        event_type='STOCK_SPLIT',status='CONFIRMED'))
    c.execute(m.corporate_action_date.insert().values(corporate_action_id=action,date_role='EFFECTIVE',date_value=date(2026,10,1)))
    with pytest.raises(service().ValuationBlocked,match='Corporate action'):
        service().calculate(c,request)


def test_session_close_after_economic_cutoff_is_not_used(valued):
    from dataclasses import replace
    c,request,_=valued
    with pytest.raises(service().ValuationBlocked,match='economic cutoff'):
        service().calculate(c,replace(request,closing_cutoff=datetime(2026,10,1,12,tzinfo=timezone.utc)))


def test_historical_population_above_1000_is_loaded_without_truncation(valued):
    c,request,trade=valued
    original=dict(c.execute(select(m.trade).where(m.trade.c.trade_id==trade)).mappings().one())
    event=dict(c.execute(select(m.trade_lifecycle_event).where(m.trade_lifecycle_event.c.trade_id==trade)).mappings().one())
    additional=[uuid4() for _ in range(1001)]
    c.execute(m.trade.insert(),[original|dict(trade_id=identity) for identity in additional])
    c.execute(m.trade_lifecycle_event.insert(),[
        event|dict(trade_lifecycle_event_id=uuid4(),trade_id=identity) for identity in additional])
    from sqlalchemy import event as sql_event
    statements=[]
    def count_sql(connection,cursor,statement,parameters,context,executemany):
        if statement.lstrip().upper().startswith('SELECT'): statements.append(statement)
    sql_event.listen(c,'before_cursor_execute',count_sql)
    try:
        from positions.repository import iter_ledger_facts
        from positions.reconstruction import reconstruct
        from positions.contracts import ProjectionRequest
        projected=ProjectionRequest(request.tenant_id,request.strategy_id,request.closing_cutoff,
            request.information_cutoff,request.opening_cutoff,'PERIOD')
        events=list(iter_ledger_facts(c,projected))
    finally:
        sql_event.remove(c,'before_cursor_execute',count_sql)
    population=reconstruct(events,projected)
    assert len(population.executions)==1002
    assert {effect.booking.trade_id for effect in population.executions}=={trade,*additional}
    assert population.buckets[0].closing_quantity==D('10020')
    assert len(statements)<=12, 'Lifecycle/convention reads grow by bounded chunks, not by trade'


def test_split_before_opening_blocks_carried_unadjusted_booking(valued):
    from dataclasses import replace
    c,request,trade=valued
    action=uuid4()
    # The existing execution is Sept 30; opening/closing are Oct 1.
    # Use timestamp precision to distinguish execution -> split -> opening.
    opening=datetime(2026,10,1,17,tzinfo=timezone.utc)
    request=replace(request,opening_cutoff=opening)
    c.execute(m.corporate_action.insert().values(corporate_action_id=action,
        affected_instrument_node_id=ids['hsbc_instrument_node'],event_type='STOCK_SPLIT',status='CONFIRMED'))
    c.execute(m.corporate_action_date.insert().values(corporate_action_id=action,date_role='EFFECTIVE',
        timestamp_value_utc=datetime(2026,9,30,15,tzinfo=timezone.utc)))
    with pytest.raises(service().ValuationBlocked,match='Corporate action') as blocked:
        service().calculate(c,request)
    assert str(action) in str(blocked.value)
    assert str(trade) in str(blocked.value)
    assert str(ids['hsbc_instrument_node']) in str(blocked.value)


@pytest.mark.parametrize('scenario,blocked',[
    ('before_execution',False),
    ('after_close',False),
    ('cancelled',False),
    ('unknown_at_cutoff',False),
    ('unrelated_instrument',False),
    ('same_day_without_time',True),
    ('missing_effective_date',True),
])
def test_action_guard_respects_holding_and_information_cutoffs(valued,scenario,blocked):
    c,request,trade=valued
    original=dict(c.execute(select(m.trade).where(m.trade.c.trade_id==trade)).mappings().one())
    action=uuid4()
    values=dict(corporate_action_id=action,affected_instrument_node_id=ids['demo_share_class_instrument_node']
        if scenario=='unrelated_instrument' else ids['hsbc_instrument_node'],
        event_type='STOCK_SPLIT',status='CANCELLED' if scenario=='cancelled' else 'CONFIRMED')
    if scenario=='unknown_at_cutoff': values['recorded_at_utc']=request.information_cutoff+timedelta(minutes=1)
    c.execute(m.corporate_action.insert().values(**values))
    if scenario!='missing_effective_date':
        date_values=dict(corporate_action_id=action,date_role='EFFECTIVE')
        if scenario=='same_day_without_time': date_values['date_value']=date(2026,9,30)
        else:
            date_values['timestamp_value_utc']=(datetime(2026,9,30,9,tzinfo=timezone.utc) if scenario=='before_execution'
                else request.closing_cutoff+timedelta(hours=1) if scenario=='after_close'
                else datetime(2026,9,30,15,tzinfo=timezone.utc))
        c.execute(m.corporate_action_date.insert().values(**date_values))
    if blocked:
        with pytest.raises(service().ValuationBlocked,match='Corporate action'): service().calculate(c,request)
    else:
        assert service().calculate(c,request).period.market_pnl==D('109.877')
    assert dict(c.execute(select(m.trade).where(m.trade.c.trade_id==trade)).mappings().one())==original
