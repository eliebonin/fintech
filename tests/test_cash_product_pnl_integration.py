"""Native cash bookings and scoped stored prices, on owned disposable databases."""
from dataclasses import replace,asdict
from datetime import datetime,date,time,timezone,timedelta
from decimal import Decimal as D
from uuid import uuid4
import json
import pytest
from sqlalchemy import select
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from tests.test_valuation_service import valued
from tests.test_cash_product_pnl import WRAPPERS


def clone_listing(c,r,kind,*,quote_currency=None,multiplier=D(1),divisor=D(1),asset_node=None,venue_id=None):
    """Actual approved cash definitions/listings, with explicitly synthetic names."""
    parent,listing=(asset_node or ids['mvp_btc_node']) if kind=='DIGITAL_ASSET' else uuid4(),uuid4();quote_currency=quote_currency or ids['gbp_currency']
    type_id=c.scalar(select(m.instrument_type.c.instrument_type_id).where(m.instrument_type.c.type_code==kind))
    if type_id is None:
        type_id=c.scalar(m.instrument_type.insert().values(type_code=kind,display_name='Synthetic '+kind,default_asset_class='ETP').returning(m.instrument_type.c.instrument_type_id))
    for table,key,old,new in [
        (m.financial_reference_node,'reference_node_id',ids['hsbc_instrument_node'],parent),
        (m.instrument,'instrument_node_id',ids['hsbc_instrument_node'],parent),
        (m.instrument_definition_version,'instrument_node_id',ids['hsbc_instrument_node'],parent),
        (m.financial_reference_node,'reference_node_id',ids['hsbc_xlon_listing_node'],listing),
        (m.listing,'listing_node_id',ids['hsbc_xlon_listing_node'],listing),
        (m.listing_definition_version,'listing_node_id',ids['hsbc_xlon_listing_node'],listing)]:
        if kind=='DIGITAL_ASSET' and new==parent:continue  # Keep real approved synthetic crypto terms/currency identity.
        values=dict(c.execute(select(table).where(table.c[key]==old)).mappings().one());values[key]=new
        for pk in table.primary_key:
            if pk.name!=key:values[pk.name]=uuid4()
        if table is m.financial_reference_node:values.update(canonical_name='Synthetic '+kind+' '+new.hex,internal_code='CASH_PNL_'+new.hex)
        if table in (m.instrument,m.instrument_definition_version):values.update(instrument_type_id=type_id,asset_class='DIGITAL_ASSET' if kind=='DIGITAL_ASSET' else 'ETP')
        if table in (m.listing,m.listing_definition_version):values.update(trading_symbol='SYN_'+listing.hex[:9],trading_currency_id=quote_currency,quote_factor=divisor,unit_multiplier=multiplier)
        if table is m.listing:values['instrument_node_id']=parent
        if kind=='DIGITAL_ASSET' and table in (m.listing,m.listing_definition_version):values['market_venue_id']=venue_id or ids['coinbase_venue']
        c.execute(table.insert().values(**values))
    for node in ((listing,) if kind=='DIGITAL_ASSET' else (parent,listing)):c.execute(m.reference_node_scope.insert().values(reference_node_id=node,scope_type='TENANT_PRIVATE',owner_tenant_id=r.tenant_id,status='ACTIVE'))
    if kind=='ETP':
        c.execute(m.etp_terms.insert().values(instrument_node_id=parent,etp_kind='ETN',legal_form='DEBT_NOTE',
            redemption_model='OPEN_ENDED',effective_from=date(2024,1,1),status='ACTIVE'))
    return parent,listing


