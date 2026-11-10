"""Scoped readiness checks; real resolver on an owned disposable database.

No operating policies, grants or financial inputs are changed by these tests.
"""
from dataclasses import replace
from datetime import datetime,time,timedelta,timezone
from decimal import Decimal as D
from uuid import uuid4

import pytest
from sqlalchemy import select
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from tests.test_valuation_service import valued
from tests.test_measure_inputs import preview


def add_direct_fx(c,r):
    """GBP -> USD, exactly 2 USD per GBP at the requested date's 16 UTC cut."""
    rule=c.execute(select(m.valuation_policy_rule).where(m.valuation_policy_rule.c.valuation_policy_rule_id==ids['valuation_policy_rule'])).mappings().one()
    cut=uuid4()
    c.execute(m.valuation_cut.insert().values(valuation_cut_id=cut,cut_code='MEASURE_FX_'+cut.hex,
        display_name='Synthetic measures FX',timezone_name='UTC',local_time=time(16),market_calendar_id=rule['market_calendar_id']))
    source=dict(c.execute(select(m.market_data_observation).where(m.market_data_observation.c.market_data_observation_id==ids['market_data_observation'])).mappings().one())
    series=uuid4()
    measure=c.scalar(select(m.series_measure_definition.c.series_measure_definition_id).where(m.series_measure_definition.c.measure_code=='FX_RATE'))
    c.execute(m.market_data_series.insert().values(market_data_series_id=series,reference_node_id=ids['gbpusd_fx_pair_node'],
        default_dataset_id=source['dataset_id'],series_type='FX_SPOT',value_type='RATE',currency_id=ids['usd_currency'],
        source_system_id='SYNTHETIC_MEASURES_FX',valuation_cut_id=cut,measure_definition_id=measure))
    for code,value in [('BASE_CURRENCY','GBP'),('QUOTE_CURRENCY','USD')]:
        c.execute(m.market_data_series_dimension.insert().values(market_data_series_id=series,dimension_code=code,dimension_value=value))
    c.execute(m.valuation_policy_rule.insert().values(valuation_policy_id=r.policy_id,rule_sequence=99,subject_type='FX_PAIR',
        series_type='FX_SPOT',value_basis='RAW',market_data_series_id=series,pricing_convention='EXPLICIT_TIME',pricing_cut_id=cut,
        market_calendar_id=rule['market_calendar_id'],selection_method='LAST_BEFORE_CUT',max_staleness_business_days=0))
    stamp=datetime.combine(r.closing_cutoff.date(),time(16),timezone.utc)
    c.execute(m.market_data_observation.insert().values(**(source|dict(market_data_observation_id=uuid4(),market_data_series_id=series,
        market_date=stamp.date(),value=D('2'),market_data_vintage_id=None,observed_at_utc=stamp,received_at_utc=stamp,
        source_published_at_utc=stamp,source_observation_key='MEASURES_FX_'+uuid4().hex))))


def test_all_three_measures_keep_native_and_convert_with_dated_direct_fx(valued):
    c,r,_=valued
    add_direct_fx(c,r)
    row=preview(c,replace(r,reporting_currency_id=ids['usd_currency']))['items'][0]
    for name,measure in row['measures'].items():
        assert measure==dict(localAmount='110',currency='GBP',strategyAmount='220',strategyCurrency='USD',status='AVAILABLE')
        proof=row['evidence']['selections'][name+'Fx']
        assert proof['method']=='DIRECT' and D(proof['rate'])==D('2')
        assert proof['observationDate']==r.closing_cutoff.date().isoformat()


def test_short_equity_preserves_sign_in_both_currencies(valued):
    c,r,trade=valued
    c.execute(m.trade.update().where(m.trade.c.trade_id==trade).values(quantity=D('-10')))
    add_direct_fx(c,r)
    row=preview(c,replace(r,reporting_currency_id=ids['usd_currency']))['items'][0]
    assert row['direction']=='SHORT'
    assert {v['localAmount'] for v in row['measures'].values()}=={'-110'}
    assert {v['strategyAmount'] for v in row['measures'].values()}=={'-220'}


