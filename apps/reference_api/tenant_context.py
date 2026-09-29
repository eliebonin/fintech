"""Trusted tenant and actor context extracted at the API boundary."""

from dataclasses import dataclass
from uuid import UUID

from fastapi import Header, HTTPException, status

from .problem_details import ApiProblem


@dataclass(frozen=True)
class TenantContext:
    tenant_id: UUID
    user_account_id: UUID | None
    source: str


@dataclass(frozen=True)
class ActorContext:
    user_account_id: UUID
    source: str


def _parse_uuid(value: str, field_name: str) -> UUID:
    try:
        return UUID(value)
    except ValueError as exc:
        raise ApiProblem(
            status.HTTP_400_BAD_REQUEST,
            "request.invalid",
            "Invalid request",
            "One or more request fields are invalid.",
        ) from exc


def get_tenant_context(
    x_tenant_id: str | None = Header(default=None),
    x_user_account_id: str | None = Header(default=None),
) -> TenantContext:
    """Require a tenant selected by trusted server/session context.

    The browser may not select a database or tenant by query parameter. The
    Next BFF supplies these headers after deriving them from the authenticated
    session; direct calls without a tenant are rejected.
    """

    if not x_tenant_id:
        raise ApiProblem(
            status.HTTP_401_UNAUTHORIZED,
            "authentication.required",
            "Authentication required",
            "Authentication context is required.",
        )
    user_account_id = _parse_uuid(x_user_account_id, "X-User-Account-Id") if x_user_account_id else None
    return TenantContext(tenant_id=_parse_uuid(x_tenant_id, "X-Tenant-Id"), user_account_id=user_account_id, source="trusted-header")


def get_actor_context(x_user_account_id: str | None = Header(default=None)) -> ActorContext:
    if not x_user_account_id:
        raise ApiProblem(status.HTTP_401_UNAUTHORIZED, "authentication.required", "Authentication required", "Authentication context is required.")
    return ActorContext(user_account_id=_parse_uuid(x_user_account_id, "X-User-Account-Id"), source="trusted-header")


def require_actor(context: TenantContext) -> UUID:
    if context.user_account_id is None:
        raise ApiProblem(
            status.HTTP_401_UNAUTHORIZED,
            "authentication.required",
            "Authentication required",
            "Authentication context is required.",
        )
    return context.user_account_id
