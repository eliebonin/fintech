"""Real bond booking, paired source data and separate daily-interest attribution."""
from dataclasses import replace
from datetime import date,datetime,time,timezone,timedelta
from decimal import Decimal as D
from uuid import UUID,uuid4
import pytest
from sqlalchemy import select
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from tests.test_valuation_service import valued,service
from tests.test_bond_booking_api import bond
from tests.test_cash_product_pnl_integration import stage
from tests.test_position_attribution_storage import reviewer
from market_data.bond_quotes import BondQuoteAccrual
from market_data.bond_quote_store import record_quote_accruals


@pytest.fixture
def dirty_bond(bond,valued):
    from apps.reference_api.product_booking import load_context,book
    from apps.reference_api.product_booking_contracts import ProductBookingRequest
    c,r,_=valued;r=replace(r,opening_cutoff=r.closing_cutoff.replace(month=9,day=30));node=UUID(bond)
    def execute(side='BUY',quantity='100000',price='100',day='2026-09-29',accrued='1250'):
        context=load_context(c,r.tenant_id,node,None,date.fromisoformat(day))
        return book(c,r.tenant_id,ids['demo_user_account'],ProductBookingRequest.model_validate(dict(
            instrumentId=str(node),strategyId=str(r.strategy_id),executionRoute='OTC',side=side,quantity=quantity,
            executionPrice=price,tradeDatetime=day+'T10:00:00Z',settlementDate='2026-10-05',priceType='CLEAN',
            accruedInterestAmount=accrued,settlementEvidence='Synthetic assessed total trade accrued; not the market quotation component',
            counterpartyOrganisationId=str(ids['bank_a_organisation']),expectedTermsFingerprint=context.terms_fingerprint)),
            str(uuid4()),'BOND','synthetic-dirty-bond')
    execute()
    series=uuid4();source=dict(c.execute(select(m.market_data_series).where(m.market_data_series.c.market_data_series_id==ids['market_data_series'])).mappings().one())
    c.execute(m.market_data_series.insert().values(**(source|dict(market_data_series_id=series,reference_node_id=node))))
    for code,value in [('BOND_PRICE_TYPE','DIRTY'),('QUOTE_FACTOR','100')]:
        c.execute(m.market_data_series_dimension.insert().values(market_data_series_id=series,dimension_code=code,dimension_value=value))
    rule=dict(c.execute(select(m.valuation_policy_rule).where(m.valuation_policy_rule.c.valuation_policy_rule_id==ids['valuation_policy_rule'])).mappings().one())
    cut=uuid4();c.execute(m.valuation_cut.insert().values(valuation_cut_id=cut,cut_code='BOND_QUOTE_'+cut.hex,
        display_name='Synthetic bond quotation cut',timezone_name='UTC',local_time=time(16),market_calendar_id=rule['market_calendar_id']))
    c.execute(m.valuation_policy_rule.insert().values(**(rule|dict(valuation_policy_rule_id=uuid4(),rule_sequence=90,
        subject_type='INSTRUMENT',instrument_type_id=None,market_venue_id=None,subject_reference_node_id=node,market_data_series_id=series,
        pricing_convention='EXPLICIT_TIME',pricing_cut_id=cut,require_official_close=False,value_basis='RAW',price_requirement=None))))
    source=dict(c.execute(select(m.market_data_observation).where(m.market_data_observation.c.market_data_observation_id==ids['market_data_observation'])).mappings().one())
    observations=[];components={}
    for cutoff,value,accrued in [(r.opening_cutoff,'101','1'),(r.closing_cutoff,'101.02','1.02')]:
        stamp=datetime.combine(cutoff.date(),time(16),timezone.utc);identifier=uuid4();observations.append(identifier)
        c.execute(m.market_data_observation.insert().values(**(source|dict(market_data_observation_id=identifier,market_data_series_id=series,
            market_date=stamp.date(),value=D(value),market_data_vintage_id=None,observed_at_utc=stamp,received_at_utc=stamp,
            source_published_at_utc=stamp,source_observation_key='DIRTY_BOND_'+uuid4().hex))))
        components[identifier]=BondQuoteAccrual(D(accrued),stamp.date()+timedelta(days=2),'Synthetic provider pair')
        if cutoff==r.opening_cutoff:
            c.execute(m.market_data_observation.insert().values(**(source|dict(market_data_observation_id=uuid4(),market_date=stamp.date(),
                market_data_vintage_id=None,observed_at_utc=stamp,received_at_utc=stamp,source_published_at_utc=stamp,source_observation_key='DIRTY_EQUITY_'+uuid4().hex))))
    record_quote_accruals(c,components,datetime.now(timezone.utc))
    return c,r,node,series,observations,execute


