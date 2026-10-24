"""Native option contracts through governed canonical premiums and retained staging."""
from dataclasses import replace,asdict
from datetime import date,datetime,time,timezone
from decimal import Decimal as D
from uuid import uuid4,UUID
import json
import pytest
from sqlalchemy import select
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from tests.test_valuation_service import valued
from tests.test_option_booking_api import listing


def setup_option(listing,valued,closing='28'):
    from apps.reference_api.option_booking import book,load
    from apps.reference_api.contracts import OptionBookingRequest
    c,r,_=valued;actor=ids['demo_user_account']
    original=dict(c.execute(select(m.strategy).where(m.strategy.c.strategy_id==r.strategy_id)).mappings().one())
    strategy=uuid4();c.execute(m.strategy.insert().values(**(original|dict(strategy_id=strategy,strategy_code='OPT_'+strategy.hex))))
    _,terms=load(c,r.tenant_id,UUID(listing),as_of=date(2026,9,29))
    request=OptionBookingRequest(listingId=listing,strategyId=strategy,side='BUY',quantity='20',executionPrice='23.8',
        tradeDatetime='2026-09-29T10:00:00Z',settlementDate='2026-09-30',positionEffect='OPEN',
        counterpartyOrganisationId=ids['bank_a_organisation'],expectedTermsFingerprint=terms.terms_fingerprint)
    detail=book(c,r.tenant_id,actor,request,str(uuid4()),'option-valuation-test')
    trade=detail.data.trade.trade_id;node=terms.instrument_id
    source=dict(c.execute(select(m.market_data_series).where(m.market_data_series.c.market_data_series_id==ids['market_data_series'])).mappings().one())
    series=uuid4();c.execute(m.market_data_series.insert().values(**(source|dict(market_data_series_id=series,reference_node_id=node,
        series_type='CLOSE',is_official=False,closing_method='PROVIDER_DEFINED'))))
    for code,value in [('OPTION_PRICE_BASIS','PREMIUM_POINTS'),('PREMIUM_MULTIPLIER','100'),('QUOTE_FACTOR','1'),('QUANTITY_UNIT','CONTRACTS')]:
        c.execute(m.market_data_series_dimension.insert().values(market_data_series_id=series,dimension_code=code,dimension_value=value))
    calendar=c.scalar(select(m.valuation_policy_rule.c.market_calendar_id).where(m.valuation_policy_rule.c.valuation_policy_rule_id==ids['valuation_policy_rule']))
    cut=uuid4();c.execute(m.valuation_cut.insert().values(valuation_cut_id=cut,cut_code='OPT_'+cut.hex,display_name='Synthetic option premium cut',
        timezone_name='UTC',local_time=time(16),market_calendar_id=calendar,status='ACTIVE'))
    c.execute(m.valuation_policy_rule.update().where(m.valuation_policy_rule.c.valuation_policy_rule_id==ids['valuation_policy_rule']).values(
        subject_type=None,instrument_type_id=None,subject_reference_node_id=node,market_data_series_id=series,
        pricing_convention='EXPLICIT_TIME',pricing_cut_id=cut,series_type='CLOSE',value_basis='RAW',price_requirement=None,allow_split_conversion=False,
        require_official_close=False,market_venue_id=None))
    observation=dict(c.execute(select(m.market_data_observation).where(m.market_data_observation.c.market_data_observation_id==ids['market_data_observation'])).mappings().one())
    for day,price in [(date(2026,9,29),'23.8'),(date(2026,10,1),closing)]:
        stamp=datetime.combine(day,time(16),timezone.utc)
        c.execute(m.market_data_observation.insert().values(**(observation|dict(market_data_observation_id=uuid4(),market_data_series_id=series,
            market_data_vintage_id=None,market_date=day,value=D(price),observed_at_utc=stamp,received_at_utc=stamp,
            source_published_at_utc=stamp,source_observation_key='OPT_'+uuid4().hex))))
    return c,replace(r,strategy_id=strategy),trade,series


