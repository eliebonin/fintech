"""Closing designation must not create another price family or weaken policy."""
import pytest
from sqlalchemy import select
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from security_master_schema.market_data_resolver import resolve_market_data, persist_resolution_snapshot
from apps.reference_api.valuation_policy_contracts import PolicyRuleInput
from tests.test_composite_policy_resolution import composite
from tests.test_composite_policy_api import call, policy_payload


def test_legacy_official_rule_is_presented_as_close_with_requirement():
    rule = PolicyRuleInput.model_validate(dict(ruleSequence=1, seriesType='OFFICIAL_CLOSE', pricingConvention='SESSION_CLOSE'))
    assert rule.series_type == 'CLOSE'
    assert rule.require_official_close is True


def test_official_requirement_cannot_apply_to_fx():
    with pytest.raises(ValueError):
        PolicyRuleInput.model_validate(dict(ruleSequence=1, seriesType='FX_SPOT', pricingConvention='LEGACY', requireOfficialClose=True))


def test_aliases_cannot_hide_conflicting_dimensions_in_one_delivery():
    from datetime import date,datetime,timezone
    from decimal import Decimal
    from market_data.contracts import DailyPoint,ParsedDelivery,ProviderSpec
    from market_data.ingestion import validate_normalized
    stamp=datetime(2026,10,7,20,tzinfo=timezone.utc)
    parsed=ParsedDelivery((DailyPoint('close',stamp.date(),stamp,Decimal('10'),'RAW','CLOSE'),
        DailyPoint('different_close',stamp.date(),stamp,Decimal('11'),'RAW','OFFICIAL_CLOSE')),(),'RAW','PROVIDER_EOD_TIMESTAMP')
    with pytest.raises(ValueError,match='Inconsistent normalized series dimensions'):
        validate_normalized(parsed,ProviderSpec('TEST',('CLOSE','OFFICIAL_CLOSE'),4096,30),date(2026,10,7),date(2026,10,7),stamp)


@pytest.mark.parametrize('method', ['UNKNOWN', 'PROVIDER_DEFINED', 'LAST_TRADE', 'EXCHANGE_OFFICIAL'])
def test_plain_close_accepts_each_method_and_freezes_it(composite, method):
    c, request, _ = composite
    c.execute(m.market_data_series.update().where(m.market_data_series.c.market_data_series_id==ids['market_data_series']).values(series_type='CLOSE', closing_method=method))
    c.execute(m.valuation_policy_rule.update().where(m.valuation_policy_rule.c.valuation_policy_rule_id==ids['valuation_policy_rule']).values(series_type='CLOSE', require_official_close=False))
    result=resolve_market_data(c, request)
    assert result.status=='SELECTED'
    assert result.pricing_evidence['closingMethod']==method
    snapshot=persist_resolution_snapshot(c,request,(result,))
    evidence=c.scalar(select(m.market_data_resolution_snapshot_item.c.pricing_evidence).where(m.market_data_resolution_snapshot_item.c.market_data_resolution_snapshot_id==snapshot))
    assert evidence['closingMethod']==method


@pytest.mark.parametrize('legacy', [False, True])
def test_official_only_rule_rejects_unknown_even_when_generic_official_flag_true(composite, legacy):
    c, request, _ = composite
    c.execute(m.market_data_series.update().where(m.market_data_series.c.market_data_series_id==ids['market_data_series']).values(series_type='CLOSE',closing_method='UNKNOWN',is_official=True))
    c.execute(m.valuation_policy_rule.update().where(m.valuation_policy_rule.c.valuation_policy_rule_id==ids['valuation_policy_rule']).values(series_type='OFFICIAL_CLOSE' if legacy else 'CLOSE', require_official_close=not legacy))
    assert resolve_market_data(c, request).status=='MISSING'
    c.execute(m.market_data_series.update().where(m.market_data_series.c.market_data_series_id==ids['market_data_series']).values(closing_method='EXCHANGE_OFFICIAL'))
    assert resolve_market_data(c, request).status=='SELECTED'


def test_new_policy_stores_close_and_official_requirement():
    payload=policy_payload()
    response=call('POST','/v1/market-data/valuation-policies',payload)
    assert response.status_code==201,response.text
    rule=response.json()['rules'][0]
    assert rule['seriesType']=='CLOSE'
    assert rule['requireOfficialClose'] is True
    assert call('GET','/v1/market-data/valuation-policies/'+response.json()['valuationPolicyId']).json()==response.json()