def deny_dataset_display(c,r):
    # Calculation-only source rights must not authorize display of the preview.
    assignment=c.execute(select(m.dataset_licence_assignment.c.dataset_licence_assignment_id,
        m.data_licence.c.licensee_organisation_id).join(m.data_licence).where(
        m.dataset_licence_assignment.c.dataset_id==ids['dataset'])).mappings().first()
    # Native product fixtures may already have a fully licensed SYNTHETIC
    # profile. Preserve its calculation scope and required layers; add an
    # unresolved display prerequisite so denial is explicit in either setup.
    if not c.scalar(select(m.dataset_access_profile.c.dataset_id).where(m.dataset_access_profile.c.dataset_id==ids['dataset'])):
        c.execute(m.dataset_access_profile.insert().values(dataset_id=ids['dataset'],
            licensee_organisation_id=assignment['licensee_organisation_id'],permitted_tenant_id=r.tenant_id,
            usage_scope='PERSONAL',provider_enabled=True,activation_reference='Synthetic calculation only',status='ACTIVE'))
        c.execute(m.dataset_right_requirement.insert().values(dataset_id=ids['dataset'],activity='NON_DISPLAY',
            requirement_code='MEASURES_CALCULATION',dataset_licence_assignment_id=assignment['dataset_licence_assignment_id']))
        c.execute(m.licence_activity_grant.insert().values(dataset_licence_assignment_id=assignment['dataset_licence_assignment_id'],
            activity='NON_DISPLAY',usage_scope='PERSONAL',evidence_basis='PERSONAL_DECLARATION',
            evidence_reference='Synthetic calculation only',valid_from=r.closing_cutoff.date(),status='ACTIVE'))
    c.execute(m.dataset_right_requirement.insert().values(dataset_id=ids['dataset'],activity='DISPLAY',
        requirement_code='MEASURES_DISPLAY_REVIEW_REQUIRED',dataset_licence_assignment_id=None))


def test_current_display_denial_is_not_downgraded_to_missing_price(valued):
    from market_data.display_access import EvidenceDisplayDenied
    c,r,_=valued
    deny_dataset_display(c,r)
    from valuation.service import _selection
    assert _selection(c,r,ids['hsbc_xlon_listing_node'],r.closing_cutoff)[1].status=='SELECTED'
    with pytest.raises(EvidenceDisplayDenied):preview(c,r)


def test_latest_accrued_balance_is_not_duplicated_between_bond_listings(valued):
    from tests.test_economic_pnl_acceptance import add_bond
    c,r,trade=valued
    add_bond(c,r,trade)
    c.execute(m.valuation_policy_rule.update().where(m.valuation_policy_rule.c.valuation_policy_id==r.policy_id,
        m.valuation_policy_rule.c.rule_sequence==90).values(rule_sequence=91))
    add_bond(c,r,trade)
    rows=[x for x in preview(c,r)['items'] if x['instrumentType']=='BOND']
    assert len(rows)==2
    assert all(x['measures']['referenceNotional']['localAmount']=='100000' for x in rows)
    assert all(x['measures']['marketValue']['localAmount'] is None for x in rows)
    assert all('duplicated' in x['evidence']['issues']['accruedBalance'] for x in rows)


