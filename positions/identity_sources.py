"""Lazy historical identity inputs for one existing ledger keyset page.

Only candidates are batched. Normalizers still match the original BOOKED
fingerprint, effective dates, currencies, venue and unique version identities.
Cancelled/malformed snapshots are never parsed merely to prefetch sources.
"""
from collections import defaultdict
from sqlalchemy import select
from security_master_schema import models as m
from .contracts import PositionError


class HistoricalIdentitySources:
    def __init__(self,connection,request,rows):
        self.connection=connection;self.transaction=connection.get_transaction()
        self.tenant,self.strategy=request.tenant_id,request.strategy_id
        self.parents={r['reference_instrument_node_id'] for r in rows}-{None}
        self.subjects={r['trade_subject_reference_node_id'] for r in rows}-{None}
        self.currencies={r['price_currency_id'] for r in rows}-{None}
        self._loaded={}

    def require_scope(self,connection,row):
        if connection is not self.connection or connection.get_transaction() is not self.transaction or row['strategy_id']!=self.strategy:
            raise PositionError('Historical identity sources belong to a different ledger read scope')
        if row['reference_instrument_node_id'] not in self.parents or row['trade_subject_reference_node_id'] not in self.subjects:
            raise PositionError('Booking identity was not included in this ledger source page')

    def _rows(self,key,table,column,identities,extra=None):
        if key not in self._loaded:
            result=defaultdict(list);ids=sorted(identities,key=str)
            for start in range(0,len(ids),500):
                statement=select(table).where(column.in_(ids[start:start+500])).order_by(*table.primary_key.columns)
                if extra is not None:statement=statement.where(extra)
                for row in self.connection.execute(statement).mappings():result[row[column.name]].append(row)
            self._loaded[key]=result
        return self._loaded[key]

    def definitions(self,connection,row):
        self.require_scope(connection,row);t=m.instrument_definition_version
        return self._rows('definitions',t,t.c.instrument_node_id,self.parents,t.c.status.in_(('APPROVED','SUPERSEDED'))).get(row['reference_instrument_node_id'],[])

    def listings(self,connection,row):
        self.require_scope(connection,row);t=m.listing_definition_version
        return self._rows('listings',t,t.c.listing_node_id,self.subjects,t.c.status.in_(('APPROVED','SUPERSEDED'))).get(row['trade_subject_reference_node_id'],[])

    def conventions(self,connection,row):
        self.require_scope(connection,row);t=m.instrument_booking_convention
        return self._rows('conventions',t,t.c.instrument_node_id,self.parents).get(row['reference_instrument_node_id'],[])

    def option_terms(self,connection,row):
        self.require_scope(connection,row);t=m.option_terms
        return [r['option_terms_id'] for r in self._rows('options',t,t.c.instrument_node_id,self.parents).get(row['reference_instrument_node_id'],[])]

    def note_terms(self,connection,row):
        self.require_scope(connection,row);t=m.structured_product_terms
        return [r['structured_product_terms_id'] for r in self._rows('notes',t,t.c.instrument_node_id,self.parents).get(row['reference_instrument_node_id'],[])]

    def family(self,connection,row):
        self.require_scope(connection,row);t=m.future_terms
        records=self._rows('futures',t,t.c.instrument_node_id,self.parents).get(row['reference_instrument_node_id'],[])
        return records[0]['future_family_id'] if records else None

    def currency(self,connection,row):
        self.require_scope(connection,row);t=m.currency
        records=self._rows('currencies',t,t.c.currency_id,self.currencies).get(row['price_currency_id'],[])
        return records[0]['currency_code'] if records else None
