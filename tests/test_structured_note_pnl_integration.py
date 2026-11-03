"""Approved notes, immutable bookings and policy-selected whole-note marks."""
from dataclasses import replace,asdict
from datetime import date,time,datetime,timezone
from decimal import Decimal as D
from uuid import uuid4,UUID
import json
import pytest
from sqlalchemy import select
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from tests.test_product_booking_api import structured,structured_convention
from tests.test_valuation_service import valued


def ready(valued,structured,*,basis='NONE',unit='NOMINAL'):
    from apps.reference_api.product_booking import book,load_context
    from apps.reference_api.product_booking_contracts import ProductBookingRequest,StructuredConvention
    c,r,_=valued;node=UUID(structured)
    c.exec_driver_sql("SET LOCAL lock_timeout='10s'")
    # Append an approved synthetic version, retaining the earlier convention.
    seq=c.scalar(select(m.instrument_booking_convention.c.version_no).where(
        m.instrument_booking_convention.c.instrument_node_id==node).order_by(m.instrument_booking_convention.c.version_no.desc()).limit(1))
    cv=StructuredConvention.model_validate(structured_convention(accrual=basis,quantityUnit=unit,
        denomination='1000' if unit=='UNITS' else None,quantityMinimum='1',quantityIncrement='1'))
    c.execute(m.instrument_booking_convention.insert().values(instrument_node_id=node,version_no=seq+1,effective_from=date(2026,9,1),
        kind='STRUCTURED_PRODUCT',convention_payload=cv.model_dump_json(by_alias=True),approved_by_user_account_id=ids['demo_user_account']))
    r=replace(r,opening_cutoff=r.closing_cutoff.replace(month=9,day=30))
    def execute(side='BUY',quantity='100000',price='98',day='2026-09-30',accrued=None):
        context=load_context(c,r.tenant_id,node,None,date.fromisoformat(day))
        return book(c,r.tenant_id,ids['demo_user_account'],ProductBookingRequest.model_validate(dict(instrumentId=str(node),
            strategyId=str(r.strategy_id),executionRoute='OTC',side=side,quantity=quantity,executionPrice=price,
            tradeDatetime=day+'T10:00:00Z',settlementDate='2026-10-05',accruedInterestAmount=accrued,
            counterpartyOrganisationId=str(ids['bank_a_organisation']),expectedTermsFingerprint=context.terms_fingerprint)),
            str(uuid4()),'STRUCTURED_PRODUCT','note-pnl-test')
    execute(quantity='100' if unit=='UNITS' else '100000')
    source=dict(c.execute(select(m.market_data_series).where(m.market_data_series.c.market_data_series_id==ids['market_data_series'])).mappings().one())
    rule=dict(c.execute(select(m.valuation_policy_rule).where(m.valuation_policy_rule.c.valuation_policy_rule_id==ids['valuation_policy_rule'])).mappings().one())
    series=uuid4();cut=uuid4();rule_id=uuid4()
    c.execute(m.valuation_cut.insert().values(valuation_cut_id=cut,cut_code='NOTE_'+cut.hex,display_name='Synthetic note cut',
        timezone_name='UTC',local_time=time(16),market_calendar_id=rule['market_calendar_id']))
    c.execute(m.market_data_series.insert().values(**(source|dict(market_data_series_id=series,reference_node_id=node,
        series_type='MARK',currency_id=ids['gbp_currency'],valuation_cut_id=cut,closing_method='UNKNOWN',is_official=False))))
    for code,value in [('STRUCTURED_PRICE_BASIS','PCT_OF_PAR'),('STRUCTURED_ACCRUAL_BASIS',basis),('QUOTE_FACTOR','100')]:
        c.execute(m.market_data_series_dimension.insert().values(market_data_series_id=series,dimension_code=code,dimension_value=value))
    c.execute(m.valuation_policy_rule.insert().values(**(rule|dict(valuation_policy_rule_id=rule_id,rule_sequence=230,
        subject_type='INSTRUMENT',instrument_type_id=None,market_venue_id=None,is_default=False,
        subject_reference_node_id=node,market_data_series_id=series,series_type='MARK',value_basis='RAW',price_requirement=None,
        require_official_close=False,pricing_convention='EXPLICIT_TIME',pricing_cut_id=cut))))
    source=dict(c.execute(select(m.market_data_observation).where(m.market_data_observation.c.market_data_observation_id==ids['market_data_observation'])).mappings().one())
    stamp=datetime.combine(r.opening_cutoff.date(),time(16),timezone.utc)
    c.execute(m.market_data_observation.insert().values(**(source|dict(market_data_observation_id=uuid4(),market_date=stamp.date(),
        value=D('1050'),market_data_vintage_id=None,observed_at_utc=stamp,received_at_utc=stamp,source_published_at_utc=stamp,
        source_observation_key='NOTE_SHARE_OPEN_'+uuid4().hex))))
    for day,price in [(r.opening_cutoff.date(),'98'),(r.closing_cutoff.date(),'99')]:
        stamp=datetime.combine(day,time(16),timezone.utc)
        c.execute(m.market_data_observation.insert().values(**(source|dict(market_data_observation_id=uuid4(),market_data_series_id=series,
            valuation_cut_id=cut,market_date=day,value=D(price),market_data_vintage_id=None,observed_at_utc=stamp,
            received_at_utc=stamp,source_published_at_utc=stamp,source_observation_key='NOTE_'+uuid4().hex))))
    return c,r,node,series,execute