@pytest.mark.parametrize('legacy,closing,expected',[(False,'28',8400),(True,'28',8400),(False,'0',-47600)])
def test_option_contract_multiplier_once_through_native_booking_resolver_and_staging(listing,valued,legacy,closing,expected):
    from valuation.service import calculate_position
    c,r,trade,_=setup_option(listing,valued,closing)
    event=c.execute(select(m.trade_lifecycle_event).where(m.trade_lifecycle_event.c.trade_id==trade)).mappings().one()
    assert json.loads(event['event_payload'])['valuationConventions']['unitMultiplier']=='100'
    if legacy:
        # Historical format is a separate test fixture, never an event rewrite.
        source=dict(c.execute(select(m.strategy).where(m.strategy.c.strategy_id==r.strategy_id)).mappings().one())
        strategy=uuid4();c.execute(m.strategy.insert().values(**(source|dict(strategy_id=strategy,strategy_code='OLD_OPT_'+strategy.hex))))
        old=dict(c.execute(select(m.trade).where(m.trade.c.trade_id==trade)).mappings().one())
        trade=uuid4();c.execute(m.trade.insert().values(**(old|dict(trade_id=trade,strategy_id=strategy))))
        payload=json.loads(event['event_payload']);payload.pop('valuationConventions')
        c.execute(m.trade_lifecycle_event.insert().values(**(dict(event)|dict(trade_lifecycle_event_id=uuid4(),trade_id=trade,
            source_event_id=str(uuid4()),event_payload=json.dumps(payload)))))
        r=replace(r,strategy_id=strategy)
    before=c.scalar(select(m.trade_lifecycle_event.c.event_payload).where(m.trade_lifecycle_event.c.trade_id==trade))
    result=calculate_position(c,r)
    assert result.period.market_pnl==expected
    assert result.projection.buckets[0].closing_quantity==20 and result.projection.buckets[0].key.unit_multiplier==100
    assert c.scalar(select(m.trade_lifecycle_event.c.event_payload).where(m.trade_lifecycle_event.c.trade_id==trade))==before
    from valuation import storage,tables as t
    from valuation.economics import canonical_payload,evidence_hash
    actor=ids['demo_user_account']
    attempt=c.execute(t.attempt.insert().values(tenant_id=r.tenant_id,strategy_id=r.strategy_id,initiated_by=actor,request_key=str(uuid4()),
        request_hash=evidence_hash(dict(request=storage.request_identity(r),actor=actor)),request_payload=canonical_payload(asdict(r)),
        correlation_id=str(uuid4()),status='RUNNING').returning(t.attempt.c.attempt_id)).scalar_one()
    batch=storage.stage(c,attempt,actor,result);view=storage.batch_view(c,r.tenant_id,batch)
    assert view['status']=='STAGED' and D(view['summary']['marketPnl'])==expected
    assert any(item['code']=='OPTION_CONTRACT_PREMIUM' for item in view['items'][0]['evidence']['appliedRules'])
    assert storage.published(c,r.tenant_id,r.strategy_id,r.closing_cutoff.date())==[]


def test_wrong_option_premium_multiplier_is_not_used(listing,valued):
    from valuation.service import calculate_position,ValuationBlocked
    c,r,_,series=setup_option(listing,valued)
    c.execute(m.market_data_series_dimension.update().where(m.market_data_series_dimension.c.market_data_series_id==series,
        m.market_data_series_dimension.c.dimension_code=='PREMIUM_MULTIPLIER').values(dimension_value='1'))
    with pytest.raises(ValuationBlocked):calculate_position(c,r)


def test_original_fingerprint_recovers_without_assuming_clock_order(listing,valued):
    from positions.option import normalize_booking
    c,_,trade,_=setup_option(listing,valued)
    row=c.execute(select(m.trade).where(m.trade.c.trade_id==trade)).mappings().one()
    event=c.execute(select(m.trade_lifecycle_event).where(m.trade_lifecycle_event.c.trade_id==row['trade_id'],m.trade_lifecycle_event.c.event_type=='BOOKED')).mappings().one()
    payload=json.loads(event['event_payload']);payload.pop('valuationConventions')
    # PostgreSQL transaction-start time can precede application approval time.
    # Exact frozen fingerprint, not clock ordering, proves historical identity.
    earlier_record=dict(event,recorded_at=datetime(2026,9,1,tzinfo=timezone.utc))
    proof=normalize_booking(c,row,payload,earlier_record)
    assert proof['unitMultiplier']=='100' and row['quantity']==20
