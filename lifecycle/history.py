"""Instrument-scoped native history, including retained cancellation receipts."""
from sqlalchemy import String,cast,or_,select

def instrument_history_clause(table,tenant,strategy,instrument,*,proposals=False):
    if proposals:return table.c.instrument_id==instrument
    original=table.alias('original_instrument_posting')
    original_ids=select(cast(original.c.posting_id,String)).where(original.c.tenant_id==tenant,
        original.c.strategy_id==strategy,original.c.evidence['instrumentId'].astext==str(instrument))
    return or_(table.c.evidence['instrumentId'].astext==str(instrument),
        table.c.evidence['originalPostingId'].astext.in_(original_ids))
