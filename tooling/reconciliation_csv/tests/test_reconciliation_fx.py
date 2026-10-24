"""Private daily FX import preserves source orientation, precision and isolation."""
from decimal import Decimal
import pytest
from tooling.reconciliation_csv.tests.test_reconciliation_seed import connection


def test_selection_keeps_direct_rates_and_skips_metals_unselected_and_identity():
    from tooling.reconciliation_csv.reconciliation_fx import select_rates,DEFAULT_CURRENCIES
    rows=[dict(id='1',date='2026-10-20',base_currency='USD',quote_currency='GBP',rate='0.74774741'),
          dict(id='2',date='2026-10-20',base_currency='GBP',quote_currency='USD',rate='1.33735'),
          dict(id='3',date='2026-10-20',base_currency='GBP',quote_currency='GBP',rate='1'),
          dict(id='4',date='2026-10-20',base_currency='XAU',quote_currency='GBP',rate='3246'),
          dict(id='5',date='2026-10-20',base_currency='ILS',quote_currency='GBP',rate='0.2')]
    points=select_rates(rows)
    assert len(DEFAULT_CURRENCIES)==15 and len(points)==2
    assert points[0]['base']=='GBP' and points[0]['quote']=='USD' and points[0]['normalization']['value']=='1.337350000000'
    assert points[1]['normalization']['value']=='0.747747410000'
    with pytest.raises(ValueError,match='Duplicate'):select_rates(rows+[rows[0]])
    with pytest.raises(ValueError,match='identity'):select_rates([rows[2]|{'rate':'0.99'}])
    with pytest.raises(ValueError):select_rates([rows[0]|{'rate':'NaN'}])
    with pytest.raises(ValueError,match='currency ID'):
        select_rates([rows[0]|{'base_currency_id':'2','quote_currency_id':'2'}],source_currency_codes={'1':'USD','2':'GBP'})


def test_native_dataset_replay_and_display_are_tenant_scoped(connection,tmp_path):
    from uuid import uuid4
    from sqlalchemy import select,func
    from security_master_schema import models as m
    from security_master_schema.demo_data import DEMO_IDS as ids
    from tooling.reconciliation_csv.tests.test_reconciliation_bundle import sample,load
    from tooling.reconciliation_csv.seed_reconciliation_bundle import apply_foundation
    from tooling.reconciliation_csv.reconciliation_fx import import_fx
    from market_data.display_access import assert_dataset_display,EvidenceDisplayDenied
    from market_data.rights import load_rights
    from security_master_schema.governance_clock import governance_date
    c=connection;bundle=load(sample(tmp_path));tenant=ids['tenant'];actor=ids['demo_user_account']
    foundation=apply_foundation(c,bundle,tenant,actor,tmp_path/'retained')
    node_type=c.scalar(select(m.reference_node_type.c.reference_node_type_id).where(m.reference_node_type.c.type_code=='FX_PAIR'))
    shared=c.scalar(m.financial_reference_node.insert().values(reference_node_type_id=node_type,internal_code='FXPAIR_GBPSGD',
        canonical_name='Existing GBP/SGD',is_tradable=False).returning(m.financial_reference_node.c.reference_node_id))
    c.execute(m.reference_node_scope.insert().values(reference_node_id=shared,scope_type='SHARED_CANONICAL'))
    before=c.scalar(select(func.count()).select_from(m.market_data_observation))
    args=(c,bundle,tenant,actor,foundation,ids['bank_a_organisation'])
    result=import_fx(*args,selected=('GBP','SGD'))
    assert result['observations']==1 and result['series']==1
    replay=import_fx(*args,selected=('GBP','SGD'))
    assert replay['replayed'] is True and replay['datasetId']==result['datasetId']
    assert c.scalar(select(func.count()).select_from(m.market_data_observation))==before+1
    did=result['datasetId'];assert_dataset_display(c,tenant,{did})
    with pytest.raises(EvidenceDisplayDenied):assert_dataset_display(c,uuid4(),{did})
    assert not load_rights(c,did,'NON_DISPLAY',governance_date()).allowed
    obs=c.execute(select(m.market_data_observation).where(m.market_data_observation.c.dataset_id==did)).mappings().one()
    assert obs['value']==Decimal('1.7') and obs['market_date'].isoformat()=='2026-10-20'
    assert obs['source_timestamp_utc'] is None and obs['source_published_at_utc'] is None
    assert obs['valuation_cut_id'] is None and obs['observed_at_utc'].hour==23
    dims=dict(c.execute(select(m.market_data_series_dimension.c.dimension_code,m.market_data_series_dimension.c.dimension_value)
        .where(m.market_data_series_dimension.c.market_data_series_id==obs['market_data_series_id'])).all())
    assert dims['BASE_CURRENCY']=='GBP' and dims['QUOTE_CURRENCY']=='SGD'
    assert dims['TIMESTAMP_SEMANTICS']=='SOURCE_DATE_ONLY_EOD_BUCKET'
    assert c.scalar(select(m.market_data_series.c.reference_node_id).where(m.market_data_series.c.market_data_series_id==obs['market_data_series_id']))==shared
    c.execute(m.licence_activity_grant.delete().where(m.licence_activity_grant.c.dataset_licence_assignment_id.in_(
        select(m.dataset_licence_assignment.c.dataset_licence_assignment_id).where(m.dataset_licence_assignment.c.dataset_id==did)),
        m.licence_activity_grant.c.activity=='DISPLAY'))
    with pytest.raises(PermissionError):import_fx(*args,selected=('GBP','SGD'))
    assert not load_rights(c,did,'DISPLAY',governance_date()).allowed


