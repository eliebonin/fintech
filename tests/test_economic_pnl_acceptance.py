"""Synthetic disposable acceptance; no operating financial publications."""
from datetime import date,timedelta
from decimal import Decimal as D
from uuid import uuid4
import json
import pytest
from sqlalchemy import select
from tests.test_valuation_service import valued,service
from tests.test_position_attribution_storage import staged,reviewer
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from valuation import storage


def add_bond(c,r,trade):
    original=dict(c.execute(select(m.trade).where(m.trade.c.trade_id==trade)).mappings().one())
    listing=uuid4();node=dict(c.execute(select(m.financial_reference_node).where(m.financial_reference_node.c.reference_node_id==ids['hsbc_xlon_listing_node'])).mappings().one())
    c.execute(m.financial_reference_node.insert().values(**(node|dict(reference_node_id=listing,canonical_name='Synthetic bond listing',internal_code='BOND_'+listing.hex))))
    listing_row=dict(c.execute(select(m.listing).where(m.listing.c.listing_node_id==ids['hsbc_xlon_listing_node'])).mappings().one())
    c.execute(m.listing.insert().values(**(listing_row|dict(listing_node_id=listing,instrument_node_id=ids['bond_instrument_node'],trading_symbol='BOND_'+listing.hex))))
    definition=c.scalar(select(m.instrument_definition_version.c.instrument_definition_version_id).where(m.instrument_definition_version.c.instrument_node_id==ids['bond_instrument_node'],m.instrument_definition_version.c.is_current))
    identity=uuid4()
    c.execute(m.trade.insert().values(**(original|dict(trade_id=identity,trade_subject_reference_node_id=listing,reference_instrument_node_id=ids['bond_instrument_node'],
        quantity=D('100000'),quantity_unit='NOMINAL',execution_price=D('99.75'),price_basis='PCT_OF_PAR'))))
    conventions=dict(instrumentDefinitionId=str(definition),instrumentId=str(ids['bond_instrument_node']),priceCurrencyId=str(ids['gbp_currency']),
        unitMultiplier='1',quoteFactor='100',productBasis='BOND',cleanExecutionAmount='98500',maturityDate='2030-01-01')
    details=dict(priceType='DIRTY',cleanAmount='98500',dirtyAmount='99750',accruedInterestAmount='1250',settlementEvidence='SYNTHETIC')
    snapshot=dict(schemaVersion=1,kind='PRODUCT_BOOKING',economics=dict(terms=dict(kind='BOND'),bondDetails=details),valuationConventions=conventions)
    c.execute(m.trade_lifecycle_event.insert().values(trade_id=identity,sequence_no=1,event_type='BOOKED',event_datetime_utc=original['trade_datetime_utc'],
        recorded_by_user_account_id=ids['demo_user_account'],event_payload=json.dumps(snapshot)))
    series=uuid4();source=dict(c.execute(select(m.market_data_series).where(m.market_data_series.c.market_data_series_id==ids['market_data_series'])).mappings().one())
    c.execute(m.market_data_series.insert().values(**(source|dict(market_data_series_id=series,reference_node_id=listing))))
    c.execute(m.market_data_series_dimension.insert().values(market_data_series_id=series,dimension_code='BOND_PRICE_TYPE',dimension_value='CLEAN'))
    rule=dict(c.execute(select(m.valuation_policy_rule).where(m.valuation_policy_rule.c.valuation_policy_rule_id==ids['valuation_policy_rule'])).mappings().one())
    c.execute(m.valuation_policy_rule.insert().values(**(rule|dict(valuation_policy_rule_id=uuid4(),rule_sequence=90,subject_reference_node_id=listing,market_data_series_id=series))))
    observation=dict(c.execute(select(m.market_data_observation).where(m.market_data_observation.c.market_data_observation_id==ids['market_data_observation'])).mappings().one())
    stamp=r.closing_cutoff.replace(hour=16,minute=0,second=0,microsecond=0)
    c.execute(m.market_data_observation.insert().values(**(observation|dict(market_data_observation_id=uuid4(),market_data_series_id=series,market_date=stamp.date(),
        value=D('101'),market_data_vintage_id=None,received_at_utc=stamp,observed_at_utc=stamp,source_published_at_utc=stamp,source_observation_key='BOND_'+uuid4().hex))))
    return identity


