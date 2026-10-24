"""Explicit source orientation, never a heuristic based on the rate level."""
from types import SimpleNamespace
from uuid import uuid4
from decimal import Decimal
import pytest
from tooling.reconciliation_csv.tests.test_reconciliation_seed import connection


def test_forward_proposal_uses_confirmed_usd_quantity_and_gbp_per_usd_rate():
    from tooling.reconciliation_csv.reconciliation_forwards import forward_proposal
    bundle=SimpleNamespace(digest='b'*64)
    row=dict(instrument_id='20764',trade_id='example',quantity='-567000',price='0.747406499446919',
        trade_currency='USD',settlement_date='2026-10-23')
    instrument=dict(short_name='Example forward',effective_date='2026-09-21',maturity_date='2026-10-23',cash_settlement_date='2026-10-23')
    currencies={'USD':uuid4(),'GBP':uuid4()}
    request,proof=forward_proposal(bundle,instrument,row,currencies,uuid4(),uuid4(),base='USD',quote='GBP')
    assert request.base_currency_id==currencies['USD'] and request.quote_currency_id==currencies['GBP']
    assert request.quote_convention=='GBP_PER_USD' and request.agreed_forward_rate==Decimal('0.747406499446')
    assert proof['sourceValue']=='0.747406499446919'
    row['trade_currency']='GBP'
    with pytest.raises(ValueError,match='quantity currency'):forward_proposal(bundle,instrument,row,currencies,uuid4(),uuid4(),base='USD',quote='GBP')


def test_forward_native_approval_booking_and_replay(connection,tmp_path):
    import csv
    from sqlalchemy import select,func
    from security_master_schema import models as m
    from security_master_schema.demo_data import DEMO_IDS as ids
    from tooling.reconciliation_csv.tests.test_reconciliation_bundle import sample,load
    from tooling.reconciliation_csv.seed_reconciliation_bundle import apply_foundation,apply_confirmed_company
    from tooling.reconciliation_csv.reconciliation_forwards import post_forwards
    source=sample(tmp_path)
    for kind in ('trades','all_instruments','currencies'):
        path=source/f'SAMPLE-2026-10-20-{kind}.csv'
        rows=list(csv.DictReader(path.read_text().splitlines()))
        if kind=='trades':rows[0].update(price='0.75',quantity='2',trade_currency='USD',settlement_date='2026-10-23')
        elif kind=='all_instruments':rows[0].update(instrument_type='FXFWD',short_name='Synthetic USD GBP forward',
            effective_date='2026-10-01',maturity_date='2026-10-23',cash_settlement_date='2026-10-23')
        else:rows.append(dict(currency_id='1',currency='USD'))
        fields=list(dict.fromkeys(k for r in rows for k in r))
        with path.open('w',newline='') as handle:
            writer=csv.DictWriter(handle,fieldnames=fields);writer.writeheader();writer.writerows(rows)
    bundle=load(source);c=connection;tenant=ids['tenant'];actor=ids['demo_user_account']
    foundation=apply_foundation(c,bundle,tenant,actor,tmp_path/'retained')
    company=apply_confirmed_company(c,bundle,tenant,actor,foundation,'21','Example custodian')
    args=(c,bundle,tenant,actor,foundation,{'21':company},{},{'10':('USD','GBP')})
    result=post_forwards(*args)
    assert len(result)==1 and post_forwards(*args)==result
    trades=c.execute(select(m.trade).where(m.trade.c.strategy_id==foundation['strategyId'])).mappings().all()
    assert len(trades)==1 and trades[0]['quantity']==2 and trades[0]['execution_price']==Decimal('0.75')
    assert trades[0]['price_currency_id']==ids['gbp_currency']