def test_inspection_only_direct_rate_cannot_shadow_eligible_inverse(valued):
    from uuid import uuid4
    from sqlalchemy import select
    from security_master_schema import models as m
    from security_master_schema.demo_data import DEMO_IDS as ids
    from valuation.fx import resolve_fx
    c,r,_=valued
    original=dict(c.execute(select(m.market_data_observation).where(m.market_data_observation.c.market_data_observation_id==ids['market_data_observation'])).mappings().one())
    rule=c.execute(select(m.valuation_policy_rule).where(m.valuation_policy_rule.c.valuation_policy_rule_id==ids['valuation_policy_rule'])).mappings().one()
    cut=uuid4()
    c.execute(m.valuation_cut.insert().values(valuation_cut_id=cut,cut_code='INVERSE_'+cut.hex,display_name='Synthetic 16 UTC FX',
        timezone_name='UTC',local_time='16:00',market_calendar_id=rule['market_calendar_id']))
    inverse=uuid4()
    c.execute(m.market_data_series.insert().values(market_data_series_id=inverse,reference_node_id=ids['gbpusd_fx_pair_node'],
        default_dataset_id=original['dataset_id'],series_type='FX_SPOT',value_type='RATE',currency_id=ids['usd_currency'],
        valuation_cut_id=cut,source_system_id='SYNTHETIC_INVERSE',measure_definition_id=c.scalar(select(m.series_measure_definition.c.series_measure_definition_id).where(m.series_measure_definition.c.measure_code=='FX_RATE'))))
    c.execute(m.market_data_series_dimension.insert(),[dict(market_data_series_id=inverse,dimension_code=k,dimension_value=v)
        for k,v in [('BASE_CURRENCY','GBP'),('QUOTE_CURRENCY','USD')]])
    c.execute(m.valuation_policy_rule.insert().values(valuation_policy_id=r.policy_id,rule_sequence=999,subject_type='FX_PAIR',
        series_type='FX_SPOT',value_basis='RAW',market_data_series_id=inverse,pricing_convention='EXPLICIT_TIME',pricing_cut_id=cut,
        market_calendar_id=rule['market_calendar_id'],selection_method='LAST_BEFORE_CUT',max_staleness_business_days=0,allow_inverse_fx=True))
    stamp=r.closing_cutoff.replace(hour=16,minute=0,second=0,microsecond=0)
    c.execute(m.market_data_observation.insert().values(**(original|dict(market_data_observation_id=uuid4(),market_data_series_id=inverse,
        market_date=stamp.date(),value=Decimal(2),market_data_vintage_id=None,observed_at_utc=stamp,received_at_utc=stamp,
        source_published_at_utc=stamp,source_observation_key='INVERSE_'+uuid4().hex))))
    assert resolve_fx(c,r,ids['usd_currency'],ids['gbp_currency'],stamp.date()).rate==Decimal('0.5')
    # A same-tenant private dataset for inspection has no VALUATION entitlement.
    ds=dict(c.execute(select(m.dataset).where(m.dataset.c.dataset_id==original['dataset_id'])).mappings().one());dataset=uuid4()
    c.execute(m.dataset.insert().values(**(ds|dict(dataset_id=dataset,dataset_code='INSPECTION_'+dataset.hex))))
    node=uuid4();kind=c.scalar(select(m.reference_node_type.c.reference_node_type_id).where(m.reference_node_type.c.type_code=='FX_PAIR'))
    c.execute(m.financial_reference_node.insert().values(reference_node_id=node,reference_node_type_id=kind,canonical_name='Synthetic USD/GBP',is_tradable=False))
    c.execute(m.reference_node_scope.insert().values(reference_node_id=node,scope_type='SHARED_CANONICAL'))
    direct=uuid4()
    c.execute(m.market_data_series.insert().values(market_data_series_id=direct,reference_node_id=node,default_dataset_id=dataset,
        series_type='FX_SPOT',value_type='RATE',currency_id=ids['gbp_currency'],source_system_id='INSPECTION_ONLY'))
    c.execute(m.market_data_series_dimension.insert(),[dict(market_data_series_id=direct,dimension_code=k,dimension_value=v)
        for k,v in [('BASE_CURRENCY','USD'),('QUOTE_CURRENCY','GBP')]])
    c.execute(m.market_data_observation.insert().values(**(original|dict(market_data_observation_id=uuid4(),market_data_series_id=direct,
        dataset_id=dataset,market_date=stamp.date(),value=Decimal('0.5'),market_data_vintage_id=None,source_observation_key='DIRECT_'+uuid4().hex))))
    assert resolve_fx(c,r,ids['usd_currency'],ids['gbp_currency'],stamp.date()).rate==Decimal('0.5')
    c.execute(m.market_data_series.update().where(m.market_data_series.c.market_data_series_id==inverse).values(default_dataset_id=dataset))
    assert resolve_fx(c,r,ids['usd_currency'],ids['gbp_currency'],stamp.date()).rate==Decimal('0.5')


from tests.test_valuation_service import valued
