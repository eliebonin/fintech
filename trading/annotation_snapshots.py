"""Batched immutable trade-property sources, bound to tenant-owned trades."""
from sqlalchemy import select
from security_master_schema import models as m
from security_master_schema.allocation_contracts import AnnotationValue

def load_trade_annotations(connection,tenant_id,trade_ids,policy=None):
    result={}
    identities=sorted(set(trade_ids),key=str)
    for start in range(0,len(identities),500):
        batch=identities[start:start+500]
        def scoped(table):
            return table.join(m.trade,m.trade.c.trade_id==table.c.trade_id).join(m.strategy,m.strategy.c.strategy_id==m.trade.c.strategy_id)
        for row in connection.execute(select(m.trade_property_value).select_from(scoped(m.trade_property_value)).where(
                m.strategy.c.tenant_id==tenant_id,m.trade_property_value.c.tenant_id==tenant_id,m.trade_property_value.c.trade_id.in_(batch))).mappings():
            result.setdefault(row['trade_id'],{})[row['definition_id']]=AnnotationValue(row['value'])
        refs=m.trade_property_reference;records=m.reference_catalogue_record;catalogues=m.reference_catalogue
        query=select(refs,records.c.record_id).select_from(scoped(refs).join(records,records.c.record_version_id==refs.c.record_version_id)
            .join(catalogues,catalogues.c.catalogue_id==records.c.catalogue_id)).where(m.strategy.c.tenant_id==tenant_id,
                refs.c.tenant_id==tenant_id,catalogues.c.tenant_id==tenant_id,refs.c.trade_id.in_(batch))
        for row in connection.execute(query).mappings():
            result.setdefault(row['trade_id'],{})[row['definition_id']]=AnnotationValue(str(row['record_version_id']),row['record_id'])
    if policy:
        for trade,values in result.items():
            for rule in policy.fields:
                candidates=[values[i] for i in rule.source_definition_ids if i in values]
                if len({v.identity() for v in candidates})>1:raise ValueError('A trade contains ambiguous versions of the same allocation field.')
                if candidates:values[rule.definition_id]=candidates[0]
        standard={r.standard_field_key:r.definition_id for r in policy.fields if r.standard_field_key}
        for start in range(0,len(identities),500):
            batch=identities[start:start+500]
            t,s,p=m.trade,m.strategy,m.trade_party_role
            if standard:
                for row in connection.execute(select(t.c.trade_id,t.c.trader_person_id,t.c.comment).join(s,s.c.strategy_id==t.c.strategy_id).where(s.c.tenant_id==tenant_id,t.c.trade_id.in_(batch))).mappings():
                    for key,value in [('TRADER',row['trader_person_id']),('COMMENT',row['comment'])]:
                        if key in standard and value is not None:result.setdefault(row['trade_id'],{})[standard[key]]=AnnotationValue(str(value))
                for row in connection.execute(select(t.c.trade_id,p.c.role,p.c.organisation_id).select_from(t.join(s,s.c.strategy_id==t.c.strategy_id).join(p,p.c.trade_id==t.c.trade_id)).where(s.c.tenant_id==tenant_id,t.c.trade_id.in_(batch),p.c.role.in_(['COUNTERPARTY','EXECUTING_BROKER']))).mappings():
                    key=row['role']
                    if key not in standard:continue
                    value=AnnotationValue(str(row['organisation_id']));values=result.setdefault(row['trade_id'],{})
                    if standard[key] in values and values[standard[key]].identity()!=value.identity():raise ValueError('Ambiguous canonical party allocation; reconcile source bookings.')
                    values[standard[key]]=value
    return result
