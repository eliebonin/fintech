"""Sourced milestones remain distinct; dates never imply financial execution."""
from datetime import date,datetime,timezone
import pytest


def test_query_and_assistance_support_futures_notifications():
 from lifecycle.worklist_contracts import WorklistQuery
 from lifecycle.assistance_contracts import AssistanceChange
 from uuid import uuid4
 assert WorklistQuery(fromDate='2026-10-01',toDate='2026-12-31',eventType='FUTURE_EXPIRY').eventType=='FUTURE_EXPIRY'
 assert AssistanceChange(strategyId=uuid4(),eventType='FUTURE_EXPIRY',selectedTier=1,expectedRevision=0,expectedSubscriptionRevision=0,reason='Notify Ops').selectedTier==1


def test_source_milestones_do_not_invent_expiry_or_notice():
 from lifecycle.worklist_futures import contract_milestones
 source=dict(lastTradingAtUtc='2026-12-18T14:30:00Z',finalSettlementDate='2026-12-21',settlementMethod='CASH')
 rows=contract_milestones(source,None)
 assert [(r['kind'],r['date']) for r in rows]==[('LAST_TRADE',date(2026,12,18)),('FINAL_SETTLEMENT',date(2026,12,21))]
 assert rows[0]['atUtc']==datetime(2026,12,18,14,30,tzinfo=timezone.utc)
 assert not any(r['kind'] in ('EXPIRY','FIRST_NOTICE','DELIVERY_START') for r in rows)
 physical=source|dict(settlementMethod='PHYSICAL',deliveryStartDate='2026-12-21',deliveryEndDate='2026-12-21')
 assert [r['kind'] for r in contract_milestones(physical,date(2026,12,18))]==['LAST_TRADE','EXPIRY','FINAL_SETTLEMENT','DELIVERY_START','DELIVERY_END']


@pytest.mark.parametrize('stamp,status,attention', [('2026-12-18T14:29:59+00:00','UPCOMING','INFORMATION'),('2026-12-18T14:30:00+00:00','DUE','ACTIONABLE'),('2026-12-18T14:30:01+00:00','OVERDUE','ACTIONABLE')])
def test_cutoff_uses_exact_instant(stamp,status,attention):
 from lifecycle.worklist_futures import milestone_state
 event=dict(date=date(2026,12,18),atUtc=datetime(2026,12,18,14,30,tzinfo=timezone.utc))
 assert milestone_state(event,datetime.fromisoformat(stamp))==(status,attention)
