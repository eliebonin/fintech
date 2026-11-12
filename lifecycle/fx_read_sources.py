"""Scoped discovery inputs; native FX valuation/booking commands do not use them."""
from collections import defaultdict
from sqlalchemy import select,tuple_
from security_master_schema import models as m
from security_master_schema.fx_forward_reference import FxForwardTermBatch
from security_master_schema.tenancy import assert_tenant_owns_strategy


class FxMaturityReadSources:
    def __init__(self,connection,tenant,pairs,now):
        self.connection,self.tenant,self.now=connection,tenant,now
        self.pairs={(row['strategy_id'],row['instrument_id']) for row in pairs}
        for strategy in sorted({key[0] for key in self.pairs},key=str):assert_tenant_owns_strategy(connection,tenant,strategy)
        self.terms=FxForwardTermBatch(connection,tenant,{key[1] for key in self.pairs})
        self.rows=defaultdict(list);self.chains={}
        identities=sorted(self.pairs,key=lambda key:tuple(map(str,key)))
        t=m.trade
        for start in range(0,len(identities),500):
            for row in connection.execute(select(t).where(tuple_(t.c.strategy_id,t.c.trade_subject_reference_node_id).in_(identities[start:start+500]),t.c.trade_datetime_utc<=now,t.c.created_at_utc<=now).order_by(t.c.trade_id)).mappings():
                self.rows[(row['strategy_id'],row['trade_subject_reference_node_id'])].append(row)
                self.chains[row['trade_id']]=[]
        trades=sorted(self.chains,key=str)
        for start in range(0,len(trades),500):
            for row in connection.execute(select(m.trade_lifecycle_event).where(m.trade_lifecycle_event.c.trade_id.in_(trades[start:start+500]),m.trade_lifecycle_event.c.recorded_at_utc<=now).order_by(m.trade_lifecycle_event.c.sequence_no)).mappings():self.chains[row['trade_id']].append(row)
        self.transaction=connection.get_transaction()

    def require_scope(self,connection,tenant,strategy,instrument,cutoff,now):
        if connection is not self.connection or tenant!=self.tenant or connection.get_transaction() is not self.transaction or (strategy,instrument) not in self.pairs or now!=self.now or cutoff>now:
            raise ValueError('Forward ledger belongs to a different discovery read scope.')

    def read(self,connection,tenant,strategy,instrument,cutoff,now):
        self.require_scope(connection,tenant,strategy,instrument,cutoff,now)
        return [row for row in self.rows[(strategy,instrument)] if row['trade_datetime_utc']<=cutoff],self.chains

    def late(self,connection,tenant,strategy,instrument,cutoff,now):
        self.require_scope(connection,tenant,strategy,instrument,cutoff,now)
        return any(row['trade_datetime_utc']>cutoff and row['lifecycle_status']=='BOOKED' for row in self.rows[(strategy,instrument)])