def note_line(result):return next(line for line in result.period.lines if line.bucket.key.product_basis=='STRUCTURED_PRODUCT')


def stage(c,r,result):
    from valuation import storage,tables as t
    from valuation.economics import canonical_payload,evidence_hash
    actor=ids['demo_user_account']
    # Real booking holds the strategy row in this test transaction. Insert the
    # synthetic attempt here too, avoiding a second connection's FK lock wait.
    attempt=c.scalar(t.attempt.insert().values(tenant_id=r.tenant_id,strategy_id=r.strategy_id,initiated_by=actor,
        request_key=str(uuid4()),request_hash=evidence_hash(dict(request=storage.request_identity(r),actor=actor)),
        request_payload=canonical_payload(asdict(r)),correlation_id=str(uuid4()),status='RUNNING').returning(t.attempt.c.attempt_id))
    return storage.stage(c,attempt,actor,result)


@pytest.mark.parametrize('unit',['NOMINAL','UNITS'])
def test_note_whole_mark_and_frozen_quotation_survive_new_versions(valued,structured,unit):
    from valuation.service import calculate_position
    c,r,node,_,execute=ready(valued,structured,unit=unit)
    result=calculate_position(c,r);assert note_line(result).attribution.market_pnl==1000
    execute('SELL','50' if unit=='UNITS' else '50000','98.5','2026-10-01')
    assert note_line(calculate_position(c,r)).attribution.market_pnl==750
    assert note_line(result).bucket.key.unit_multiplier==(1000 if unit=='UNITS' else 1)
    original=dict(c.execute(select(m.instrument_booking_convention).where(m.instrument_booking_convention.c.instrument_node_id==node)
        .order_by(m.instrument_booking_convention.c.version_no.desc()).limit(1)).mappings().one())
    revised=json.loads(original['convention_payload']);revised.update(quantityUnit='NOMINAL' if unit=='UNITS' else 'UNITS',
        denomination=None if unit=='UNITS' else '1000',sourceReference='Subsequent convention, not the recorded execution')
    c.execute(m.instrument_booking_convention.insert().values(**(original|dict(instrument_booking_convention_id=uuid4(),
        version_no=original['version_no']+1,convention_payload=json.dumps(revised)))))
    assert note_line(calculate_position(c,r)).attribution.market_pnl==750


