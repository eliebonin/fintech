"""Per-trade earned amounts aggregate once per bond/date/currency, never stock."""
from types import SimpleNamespace
import pytest
from tooling.reconciliation_csv.tests.test_reconciliation_seed import connection


def test_daily_source_interest_is_aggregated_without_inventing_missing_days():
    from tooling.reconciliation_csv.reconciliation_accruals import aggregate_accruals
    rows=[dict(trade_id='a',instrument_id='10',value_date='2026-10-20',trade_daily_accrual_amount='2.12'),
          dict(trade_id='b',instrument_id='10',value_date='2026-10-20',trade_daily_accrual_amount='-0.10')]
    bundle=SimpleNamespace(positions=[dict(trade_id='a',instrument_id='10',trade_currency='GBP'),
        dict(trade_id='b',instrument_id='10',trade_currency='GBP')],tables={'accrued_interests':rows})
    result=aggregate_accruals(bundle)
    assert len(result)==1 and result[0]['normalization']['value']=='2.020000000000'
    assert result[0]['valueDate']=='2026-10-20' and result[0]['currency']=='GBP'
    assert result[0]['originalRows']==rows
    bundle.tables['accrued_interests']=rows+[rows[0]]
    with pytest.raises(ValueError,match='Duplicate'):aggregate_accruals(bundle)


def test_native_daily_interest_posting_and_replay(connection,tmp_path):
    from tooling.reconciliation_csv.tests.test_reconciliation_bundle import sample,load
    from tooling.reconciliation_csv.seed_reconciliation_bundle import apply_foundation
    from apps.reference_api.contracts import BondProposalRequest
    from apps.reference_api.repository import submit_bond_proposal,decide_bond_proposal
    from security_master_schema.demo_data import DEMO_IDS as ids
    from valuation import tables as t
    from sqlalchemy import select
    from tooling.reconciliation_csv.reconciliation_accruals import post_accruals
    source=sample(tmp_path)
    path=source/'SAMPLE-2026-10-20-all_instruments.csv';path.write_text(path.read_text().replace('10,FUND,','10,BOND,'))
    (source/'SAMPLE-2026-10-20-accrued_interests.csv').write_text('trade_id,value_date,instrument_id,trade_daily_accrual_amount\nopen,2026-10-20,10,2.12\n')
    bundle=load(source);c=connection;tenant=ids['tenant'];actor=ids['demo_user_account']
    foundation=apply_foundation(c,bundle,tenant,actor,tmp_path/'retained')
    request=BondProposalRequest(canonicalName='Synthetic interest bond',baseCurrencyId=ids['gbp_currency'],effectiveFrom='2026-01-01',
        issueDate='2026-01-01',maturityDate='2027-01-01',couponType='ZERO',parAmount='100',redemptionAmountPerPar='100',
        submissionMode='AUTOMATED',sourceSystemId=foundation['sourceId'],sourceExternalId='10',sourceNamespace='SYNTHETIC_INTEREST',
        idempotencyKey='synthetic-interest')
    proposal=submit_bond_proposal(c,tenant,actor,request)
    decide_bond_proposal(c,tenant,actor,proposal.proposal_id,'APPROVED','Synthetic imported assessed interest')
    result=post_accruals(c,bundle,tenant,actor,foundation)
    assert result=={'sourceRows':1,'dailyBondInputs':1}
    assert post_accruals(c,bundle,tenant,actor,foundation)==result
    rows=c.execute(select(t.accrual_input).where(t.accrual_input.c.strategy_id==foundation['strategyId'])).mappings().all()
    assert len(rows)==1 and str(rows[0]['daily_earned_interest'])=='2.120000000000'