def ready(valued,kind='ETN',*,quote_currency=None,opening=None,closing=None,multiplier=D(1),divisor=D(1),asset_node=None):
    from apps.reference_api.repository import book_listed_cash_trade
    from apps.reference_api.contracts import TradeBookingRequest
    c,r,_=valued;c.exec_driver_sql("SET LOCAL lock_timeout='10s'")
    r=replace(r,opening_cutoff=opening or r.opening_cutoff,closing_cutoff=closing or r.closing_cutoff)
    parent,listing=clone_listing(c,r,kind,quote_currency=quote_currency,multiplier=multiplier,divisor=divisor,asset_node=asset_node)
    def execute(side='BUY',quantity='10',price='100',day=None,subject=listing):
        when=day or r.opening_cutoff.date()
        return book_listed_cash_trade(c,r.tenant_id,ids['demo_user_account'],TradeBookingRequest(
            listingId=subject,strategyId=r.strategy_id,side=side,quantity=quantity,executionPrice=price,
            tradeDatetime=datetime.combine(when,time(10),timezone.utc),settlementDate=when),str(uuid4()),'cash-pnl-fixture')
    series=uuid4();rule_id=uuid4()
    source=dict(c.execute(select(m.market_data_series).where(m.market_data_series.c.market_data_series_id==ids['market_data_series'])).mappings().one())
    c.execute(m.market_data_series.insert().values(**(source|dict(market_data_series_id=series,reference_node_id=listing,
        series_type='CLOSE',currency_id=quote_currency or ids['gbp_currency'],closing_method='UNKNOWN',is_official=False))))
    rule=dict(c.execute(select(m.valuation_policy_rule).where(m.valuation_policy_rule.c.valuation_policy_rule_id==ids['valuation_policy_rule'])).mappings().one())
    c.execute(m.valuation_policy_rule.insert().values(**(rule|dict(valuation_policy_rule_id=rule_id,rule_sequence=240,
        subject_type='LISTING',subject_reference_node_id=listing,instrument_type_id=None,market_venue_id=None,is_default=False,
        market_data_series_id=series,series_type='CLOSE',value_basis='RAW',price_requirement=None,require_official_close=False))))
    observation=dict(c.execute(select(m.market_data_observation).where(m.market_data_observation.c.market_data_observation_id==ids['market_data_observation'])).mappings().one())
    for day,price in [(r.opening_cutoff.date(),'100'),(r.closing_cutoff.date(),'110')]:
        stamp=datetime.combine(day,time(16),timezone.utc)
        c.execute(m.market_data_observation.insert().values(**(observation|dict(market_data_observation_id=uuid4(),market_data_series_id=series,
            market_date=day,value=D(price),value_basis='RAW',market_data_vintage_id=None,observed_at_utc=stamp,received_at_utc=stamp,
            source_published_at_utc=stamp,source_observation_key='CASH_PNL_'+uuid4().hex))))
    return c,r,parent,listing,series,rule_id,execute


def cash_line(result,subject):return next(line for line in result.period.lines if line.bucket.key.subject_id==subject)


def stage(c,r,result):
    from valuation import storage,tables as t
    from valuation.economics import canonical_payload,evidence_hash
    actor=ids['demo_user_account']
    attempt=c.scalar(t.attempt.insert().values(tenant_id=r.tenant_id,strategy_id=r.strategy_id,initiated_by=actor,
        request_key=str(uuid4()),request_hash=evidence_hash(dict(request=storage.request_identity(r),actor=actor)),
        request_payload=canonical_payload(asdict(r)),correlation_id=str(uuid4()),status='RUNNING').returning(t.attempt.c.attempt_id))
    return storage.stage(c,attempt,actor,result)


@pytest.mark.parametrize('kind',[*WRAPPERS,'ETP'])
def test_wrappers_book_and_value_with_their_actual_product_type(valued,kind):
    from valuation.service import calculate_position
    from positions.contracts import ProjectionRequest
    from positions.holdings_repository import load_holdings_facts
    c,r,parent,listing,_,_,execute=ready(valued,kind);execute()
    result=calculate_position(c,r);line=cash_line(result,listing)
    assert line.attribution.market_pnl==100 and line.bucket.key.product_basis==('ETN' if kind=='ETP' else kind)
    assert line.bucket.key.quantity_unit=='UNITS'
    facts,_=load_holdings_facts(c,ProjectionRequest(r.tenant_id,r.strategy_id,r.closing_cutoff,r.information_cutoff))
    assert next(f.booking.product_basis for f in facts if f.booking and f.booking.subject_id==listing)==line.bucket.key.product_basis
    raw=c.scalar(select(m.trade_lifecycle_event.c.event_payload).join(m.trade).where(m.trade.c.strategy_id==r.strategy_id,m.trade.c.trade_subject_reference_node_id==listing))
    proof=json.loads(raw)
    if kind=='ETP':assert proof['etpTermsId']