@pytest.mark.parametrize('dimension,value',[('STRUCTURED_ACCRUAL_BASIS','CLEAN'),('QUOTE_FACTOR','1'),('STRUCTURED_PRICE_BASIS','UNIT_PRICE')])
def test_incompatible_note_quotation_cannot_be_selected(valued,structured,dimension,value):
    from valuation.service import calculate_position,ValuationBlocked
    c,r,_,series,_=ready(valued,structured,basis='DIRTY')
    c.execute(m.market_data_series_dimension.update().where(m.market_data_series_dimension.c.market_data_series_id==series,
        m.market_data_series_dimension.c.dimension_code==dimension).values(dimension_value=value))
    with pytest.raises(ValuationBlocked):calculate_position(c,r)


@pytest.mark.parametrize('basis',['CLEAN','DIRTY'])
def test_only_clean_marks_add_supplied_daily_interest(valued,structured,basis):
    from valuation.accruals import record_accrual
    from valuation.service import calculate_position
    c,r,node,_,_=ready(valued,structured,basis=basis)
    record_accrual(c,r.tenant_id,ids['demo_user_account'],dict(strategyId=r.strategy_id,instrumentId=node,valueDate=r.closing_cutoff.date(),
        currencyId=ids['gbp_currency'],inputType='DAILY_INTEREST',dailyEarned=D(20),sourceReference='Assessed synthetic note interest'),str(uuid4()))
    result=calculate_position(c,r);line=note_line(result)
    assert line.economic_components.get('ACCRUAL',0)==(20 if basis=='CLEAN' else 0)
    if basis=='DIRTY':assert not any(line.instrument_id==node for line in result.accrued_balance.lines)


def test_note_coupon_income_and_later_payment_do_not_double_count(valued,structured):
    from valuation.flows import book_flow
    from valuation.service import calculate_position
    c,r,node,_,_=ready(valued,structured,basis='DIRTY')
    data=dict(strategyId=r.strategy_id,instrumentId=node,currencyId=ids['gbp_currency'],amount=D(2000),component='COUPON',
        recognitionRole='INCOME',economicDate=r.closing_cutoff.date(),paymentDate=None,sourceReference='Synthetic coupon detached')
    key=str(uuid4());book_flow(c,r.tenant_id,ids['demo_user_account'],data,key)
    book_flow(c,r.tenant_id,ids['demo_user_account'],data,key)
    book_flow(c,r.tenant_id,ids['demo_user_account'],data|dict(recognitionRole='PAYMENT_ONLY'),str(uuid4()))
    result=calculate_position(c,r)
    assert sum(line.economic_components.get('COUPON',0) for line in result.period.lines)==2000


def test_clean_note_optional_interest_absence_does_not_block(valued,structured):
    from valuation.service import calculate_position
    c,r,_,_,_=ready(valued,structured,basis='CLEAN');result=calculate_position(c,r)
    assert note_line(result).attribution.market_pnl==1000
    assert result.evidence['accrualCoverage']['missingCount']==1


