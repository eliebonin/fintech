"""Known reset references post dated flows; unknown links never become positions."""
from types import SimpleNamespace
from uuid import uuid4
from tooling.reconciliation_csv.tests.test_reconciliation_seed import connection


def test_reset_mapping_never_invents_an_instrument_for_missing_references():
    from tooling.reconciliation_csv.reconciliation_flows import mapped_flows
    node=uuid4()
    bundle=SimpleNamespace(flows=[dict(trade_id='known',reference_instrument_id='10.0'),
        dict(trade_id='missing',reference_instrument_id=''),dict(trade_id='closed',reference_instrument_id='99')])
    known,blocked=mapped_flows(bundle,{'10':node})
    assert [(r['trade_id'],n) for r,n in known]==[('known',node)]
    assert {r['sourceTradeId'] for r in blocked}=={'missing','closed'}


def test_native_reset_is_dated_income_and_replay_does_not_duplicate_it(connection,tmp_path):
    import csv
    from sqlalchemy import select,func
    from security_master_schema import models as m
    from security_master_schema.demo_data import DEMO_IDS as ids
    from tooling.reconciliation_csv.tests.test_reconciliation_bundle import sample,load
    from tooling.reconciliation_csv.seed_reconciliation_bundle import apply_foundation
    from tests.test_amc import draft
    from apps.reference_api.amc_contracts import AmcProposalRequest
    from apps.reference_api.product_booking import submit_proposal,decide_proposal
    from tooling.reconciliation_csv.reconciliation_flows import post_flows
    source=sample(tmp_path);path=source/'SAMPLE-2026-10-20-trades.csv'
    rows=list(csv.DictReader(path.read_text().splitlines()));rows[1]['reference_instrument_id']='10'
    with path.open('w',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(rows[0])+['reference_instrument_id']);writer.writeheader();writer.writerows(rows)
    bundle=load(source);c=connection;tenant=ids['tenant'];actor=ids['demo_user_account']
    foundation=apply_foundation(c,bundle,tenant,actor,tmp_path/'retained')
    proposal=submit_proposal(c,tenant,actor,AmcProposalRequest.model_validate(draft()))
    node=decide_proposal(c,tenant,actor,proposal.proposal_id,'APPROVED','Synthetic reset reference').reference_node_id
    args=(c,bundle,tenant,actor,foundation)
    result=post_flows(*args,nodes={'10':node})
    assert result['postedFlows']==1 and result['unpostedFlows']==0
    assert post_flows(*args,nodes={'10':node})==result
    rows=c.execute(select(m.trade).where(m.trade.c.strategy_id==foundation['strategyId'])).mappings().all()
    assert len(rows)==1 and rows[0]['trade_type']=='RESET' and rows[0]['price_basis']=='CASH_AMOUNT'
    assert str(rows[0]['trade_datetime_utc'].date())=='2026-10-20' and rows[0]['quantity_unit']=='CURRENCY_AMOUNT'
    assert c.scalar(select(func.count()).select_from(m.cash_balance).where(m.cash_balance.c.strategy_id==foundation['strategyId']))==0