def bond_line(result,node):return next(line for line in result.period.lines if line.bucket.key.subject_id==node)


def test_dirty_marks_are_normalized_without_creating_daily_interest(dirty_bond):
    c,r,node,_,observations,_=dirty_bond;result=service().calculate(c,r)
    assert bond_line(result,node).attribution.market_pnl==0
    assert result.evidence['accrualCoverage']['missingCount']>0
    selected=[s for s in result.evidence['selections'] if s['subject_reference_node_id']==str(node)]
    assert {D(s['valuation_value']) for s in selected}=={D(100)}
    assert {D(s['selected_value']) for s in selected}=={D('101'),D('101.02')}
    assert all(s['valuation_basis']!='CLEAN' for s in selected) # Never conflate adjustment basis with bond quotation.
    assert {s['pricing_evidence']['bondPriceNormalization']['accruedPer100'] for s in selected}=={'1','1.02'}
    assert list(c.scalars(select(m.market_data_observation.c.value).where(m.market_data_observation.c.market_data_observation_id.in_(observations))))!=[D(100),D(100)]


def test_supplied_daily_interest_is_added_once_and_publishable(dirty_bond):
    from valuation.accruals import record_accrual
    from valuation import storage
    c,r,node,_,_,_=dirty_bond
    record_accrual(c,r.tenant_id,ids['demo_user_account'],dict(strategyId=r.strategy_id,instrumentId=node,valueDate=r.closing_cutoff.date(),
        inputType='DAILY_INTEREST',dailyEarned=D(20),currencyId=ids['gbp_currency'],sourceReference='Synthetic independent daily interest'),str(uuid4()))
    result=service().calculate(c,r);line=bond_line(result,node)
    assert line.attribution.market_pnl==0 and line.components()['ACCRUAL']==20
    batch=stage(c,r,result);storage.publish(c,r.tenant_id,batch,reviewer(c),'Reviewed normalized bond with independent interest')
    assert storage.batch_view(c,r.tenant_id,batch)['status']=='PUBLISHED'


def test_coupon_quote_reset_keeps_market_price_constant(dirty_bond):
    c,r,node,series,observations,_=dirty_bond
    source=dict(c.execute(select(m.market_data_observation).where(m.market_data_observation.c.market_data_observation_id==observations[-1])).mappings().one())
    correction=uuid4();stamp=datetime.now(timezone.utc)
    c.execute(m.market_data_observation.insert().values(**(source|dict(market_data_observation_id=correction,value=D(100),
        received_at_utc=stamp,source_observation_key='COUPON_RESET_'+uuid4().hex,supersedes_observation_id=observations[-1]))))
    record_quote_accruals(c,{correction:BondQuoteAccrual(D(0),date(2026,10,5),'Synthetic ex-coupon quote')},stamp)
    result=service().calculate(c,r)
    assert bond_line(result,node).attribution.market_pnl==0


def test_quote_component_is_immutable_and_known_by_the_information_cutoff(dirty_bond):
    from market_data.bond_quote_store import load_quote_accruals
    c,r,_,_,observations,_=dirty_bond;table=m.market_data_bond_quote_accrual
    with pytest.raises(Exception,match='immutable'):
        with c.begin_nested():c.execute(table.update().where(table.c.observation_id==observations[0]).values(accrued_interest_per_100=99))
    assert load_quote_accruals(c,observations,datetime(2026,10,2,tzinfo=timezone.utc))=={}


def test_component_only_source_correction_blocks_stale_staged_publication(dirty_bond):
    from valuation import storage
    c,r,node,_,observations,_=dirty_bond;result=service().calculate(c,r);batch=stage(c,r,result)
    source=dict(c.execute(select(m.market_data_observation).where(m.market_data_observation.c.market_data_observation_id==observations[-1])).mappings().one())
    correction=uuid4();stamp=datetime.now(timezone.utc)
    c.execute(m.market_data_observation.insert().values(**(source|dict(market_data_observation_id=correction,received_at_utc=stamp,
        source_observation_key='COMPONENT_CORRECTION_'+uuid4().hex,supersedes_observation_id=observations[-1]))))
    record_quote_accruals(c,{correction:BondQuoteAccrual(D('1.03'),date(2026,10,5),'Synthetic corrected component')},stamp)
    with pytest.raises(ValueError,match='quotation|quoted|recalculate'):
        storage.publish(c,r.tenant_id,batch,reviewer(c),'Old quote pair cannot be published')