def test_dirty_execution_clean_mark_coupon_daily_accrual_stage_publish(valued):
    from valuation.accruals import accrual_amounts,record_accrual
    c,r,trade=valued
    from apps.reference_api.db import get_engine
    # Operational attempt precedes booking's strategy lock, as it does in the
    # app after the independently committed booking transaction.
    attempt=storage.begin_attempt(get_engine(),r,ids['demo_user_account'],str(uuid4()))
    add_bond(c,r,trade)
    with pytest.raises(ValueError,match='Missing assessed daily'): service().calculate(c,r)
    inputs=dict(openingBalance=D('990'),dailyEarned=D('10'),closingBalance=D('0'),balanceMovements=D('-1000'),openingFx=D('1'),closingFx=D('1'))
    payload=dict(strategyId=r.strategy_id,instrumentId=ids['bond_instrument_node'],valueDate=date(2026,9,30),inputType='DAILY_INTEREST',
        currencyId=ids['gbp_currency'],reportingCurrencyId=ids['gbp_currency'],eligibleNominal=D('100000'),sourceReference='SYNTHETIC',
        eligibilityConvention='OPS_ASSESSED_NOMINAL',inputs=inputs,amounts=accrual_amounts(inputs),fxEvidence=[],supersedesInputId=None)
    record_accrual(c,r.tenant_id,ids['demo_user_account'],payload,str(uuid4()))
    record_accrual(c,r.tenant_id,ids['demo_user_account'],payload|dict(valueDate=date(2026,10,1)),str(uuid4()))
    from valuation.flows import book_flow
    book_flow(c,r.tenant_id,ids['demo_user_account'],dict(strategyId=r.strategy_id,instrumentId=ids['hsbc_instrument_node'],currencyId=ids['gbp_currency'],
        amount=D('100'),component='DIVIDEND',recognitionRole='INCOME',economicDate=date(2026,10,1),paymentDate=None,sourceReference='SYNTHETIC DIVIDEND'),str(uuid4()))
    result=service().calculate(c,r)
    assert result.period.market_pnl==D('2609.877')
    assert result.gross_pnl==D('2729.877')
    batch=storage.stage(c,attempt,ids['demo_user_account'],result)
    storage.publish(c,r.tenant_id,batch,reviewer(c),'Synthetic economics and coverage reviewed')
    assert storage.batch_view(c,r.tenant_id,batch)['summary']['grossPnl']=='2729.877'


def test_fund_nav_lag_uses_closed_fund_day_and_publication_cutoff(valued):
    from datetime import datetime,time,timezone
    c,r,trade=valued
    calendar=uuid4()
    c.execute(m.market_calendar.insert().values(market_calendar_id=calendar,calendar_code='NAV_'+calendar.hex,display_name='Synthetic NAV calendar',
        timezone_name='Europe/Dublin',calendar_kind='VALUATION'))
    for day in [date(2026,9,28),date(2026,9,29),date(2026,9,30),date(2026,10,1)]:
        c.execute(m.market_calendar_session.insert().values(market_calendar_id=calendar,session_date=day,session_status='CLOSED' if day==date(2026,9,30) else 'OPEN',
            open_local_time=None if day==date(2026,9,30) else time(8),
            close_local_time=None if day==date(2026,9,30) else time(16)))
    c.execute(m.market_calendar.update().where(m.market_calendar.c.market_calendar_id==calendar).values(sealed=True))
    c.execute(m.valuation_policy_rule.update().where(m.valuation_policy_rule.c.valuation_policy_rule_id==ids['demo_fund_nav_policy_rule']).values(
        market_calendar_id=calendar,pricing_convention='NAV_DATE',value_basis='RAW',pricing_date_rule='FIXED_LAG',lag_business_days=1,max_staleness_business_days=0))
    measure=c.scalar(select(m.series_measure_definition.c.series_measure_definition_id).where(m.series_measure_definition.c.measure_code=='PRICE'))
    c.execute(m.market_data_series.update().where(m.market_data_series.c.market_data_series_id==ids['demo_fund_nav_series']).values(measure_definition_id=measure))
    source=dict(c.execute(select(m.market_data_observation).where(m.market_data_observation.c.market_data_observation_id==ids['market_data_observation'])).mappings().one())
    for day,price in [(date(2026,9,28),'99'),(date(2026,9,29),'100')]:
        published=datetime.combine(day+timedelta(days=1),time(16),timezone.utc)
        c.execute(m.market_data_observation.insert().values(**(source|dict(market_data_observation_id=uuid4(),market_data_series_id=ids['demo_fund_nav_series'],
            market_data_vintage_id=None,market_date=day,value=D(price),received_at_utc=published,source_published_at_utc=published,observed_at_utc=published,
            source_observation_key='NAV_'+uuid4().hex))))
    rr,selected=service()._selection(c,r,ids['demo_share_class_instrument_node'],r.closing_cutoff,'FUND')
    assert selected.pricing_date_used==date(2026,9,29)
    assert selected.selected_value==D('100')
    late=r.information_cutoff+timedelta(seconds=1)
    c.execute(m.market_data_observation.insert().values(**(source|dict(market_data_observation_id=uuid4(),market_data_series_id=ids['demo_fund_nav_series'],
        market_data_vintage_id=None,market_date=date(2026,9,29),value=D('999'),received_at_utc=late,source_published_at_utc=late,observed_at_utc=late,
        source_observation_key='NAV_LATE_'+uuid4().hex))))
    assert service()._selection(c,r,ids['demo_share_class_instrument_node'],r.closing_cutoff,'FUND')[1].selected_value==D('100')
    c.execute(m.valuation_policy_rule.update().where(m.valuation_policy_rule.c.valuation_policy_rule_id==ids['demo_fund_nav_policy_rule']).values(lag_business_days=2))
    assert service()._selection(c,r,ids['demo_share_class_instrument_node'],r.closing_cutoff,'FUND')[1].pricing_date_used==date(2026,9,28)
    # A traded listing remains the position owner, but its NAV belongs to the
    # canonical share class. Never fabricate a duplicate listing NAV stream.
    listing=uuid4();parent=ids['demo_share_class_instrument_node']
    node=dict(c.execute(select(m.financial_reference_node).where(m.financial_reference_node.c.reference_node_id==ids['hsbc_xlon_listing_node'])).mappings().one())
    c.execute(m.financial_reference_node.insert().values(**(node|dict(reference_node_id=listing,canonical_name='Synthetic fund listing',internal_code='NAV_LIST_'+listing.hex))))
    definition=dict(c.execute(select(m.instrument_definition_version).where(m.instrument_definition_version.c.instrument_node_id==ids['hsbc_instrument_node'],m.instrument_definition_version.c.is_current)).mappings().one())
    fund=c.execute(select(m.instrument).where(m.instrument.c.instrument_node_id==parent)).mappings().one()
    definition_id=c.scalar(select(m.instrument_definition_version.c.instrument_definition_version_id).where(m.instrument_definition_version.c.instrument_node_id==parent,m.instrument_definition_version.c.is_current))
    if not definition_id:
        definition_id=uuid4()
        c.execute(m.instrument_definition_version.insert().values(**(definition|dict(instrument_definition_version_id=definition_id,instrument_node_id=parent,instrument_type_id=fund['instrument_type_id']))))
    values=dict(c.execute(select(m.listing).where(m.listing.c.listing_node_id==ids['hsbc_xlon_listing_node'])).mappings().one())
    c.execute(m.listing.insert().values(**(values|dict(listing_node_id=listing,instrument_node_id=parent,trading_symbol='NAV_'+listing.hex,quote_factor=1))))
    original=dict(c.execute(select(m.trade).where(m.trade.c.trade_id==trade)).mappings().one())
    identity=uuid4();c.execute(m.trade.insert().values(**(original|dict(trade_id=identity,trade_subject_reference_node_id=listing,reference_instrument_node_id=parent,
        execution_price=D('98'),quantity=D('10'),quantity_unit='UNITS'))))
    c.execute(m.trade_lifecycle_event.insert().values(trade_id=identity,sequence_no=1,event_type='BOOKED',event_datetime_utc=original['trade_datetime_utc'],
        recorded_by_user_account_id=ids['demo_user_account'],event_payload=json.dumps(dict(schemaVersion=1,kind='CASH_BOOKING',instrumentDefinitionId=str(definition_id),
            instrumentId=str(parent),quoteFactor='1',unitMultiplier='1',priceCurrencyId=str(ids['gbp_currency'])))))
    result=service().calculate(c,r)
    assert result.period.market_pnl==D('119.877')
    batch=staged(c,r,result);storage.publish(c,r.tenant_id,batch,reviewer(c),'Canonical NAV and independent position evidence checked')


