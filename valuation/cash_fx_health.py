"""Batched cash-source change notices; published figures are never rewritten."""
from datetime import date,datetime
from sqlalchemy import select,values,column,Date,DateTime,or_
from security_master_schema import models as m
from . import tables as t


def cash_reassessment_predicate(batch):
    """Filter before queue counts/pagination; never scan cash per loaded result."""
    source=batch.c.summary['cashCoverage']['sourceState']
    info=source['informationCutoff'].astext.cast(DateTime(timezone=True))
    opening=source['openingDate'].astext.cast(Date())
    closing=source['closingDate'].astext.cast(Date())
    b=m.cash_balance
    changed=select(1).where(b.c.strategy_id==batch.c.strategy_id,b.c.source_system_id=='TENANT_EOD',
        b.c.balance_as_of_date>=opening,b.c.balance_as_of_date<=closing,b.c.received_at_utc>info).exists()
    return or_(source['version'].as_integer().is_(None),source['version'].as_integer()!=1,
        info.is_(None),opening.is_(None),closing.is_(None),changed)


def cash_health_statuses(c,headers):
    states={};rows=[]
    for h in headers:
        source=(h['summary'].get('cashCoverage') or {}).get('sourceState') or {}
        try:
            if source['version']!=1:raise ValueError()
            info=datetime.fromisoformat(source['informationCutoff'])
            if info.tzinfo is None:raise ValueError()
            opening=date.fromisoformat(source['openingDate']);closing=date.fromisoformat(source['closingDate'])
            if opening>=closing:raise ValueError()
        except (KeyError,ValueError,TypeError):states[h['batch_id']]='UNKNOWN_LEGACY';continue
        rows.append((h['batch_id'],h['strategy_id'],opening,closing,info))
    if rows:
        frozen=values(column('batch_id',t.batch.c.batch_id.type),column('strategy_id',m.strategy.c.strategy_id.type),
            column('opening_date',Date()),column('closing_date',Date()),
            column('information_cutoff',DateTime(timezone=True))).data(rows).cte('frozen_cash_sources')
        b=m.cash_balance
        changed=select(1).where(b.c.strategy_id==frozen.c.strategy_id,b.c.source_system_id=='TENANT_EOD',
            b.c.balance_as_of_date>=frozen.c.opening_date,b.c.balance_as_of_date<=frozen.c.closing_date,
            b.c.received_at_utc>frozen.c.information_cutoff).exists()
        for batch_id,stale in c.execute(select(frozen.c.batch_id,changed)):
            states[batch_id]='REASSESSMENT_REQUIRED' if stale else 'CURRENT'
    return states