@pytest.mark.parametrize('listed',[False,True])
def test_fund_measures_use_canonical_prior_nav_and_exclude_late_revision(valued,listed):
    import json
    c,r,trade=valued
    parent=ids['demo_share_class_instrument_node']
    original=dict(c.execute(select(m.trade).where(m.trade.c.trade_id==trade)).mappings().one())
    fund=c.execute(select(m.instrument).where(m.instrument.c.instrument_node_id==parent)).mappings().one()
    definition=c.scalar(select(m.instrument_definition_version.c.instrument_definition_version_id).where(
        m.instrument_definition_version.c.instrument_node_id==parent,m.instrument_definition_version.c.is_current))
    if not definition:
        prototype=dict(c.execute(select(m.instrument_definition_version).where(
            m.instrument_definition_version.c.instrument_node_id==ids['hsbc_instrument_node'],m.instrument_definition_version.c.is_current)).mappings().one())
        definition=uuid4()
        c.execute(m.instrument_definition_version.insert().values(**(prototype|dict(instrument_definition_version_id=definition,
            instrument_node_id=parent,instrument_type_id=fund['instrument_type_id']))))
    subject=parent
    if listed:
        subject=uuid4()
        prototype=dict(c.execute(select(m.financial_reference_node).where(m.financial_reference_node.c.reference_node_id==ids['hsbc_xlon_listing_node'])).mappings().one())
        c.execute(m.financial_reference_node.insert().values(**(prototype|dict(reference_node_id=subject,
            canonical_name='Synthetic fund listing',internal_code='MEASURE_FUND_'+subject.hex))))
        prototype=dict(c.execute(select(m.listing).where(m.listing.c.listing_node_id==ids['hsbc_xlon_listing_node'])).mappings().one())
        c.execute(m.listing.insert().values(**(prototype|dict(listing_node_id=subject,instrument_node_id=parent,
            trading_symbol='MEASURE_FUND_'+subject.hex,quote_factor=1))))
    identity=uuid4()
    c.execute(m.trade.insert().values(**(original|dict(trade_id=identity,trade_subject_reference_node_id=subject,
        reference_instrument_node_id=None if listed else parent,quantity=D('10'),quantity_unit='UNITS',execution_price=D('98')))))
    c.execute(m.trade_lifecycle_event.insert().values(trade_id=identity,sequence_no=1,event_type='BOOKED',
        event_datetime_utc=original['trade_datetime_utc'],recorded_by_user_account_id=ids['demo_user_account'],event_payload=json.dumps(dict(
            schemaVersion=1,kind='CASH_BOOKING',instrumentDefinitionId=str(definition),instrumentId=str(parent),
            quoteFactor='1',unitMultiplier='1',priceCurrencyId=str(ids['gbp_currency'])))))
    calendar=c.scalar(select(m.valuation_policy_rule.c.market_calendar_id).where(m.valuation_policy_rule.c.valuation_policy_rule_id==ids['valuation_policy_rule']))
    c.execute(m.valuation_policy_rule.update().where(m.valuation_policy_rule.c.valuation_policy_rule_id==ids['demo_fund_nav_policy_rule']).values(
        market_calendar_id=calendar,pricing_convention='NAV_DATE',value_basis='RAW',pricing_date_rule='FIXED_LAG',lag_business_days=1,max_staleness_business_days=0))
    measure=c.scalar(select(m.series_measure_definition.c.series_measure_definition_id).where(m.series_measure_definition.c.measure_code=='PRICE'))
    c.execute(m.market_data_series.update().where(m.market_data_series.c.market_data_series_id==ids['demo_fund_nav_series']).values(measure_definition_id=measure))
    source=dict(c.execute(select(m.market_data_observation).where(m.market_data_observation.c.market_data_observation_id==ids['market_data_observation'])).mappings().one())
    nav_day=r.closing_cutoff.date()-timedelta(days=1)
    stamp=datetime.combine(r.closing_cutoff.date(),time(16),timezone.utc)
    for value,available in [('100',stamp),('999',r.information_cutoff+timedelta(seconds=1))]:
        c.execute(m.market_data_observation.insert().values(**(source|dict(market_data_observation_id=uuid4(),market_data_series_id=ids['demo_fund_nav_series'],
            market_date=nav_day,value=D(value),market_data_vintage_id=None,received_at_utc=available,observed_at_utc=available,
            source_published_at_utc=available,source_observation_key='MEASURES_NAV_'+uuid4().hex))))
    row=next(x for x in preview(c,r)['items'] if x['subjectId']==str(subject))
    assert row['instrumentType']=='FUND',row['instrumentType']
    assert {v['localAmount'] for v in row['measures'].values()}=={'1000'},row['evidence']
    assert row['evidence']['selections']['securityPrice']['selection']['pricing_date_used']==nav_day.isoformat()


