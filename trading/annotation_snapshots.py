"""Batched immutable trade-property sources, bound to tenant-owned trades."""
from collections import defaultdict
from sqlalchemy import select
from security_master_schema import models as m
from security_master_schema.allocation_contracts import AnnotationValue


class TradeAnnotationBatch:
    """Raw tenant-scoped reads once; the existing policy checks per subset.

    Do not validate a whole union before partitioning: a conflicting legacy
    annotation on one instrument must not poison another instrument's view.
    """
    def __init__(self,connection,tenant_id,trade_ids,policy=None):
        self.connection,self.tenant,self.policy=connection,tenant_id,policy
        self.identities=set(trade_ids)
        self.properties=[];self.references=[];self.standard_rows=[];self.party_rows=[]
        standard={r.standard_field_key for r in policy.fields if r.standard_field_key} if policy else set()
        identities=sorted(self.identities,key=str)
        for start in range(0,len(identities),500):
            batch=identities[start:start+500]
            def scoped(table):
                return table.join(m.trade,m.trade.c.trade_id==table.c.trade_id).join(m.strategy,m.strategy.c.strategy_id==m.trade.c.strategy_id)
            self.properties.extend(connection.execute(select(m.trade_property_value).select_from(scoped(m.trade_property_value)).where(
                m.strategy.c.tenant_id==tenant_id,m.trade_property_value.c.tenant_id==tenant_id,m.trade_property_value.c.trade_id.in_(batch))).mappings())
            refs=m.trade_property_reference;records=m.reference_catalogue_record;catalogues=m.reference_catalogue
            query=select(refs,records.c.record_id).select_from(scoped(refs).join(records,records.c.record_version_id==refs.c.record_version_id)
                .join(catalogues,catalogues.c.catalogue_id==records.c.catalogue_id)).where(m.strategy.c.tenant_id==tenant_id,
                refs.c.tenant_id==tenant_id,catalogues.c.tenant_id==tenant_id,refs.c.trade_id.in_(batch))
            self.references.extend(connection.execute(query).mappings())
            if standard:
                t,s,p=m.trade,m.strategy,m.trade_party_role
                self.standard_rows.extend(connection.execute(select(t.c.trade_id,t.c.trader_person_id,t.c.comment).join(s,s.c.strategy_id==t.c.strategy_id).where(s.c.tenant_id==tenant_id,t.c.trade_id.in_(batch))).mappings())
                self.party_rows.extend(connection.execute(select(t.c.trade_id,p.c.role,p.c.organisation_id).select_from(t.join(s,s.c.strategy_id==t.c.strategy_id).join(p,p.c.trade_id==t.c.trade_id)).where(s.c.tenant_id==tenant_id,t.c.trade_id.in_(batch),p.c.role.in_(['COUNTERPARTY','EXECUTING_BROKER']))).mappings())
        # Index once: each root inspects only its own rows, not the whole union.
        for name in ('properties','references','standard_rows','party_rows'):
            grouped=defaultdict(list)
            for row in getattr(self,name):grouped[row['trade_id']].append(row)
            setattr(self,name,grouped)
        self.transaction=connection.get_transaction()

    def for_trades(self,connection,tenant_id,trade_ids):
        identities=set(trade_ids)
        if connection is not self.connection or tenant_id!=self.tenant or connection.get_transaction() is not self.transaction or not identities<=self.identities:
            raise ValueError('Trade annotation sources belong to a different read scope.')
        result={}
        def selected(rows):
            return (row for identity in identities for row in rows.get(identity,()))
        for row in selected(self.properties):
            result.setdefault(row['trade_id'],{})[row['definition_id']]=AnnotationValue(row['value'])
        for row in selected(self.references):
            result.setdefault(row['trade_id'],{})[row['definition_id']]=AnnotationValue(str(row['record_version_id']),row['record_id'])
        policy=self.policy
        if policy:
            for trade,values in result.items():
                for rule in policy.fields:
                    candidates=[values[i] for i in rule.source_definition_ids if i in values]
                    if len({v.identity() for v in candidates})>1:raise ValueError('A trade contains ambiguous versions of the same allocation field.')
                    if candidates:values[rule.definition_id]=candidates[0]
            standard={r.standard_field_key:r.definition_id for r in policy.fields if r.standard_field_key}
            for row in selected(self.standard_rows):
                for key,value in [('TRADER',row['trader_person_id']),('COMMENT',row['comment'])]:
                    if key in standard and value is not None:result.setdefault(row['trade_id'],{})[standard[key]]=AnnotationValue(str(value))
            for row in selected(self.party_rows):
                key=row['role']
                if key not in standard:continue
                value=AnnotationValue(str(row['organisation_id']));values=result.setdefault(row['trade_id'],{})
                if standard[key] in values and values[standard[key]].identity()!=value.identity():raise ValueError('Ambiguous canonical party allocation; reconcile source bookings.')
                values[standard[key]]=value
        return result


def load_trade_annotations(connection,tenant_id,trade_ids,policy=None):
    identities=tuple(trade_ids)
    return TradeAnnotationBatch(connection,tenant_id,identities,policy).for_trades(connection,tenant_id,identities)
