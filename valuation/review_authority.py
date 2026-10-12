"""Real-operator independence retained in immutable valuation run events.

Legacy records use their existing access audit and parent lineage. Missing legacy
operator evidence cannot authorize review through an impersonated identity.
"""
from dataclasses import dataclass
from uuid import UUID
from sqlalchemy import select
from security_master_schema import models as m
from . import tables as t


@dataclass(frozen=True)
class OperatorLineage:
    operators: frozenset[UUID]
    complete: bool


def _legacy(c, tenant, resource, subject):
    actors=frozenset(c.scalars(select(m.access_audit_event.c.actor_id).where(
        m.access_audit_event.c.tenant_id==tenant,
        m.access_audit_event.c.subject_id==subject,
        m.access_audit_event.c.action=='TENANT_REQUEST',
        m.access_audit_event.c.details['permission'].astext=='VALUATION_RUN',
        m.access_audit_event.c.details['resourceIds'].contains([str(resource)]))))
    return OperatorLineage(actors or frozenset({subject}), bool(actors))


def request_operator_lineage(c, tenant, request_id):
    row=c.execute(select(t.amendment).where(t.amendment.c.tenant_id==tenant,
        t.amendment.c.request_id==request_id)).mappings().one_or_none()
    if row is None: raise LookupError('Amendment request not found')
    events=c.scalars(select(t.run_event.c.details).join(t.attempt).where(
        t.attempt.c.tenant_id==tenant,t.run_event.c.event_code=='AMENDMENT_REQUESTED',
        t.run_event.c.details['requestId'].astext==str(request_id))).all()
    if events:
        return OperatorLineage(frozenset(UUID(e['realOperatorId']) for e in events),True)
    return _legacy(c,tenant,request_id,row['requested_by'])


def batch_operator_lineage(c, tenant, batch_id, _visited=None):
    visited=set() if _visited is None else _visited
    if batch_id in visited: raise ValueError('Cyclic valuation operator lineage')
    visited.add(batch_id)
    row=c.execute(select(t.batch).where(t.batch.c.tenant_id==tenant,
        t.batch.c.batch_id==batch_id)).mappings().one_or_none()
    if row is None: raise LookupError('Review batch not found')
    events=c.scalars(select(t.run_event.c.details).where(
        t.run_event.c.attempt_id==row['attempt_id'],t.run_event.c.event_code=='STARTED')).all()
    retained=[e for e in events if 'contributorOperatorIds' in e or 'realOperatorId' in e]
    if retained:
        operators=set()
        complete=True
        for evidence in retained:
            values=evidence.get('contributorOperatorIds')
            if values is None: values=[evidence['realOperatorId']]
            if not values: raise ValueError('Missing valuation operator lineage')
            operators.update(UUID(value) for value in values)
            complete=complete and evidence.get('operatorLineageComplete',True)
        return OperatorLineage(frozenset(operators),complete)
    result=_legacy(c,tenant,batch_id,row['staged_by'])
    parent=row['summary'].get('parentBatchId')
    if parent:
        original=batch_operator_lineage(c,tenant,UUID(parent),visited)
        request_id=row['summary'].get('amendmentRequestId')
        if not request_id: raise ValueError('Missing amended candidate request lineage')
        requester=request_operator_lineage(c,tenant,UUID(request_id))
        return OperatorLineage(original.operators | requester.operators,
            original.complete and requester.complete)
    return result


def assert_independent(lineage, subject, real_operator_id=None):
    operator=real_operator_id or subject
    if operator in lineage.operators:
        raise PermissionError('Independent review requires a different real operator, not merely a different selected user')
    if operator!=subject and not lineage.complete:
        raise PermissionError('Real operator lineage is unavailable; recalculate before selected-user review')


def assert_batch_independent(c,tenant,batch_id,subject,real_operator_id=None):
    assert_independent(batch_operator_lineage(c,tenant,batch_id),subject,real_operator_id)


def assert_request_independent(c,tenant,request_id,subject,real_operator_id=None):
    assert_independent(request_operator_lineage(c,tenant,request_id),subject,real_operator_id)
