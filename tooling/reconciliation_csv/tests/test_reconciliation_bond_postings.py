"""Bond imports exercise native booking, not direct trade-table insertion."""
import csv
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4
import pytest
from sqlalchemy import select,func,text
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from tooling.reconciliation_csv.tests.test_reconciliation_seed import connection


@pytest.mark.parametrize('quantity,cash_accrual,native_accrual',[
    ('150000','-1131.11','1131.11'),('-150000','1131.11','1131.11'),
    ('150000','25','-25')])
def test_clean_quote_keeps_nominal_and_translates_cash_accrual_sign(quantity,cash_accrual,native_accrual):
    from tooling.reconciliation_csv.reconciliation_bond_postings import bond_booking_request
    row=dict(trade_id='bond-1',instrument_id='40',quantity=quantity,price='0.9967199999999999',
        accrued_interests=cash_accrual,trade_currency='GBP',trade_datetime_utc='2026-10-02 11:00:00',
        settlement_date='2026-10-05',price_type='notional',par_value='1',denomination='1',
        quote_factor='1',unit_multiplier='1')
    context=SimpleNamespace(kind='BOND',currency='GBP',terms_fingerprint='a'*64,coupon_type='FIXED',
        convention=SimpleNamespace(quantity_unit='NOMINAL',price_basis='PCT_OF_PAR',quote_factor=Decimal(100)))
    request,evidence=bond_booking_request(row,uuid4(),uuid4(),uuid4(),uuid4(),context,[])
    assert request.quantity==Decimal('150000') and request.execution_price==Decimal('99.671999999999')
    assert request.price_type=='CLEAN' and request.accrued_interest_amount==Decimal(native_accrual)
    assert request.side==('BUY' if quantity[0]!='-' else 'SELL')
    assert evidence['price']['sourceValue']=='0.9967199999999999'
    assert evidence['accrual']['sourceValue']==cash_accrual
    row['accrued_interests']=''
    with pytest.raises(ValueError,match='accrued'):bond_booking_request(row,uuid4(),uuid4(),uuid4(),uuid4(),context,[])
    context.coupon_type='ZERO'
    request,evidence=bond_booking_request(row,uuid4(),uuid4(),uuid4(),uuid4(),context,[])
    assert request.accrued_interest_amount==0 and evidence['accrual']['basis']=='ZERO_COUPON_TERMS'


def bond_bundle(tmp_path):
    from tooling.reconciliation_csv.tests.test_reconciliation_bundle import sample
    from tooling.reconciliation_csv.reconciliation import load_bundle
    p=sample(tmp_path)
    tables={
        'trades':[dict(trade_id='bond-buy',instrument_id='40',strategy_id='2',trade_type='Investment',
            trade_datetime_utc='2026-10-16 11:00:00',settlement_date='2026-10-19',quantity='150000',
            price='0.9802052299999999',trade_currency='GBP',counterparty_id='21',price_type='notional',
            par_value='1',denomination='1',quote_factor='1',unit_multiplier='1',accrued_interests=''),
            dict(trade_id='bond-sell',instrument_id='40',strategy_id='2',trade_type='Investment',
            trade_datetime_utc='2026-10-20 11:00:00',settlement_date='2026-10-21',quantity='-25000',
            price='0.981',trade_currency='GBP',counterparty_id='21',price_type='notional',
            par_value='1',denomination='1',quote_factor='1',unit_multiplier='1',accrued_interests='')],
        'all_instruments':[dict(instrument_id='40',instrument_type='BOND',currency='GBP',isin='GB00TEST0040',maturity_date='2027-02-08')],
        'bonds':[dict(instrument_id='40',id_isin='GB00TEST0040',security_des='Synthetic UK bill',
            cpn_typ='ZERO COUPON',cpn='0',issue_dt='2026-10-19',maturity='2027-02-08',crncy='GBP',
            redemp_val='100',cpn_freq='',day_cnt_des='',px_dirty_clean='CLEAN',par_amt='0.01')],
        'prices':[],'cash_balances':[]}
    for name,rows in tables.items():
        with (p/f'SAMPLE-2026-10-20-{name}.csv').open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]) if rows else ['instrument_id'])
            writer.writeheader();writer.writerows(rows)
    return load_bundle(p,'SAMPLE',date(2026,10,20))