@pytest.mark.parametrize('quantity,price,expected',[('5','105','75'),('10','105','50'),('15','105','25')])
def test_wrapper_partial_full_and_short_crossing_closures_keep_pnl_on_trade_day(valued,quantity,price,expected):
    from valuation.service import calculate_position
    c,r,_,listing,_,_,execute=ready(valued);execute();execute('SELL',quantity,price,r.closing_cutoff.date())
    assert cash_line(calculate_position(c,r),listing).attribution.market_pnl==D(expected)


def test_wrapper_zero_mark_and_source_unit_factors_are_real_economics(valued):
    from valuation.service import calculate_position
    c,r,_,listing,series,_,execute=ready(valued,'ETC',multiplier=D(3),divisor=D(100))
    execute()
    assert cash_line(calculate_position(c,r),listing).attribution.market_pnl==3
    c.execute(m.market_data_observation.update().where(m.market_data_observation.c.market_data_series_id==series,
        m.market_data_observation.c.market_date==r.closing_cutoff.date()).values(value=D(0)))
    assert cash_line(calculate_position(c,r),listing).attribution.market_pnl==-30


def test_wrapper_stages_amends_and_publishes_under_existing_review_controls(valued):
    from valuation.service import calculate_position
    from valuation import storage
    from valuation.amendments import request_component_change,approve_component_change
    from tests.test_position_attribution_storage import reviewer
    c,r,_,listing,_,_,execute=ready(valued);execute();result=calculate_position(c,r)
    batch=stage(c,r,result);item=next(item for item in storage.batch_view(c,r.tenant_id,batch)['items'] if item['subject_id']==listing)
    change=request_component_change(c,r.tenant_id,batch,item['attribution_id'],ids['demo_user_account'],
        dict(component='BROKER_FEE',amount=D('-1'),reason='Synthetic fee',sourceReference='Synthetic ETP statement'),str(uuid4()))
    other=reviewer(c);batch=approve_component_change(c,r.tenant_id,change,other,'Reviewed synthetic fee')
    storage.publish(c,r.tenant_id,batch,other,'Independent ETP review')
    item=next(item for item in storage.batch_view(c,r.tenant_id,batch)['items'] if item['subject_id']==listing)
    assert item['market_pnl']==100 and item['net_pnl']==99


def test_old_wrapper_share_label_and_new_unit_sale_close_one_position_without_rewriting(valued):
    from valuation.service import calculate_position
    from valuation import storage
    from tests.test_position_attribution_storage import reviewer
    c,r,parent,listing,_,_,execute=ready(valued)
    definition=c.scalar(select(m.instrument_definition_version.c.instrument_definition_version_id).where(m.instrument_definition_version.c.instrument_node_id==parent))
    identity=uuid4();stamp=datetime.combine(r.opening_cutoff.date(),time(10),timezone.utc)
    c.execute(m.trade.insert().values(trade_id=identity,strategy_id=r.strategy_id,reference_instrument_node_id=parent,
        trade_subject_reference_node_id=listing,trade_type='INVESTMENT',quantity=D(10),quantity_unit='SHARES',execution_price=D(100),price_basis='UNIT_PRICE',
        price_currency_id=ids['gbp_currency'],trade_datetime_utc=stamp,execution_channel='API',booked_by_user_account_id=ids['demo_user_account'],created_by_user_account_id=ids['demo_user_account']))
    c.execute(m.trade_lifecycle_event.insert().values(trade_id=identity,sequence_no=1,event_type='BOOKED',event_datetime_utc=stamp,
        recorded_by_user_account_id=ids['demo_user_account'],event_payload=json.dumps(dict(kind='CASH_BOOKING',instrumentId=str(parent),
            instrumentDefinitionId=str(definition),priceCurrencyId=str(ids['gbp_currency']),unitMultiplier='1',quoteFactor='1'))))
    execute('SELL','10','105',r.closing_cutoff.date());result=calculate_position(c,r);line=cash_line(result,listing)
    assert line.bucket.closing_quantity==0 and line.attribution.market_pnl==50
    assert c.scalar(select(m.trade.c.quantity_unit).where(m.trade.c.trade_id==identity))=='SHARES'
    batch=stage(c,r,result)
    storage.publish(c,r.tenant_id,batch,reviewer(c),'Historical unit label reconciled with new closing trade')
    assert storage.batch_view(c,r.tenant_id,batch)['status']=='PUBLISHED'