@pytest.mark.parametrize('amend',[False,True])
def test_structured_note_stages_and_publishes_with_independent_review(valued,structured,amend):
    from valuation.service import calculate_position
    from valuation import storage,tables as t
    from valuation.economics import canonical_payload,evidence_hash
    c,r,_,_,_=ready(valued,structured,basis='DIRTY');result=calculate_position(c,r);actor=ids['demo_user_account']
    attempt=c.scalar(t.attempt.insert().values(tenant_id=r.tenant_id,strategy_id=r.strategy_id,initiated_by=actor,
        request_key=str(uuid4()),request_hash=evidence_hash(dict(request=storage.request_identity(r),actor=actor)),
        request_payload=canonical_payload(asdict(r)),correlation_id=str(uuid4()),status='RUNNING').returning(t.attempt.c.attempt_id))
    batch=storage.stage(c,attempt,actor,result)
    reviewer=c.scalar(select(m.user_account.c.user_account_id).where(m.user_account.c.user_account_id!=actor,m.user_account.c.status=='ACTIVE').limit(1))
    if amend:
        from valuation.amendments import request_component_change,approve_component_change
        row=next(item for item in storage.batch_view(c,r.tenant_id,batch)['items']
            if item['evidence']['identity']['bucket']['key']['product_basis']=='STRUCTURED_PRODUCT')
        change=request_component_change(c,r.tenant_id,batch,row['attribution_id'],actor,
            dict(component='BROKER_FEE',amount=D('-1'),reason='Synthetic note fee',sourceReference='Synthetic broker evidence'),str(uuid4()))
        batch=approve_component_change(c,r.tenant_id,change,reviewer,'Reviewed synthetic note fee.')
        after=next(item for item in storage.batch_view(c,r.tenant_id,batch)['items']
            if item['evidence']['identity']['bucket']['key']['product_basis']=='STRUCTURED_PRODUCT')
        assert after['market_pnl']==1000 and after['net_pnl']==999
    storage.publish(c,r.tenant_id,batch,reviewer,'Reviewed synthetic whole-note mark bridge.')
    assert storage.batch_view(c,r.tenant_id,batch)['status']=='PUBLISHED'


def test_confirmed_zero_note_mark_and_full_sale_need_no_invented_terminal_price(valued,structured):
    from valuation.service import calculate_position
    c,r,_,series,execute=ready(valued,structured,basis='DIRTY')
    c.execute(m.market_data_observation.update().where(m.market_data_observation.c.market_data_series_id==series,
        m.market_data_observation.c.market_date==r.closing_cutoff.date()).values(value=D(0)))
    assert note_line(calculate_position(c,r)).attribution.market_pnl==-98000
    execute('SELL','100000','98.5','2026-10-01')
    assert note_line(calculate_position(c,r)).attribution.market_pnl==500


def test_equivalent_decimal_quote_divisor_is_accepted(valued,structured):
    from valuation.service import calculate_position
    c,r,_,series,_=ready(valued,structured)
    c.execute(m.market_data_series_dimension.update().where(m.market_data_series_dimension.c.market_data_series_id==series,
        m.market_data_series_dimension.c.dimension_code=='QUOTE_FACTOR').values(dimension_value='100.00'))
    assert note_line(calculate_position(c,r)).attribution.market_pnl==1000


