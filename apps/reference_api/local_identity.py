"""Local-only capability verification; production authentication is deferred."""
from hmac import compare_digest
from uuid import UUID

from security_master_schema import access_sessions
from .tenant_context import ActorContext, TenantContext


class AuthenticationRequired(PermissionError):
    """No valid opaque local session has established the caller's identity."""


def _agrees(supplied, expected):
    if supplied is None: return True
    try: return expected is not None and UUID(supplied)==UUID(str(expected))
    except ValueError: return False


def bootstrap_actor(request, settings):
    supplied=request.headers.get('x-local-operator-key','')
    if not compare_digest(supplied.encode(),settings.local_operator_key.encode()):
        raise AuthenticationRequired('A local operator credential is required')
    actor=settings.local_operator_id
    if not _agrees(request.headers.get('x-user-account-id'),actor):
        raise PermissionError('Request does not match the configured local operator')
    request.state.actor_context=ActorContext(actor,'local-operator')
    request.state.real_actor_id=actor
    request.state.effective_actor_id=actor


def verified_session(connection, request, settings):
    token=request.headers.get('x-local-access-token')
    if not token:
        raise AuthenticationRequired('Select a local testing context first')
    try:
        context=access_sessions.resolve(connection,token,environment=settings.environment)
    except PermissionError as exc:
        raise AuthenticationRequired('Testing session expired, revoked or invalid; select a context again') from exc
    actor=UUID(context['userId'])
    request.state.actor_context=ActorContext(actor,'local-session')
    request.state.real_actor_id=UUID(context['actorId'])
    request.state.effective_actor_id=actor
    if context['tenantId']:
        request.state.tenant_context=TenantContext(UUID(context['tenantId']),actor,'local-session')
    if not _agrees(request.headers.get('x-user-account-id'),context['userId']) or not _agrees(request.headers.get('x-tenant-id'),context['tenantId']):
        raise PermissionError('Request does not match the selected testing context')
    return context