def test_wrapper_income_and_payment_only_flows_keep_original_bond_guard(valued):
    from valuation.flows import book_flow
    from valuation.service import calculate_position
    c,r,parent,listing,_,_,execute=ready(valued);execute()
    data=dict(strategyId=r.strategy_id,instrumentId=parent,currencyId=ids['gbp_currency'],economicDate=r.closing_cutoff.date(),
        component='COUPON',amount=D(20),recognitionRole='INCOME',sourceReference='Synthetic note distribution')
    book_flow(c,r.tenant_id,ids['demo_user_account'],data,str(uuid4()))
    book_flow(c,r.tenant_id,ids['demo_user_account'],data|dict(recognitionRole='PAYMENT_ONLY'),str(uuid4()))
    assert sum(line.economic_components.get('COUPON',0) for line in calculate_position(c,r).period.lines)==20
    with pytest.raises(ValueError,match='payment-only'):
        book_flow(c,r.tenant_id,ids['demo_user_account'],data|dict(instrumentId=ids['bond_instrument_node']),str(uuid4()))


def test_shared_cash_writer_keeps_fund_units_compatible_with_existing_nav_path(valued):
    from valuation.service import calculate_position
    c,r,parent,listing,series,rule,execute=ready(valued,'FUND_SHARE_CLASS');execute()
    c.execute(m.market_data_series.update().where(m.market_data_series.c.market_data_series_id==series).values(reference_node_id=parent,series_type='NAV'))
    c.execute(m.valuation_policy_rule.update().where(m.valuation_policy_rule.c.valuation_policy_rule_id==rule).values(
        subject_type='INSTRUMENT',subject_reference_node_id=parent,series_type='NAV',pricing_convention='NAV_DATE'))
    line=cash_line(calculate_position(c,r),listing)
    assert line.attribution.market_pnl==100 and line.bucket.key.quantity_unit=='UNITS'


def test_legacy_generic_etp_holdings_use_original_definition_parent_without_price_assumptions(valued):
    from positions.contracts import ProjectionRequest
    from positions.holdings_repository import load_holdings_facts
    c,r,parent,listing,_,_,_=ready(valued,'ETP')
    definition=c.scalar(select(m.instrument_definition_version.c.instrument_definition_version_id).where(m.instrument_definition_version.c.instrument_node_id==parent))
    identity=uuid4();stamp=datetime.combine(r.opening_cutoff.date(),time(10),timezone.utc)
    c.execute(m.trade.insert().values(trade_id=identity,strategy_id=r.strategy_id,trade_subject_reference_node_id=listing,trade_type='INVESTMENT',
        quantity=D(10),quantity_unit='SHARES',execution_price=D(100),price_basis='UNIT_PRICE',price_currency_id=ids['gbp_currency'],
        trade_datetime_utc=stamp,execution_channel='API',booked_by_user_account_id=ids['demo_user_account'],created_by_user_account_id=ids['demo_user_account']))
    c.execute(m.trade_lifecycle_event.insert().values(trade_id=identity,sequence_no=1,event_type='BOOKED',event_datetime_utc=stamp,
        recorded_by_user_account_id=ids['demo_user_account'],event_payload=json.dumps(dict(kind='CASH_BOOKING',instrumentDefinitionId=str(definition)))))
    facts,_=load_holdings_facts(c,ProjectionRequest(r.tenant_id,r.strategy_id,r.closing_cutoff,r.information_cutoff))
    booking=next(f.booking for f in facts if f.booking and f.trade_id==identity)
    assert booking.product_basis=='ETN' and booking.quantity_unit=='UNITS' and booking.quantity==10


