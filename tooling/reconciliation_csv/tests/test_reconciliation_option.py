"""Confirmed source option units become real contracts without changing premium."""
from decimal import Decimal
from uuid import uuid4
import pytest
from sqlalchemy import select,func
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from tooling.reconciliation_csv.tests.test_reconciliation_seed import connection


def test_contract_normalization_preserves_premium_and_rejects_fractional_contracts():
    from tooling.reconciliation_csv.reconciliation_option import normalize_option_units
    row=dict(quantity='2000.0',price='23.8',unit_multiplier='1.0',quote_factor='1.0',price_type='unit',trade_currency='USD')
    value=normalize_option_units(row)
    assert value['quantity']=='20' and value['premium']=='23.800000000000'
    assert value['grossPremium']=='47600.000000000000'
    assert value['originalQuantity']=='2000.0' and value['premiumMultiplier']=='100'
    row['quantity']='-2000'
    assert normalize_option_units(row)['quantity']=='-20'
    row['quantity']='2001'
    with pytest.raises(ValueError,match='whole contracts'):normalize_option_units(row)
    row.update(quantity='2000',unit_multiplier='100')
    with pytest.raises(ValueError,match='source units'):normalize_option_units(row)


def option_bundle(tmp_path):
    from tooling.reconciliation_csv.tests.test_reconciliation_products import additional_bundle
    additional_bundle(tmp_path)
    import csv
    from datetime import date
    from tooling.reconciliation_csv.reconciliation import load_bundle
    p=tmp_path/'SAMPLE-2026-10-20-trades.csv'
    with p.open(newline='') as f:rows=list(csv.DictReader(f))
    for r in rows:
        if r['instrument_id']=='20265':r.update(price_type='unit',quote_factor='1',settlement_date='2026-08-14')
    fields=list(dict.fromkeys(k for r in rows for k in r))
    with p.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(rows)
    return load_bundle(tmp_path,'SAMPLE',date(2026,10,20),excluded_trade_ids={'exclude'},amc_ids={'1857'})


def test_source_option_is_replaced_listed_and_booked_once(connection,tmp_path):
    from tooling.reconciliation_csv.seed_reconciliation_bundle import apply_foundation
    from tooling.reconciliation_csv.reconciliation_products import seed_products,seed_additional
    from tooling.reconciliation_csv.reconciliation_option import post_option
    c=connection;bundle=option_bundle(tmp_path)
    tenant=ids['tenant'];actor=ids['demo_user_account']
    foundation=apply_foundation(c,bundle,tenant,actor,tmp_path/'evidence')
    seed_products(c,bundle,tenant,actor,foundation)
    original=seed_additional(c,bundle,tenant,actor,foundation)['options']['20265']
    before=c.scalar(select(func.count()).select_from(m.trade))
    result=post_option(c,bundle,tenant,actor,foundation,{})
    trade=c.execute(select(m.trade).where(m.trade.c.trade_id==result['tradeId'])).mappings().one()
    assert trade['quantity']==20 and trade['quantity_unit']=='CONTRACTS'
    assert trade['execution_price']==Decimal('23.8') and trade['position_effect']=='OPEN'
    assert c.scalar(select(func.count()).select_from(m.trade))==before+1
    import json
    event=json.loads(c.scalar(select(m.trade_lifecycle_event.c.event_payload).where(m.trade_lifecycle_event.c.trade_id==trade['trade_id'])))
    assert event['economics']['grossPremium']=='47600'
    assert event['economics']['terms']['premiumMultiplier']=='100'
    assert c.scalar(select(m.financial_reference_node.c.is_tradable).where(m.financial_reference_node.c.reference_node_id==original)) is False
    assert c.scalar(select(m.option_terms.c.premium_multiplier).where(m.option_terms.c.instrument_node_id==original))==1
    assert post_option(c,bundle,tenant,actor,foundation,{})['tradeId']==result['tradeId']
    assert c.scalar(select(func.count()).select_from(m.trade))==before+1
    from security_master_schema.tenant_workspace import TenantActionForbidden
    with pytest.raises(TenantActionForbidden):post_option(c,bundle,uuid4(),actor,foundation,{})