def test_permitted_stale_raw_mark_cannot_price_post_split_quantity(valued):
    from positions.contracts import ProjectionRequest,SplitEvent
    from positions.holdings_repository import load_holdings_facts
    from positions.holdings import project_holdings
    from apps.reference_api.strategy_workspace import position_rows
    from valuation.measure_inputs import preview_measures
    c,r,_=valued
    # Own the missing/stale population. Other tests legitimately retain frozen
    # snapshots referencing this date; never delete their immutable observations.
    owned=uuid4()
    series=dict(c.execute(select(m.market_data_series).where(
        m.market_data_series.c.market_data_series_id==ids['market_data_series'])).mappings().one())
    c.execute(m.market_data_series.insert().values(**(series|dict(market_data_series_id=owned))))
    source=dict(c.execute(select(m.market_data_observation).where(
        m.market_data_observation.c.market_data_observation_id==ids['market_data_observation'])).mappings().one())
    source=source|dict(market_data_series_id=owned)
    prior=r.opening_cutoff.replace(hour=16)
    c.execute(m.market_data_observation.insert().values(**(source|dict(market_data_observation_id=uuid4(),market_date=prior.date(),
        value=D('1000'),market_data_vintage_id=None,observed_at_utc=prior,received_at_utc=prior,
        source_published_at_utc=prior,source_observation_key='MEASURES_PRE_SPLIT_'+uuid4().hex))))
    c.execute(m.valuation_policy_rule.update().where(m.valuation_policy_rule.c.valuation_policy_rule_id==ids['valuation_policy_rule'])
        .values(market_data_series_id=owned,pricing_date_rule='PRIOR_AVAILABLE',max_staleness_business_days=2))
    pr=ProjectionRequest(r.tenant_id,r.strategy_id,r.closing_cutoff,r.information_cutoff)
    facts,descriptions=load_holdings_facts(c,pr)
    effective=r.closing_cutoff.replace(hour=7)
    split=SplitEvent(uuid4(),uuid4(),ids['hsbc_xlon_listing_node'],effective,effective.date(),
        effective-timedelta(days=1),D('2'),True,{'sourceReference':'Synthetic reviewed two-for-one'})
    projection=project_holdings(facts,pr,splits=[split])
    assert projection.buckets[0].closing_quantity==D('20')
    row=preview_measures(c,r,projection,descriptions,position_rows(projection,descriptions))['items'][0]
    # A permitted prior-day price is still in old units: must not return 200.
    assert row['measures']['marketValue']['localAmount'] is None,dict(
        quantity=row['quantity'],amount=row['measures']['marketValue']['localAmount'],
        priceDate=row['evidence']['selections']['securityPrice']['selection']['pricing_date_used'])
    assert 'pre-action' in row['evidence']['issues']['securityPrice']
    stamp=r.closing_cutoff.replace(hour=16)
    c.execute(m.market_data_observation.insert().values(**(source|dict(market_data_observation_id=uuid4(),market_date=stamp.date(),
        value=D('500'),market_data_vintage_id=None,observed_at_utc=stamp,received_at_utc=stamp,
        source_published_at_utc=stamp,source_observation_key='MEASURES_POST_SPLIT_'+uuid4().hex))))
    row=preview_measures(c,r,projection,descriptions,position_rows(projection,descriptions))['items'][0]
    assert {v['localAmount'] for v in row['measures'].values()}=={'100'}
