"""Governed selection, not manual prices, feeds monetary measures."""
from dataclasses import replace
from decimal import Decimal as D
from sqlalchemy import select
from tests.test_valuation_service import valued
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from positions.contracts import ProjectionRequest
from positions.holdings_repository import load_holdings_facts
from positions.holdings import project_holdings
from apps.reference_api.strategy_workspace import position_rows


def preview(c,r):
    from valuation.measure_inputs import preview_measures
    request=ProjectionRequest(r.tenant_id,r.strategy_id,r.closing_cutoff,r.information_cutoff)
    facts,descriptions=load_holdings_facts(c,request)
    projection=project_holdings(facts,request)
    return preview_measures(c,r,projection,descriptions,position_rows(projection,descriptions))


def test_equity_preview_equal_measures_use_policy_price_and_frozen_quote_factor(valued):
    c,r,_=valued
    result=preview(c,r)
    assert result['status']=='PREVIEW_NOT_PUBLISHED'
    row=result['items'][0]
    assert {v['localAmount'] for v in row['measures'].values()}=={'110'}
    assert {v['strategyAmount'] for v in row['measures'].values()}=={'110'}
    assert row['evidence']['selections']['securityPrice']['selection']['pricing_date_used']=='2026-10-01'


def test_missing_price_or_fx_does_not_become_zero_or_trade_price(valued):
    c,r,_=valued
    foreign=preview(c,replace(r,reporting_currency_id=ids['usd_currency']))
    row=foreign['items'][0]
    assert row['measures']['marketValue']['status']=='LOCAL_ONLY'
    assert row['measures']['marketValue']['reasonCode']=='FX_UNAVAILABLE'
    assert row['measures']['marketValue']['strategyAmount'] is None
    # Historical snapshots from other accepted tests may still reference the
    # shared observations. Point this fixture at an empty eligible series instead
    # of deleting retained evidence belonging to other synthetic strategies.
    from uuid import uuid4
    source=dict(c.execute(select(m.market_data_series).where(m.market_data_series.c.market_data_series_id==ids['market_data_series'])).mappings().one())
    empty=uuid4()
    c.execute(m.market_data_series.insert().values(**(source|dict(market_data_series_id=empty,source_system_id='SYNTHETIC_EMPTY_'+empty.hex))))
    c.execute(m.valuation_policy_rule.update().where(m.valuation_policy_rule.c.valuation_policy_rule_id==ids['valuation_policy_rule']).values(market_data_series_id=empty))
    row=preview(c,r)['items'][0]
    assert row['measures']['marketValue']['localAmount'] is None
    assert row['measures']['marketValue']['status']=='UNAVAILABLE'
    assert row['measures']['marketValue']['reasonCode']=='MISSING_INPUT'


def test_semantic_dimension_filter_excludes_wrong_quote_basis_without_relaxing_policy(valued):
    from security_master_schema.market_data_resolver import resolve_market_data,ResolutionRequest
    c,r,_=valued
    request=ResolutionRequest(r.tenant_id,ids['hsbc_xlon_listing_node'],r.policy_id,r.closing_cutoff.date(),r.cut_id,r.information_cutoff,'VALUATION',r.strategy_id)
    assert resolve_market_data(c,request).status=='SELECTED'
    assert resolve_market_data(c,replace(request,series_dimension_filters=(('BOND_PRICE_TYPE','DIRTY'),))).status!='SELECTED'
    c.execute(m.market_data_series_dimension.insert().values(market_data_series_id=ids['market_data_series'],dimension_code='BOND_PRICE_TYPE',dimension_value='CLEAN'))
    assert resolve_market_data(c,replace(request,series_dimension_filters=(('BOND_PRICE_TYPE','CLEAN'),))).status=='SELECTED'
    assert resolve_market_data(c,replace(request,series_dimension_filters=(('BOND_PRICE_TYPE','DIRTY'),))).status!='SELECTED'