def test_bond_import_versions_terms_preserves_issue_date_and_books_exactly_once(connection,tmp_path):
    from tooling.reconciliation_csv.seed_reconciliation_bundle import apply_foundation
    from tooling.reconciliation_csv.reconciliation_bonds import stage_bonds
    from tooling.reconciliation_csv.reconciliation_bond_postings import post_bonds
    c=connection;bundle=bond_bundle(tmp_path);tenant=ids['tenant'];actor=ids['demo_user_account']
    foundation=apply_foundation(c,bundle,tenant,actor,tmp_path/'retained')
    node=stage_bonds(c,bundle,tenant,actor,foundation,approve_ready=True)[0]['instrumentId']
    before=c.scalar(select(func.count()).select_from(m.trade))
    result=post_bonds(c,bundle,tenant,actor,foundation,{})
    assert result['booked']==2 and result['failed']==0,result
    assert result['sourceResetFlowsExcludedFromThisBatch']==0
    assert c.scalar(select(func.count()).select_from(m.trade))==before+2
    terms=c.execute(select(m.bond_terms).where(m.bond_terms.c.instrument_node_id==node).order_by(m.bond_terms.c.sequence_no)).mappings().all()
    assert len(terms)==2 and terms[0]['par_amount'] is None and not terms[0]['is_current']
    assert terms[1]['par_amount']==Decimal('.01') and terms[1]['effective_from']==date(2026,10,16)
    definitions=c.execute(select(m.instrument_definition_version).where(m.instrument_definition_version.c.instrument_node_id==node)
        .order_by(m.instrument_definition_version.c.sequence_no)).mappings().all()
    assert len(definitions)==2 and definitions[0]['effective_from']==date(2026,10,19)
    assert definitions[0]['status']=='SUPERSEDED' and not definitions[0]['is_current']
    assert definitions[1]['effective_from']==date(2026,10,16) and definitions[1]['is_current']
    assert c.scalar(select(m.instrument_dates.c.issue_date).where(m.instrument_dates.c.instrument_node_id==node))==date(2026,10,19)
    events=c.execute(select(m.trade_lifecycle_event.c.event_payload).join(m.trade).where(m.trade.c.strategy_id==foundation['strategyId'],m.trade_lifecycle_event.c.event_type=='BOOKED')).scalars().all()
    import json
    assert all(json.loads(raw)['economics']['bondDetails']['priceType']=='CLEAN' for raw in events)
    assert post_bonds(c,bundle,tenant,actor,foundation,{})['replayed']==2
    c.execute(text('SET CONSTRAINTS ALL IMMEDIATE'))
    assert c.scalar(select(func.count()).select_from(m.bond_terms).where(m.bond_terms.c.instrument_node_id==node))==2
    assert c.scalar(select(func.count()).select_from(m.trade))==before+2
    from security_master_schema.tenant_workspace import TenantActionForbidden
    with pytest.raises(TenantActionForbidden):post_bonds(c,bundle,uuid4(),actor,foundation,{})
    # Governance drift must not be silently repaired on a later replay.
    c.execute(m.bond_terms.update().where(m.bond_terms.c.instrument_node_id==node,m.bond_terms.c.is_current).values(par_amount=1))
    with pytest.raises(ValueError,match='changed'):post_bonds(c,bundle,tenant,actor,foundation,{})


def test_definition_retirement_requires_replacement_and_never_changes_old_facts(connection):
    from sqlalchemy.exc import DBAPIError
    c=connection;node=ids['bond_instrument_node']
    definition=c.execute(select(m.instrument_definition_version).where(m.instrument_definition_version.c.instrument_node_id==node,
        m.instrument_definition_version.c.is_current)).mappings().one()
    with pytest.raises(DBAPIError,match='replacement'):
        with c.begin_nested():
            c.execute(m.instrument_definition_version.update().where(m.instrument_definition_version.c.instrument_definition_version_id==definition['instrument_definition_version_id']).values(is_current=False,status='SUPERSEDED'))
            c.execute(text('SET CONSTRAINTS ALL IMMEDIATE'))
    with pytest.raises(DBAPIError,match='immutable'):
        with c.begin_nested():
            c.execute(m.instrument_definition_version.update().where(m.instrument_definition_version.c.instrument_definition_version_id==definition['instrument_definition_version_id']).values(effective_from=date(2020,1,1)))
