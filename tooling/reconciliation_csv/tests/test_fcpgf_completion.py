"""Synthetic metadata completion; supplied financial inputs remain separate."""
from types import SimpleNamespace
from uuid import uuid4
from datetime import date
from dataclasses import replace
from sqlalchemy import select,func
from .test_reconciliation_seed import connection
from .test_reconciliation_bundle import sample,load


def test_mock_autocall_is_valid_complete_and_explicitly_synthetic():
    from tooling.reconciliation_csv.fcpgf_instruments import autocall_request
    result=autocall_request(SimpleNamespace(digest='abc'),dict(instrument_id='4',short_name='Test',maturity_date='2030-10-20'),{},
        '2026-01-01',uuid4(),uuid4(),uuid4(),uuid4(),uuid4())
    assert 'SYNTHETIC' in result.canonical_name
    assert result.product_subtype=='AUTOCALL'
    assert result.maturity_date==date(2030,10,20)
    assert sum(r.condition_role=='AUTOCALL' for r in result.rows)==4
    assert sum(r.condition_role=='FINAL_REDEMPTION' for r in result.rows)==1
    assert result.underlyings[0].initial_fixing==100
    assert result.source_system_id is not None


def test_whole_swap_marks_and_eur_forward_orientation_are_not_reinterpreted():
    from tooling.reconciliation_csv.reconciliation_prices import normalize_prices
    rows=[dict(id='1',instrument_id='1',date='2026-10-20',price='-0.01'),dict(id='2',instrument_id='2',date='2026-10-20',price='0.84'),dict(id='3',instrument_id='3',date='2026-10-20',price='120')]
    ins={'1':dict(instrument_type='EQUITY OTC',price_type='notional',currency='GBP'),
        '2':dict(instrument_type='FXFWD',price_type='unit',currency='GBP'),'3':dict(instrument_type='FUND',price_type='unit',currency='GBP')}
    p=normalize_prices(rows,ins,forward_orientations={'2':('EUR','GBP')})
    assert p[0]['seriesType']=='MARK' and p[0]['normalization']['value']=='-0.010000000000'
    assert p[1]['dimensions']['QUOTE_CONVENTION']=='GBP_PER_EUR'
    assert p[2]['seriesType']=='NAV'


def test_missing_bond_accrual_completion_preserves_supplied_and_signed_values():
    from decimal import Decimal
    from tooling.reconciliation_csv.fcpgf_bond_completion import estimated_settlement_accrual
    bond=dict(cpn='4',cpn_freq='2',maturity='2027-01-01',issue_dt='2020-01-01',int_acc_dt='2020-01-01')
    row=dict(quantity='1000',settlement_date='2026-07-11',accrued_interests='')
    estimate=estimated_settlement_accrual(row,bond)
    assert estimate['estimated'] and estimate['periodStart']=='2026-07-01'
    assert Decimal(estimate['value'])==Decimal('-1.086956521739')
    assert row['accrued_interests']==''
    assert estimated_settlement_accrual(dict(row,accrued_interests='-99'),bond) is None
    assert estimated_settlement_accrual(dict(row,quantity='-1000'),bond)['value']=='1.086956521739'
    assert estimated_settlement_accrual(row,dict(bond,cpn='0'))==dict(value='0',method='SOURCE_ZERO_COUPON_RATE',estimated=False)


def test_extended_policy_uses_nav_date_for_funds_without_changing_other_products():
    from tooling.reconciliation_csv.reconciliation_eligibility import build_policy
    types={kind:uuid4() for kind in ('BOND','ACTIVELY_MANAGED_CERTIFICATE','OPTION','SWAP','FX_FORWARD','FUND_SHARE_CLASS')}
    args=(*[uuid4() for _ in range(5)],date(2026,9,21),types)
    nav_calendar=uuid4()
    original=build_policy(*args);extended=build_policy(*args,include_fund_nav=True,fund_nav_calendar_id=nav_calendar)
    assert len(extended.rules)==len(original.rules)+1
    assert extended.rules[:-1]==original.rules
    rule=extended.rules[-1]
    assert rule.series_type=='NAV' and rule.pricing_convention=='NAV_DATE'
    assert rule.instrument_type_id==types['FUND_SHARE_CLASS']
    assert rule.pricing_date_rule=='SAME_DAY' and rule.pricing_cut_id is None
    assert rule.market_calendar_id==nav_calendar and rule.market_calendar_id!=args[2]


