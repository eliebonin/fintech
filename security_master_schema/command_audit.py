"""Request intent carried to the transaction owner, without HTTP dependencies.

Ordinary commands audit at their own commit. Multi-transaction calculations audit
REQUEST_ACCEPTED with their retained attempt/request, before any financial stage;
their existing domain events describe subsequent completion or failure.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from uuid import UUID


@dataclass
class CommandAudit:
    tenant: UUID
    operator: UUID
    subject: UUID
    permission: str | None
    path: str
    method: str
    request_id: str | None
    resources: set[str] = field(default_factory=set)
    result_captured: bool = False
    retained: bool = False


_command: ContextVar[CommandAudit | None] = ContextVar('command_audit', default=None)


@contextmanager
def command_scope(command):
    token = _command.set(command)
    try:
        yield command
    finally:
        _command.reset(token)


def current_command():
    return _command.get()


def resource_ids(value):
    if isinstance(value, dict):
        return set().union(*(resource_ids(child) for child in value.values())) if value else set()
    if isinstance(value, (list, tuple)):
        return set().union(*(resource_ids(child) for child in value)) if value else set()
    if isinstance(value, (str, UUID)):
        try:
            return {str(UUID(str(value)))}
        except ValueError:
            pass
    return set()


def capture_result(value):
    command = current_command()
    if command is not None:
        command.resources.update(resource_ids(value))
        command.result_captured = True


def retain_command_audit(c, *, resources=(), phase='COMMAND_COMMITTED'):
    """Call inside the effect transaction; an audit error must roll it back."""
    command = current_command()
    if command is None or command.retained:
        return
    if phase == 'COMMAND_COMMITTED' and not command.result_captured:
        raise RuntimeError('Command result was not captured before transaction finalization')
    from .access_management import audit
    audit(c, command.operator, command.tenant, 'TENANT_REQUEST', dict(
        path=command.path, method=command.method, permission=command.permission,
        resourceIds=sorted(command.resources | set(map(str, resources))),
        requestId=command.request_id, phase=phase), command.subject)
    # No later supplementary write is required to make this command auditable.
    # If commit raises, the exception still reaches the caller and no success
    # response is advertised; the scope is then discarded with that request.
    command.retained = True
