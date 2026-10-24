"""Private price imports preserve quote dimensions and source-to-native mapping."""
from decimal import Decimal
from uuid import uuid4
import pytest
from sqlalchemy import select,func
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from tooling.reconciliation_csv.tests.test_reconciliation_seed import connection


def test_price_normalization_respects_bond_option_swap_and_rate_dimensions():
    from tooling.reconciliation_csv.reconciliation_prices import normalize_prices
    instruments={
        '1':dict(instrument_type='BOND',currency='GBP',price_type='notional'),
        '20265':dict(instrument_type='VANILLA',currency='USD',price_type='unit'),
        '3':dict(instrument_type='DIVER OTC',currency='USD',price_type='unitlev'),
        '1396':dict(instrument_type='INDEX',currency='USD',price_type='notional'),
        '20764':dict(instrument_type='FXFWD',currency='GBP',price_type='notional'),
        '1857':dict(instrument_type='FUND',currency='USD',price_type='unit')}
    rows=[dict(id=k,instrument_id=k,date='2026-10-20',price=v) for k,v in
        [('1','0.9967199999999999'),('20265','12'),('3','-4.6790375828'),('1396','3.9'),('1857','1.0155459999999998'),('20764','0.7508918390497994')]]
    result=normalize_prices(rows,instruments,amc_ids={'1857'})
    by_id={p['sourceId']:p for p in result}
    assert by_id['1']['normalization']['value']=='99.671999999999'
    assert by_id['1']['dimensions']['BOND_PRICE_TYPE']=='CLEAN'
    assert by_id['20265']['normalization']['value']=='12.000000000000'
    assert by_id['20265']['dimensions']['OPTION_PRICE_BASIS']=='PREMIUM_POINTS'
    assert by_id['3']['normalization']['value']=='-4.679037582800'
    assert by_id['3']['dimensions']['SWAP_PRICE_BASIS']=='WHOLE_SWAP_MTM_PER_UNIT'
    assert by_id['1396']['measure']=='RATE' and by_id['1396']['normalization']['value']=='3.900000000000'
    assert by_id['1857']['dimensions']['AMC_PRICE_BASIS']=='UNIT_PRICE'
    assert by_id['20764']['normalization']['value']=='0.750891839049'
    assert by_id['20764']['dimensions']['QUOTE_CONVENTION']=='GBP_PER_USD'
    with pytest.raises(ValueError,match='Duplicate'):normalize_prices(rows+[rows[0]],instruments,amc_ids={'1857'})
    with pytest.raises(ValueError):normalize_prices([rows[1]|{'price':'NaN'}],instruments)
    with pytest.raises(ValueError,match='negative'):normalize_prices([rows[0]|{'price':'-1'}],instruments)


def test_private_native_price_delivery_retains_replay_and_denies_other_tenants(connection,tmp_path):
    import csv
    from datetime import date
    from tooling.reconciliation_csv.tests.test_reconciliation_option import option_bundle
    from tooling.reconciliation_csv.reconciliation import load_bundle
    from tooling.reconciliation_csv.reconciliation_products import seed_products,seed_additional
    from tooling.reconciliation_csv.reconciliation_option import post_option
    from tooling.reconciliation_csv.seed_reconciliation_bundle import apply_foundation
    from tooling.reconciliation_csv.reconciliation_prices import import_prices
    from market_data.display_access import assert_dataset_display,EvidenceDisplayDenied
    from market_data.rights import load_rights
    from security_master_schema.governance_clock import governance_date
    option_bundle(tmp_path)
    rows=[dict(id=k,instrument_id=k,date='2026-10-20',price=v) for k,v in [('10','-4.6790375828'),('1857','1.0155459999999998'),('20265','12'),('1048','3.7324')]]
    with (tmp_path/'SAMPLE-2026-10-20-prices.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    bundle=load_bundle(tmp_path,'SAMPLE',date(2026,10,20),excluded_trade_ids={'exclude'},amc_ids={'1857'})
    c=connection;tenant=ids['tenant'];actor=ids['demo_user_account']
    foundation=apply_foundation(c,bundle,tenant,actor,tmp_path/'evidence')
    seed_products(c,bundle,tenant,actor,foundation);additional=seed_additional(c,bundle,tenant,actor,foundation)
    # The old multiplier-one option must never receive the corrected contract's prices.
    with pytest.raises(ValueError,match='standard option'):import_prices(c,bundle,tenant,actor,foundation,ids['bank_a_organisation'])
    option=post_option(c,bundle,tenant,actor,foundation,{})
    args=(c,bundle,tenant,actor,foundation,ids['bank_a_organisation'])
    before=c.scalar(select(func.count()).select_from(m.market_data_observation))
    result=import_prices(*args);assert result['observations']==4 and result['series']==4
    assert import_prices(*args)['replayed'] is True
    assert c.scalar(select(func.count()).select_from(m.market_data_observation))==before+4
    did=result['datasetId'];assert_dataset_display(c,tenant,{did})
    with pytest.raises(EvidenceDisplayDenied):assert_dataset_display(c,uuid4(),{did})
    assert not load_rights(c,did,'NON_DISPLAY',governance_date()).allowed
    obs=c.execute(select(m.market_data_observation,m.market_data_series.c.reference_node_id)
        .join(m.market_data_series).where(m.market_data_observation.c.dataset_id==did)).mappings().all()
    assert any(r['reference_node_id']==option['instrumentId'] and r['value']==12 for r in obs)
    assert all(r['reference_node_id']!=additional['options']['20265'] for r in obs)
    assert all(r['source_timestamp_utc'] is None and r['source_published_at_utc'] is None and r['valuation_cut_id'] is None for r in obs)
    # Removed rights are not silently recreated by re-import.
    c.execute(m.licence_activity_grant.delete().where(m.licence_activity_grant.c.activity=='DISPLAY',
        m.licence_activity_grant.c.dataset_licence_assignment_id.in_(select(m.dataset_licence_assignment.c.dataset_licence_assignment_id).where(m.dataset_licence_assignment.c.dataset_id==did))))
    with pytest.raises(PermissionError):import_prices(*args)