def crypto_ready(valued,*,weekend=False,closed_day=None,quote_currency=None,asset_node=None):
    c,original,_=valued
    strategy=uuid4();values=dict(c.execute(select(m.strategy).where(m.strategy.c.strategy_id==original.strategy_id)).mappings().one())
    c.execute(m.strategy.insert().values(**(values|dict(strategy_id=strategy,strategy_code='CRYPTO_'+strategy.hex,display_name='Synthetic crypto-only strategy'))))
    original=replace(original,strategy_id=strategy)
    opening=original.opening_cutoff.replace(month=10,day=2 if weekend else 1)
    closing=opening+timedelta(days=1)
    c,r,parent,listing,series,rule,execute=ready((c,original,None),'DIGITAL_ASSET',quote_currency=quote_currency or ids['usd_currency'],
        opening=opening,closing=closing,asset_node=asset_node)
    calendar,cut=uuid4(),uuid4()
    c.execute(m.market_calendar.insert().values(market_calendar_id=calendar,calendar_code='CRYPTO_'+calendar.hex,
        display_name='Synthetic continuous pricing calendar',timezone_name='UTC',calendar_kind='TRADING'))
    day=opening.date()-timedelta(days=2)
    while day<=closing.date():
        closed=day==closed_day
        c.execute(m.market_calendar_session.insert().values(market_calendar_id=calendar,session_date=day,
            session_status='CLOSED' if closed else 'OPEN',open_local_time=None if closed else time.min,close_local_time=None if closed else time(23,59,59)))
        day+=timedelta(days=1)
    c.execute(m.market_calendar.update().where(m.market_calendar.c.market_calendar_id==calendar).values(sealed=True))
    c.execute(m.valuation_cut.insert().values(valuation_cut_id=cut,cut_code='CRYPTO_'+cut.hex,display_name='Synthetic daily crypto cut',
        timezone_name='UTC',local_time=time(16),market_calendar_id=calendar))
    c.execute(m.valuation_policy_rule.update().where(m.valuation_policy_rule.c.valuation_policy_rule_id==rule).values(
        pricing_convention='EXPLICIT_TIME',pricing_cut_id=cut,market_calendar_id=calendar))
    c.execute(m.market_data_series.update().where(m.market_data_series.c.market_data_series_id==series).values(valuation_cut_id=cut))
    c.execute(m.market_data_observation.update().where(m.market_data_observation.c.market_data_series_id==series).values(valuation_cut_id=cut))
    return c,replace(r,reporting_currency_id=ids['usd_currency']),parent,listing,series,rule,execute,calendar


@pytest.mark.parametrize('weekend',[False,True])
def test_spot_crypto_fraction_uses_its_explicit_daily_cut_including_saturday(valued,weekend):
    from valuation.service import calculate_position
    c,r,_,listing,_,_,execute,_=crypto_ready(valued,weekend=weekend);execute(quantity='.125')
    line=cash_line(calculate_position(c,r),listing)
    assert line.attribution.market_pnl==D('1.25') and line.bucket.key.quantity_unit=='UNITS'
    assert line.bucket.key.product_basis=='DIGITAL_ASSET'


def test_crypto_cannot_treat_a_closed_weekend_as_unchanged_friday_price(valued):
    from valuation.service import calculate_position,ValuationBlocked
    c,r,_,_,_,_,execute,_=crypto_ready(valued,weekend=True,closed_day=date(2026,10,3));execute(quantity='.125')
    with pytest.raises(ValuationBlocked,match='crypto.*calendar|calendar.*crypto'):calculate_position(c,r)


