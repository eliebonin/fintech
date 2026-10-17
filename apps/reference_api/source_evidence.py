"""Pin source evidence scope inside the proposal transaction, including retries."""
from sqlalchemy import select
from security_master_schema import models as m
from .booking_errors import InvalidWorkflowState, RepositoryNotFound


def require_scoped_source_evidence(c, tenant, source_id, payload_id):
    if payload_id is not None and source_id is None:
        raise InvalidWorkflowState('sourcePayloadId requires sourceSystemId')
    if source_id is None:
        return
    # A null scope is explicitly shared; client-specific sources remain private,
    # even if someone incorrectly marks one of their payloads as shared.
    source = c.scalar(select(m.integration_source_system.c.integration_source_system_id).where(
        m.integration_source_system.c.integration_source_system_id == source_id,
        m.integration_source_system.c.status == 'ACTIVE',
        (m.integration_source_system.c.tenant_id == tenant) | m.integration_source_system.c.tenant_id.is_(None)
    ).with_for_update(read=True))
    if source is None:
        raise RepositoryNotFound('Source evidence is unavailable for this tenant and source system')
    if payload_id is not None:
        payload = c.scalar(select(m.source_payload.c.source_payload_id).where(
            m.source_payload.c.source_payload_id == payload_id,
            m.source_payload.c.integration_source_system_id == source_id,
            (m.source_payload.c.tenant_id == tenant) | m.source_payload.c.tenant_id.is_(None)
        ).with_for_update(read=True))
        if payload is None:
            raise RepositoryNotFound('Source evidence is unavailable for this tenant and source system')
