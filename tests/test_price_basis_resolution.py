from datetime import datetime, timezone
from dataclasses import replace
from sqlalchemy import select
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from security_master_schema.market_data_resolver import resolve_market_data, persist_resolution_snapshot
from tests.test_composite_policy_resolution import composite


def configured(c):
    c.execute(m.valuation_policy_rule.update().where(m.valuation_policy_rule.c.valuation_policy_rule_id==ids['valuation_policy_rule']).values(
        price_requirement='AS_TRADED', allow_split_conversion=True))
    c.execute(m.market_data_observation.update().where(m.market_data_observation.c.market_data_observation_id==ids['market_data_observation']).values(
        value=40, value_basis='SPLIT_ADJUSTED'))


def test_missing_proof_blocks_instead_of_using_adjusted_price(composite):
    c, request, _ = composite
    configured(c)
    result = resolve_market_data(c, request)
    assert result.status == 'MISSING'
    assert result.exception_code == 'PRICE_BASIS_PROOF_MISSING'
    assert result.selected_value is None


def test_frozen_normalized_value_preserves_original_source_and_cutoff(composite):
    from market_data.price_basis_store import record_price_basis_proof
    c, request, _ = composite
    configured(c)
    proof = dict(method='SPLIT_ONLY', complete=True, anchorDate='2026-08-31',
        marketDate='2026-08-28', coverageStart='2026-08-01', coverageEnd='2026-08-31',
        sourceReference='synthetic-vintage', splits=[dict(date='2026-08-31', numerator='2', denominator='1')])
    record_price_basis_proof(c, ids['market_data_observation'], proof,
        datetime(2026,8,31,17,tzinfo=timezone.utc))
    result = resolve_market_data(c, request)
    assert result.status == 'SELECTED'
    assert str(result.selected_value) == '40.000000000000'
    assert result.valuation_value == 80
    assert result.valuation_basis == 'AS_TRADED'
    snapshot = persist_resolution_snapshot(c, request, (result,))
    stored = c.scalar(select(m.market_data_resolution_snapshot_item.c.pricing_evidence).where(
        m.market_data_resolution_snapshot_item.c.market_data_resolution_snapshot_id==snapshot))
    assert stored['priceBasis']['valuationValue'] == '80.000000000000'
    earlier = resolve_market_data(c, replace(request,market_data_as_of_utc=datetime(2026,8,31,16,tzinfo=timezone.utc)))
    assert earlier.exception_code == 'PRICE_BASIS_PROOF_MISSING'


def test_derived_raw_freezes_split_lineage_and_blocks_if_proof_is_missing(composite):
    from market_data.price_basis_store import record_price_basis_proof
    c,request,_=composite
    configured(c)
    c.execute(m.market_data_observation.update().where(
        m.market_data_observation.c.market_data_observation_id==ids['market_data_observation']).values(value=80,value_basis='RAW'))
    c.execute(m.market_data_series_dimension.insert().values(market_data_series_id=ids['market_data_series'],
        dimension_code='NORMALIZATION_METHOD',dimension_value='YAHOO_SPLIT_TO_AS_TRADED_V1'))
    missing=resolve_market_data(c,request)
    assert missing.exception_code=='PRICE_BASIS_PROOF_MISSING'
    proof=dict(method='DERIVED_SPLIT_ONLY',complete=True,marketDate='2026-08-28',anchorDate='2026-08-31',
        coverageStart='2026-08-01',coverageEnd='2026-08-31',sourceReference='synthetic-only',
        sourceValue='40',valuationValue='80',factor='0.5',sourceObservationId='retained-source')
    record_price_basis_proof(c,ids['market_data_observation'],proof,datetime(2026,8,31,17,tzinfo=timezone.utc))
    selected=resolve_market_data(c,request)
    assert selected.status=='SELECTED' and selected.valuation_value==80
    assert selected.pricing_evidence['priceBasis']['derivation']['sourceValue']=='40'