def test_crypto_stablecoin_quote_requires_real_fx_without_a_usd_peg(valued):
    from valuation.service import calculate_position,ValuationBlocked
    c,r,_,_,_,_,execute,_=crypto_ready(valued,quote_currency=ids['mvp_usdc_currency']);execute(quantity='.125')
    with pytest.raises(ValuationBlocked,match='FX|currency pair'):calculate_position(c,r)


def test_native_crypto_raw_zero_is_compatible_with_as_traded_policy(valued):
    from valuation.service import calculate_position
    c,r,_,listing,series,rule,execute,_=crypto_ready(valued);execute(quantity='.125')
    c.execute(m.valuation_policy_rule.update().where(m.valuation_policy_rule.c.valuation_policy_rule_id==rule).values(price_requirement='AS_TRADED'))
    c.execute(m.market_data_observation.update().where(m.market_data_observation.c.market_data_series_id==series,
        m.market_data_observation.c.market_date==r.closing_cutoff.date()).values(value=D(0)))
    assert cash_line(calculate_position(c,r),listing).attribution.market_pnl==D('-12.5')


def test_spot_crypto_rejects_share_adjusted_quotes_and_keeps_exchange_identity(valued):
    from valuation.service import calculate_position,ValuationBlocked
    c,r,_,_,series,rule,execute,_=crypto_ready(valued);execute(quantity='.125')
    c.execute(m.valuation_policy_rule.update().where(m.valuation_policy_rule.c.valuation_policy_rule_id==rule).values(value_basis='SPLIT_ADJUSTED'))
    c.execute(m.market_data_observation.update().where(m.market_data_observation.c.market_data_series_id==series).values(value_basis='SPLIT_ADJUSTED'))
    with pytest.raises(ValuationBlocked,match='Native RAW spot-crypto'):calculate_position(c,r)


def test_crypto_position_cannot_use_another_exchange_listing_price(valued):
    from valuation.service import calculate_position,ValuationBlocked
    c,r,_,_,_,_,execute,_=crypto_ready(valued);execute(quantity='.125')
    _,other=clone_listing(c,r,'DIGITAL_ASSET',quote_currency=ids['usd_currency'])
    execute(quantity='.2',subject=other)
    with pytest.raises(ValuationBlocked,match='Input selection blocked'):calculate_position(c,r)


def test_spot_crypto_stages_and_publishes_with_original_authority(valued):
    from valuation.service import calculate_position
    from valuation import storage
    from tests.test_position_attribution_storage import reviewer
    c,r,_,listing,_,_,execute,_=crypto_ready(valued);execute(quantity='.125')
    batch=stage(c,r,calculate_position(c,r));other=reviewer(c)
    storage.publish(c,r.tenant_id,batch,other,'Reviewed synthetic fractional spot holding')
    result=storage.batch_view(c,r.tenant_id,batch)
    assert result['status']=='PUBLISHED'
    assert next(item for item in result['items'] if item['subject_id']==listing)['market_pnl']==D('1.25')


def test_crypto_quote_currency_fx_is_selected_without_converting_the_native_token_again(valued):
    from valuation.service import calculate_position
    from tests.test_position_measures_assurance import add_direct_fx
    c,r,_,listing,_,_,execute,calendar=crypto_ready(valued);execute(quantity='.125')
    r=replace(r,reporting_currency_id=ids['gbp_currency'])
    c.execute(m.valuation_policy_rule.update().where(m.valuation_policy_rule.c.valuation_policy_rule_id==ids['valuation_policy_rule']).values(market_calendar_id=calendar))
    add_direct_fx(c,r)
    fx_series=c.scalar(select(m.market_data_series.c.market_data_series_id).where(m.market_data_series.c.source_system_id=='SYNTHETIC_MEASURES_FX'))
    source=dict(c.execute(select(m.market_data_observation).where(m.market_data_observation.c.market_data_series_id==fx_series)).mappings().one())
    stamp=datetime.combine(r.opening_cutoff.date(),time(16),timezone.utc)
    c.execute(m.market_data_observation.insert().values(**(source|dict(market_data_observation_id=uuid4(),market_date=stamp.date(),
        observed_at_utc=stamp,received_at_utc=stamp,source_published_at_utc=stamp,source_observation_key='CRYPTO_FX_'+uuid4().hex))))
    c.execute(m.valuation_policy_rule.update().where(m.valuation_policy_rule.c.market_data_series_id==fx_series).values(allow_inverse_fx=True))
    result=calculate_position(c,r)
    assert cash_line(result,listing).attribution.market_pnl==D('.625')
    assert {proof['sourceCurrencyId'] for proof in result.evidence['fxConversions']}=={str(ids['usd_currency'])}