def test_native_fund_seed_has_consistent_private_definitions_and_replay(connection,tmp_path,monkeypatch):
    from security_master_schema import models as m
    from security_master_schema.demo_data import DEMO_IDS as ids
    from tooling.reconciliation_csv.seed_reconciliation_bundle import apply_foundation
    from tooling.reconciliation_csv.fcpgf_instruments import seed_funds
    c=connection;b=load(sample(tmp_path));tenant=ids['tenant'];actor=ids['demo_user_account']
    tables=dict(b.tables)
    tables['all_instruments']=[dict(r,long_name='Synthetic test share class',short_name='Synthetic',isin='') for r in tables['all_instruments']]
    tables['funds']=[dict(instrument_id='10',launched_date='2020-01-01',fund_name='Synthetic fund',class_code='GBP_ACC',is_distribution='False')]
    b=replace(b,tables=tables)
    foundation=apply_foundation(c,b,tenant,actor,tmp_path/'retained')
    # Receipt is retained explicitly; the synthetic test's original fixture has
    # no funds CSV, so reuse its retained instrument receipt for the seed proof.
    old=c.execute(select(m.source_payload).where(m.source_payload.c.integration_source_system_id==foundation['sourceId'])).mappings().first()
    fields={k:v for k,v in old.items() if k not in {'source_payload_id','received_at_utc'}}
    fields['external_message_reference']=b.digest+':funds';c.execute(m.source_payload.insert().values(**fields))
    before=c.scalar(select(func.count()).select_from(m.trade))
    nodes,listings=seed_funds(c,b,tenant,actor,foundation)
    assert seed_funds(c,b,tenant,actor,foundation)==(nodes,listings)
    assert c.scalar(select(func.count()).select_from(m.trade))==before
    from trading.cash_reference import load_cash_booking_listing
    context=load_cash_booking_listing(c,tenant,listings['10'],date(2026,10,19))
    assert context['booking_snapshot']['productBasis']=='FUND'
    assert context['booking_snapshot']['quantityUnit']=='UNITS'
    from tooling.reconciliation_csv import fcpgf_import as operator
    from tooling.reconciliation_csv.seed_reconciliation_bundle import apply_confirmed_company
    from decimal import Decimal
    monkeypatch.setattr(operator,'PROPERTIES',{})
    party=apply_confirmed_company(c,b,tenant,actor,foundation,'21','Synthetic source party',confirmed=False)
    opening=dict(b.positions[0],trade_id='fund-buy',quantity='20.25',price='100')
    sale=dict(opening,trade_id='fund-sell',quantity='-7.25',price='101',trade_datetime_utc='2026-10-20T12:00:00+00:00')
    invalid=dict(opening,trade_id='fund-transfer',quantity='10',price='0')
    bookable=replace(b,positions=[opening,sale,invalid])
    first=operator.book_funds(c,bookable,foundation,nodes,listings,{'21':party})
    assert first['fundTrades']==2 and len(first['unpostedFundTrades'])==1
    assert operator.book_funds(c,bookable,foundation,nodes,listings,{'21':party})==first
    quantities=list(c.scalars(select(m.trade.c.quantity).where(m.trade.c.strategy_id==foundation['strategyId'])))
    assert sorted(quantities)==[Decimal('-7.25'),Decimal('20.25')]
    assert sum(quantities)==13
