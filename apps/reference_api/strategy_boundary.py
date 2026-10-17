"""Resolve scoped transport targets using authoritative parent ownership.

Query filters still protect collections; this guard protects guessed direct IDs,
submitted strategy IDs and derived valuation objects before handlers release data.
"""
from uuid import UUID
from sqlalchemy import select
from security_master_schema import models as m
from security_master_schema.strategy_access import SCOPED_ACTIONS,require_strategy_action


def enforce_targets(c,tenant,actor,action,path,query,body):
    targets=set()
    for source in (query,body):
        for key in ('strategyId','strategy_id'):
            if source.get(key): targets.add(UUID(str(source[key])))
    if body.get('targetKind')=='STRATEGY' and body.get('targetId'):
        targets.add(UUID(str(body['targetId'])))
    parts=path.removeprefix('/v1/').split('/')
    try: identity=UUID(parts[1]) if len(parts)>1 else None
    except ValueError: identity=None
    if parts[0]=='strategies' and identity: targets.add(identity)
    if parts[0]=='trades' and identity:
        strategy=c.scalar(select(m.trade.c.strategy_id).join(m.strategy).where(
            m.trade.c.trade_id==identity,m.strategy.c.tenant_id==tenant))
        if strategy: targets.add(strategy)
    if parts[0]=='valuation' and len(parts)>2:
        from valuation import tables as t
        try: identity=UUID(parts[2])
        except ValueError: identity=None
        table,key={'attempts':(t.attempt,'attempt_id'),'batches':(t.batch,'batch_id'),
                   'amendments':(t.amendment,'request_id'),'economic-flows':(m.trade,'trade_id')}.get(parts[1],(None,None))
        if table is not None and identity:
            statement=select(table.c.strategy_id).where(table.c[key]==identity)
            if table is m.trade: statement=statement.join(m.strategy).where(m.strategy.c.tenant_id==tenant)
            else: statement=statement.where(table.c.tenant_id==tenant)
            strategy=c.scalar(statement)
            if strategy: targets.add(strategy)
    # Strategy-specific pricing/configuration is also scoped, but shared reference
    # catalogues/provider licensing remain tenant-wide and are not restricted here.
    effective=action if action in SCOPED_ACTIONS else ('STRATEGY_READ' if action=='MARKET_DATA_READ' else 'STRATEGY_WRITE')
    for strategy in targets: require_strategy_action(c,tenant,actor,effective,strategy)