def test_bond_clean_plus_assessed_balance_and_dirty_preference(valued):
    from uuid import uuid4
    from tests.test_economic_pnl_acceptance import add_bond
    from valuation.accruals import record_accrual,accrual_amounts
    c,r,trade=valued
    bond_trade=add_bond(c,r,trade)
    row=next(x for x in preview(c,r)['items'] if x['instrumentType']=='BOND')
    assert row['measures']['referenceNotional']['localAmount']=='100000'
    assert row['measures']['marketValue']['localAmount'] is None
    inputs=dict(openingBalance=D('1190'),dailyEarned=D('10'),closingBalance=D('1200'),balanceMovements=D('0'),openingFx=D('1'),closingFx=D('1'))
    record_accrual(c,r.tenant_id,ids['demo_user_account'],dict(strategyId=r.strategy_id,instrumentId=ids['bond_instrument_node'],
        valueDate=r.closing_cutoff.date(),inputType='DAILY_INTEREST',currencyId=ids['gbp_currency'],reportingCurrencyId=ids['gbp_currency'],
        dailyEarned=D('10'),eligibleNominal=D('100000'),sourceReference='SYNTHETIC assessed balance',eligibilityConvention='OPS_ASSESSED_NOMINAL',
        inputs=inputs,amounts=accrual_amounts(inputs),fxEvidence=[]),str(uuid4()))
    # A rich daily input is a source, not a maintained closing-stock publication.
    row=next(x for x in preview(c,r)['items'] if x['instrumentType']=='BOND')
    assert row['measures']['marketValue']['localAmount'] is None
    from valuation.balance_history import refresh_history
    from valuation.balance_history_contracts import BalanceHistoryRefresh
    refresh_history(c,r.tenant_id,ids['demo_user_account'],BalanceHistoryRefresh(strategyId=r.strategy_id,
        fromDate=r.closing_cutoff.date(),toDate=r.closing_cutoff.date()),uuid4().hex)
    row=next(x for x in preview(c,r)['items'] if x['instrumentType']=='BOND')
    assert row['measures']['marketValue']['localAmount']=='102200'
    assert row['evidence']['route']=='CLEAN_PLUS_ACCRUED_BALANCE'
    subject=c.scalar(select(m.trade.c.trade_subject_reference_node_id).where(m.trade.c.trade_id==bond_trade))
    original=dict(c.execute(select(m.market_data_series).where(m.market_data_series.c.reference_node_id==subject)).mappings().one())
    series=uuid4();c.execute(m.market_data_series.insert().values(**(original|dict(market_data_series_id=series))))
    c.execute(m.market_data_series_dimension.insert().values(market_data_series_id=series,dimension_code='BOND_PRICE_TYPE',dimension_value='DIRTY'))
    c.execute(m.valuation_policy_rule.update().where(m.valuation_policy_rule.c.subject_reference_node_id==subject).values(market_data_series_id=None))
    original_obs=dict(c.execute(select(m.market_data_observation).where(m.market_data_observation.c.market_data_series_id==original['market_data_series_id'],m.market_data_observation.c.market_date==r.closing_cutoff.date())).mappings().one())
    c.execute(m.market_data_observation.insert().values(**(original_obs|dict(market_data_observation_id=uuid4(),market_data_series_id=series,value=D('99.2'),source_observation_key='DIRTY_'+uuid4().hex))))
    row=next(x for x in preview(c,r)['items'] if x['instrumentType']=='BOND')
    assert row['measures']['marketValue']['localAmount']=='99200'
    assert row['evidence']['route']=='DIRTY_PRICE'
    assert 'accruedBalance' not in row['evidence']['selections']


