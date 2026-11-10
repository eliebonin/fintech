"""Bond monetary values consume maintained stocks, never daily earnings as a stock."""
from uuid import uuid4
from decimal import Decimal as D
from tests.test_valuation_service import valued
from tests.test_economic_pnl_acceptance import add_bond
from tests.test_measure_inputs import preview
from tests.test_accrued_balance_integration import daily
from valuation.balance_history import record_balance_input,refresh_history
from valuation.balance_history_contracts import BalanceInputCreate,BalanceHistoryRefresh
from security_master_schema.demo_data import DEMO_IDS as ids


def maintain(c,r,amount='2000'):
    record_balance_input(c,r.tenant_id,ids['demo_user_account'],BalanceInputCreate(strategyId=r.strategy_id,
        instrumentId=ids['bond_instrument_node'],currencyId=ids['gbp_currency'],valueDate=r.closing_cutoff.date(),
        closingBalance=amount,sourceReference='Synthetic assessed position stock',reason='Reviewed closing stock'),uuid4().hex)
    return refresh_history(c,r.tenant_id,ids['demo_user_account'],BalanceHistoryRefresh(strategyId=r.strategy_id,
        fromDate=r.closing_cutoff.date(),toDate=r.closing_cutoff.date()),uuid4().hex)


def bond_row(c,r):
    return next(x for x in preview(c,r)['items'] if x['instrumentType']=='BOND')


def test_clean_market_value_uses_maintained_balance_with_exact_history_proof(valued):
    c,r,trade=valued;add_bond(c,r,trade);build=maintain(c,r)
    row=bond_row(c,r)
    assert row['measures']['marketValue']['localAmount']=='103000'
    assert row['measures']['marketValue']['strategyAmount']=='103000'
    assert row['measures']['referenceNotional']['localAmount']=='100000'
    proof=row['evidence']['selections']['accruedBalance']
    assert proof['buildId']==str(build['build_id']) and proof['sourceStatus']=='CURRENT'
    assert proof['valueDate']==r.closing_cutoff.date().isoformat()
    assert len(proof['sourceProofHash'])==64
    assert 'buildSourceProof' not in proof and 'historyEvidence' not in proof


def test_daily_earnings_alone_never_become_a_closing_stock(valued):
    c,r,trade=valued;add_bond(c,r,trade);daily(c,r,r.closing_cutoff.date(),amount='10')
    row=bond_row(c,r)
    assert row['measures']['marketValue']['localAmount'] is None
    assert 'maintained' in row['evidence']['issues']['accruedBalance'].lower()
    assert row['measures']['referenceNotional']['localAmount']=='100000'


def test_stale_stock_is_not_used_until_explicit_history_rebuild(valued):
    c,r,trade=valued;add_bond(c,r,trade);maintain(c,r)
    daily(c,r,r.closing_cutoff.date(),amount='10')
    row=bond_row(c,r)
    assert row['measures']['marketValue']['localAmount'] is None
    assert 'stale' in row['evidence']['issues']['accruedBalance'].lower()
    refresh_history(c,r.tenant_id,ids['demo_user_account'],BalanceHistoryRefresh(strategyId=r.strategy_id,
        fromDate=r.closing_cutoff.date(),toDate=r.closing_cutoff.date()),uuid4().hex)
    assert bond_row(c,r)['measures']['marketValue']['localAmount']=='103000'


def test_instrument_stock_is_not_duplicated_between_two_listing_positions(valued):
    c,r,trade=valued;add_bond(c,r,trade)
    from sqlalchemy import select
    from security_master_schema import models as m
    # The shared fixture helper uses sequence 90; reserve it for its second
    # distinct listing without changing either subject-specific rule's meaning.
    c.execute(m.valuation_policy_rule.update().where(m.valuation_policy_rule.c.valuation_policy_id==r.policy_id,m.valuation_policy_rule.c.rule_sequence==90).values(rule_sequence=91))
    add_bond(c,r,trade);maintain(c,r)
    rows=[x for x in preview(c,r)['items'] if x['instrumentType']=='BOND']
    assert len(rows)==2
    assert all(row['measures']['marketValue']['localAmount'] is None for row in rows)
    assert all('duplicated' in row['evidence']['issues']['accruedBalance'] for row in rows)


def test_frozen_zero_coupon_terms_allow_clean_value_without_inventing_interest(valued):
    c,r,trade=valued;add_bond(c,r,trade,coupon_type='ZERO')
    row=bond_row(c,r)
    assert row['measures']['marketValue']['localAmount']=='101000'
    assert row['evidence']['selections']['accruedBalance']['basis']=='FROZEN_ZERO_COUPON_TERMS'


def test_an_explicit_zero_stock_is_available_and_differs_from_missing(valued):
    c,r,trade=valued;add_bond(c,r,trade);maintain(c,r,amount='0')
    row=bond_row(c,r)
    assert row['measures']['marketValue']['localAmount']=='101000'
    assert row['evidence']['selections']['accruedBalance']['sourceStatus']=='CURRENT'
    assert D(row['evidence']['selections']['accruedBalance']['amount'])==0


def test_a_current_but_unassessed_history_row_remains_unavailable(valued):
    c,r,trade=valued;add_bond(c,r,trade)
    refresh_history(c,r.tenant_id,ids['demo_user_account'],BalanceHistoryRefresh(strategyId=r.strategy_id,
        fromDate=r.closing_cutoff.date(),toDate=r.closing_cutoff.date()),uuid4().hex)
    row=bond_row(c,r)
    assert row['measures']['marketValue']['localAmount'] is None
    assert 'not assessed' in row['evidence']['issues']['accruedBalance']
