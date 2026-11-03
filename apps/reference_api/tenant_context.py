"""Verified tenant and actor context established by the API identity boundary."""

from dataclasses import dataclass
from uuid import UUID

from fastapi import Header, Request, status

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


def get_tenant_context(
    request: Request,
    x_tenant_id: str | None = Header(default=None),
    x_user_account_id: str | None = Header(default=None),
) -> TenantContext:
    """Headers retain their wire shape but never establish caller identity."""
    context=getattr(request.state,'tenant_context',None)
    if context is None:
        raise ApiProblem(
            status.HTTP_401_UNAUTHORIZED,
            "authentication.required",
            "Authentication required",
            "Authentication context is required.",
        )
    return context


def get_actor_context(request:Request,x_user_account_id: str | None = Header(default=None)) -> ActorContext:
    context=getattr(request.state,'actor_context',None)
    if context is None:
        raise ApiProblem(status.HTTP_401_UNAUTHORIZED, "authentication.required", "Authentication required", "Authentication context is required.")
    return context


def require_actor(context: TenantContext) -> UUID:
    if context.user_account_id is None:
        raise ApiProblem(
            status.HTTP_401_UNAUTHORIZED,
            "authentication.required",
            "Authentication required",
            "Authentication context is required.",
        )
    return context.user_account_id