def test_unit_index_swap_preview_uses_underlying_for_exposure_and_signed_swap_mark_for_mtm(valued):
    from uuid import uuid4,UUID
    from apps.reference_api.db import get_engine
    from tests.test_swap_creation_api import create_index,clone_profile,proposal
    from apps.reference_api.swap_creation import materialize_swap
    from apps.reference_api.swap_creation_contracts import SwapProposalRequest
    from apps.reference_api.product_booking import load_context,book
    from apps.reference_api.product_booking_contracts import ProductBookingRequest
    c,r,_=valued
    underlying=create_index(clone_profile('PRICE_RETURN'))
    with get_engine().begin() as setup:
        setup.execute(m.index_terms.update().where(m.index_terms.c.index_node_id==underlying).values(base_currency_id=ids['gbp_currency']))
    # Stay on this fixture's transaction: independent HTTP approval would wait
    # on the currency FK locks intentionally held by its uncommitted trades.
    node=materialize_swap(c,r.tenant_id,ids['demo_user_account'],SwapProposalRequest.model_validate(proposal(underlying,
        quantityUnit='UNITS',contractualUnits='25000',notionalPerUnit='8250',contractualNotional='206250000',
        quoteFactor='1',leverage='1.5',performanceResetFrequency='AT_MATURITY')))
    context=load_context(c,r.tenant_id,node,as_of=r.closing_cutoff.date())
    booked=book(c,r.tenant_id,ids['demo_user_account'],ProductBookingRequest.model_validate(dict(instrumentId=str(node),executionRoute='OTC',
        strategyId=str(r.strategy_id),quantity='25000',executionPrice='0',side='BUY',tradeDatetime='2026-10-01T10:00:00Z',
        counterpartyOrganisationId=str(ids['bank_a_organisation']),expectedTermsFingerprint=context.terms_fingerprint)),str(uuid4()),'SWAP','measure-test')
    assert booked.data.trade.quantity_unit=='UNITS'
    source=dict(c.execute(select(m.market_data_series).where(m.market_data_series.c.market_data_series_id==ids['market_data_series'])).mappings().one())
    rule=dict(c.execute(select(m.valuation_policy_rule).where(m.valuation_policy_rule.c.valuation_policy_rule_id==ids['valuation_policy_rule'])).mappings().one())
    observation=dict(c.execute(select(m.market_data_observation).where(m.market_data_observation.c.market_data_series_id==ids['market_data_series'],m.market_data_observation.c.market_date==r.closing_cutoff.date()).order_by(m.market_data_observation.c.market_data_observation_id.desc()).limit(1)).mappings().one())
    from datetime import time
    cut=uuid4()
    c.execute(m.valuation_cut.insert().values(valuation_cut_id=cut,cut_code='MEASURE_'+cut.hex,display_name='Synthetic 16 UTC mark',
        timezone_name='UTC',local_time=time(16),market_calendar_id=rule['market_calendar_id'],status='ACTIVE'))
    swap_series=None
    for index,(subject,price) in enumerate(((node,'20'),(underlying,'9000')),900):
        series=uuid4()
        is_index=subject==underlying
        index_measure=c.scalar(select(m.series_measure_definition.c.series_measure_definition_id).where(m.series_measure_definition.c.measure_code=='INDEX_LEVEL'))
        c.execute(m.market_data_series.insert().values(**(source|dict(market_data_series_id=series,reference_node_id=subject,currency_id=ids['gbp_currency'],
            series_type='INDEX_LEVEL' if is_index else 'CLOSE',value_type='INDEX_LEVEL' if is_index else 'PRICE',closing_method='UNKNOWN' if is_index else 'PROVIDER_DEFINED',
            is_official=False,measure_definition_id=index_measure if is_index else source['measure_definition_id']))))
        c.execute(m.valuation_policy_rule.insert().values(**(rule|dict(valuation_policy_rule_id=uuid4(),rule_sequence=index,subject_type=None,instrument_type_id=None,
            market_venue_id=None,subject_reference_node_id=subject,market_data_series_id=series,price_requirement=None,
            series_type='INDEX_LEVEL' if is_index else 'CLOSE',value_basis='INDEX_LEVEL' if is_index else 'RAW',require_official_close=False,pricing_convention='EXPLICIT_TIME',pricing_cut_id=cut))))
        c.execute(m.market_data_observation.insert().values(**(observation|dict(market_data_observation_id=uuid4(),market_data_series_id=series,value=D(price),value_basis='INDEX_LEVEL' if is_index else 'RAW',source_observation_key='SWAP_MEASURE_'+uuid4().hex))))
        if subject==node:
            swap_series=series
            for code,value in [('SWAP_PRICE_BASIS','WHOLE_SWAP_MTM_PER_UNIT'),('QUOTE_FACTOR','1')]:
                c.execute(m.market_data_series_dimension.insert().values(market_data_series_id=series,dimension_code=code,dimension_value=value))
    row=next(x for x in preview(c,r)['items'] if x['instrumentType']=='SWAP')
    assert row['measures']['referenceNotional']['localAmount']=='206250000',row['evidence']['issues']
    assert row['measures']['economicExposure']['localAmount']=='337500000',row['evidence']['issues']
    assert row['measures']['marketValue']['localAmount']=='500000',row['evidence']['issues']
    c.execute(m.market_data_observation.update().where(m.market_data_observation.c.market_data_series_id==swap_series).values(value=D('-20')))
    row=next(x for x in preview(c,r)['items'] if x['instrumentType']=='SWAP')
    assert row['measures']['marketValue']['localAmount']=='-500000'
    c.execute(m.market_data_series_dimension.update().where(m.market_data_series_dimension.c.market_data_series_id==swap_series,m.market_data_series_dimension.c.dimension_code=='QUOTE_FACTOR').values(dimension_value='100'))
    row=next(x for x in preview(c,r)['items'] if x['instrumentType']=='SWAP')
    assert row['measures']['marketValue']['localAmount'] is None
    assert row['measures']['referenceNotional']['localAmount']=='206250000'