def test_two_actual_exchange_listings_select_their_own_prices_and_remain_separate(valued):
    from valuation.service import calculate_position
    c,r,_,listing,series,rule_id,execute,_=crypto_ready(valued);execute(quantity='.125')
    _,other=clone_listing(c,r,'DIGITAL_ASSET',quote_currency=ids['usd_currency'],venue_id=ids['binance_venue'])
    execute(quantity='.2',subject=other)
    second=uuid4();source=dict(c.execute(select(m.market_data_series).where(m.market_data_series.c.market_data_series_id==series)).mappings().one())
    c.execute(m.market_data_series.insert().values(**(source|dict(market_data_series_id=second,reference_node_id=other))))
    rule=dict(c.execute(select(m.valuation_policy_rule).where(m.valuation_policy_rule.c.valuation_policy_rule_id==rule_id)).mappings().one())
    c.execute(m.valuation_policy_rule.insert().values(**(rule|dict(valuation_policy_rule_id=uuid4(),rule_sequence=241,
        subject_reference_node_id=other,market_data_series_id=second))))
    for row in c.execute(select(m.market_data_observation).where(m.market_data_observation.c.market_data_series_id==series)).mappings().all():
        c.execute(m.market_data_observation.insert().values(**(dict(row)|dict(market_data_observation_id=uuid4(),market_data_series_id=second,
            value=D(120) if row['market_date']==r.closing_cutoff.date() else D(100),source_observation_key='CRYPTO_SECOND_'+uuid4().hex))))
    lines=[line for line in calculate_position(c,r).period.lines if line.bucket.key.product_basis=='DIGITAL_ASSET']
    assert len(lines)==2 and {line.bucket.key.subject_id for line in lines}=={listing,other}
    assert sum(line.attribution.market_pnl for line in lines)==D('5.25')


@pytest.mark.parametrize('sell,expected',[('.05','1'),('.125','.625'),('.2','.25')])
def test_crypto_partial_full_and_short_crossing_use_actual_closing_trade(valued,sell,expected):
    from valuation.service import calculate_position
    c,r,_,listing,_,_,execute,_=crypto_ready(valued);execute(quantity='.125')
    execute('SELL',sell,'105',r.closing_cutoff.date())
    assert cash_line(calculate_position(c,r),listing).attribution.market_pnl==D(expected)


@pytest.mark.parametrize('kind',['ETN','DIGITAL_ASSET'])
def test_new_products_cannot_bypass_source_valuation_rights_or_tenant_scope(valued,kind):
    from valuation.service import calculate_position,ValuationBlocked
    if kind=='DIGITAL_ASSET':c,r,_,_,series,_,execute,_=crypto_ready(valued)
    else:c,r,_,_,series,_,execute=ready(valued,kind)
    execute()
    with pytest.raises((PermissionError,ValueError)):
        calculate_position(c,replace(r,tenant_id=ids['second_tenant']))
    dataset=c.scalar(select(m.market_data_series.c.default_dataset_id).where(m.market_data_series.c.market_data_series_id==series))
    c.execute(m.tenant_dataset_entitlement.update().where(m.tenant_dataset_entitlement.c.tenant_id==r.tenant_id,
        m.tenant_dataset_entitlement.c.dataset_id==dataset,m.tenant_dataset_entitlement.c.use_purpose=='VALUATION').values(status='INACTIVE'))
    with pytest.raises(ValuationBlocked,match='ENTITLEMENT'):calculate_position(c,r)
