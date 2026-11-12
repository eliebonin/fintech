"""Expiry, trading and settlement are distinct sourced deadlines."""
from datetime import date,datetime,timezone
import pytest


def test_independent_option_notification_contract():
 from uuid import uuid4
 from lifecycle.worklist_contracts import WorklistQuery
 from lifecycle.assistance_contracts import AssistanceChange
 assert WorklistQuery(fromDate='2026-01-01',toDate='2028-01-01',eventType='OPTION_EXPIRY').eventType=='OPTION_EXPIRY'
 assert AssistanceChange(strategyId=uuid4(),eventType='OPTION_EXPIRY',selectedTier=1,expectedRevision=0,expectedSubscriptionRevision=0,reason='Option notifications').eventType=='OPTION_EXPIRY'


def test_option_milestones_do_not_assume_expiry_or_settlement_lag():
 from lifecycle.worklist_options import option_milestones
 cutoff=datetime(2027,9,16,21,tzinfo=timezone.utc)
 rows=option_milestones(dict(last_trading_at_utc=cutoff),dict(expiry_date=date(2027,9,17)))
 assert [(r['kind'],r['date']) for r in rows]==[('LAST_TRADE',date(2027,9,16)),('EXPIRY',date(2027,9,17))]
 assert rows[0]['atUtc']==cutoff and rows[1]['atUtc'] is None
 missing=option_milestones({}, {})
 assert missing==[dict(kind='SOURCE_REVIEW',date=None,atUtc=None)]
 rows=option_milestones({},dict(expiry_date=date(2027,9,17),final_settlement_date=date(2027,9,20)))
 assert [r['kind'] for r in rows]==['EXPIRY','FINAL_SETTLEMENT']


@pytest.mark.parametrize('stamp,status',[('2027-09-16T20:59:59+00:00','UPCOMING'),('2027-09-16T21:00:00+00:00','DUE'),('2027-09-16T21:00:01+00:00','OVERDUE')])
def test_shared_exact_deadline_state(stamp,status):
 from lifecycle.worklist_holdings import milestone_state
 row=dict(date=date(2027,9,16),atUtc=datetime(2027,9,16,21,tzinfo=timezone.utc))
 assert milestone_state(row,datetime.fromisoformat(stamp))[0]==status


def test_display_and_comparison_never_round_contract_decimals():
 from lifecycle.worklist_options import _number
 assert _number('123456789012345678901234567890.123456789012')=='123456789012345678901234567890.123456789012'
 assert _number('100.0000')=='100' and _number('-0.000')=='0'
