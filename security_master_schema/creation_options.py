"""Read-only canonical creation choices from effective, tenant-visible configuration."""
from sqlalchemy import select, or_
from . import models as m


def equity_creation_options(c, tenant_id, effective_date):
    source=m.integration_source_system;policy=m.reference_data_automation_policy;ns=m.external_id_namespace
    rows=c.execute(select(source.c.integration_source_system_id,source.c.display_name.label('source_name'),
        policy.c.policy_code,policy.c.display_name.label('policy_name'),policy.c.version_no,policy.c.tenant_id,
        ns.c.namespace_code).select_from(source.join(policy,policy.c.source_system_id==source.c.integration_source_system_id)
        .join(ns,ns.c.integration_source_system_id==source.c.integration_source_system_id)).where(
        source.c.status=='ACTIVE',or_(source.c.tenant_id.is_(None),source.c.tenant_id==tenant_id),
        policy.c.status=='ACTIVE',policy.c.target_object_type=='EQUITY',policy.c.operation_type=='CREATE',
        or_(policy.c.tenant_id.is_(None),policy.c.tenant_id==tenant_id),policy.c.valid_from<=effective_date,
        or_(policy.c.valid_to.is_(None),policy.c.valid_to>=effective_date),ns.c.status=='ACTIVE',
        or_(ns.c.external_object_type.is_(None),ns.c.external_object_type=='INSTRUMENT'),ns.c.valid_from<=effective_date,
        or_(ns.c.valid_to.is_(None),ns.c.valid_to>=effective_date)).order_by(
        source.c.display_name,policy.c.policy_code,ns.c.namespace_code,
        policy.c.tenant_id.is_(None),policy.c.version_no.desc())).mappings()
    chosen={}
    for row in rows:
        key=(row['integration_source_system_id'],row['policy_code'],row['namespace_code'])
        chosen.setdefault(key,dict(sourceSystemId=str(row['integration_source_system_id']),sourceName=row['source_name'],
            sourceNamespace=row['namespace_code'],policyCode=row['policy_code'],policyName=row['policy_name'],policyVersion=row['version_no']))
    return list(chosen.values())