def test_position_monetary_preview_still_uses_the_original_dirty_value(dirty_bond):
    from tests.test_measure_inputs import preview
    c,r,node,_,_,_=dirty_bond
    row=next(item for item in preview(c,r)['items'] if item['instrumentId']==str(node))
    assert D(row['measures']['marketValue']['localAmount'])==D('101020')
    assert bond_line(service().calculate(c,r),node).attribution.market_pnl==0


def test_valuation_rights_revocation_blocks_normalized_bond_publication(dirty_bond):
    from valuation import storage
    c,r,_,series,_,_=dirty_bond;batch=stage(c,r,service().calculate(c,r))
    dataset=c.scalar(select(m.market_data_series.c.default_dataset_id).where(m.market_data_series.c.market_data_series_id==series))
    c.execute(m.tenant_dataset_entitlement.update().where(m.tenant_dataset_entitlement.c.tenant_id==r.tenant_id,
        m.tenant_dataset_entitlement.c.dataset_id==dataset,m.tenant_dataset_entitlement.c.use_purpose=='VALUATION').values(status='INACTIVE'))
    with pytest.raises(ValueError,match='quotation|recalculate'):
        storage.publish(c,r.tenant_id,batch,reviewer(c),'Valuation source rights were revoked')


def test_quoted_accrual_known_after_cutoff_cannot_normalize_an_earlier_run(dirty_bond):
    from valuation.service import ValuationBlocked
    c,r,_,_,observations,_=dirty_bond
    stamp=c.scalar(select(m.market_data_bond_quote_accrual.c.recorded_at_utc).where(m.market_data_bond_quote_accrual.c.observation_id==observations[0]))
    with pytest.raises(ValuationBlocked,match='information cutoff'):
        service().calculate(c,replace(r,information_cutoff=stamp-timedelta(microseconds=1)))


def test_dirty_price_without_matching_component_is_not_treated_as_clean_or_zero_accrual(dirty_bond):
    from valuation.service import ValuationBlocked
    c,r,_,_,observations,_=dirty_bond
    source=dict(c.execute(select(m.market_data_observation).where(m.market_data_observation.c.market_data_observation_id==observations[-1])).mappings().one())
    c.execute(m.market_data_observation.insert().values(**(source|dict(market_data_observation_id=uuid4(),received_at_utc=datetime.now(timezone.utc),
        source_observation_key='MISSING_PAIR_'+uuid4().hex,supersedes_observation_id=observations[-1]))))
    with pytest.raises(ValuationBlocked,match='matching quoted accrued'):
        service().calculate(c,r)


def test_foreign_interest_and_opening_stock_fx_are_included_once_after_clean_normalization(dirty_bond):
    from valuation.accruals import record_accrual
    from tests.test_accrued_balance_integration import calculated
    from tests.test_position_measures_assurance import add_direct_fx
    c,r,node,_,_,_=dirty_bond;add_direct_fx(c,r)
    fx_series=c.scalar(select(m.market_data_series.c.market_data_series_id).where(m.market_data_series.c.source_system_id=='SYNTHETIC_MEASURES_FX'))
    source=dict(c.execute(select(m.market_data_observation).where(m.market_data_observation.c.market_data_series_id==fx_series)).mappings().one())
    stamp=datetime.combine(r.opening_cutoff.date(),time(16),timezone.utc)
    c.execute(m.market_data_observation.insert().values(**(source|dict(market_data_observation_id=uuid4(),market_date=stamp.date(),value=D('1.5'),
        observed_at_utc=stamp,received_at_utc=stamp,source_published_at_utc=stamp,source_observation_key='BOND_OPEN_FX_'+uuid4().hex))))
    for day,amount in [(date(2026,9,29),0),(date(2026,9,30),0),(date(2026,10,1),20)]:
        record_accrual(c,r.tenant_id,ids['demo_user_account'],dict(strategyId=r.strategy_id,instrumentId=node,valueDate=day,
            inputType='DAILY_INTEREST',dailyEarned=D(amount),currencyId=ids['gbp_currency'],sourceReference='Synthetic independent strategy earnings'),str(uuid4()))
    result=calculated(c,replace(r,reporting_currency_id=ids['usd_currency']));line=bond_line(result,node)
    assert line.attribution.market_pnl==50000
    assert line.components()['ACCRUAL']==40 and line.components()['CARRY']==625
    assert line.gross_pnl==50665 # bought accrued 1250 × FX change .5; never quote accrual 1 × nominal/100.