def test_pre_consolidation_policy_key_replays_but_cannot_remove_requirement():
    import hashlib,json
    from uuid import uuid4
    from apps.reference_api.db import get_engine
    from apps.reference_api.valuation_policy_contracts import PolicyCreate
    payload=policy_payload();key=str(uuid4())
    old=PolicyCreate.model_validate(payload).model_dump(mode='json')
    old.pop('selection_mode');old.pop('default_rules')
    old['rules'][0].pop('price_requirement');old['rules'][0].pop('allow_split_conversion')
    old['rules'][0].pop('allow_inverse_fx')
    old['rules'][0].pop('require_official_close');old['rules'][0]['series_type']='OFFICIAL_CLOSE'
    digest=hashlib.sha256(json.dumps(old,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    with get_engine().begin() as c:
        policy=c.execute(m.valuation_policy.insert().values(tenant_id=ids['tenant'],policy_code=payload['policyCode'],display_name=payload['displayName'],
            valuation_cut_id=ids['valuation_cut'],valid_from='2026-08-01',status='DRAFT',created_by_user_account_id=ids['demo_user_account'],
            submission_key=key,submission_fingerprint=digest).returning(m.valuation_policy.c.valuation_policy_id)).scalar_one()
        c.execute(m.valuation_policy_rule.insert().values(valuation_policy_id=policy,**old['rules'][0]))
        c.execute(m.valuation_policy.update().where(m.valuation_policy.c.valuation_policy_id==policy).values(status='ACTIVE'))
    replay=call('POST','/v1/market-data/valuation-policies',payload,key)
    assert replay.status_code==201,replay.text
    assert replay.json()['valuationPolicyId']==str(policy)
    assert replay.json()['rules'][0]['requireOfficialClose'] is True
    payload['rules'][0]['seriesType']='CLOSE'
    assert call('POST','/v1/market-data/valuation-policies',payload,key).status_code==409
    with get_engine().connect() as c:
        row=c.execute(select(m.valuation_policy_rule).where(m.valuation_policy_rule.c.valuation_policy_id==policy)).mappings().one()
        assert row['series_type']=='OFFICIAL_CLOSE'  # Immutable historical rule untouched.
        assert c.scalar(select(m.valuation_policy.c.submission_fingerprint).where(m.valuation_policy.c.valuation_policy_id==policy))==digest


def test_migration_preserves_observations_and_immutable_rules():
    """Exercise the real upgrade against a transactional pre-76 schema."""
    import importlib.util
    from pathlib import Path
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import text
    from apps.reference_api.db import get_engine
    spec=importlib.util.spec_from_file_location('close_migration',Path(__file__).resolve().parents[1]/'alembic/versions/20261008_76_closing_method.py')
    migration=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    with get_engine().connect() as c:
        tx=c.begin()
        try:
            assert c.scalar(text('SELECT current_database()')).startswith('fortem_isolated_tests_'), 'Migration test requires the disposable database runner'
            before=c.execute(text('SELECT market_data_observation_id,value,value_basis FROM md.market_data_observation ORDER BY market_data_observation_id')).all()
            rules=c.execute(text('SELECT valuation_policy_rule_id,series_type FROM ten.valuation_policy_rule ORDER BY valuation_policy_rule_id')).all()
            c.execute(text('DROP TRIGGER normalize_closing_series ON md.market_data_series'))
            c.execute(text('DROP FUNCTION md.normalize_closing_series()'))
            c.execute(text('ALTER TABLE md.market_data_series DROP COLUMN closing_method'))
            c.execute(text('ALTER TABLE ten.valuation_policy_rule DROP COLUMN require_official_close'))
            c.execute(text("UPDATE md.market_data_series SET series_type='OFFICIAL_CLOSE' WHERE market_data_series_id=:id"),{'id':ids['market_data_series']})
            with Operations.context(MigrationContext.configure(c)):
                migration.upgrade()
            row=c.execute(select(m.market_data_series).where(m.market_data_series.c.market_data_series_id==ids['market_data_series'])).mappings().one()
            assert row['series_type']=='CLOSE' and row['closing_method']=='EXCHANGE_OFFICIAL'
            assert c.execute(text('SELECT market_data_observation_id,value,value_basis FROM md.market_data_observation ORDER BY market_data_observation_id')).all()==before
            assert c.execute(text('SELECT valuation_policy_rule_id,series_type FROM ten.valuation_policy_rule ORDER BY valuation_policy_rule_id')).all()==rules
        finally:tx.rollback()


def test_series_catalogue_exposes_method_and_accepts_legacy_official_filter():
    response=call('GET','/v1/market-data/series?seriesType=OFFICIAL_CLOSE&limit=5')
    assert response.status_code==200,response.text
    assert response.json()['data']
    assert all(row['seriesType']=='CLOSE' and row['closingMethod']=='EXCHANGE_OFFICIAL' for row in response.json()['data'])