def test_clean_note_assessed_stock_fx_is_retained_and_revisions_block_old_publication(valued,structured):
    from valuation.service import calculate_position
    from valuation.accruals import record_accrual,accrual_amounts
    from tests.test_economic_pnl_acceptance import reviewer
    from tests.test_position_measures_assurance import add_direct_fx
    from valuation import storage
    from valuation.accrued_balance_tables import balance_snapshot
    from valuation.fx import resolve_fx
    c,r,node,_,_=ready(valued,structured,basis='CLEAN');r=replace(r,reporting_currency_id=ids['usd_currency'])
    add_direct_fx(c,r)
    series=c.scalar(select(m.market_data_series.c.market_data_series_id).where(m.market_data_series.c.source_system_id=='SYNTHETIC_MEASURES_FX'))
    observation=dict(c.execute(select(m.market_data_observation).where(m.market_data_observation.c.market_data_series_id==series)).mappings().one())
    stamp=datetime.combine(r.opening_cutoff.date(),time(16),timezone.utc)
    c.execute(m.market_data_observation.insert().values(**(observation|dict(market_data_observation_id=uuid4(),market_date=stamp.date(),value=D('1.9'),
        observed_at_utc=stamp,received_at_utc=stamp,source_published_at_utc=stamp,source_observation_key='NOTE_FX_OPEN_'+uuid4().hex))))
    values=dict(openingBalance=D(1000),dailyEarned=D(20),closingBalance=D(1020),balanceMovements=D(0),openingFx=D('1.9'),closingFx=D(2))
    payload=dict(strategyId=r.strategy_id,instrumentId=node,valueDate=r.closing_cutoff.date(),inputType='DAILY_INTEREST',dailyEarned=D(20),
        currencyId=ids['gbp_currency'],reportingCurrencyId=r.reporting_currency_id,inputs=values,amounts=accrual_amounts(values),
        policyId=r.policy_id,cutId=r.cut_id,fxEvidence=[resolve_fx(c,r,ids['gbp_currency'],r.reporting_currency_id,day).evidence for day in (r.opening_cutoff.date(),r.closing_cutoff.date())])
    # Service payloads are canonical JSON, as produced by the HTTP adapter.
    payload['policyId']=str(payload['policyId']);payload['cutId']=str(payload['cutId'])
    identity=record_accrual(c,r.tenant_id,ids['demo_user_account'],payload,str(uuid4()))
    result=calculate_position(c,r);line=note_line(result)
    assert line.economic_components['ACCRUAL']==40 and line.economic_components['CARRY']==100
    batch=stage(c,r,result)
    stock=c.execute(select(balance_snapshot).where(balance_snapshot.c.instrument_id==node)).mappings().one()
    assert stock['opening_balance']==1000 and stock['fx_pnl']==100 and stock['coupon_paid'] is None
    with pytest.raises(Exception,match='canonical bond|assessed CLEAN'):
        with c.begin_nested():
            c.execute(balance_snapshot.insert().values(**(dict(stock)|dict(balance_id=uuid4(),instrument_id=ids['hsbc_instrument_node']))))
    record_accrual(c,r.tenant_id,ids['demo_user_account'],payload|dict(supersedesInputId=identity,sourceReference='Corrected source evidence'),str(uuid4()))
    with pytest.raises(ValueError,match='changed|reassess|recalculate'):
        storage.publish(c,r.tenant_id,batch,reviewer(c),'Stale inputs must not publish.')


def test_overlapping_clean_coupon_income_requires_explicit_payment_classification(valued,structured):
    from valuation.accruals import record_accrual
    from valuation.flows import book_flow
    from valuation.service import calculate_position,ValuationBlocked
    c,r,node,_,_=ready(valued,structured,basis='CLEAN')
    record_accrual(c,r.tenant_id,ids['demo_user_account'],dict(strategyId=r.strategy_id,instrumentId=node,valueDate=r.closing_cutoff.date(),
        currencyId=ids['gbp_currency'],inputType='DAILY_INTEREST',dailyEarned=D(20)),str(uuid4()))
    book_flow(c,r.tenant_id,ids['demo_user_account'],dict(strategyId=r.strategy_id,instrumentId=node,currencyId=ids['gbp_currency'],
        economicDate=r.closing_cutoff.date(),amount=D(2000),component='COUPON',recognitionRole='INCOME',sourceReference='Ambiguous overlapping income'),str(uuid4()))
    with pytest.raises(ValuationBlocked,match='PAYMENT_ONLY'):calculate_position(c,r)


@pytest.mark.parametrize('basis,total',[('CLEAN','98125'),('DIRTY','98000')])
def test_trade_accrued_is_recorded_once_without_changing_the_quoted_execution(valued,structured,basis,total):
    from valuation.service import calculate_position
    c,r,node,_,execute=ready(valued,structured,basis=basis)
    execute(day='2026-10-01',accrued='125')
    raw=c.scalar(select(m.trade_lifecycle_event.c.event_payload).join(m.trade).where(m.trade.c.strategy_id==r.strategy_id,
        m.trade.c.reference_instrument_node_id==node,m.trade.c.trade_datetime_utc==datetime(2026,10,1,10,tzinfo=timezone.utc)))
    economics=json.loads(raw)['economics']
    assert economics['amount']==total and economics['structuredDetails']['quotedAmount']=='98000'
    assert economics['structuredDetails']['accruedInterestAmount']=='125'
    assert note_line(calculate_position(c,r)).attribution.market_pnl==2000
