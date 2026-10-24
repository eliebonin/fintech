"""Cash snapshots stay separate by source account and exact value date."""
from decimal import Decimal
from sqlalchemy import select,func
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from tooling.reconciliation_csv.tests.test_reconciliation_seed import connection
from tooling.reconciliation_csv.tests.test_reconciliation_bundle import sample,load


def test_account_key_does_not_merge_wash_or_third_party_balances():
    from tooling.reconciliation_csv.reconciliation_cash import account_key
    row=dict(counterparty_id='21',agent='NT',instrument_id='1662',comment='US DOLLARS',trade_currency='USD')
    assert len({account_key(row),account_key(row|{'agent':'IB/Misc'}),account_key(row|{'comment':'DERIVATIVES WASH'})})==3


def test_cash_posting_keeps_dated_balances_and_replays_without_new_revisions(connection,tmp_path):
    from tooling.reconciliation_csv.seed_reconciliation_bundle import apply_foundation,apply_confirmed_company
    from tooling.reconciliation_csv.reconciliation_cash import post_cash
    c=connection;bundle=load(sample(tmp_path));tenant=ids['tenant'];actor=ids['demo_user_account']
    foundation=apply_foundation(c,bundle,tenant,actor,tmp_path/'retained')
    company=apply_confirmed_company(c,bundle,tenant,actor,foundation,'21','Example custodian')
    result=post_cash(c,bundle,tenant,actor,foundation,{'21':company})
    assert result['snapshots']==1 and result['accounts']==1
    assert post_cash(c,bundle,tenant,actor,foundation,{'21':company})==result
    rows=c.execute(select(m.cash_balance).where(m.cash_balance.c.strategy_id==foundation['strategyId'])).mappings().all()
    assert len(rows)==1 and rows[0]['amount']==Decimal(5) and str(rows[0]['balance_as_of_date'])=='2026-10-20'
    assert c.scalar(select(func.count()).select_from(m.trade).where(m.trade.c.strategy_id==foundation['strategyId']))==0