def test_flow_only_strategy_payment_and_reset_are_not_positions(valued):
    from dataclasses import replace
    from apps.reference_api.db import get_engine
    from valuation.flows import book_flow
    from valuation.evidence_access import assert_batch_display
    c,r,trade=valued
    r=replace(r,opening_cutoff=r.closing_cutoff-timedelta(days=1))
    attempt=storage.begin_attempt(get_engine(),r,ids['demo_user_account'],str(uuid4()))
    original=c.execute(select(m.trade_lifecycle_event).where(m.trade_lifecycle_event.c.trade_id==trade)).mappings().one()
    c.execute(m.trade_lifecycle_event.insert().values(trade_id=trade,sequence_no=2,event_type='CANCELLED',
        event_datetime_utc=original['event_datetime_utc'],recorded_by_user_account_id=ids['demo_user_account'],
        supersedes_event_id=original['trade_lifecycle_event_id'],event_payload='{}'))
    for component,role,amount in [('DIVIDEND','INCOME','100'),('RESET','INCOME','20'),('BROKER_FEE','INCOME','-5'),('COUPON','PAYMENT_ONLY','1000')]:
        book_flow(c,r.tenant_id,ids['demo_user_account'],dict(strategyId=r.strategy_id,instrumentId=ids['hsbc_instrument_node'],
            currencyId=ids['gbp_currency'],amount=D(amount),component=component,recognitionRole=role,
            economicDate=r.closing_cutoff.date(),paymentDate=None,sourceReference='SYNTHETIC '+component),str(uuid4()))
    result=service().calculate(c,r)
    assert result.period.market_pnl==0 and result.resolution_snapshot_ids==()
    assert result.gross_pnl==120 and result.net_pnl==115
    assert all(l.bucket.opening_quantity==l.bucket.closing_quantity==0 for l in result.period.lines)
    batch=storage.stage(c,attempt,ids['demo_user_account'],result)
    assert_batch_display(c,r.tenant_id,storage.batch_view(c,r.tenant_id,batch))
    storage.publish(c,r.tenant_id,batch,reviewer(c),'Recorded flows and payment-only coupon reconciled')
