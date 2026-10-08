"""Safe RFC 9457 error responses and request correlation for the API boundary."""

from __future__ import annotations

import logging
from contextvars import ContextVar
from time import perf_counter
from traceback import extract_tb
from typing import Any
from uuid import UUID, uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException
from security_master_schema.tenant_workspace import TenantActionForbidden


LOGGER = logging.getLogger("apps.reference_api")
_request_id: ContextVar[str | None] = ContextVar("reference_api_request_id", default=None)
_api_version: ContextVar[str | None] = ContextVar('reference_api_version',default=None)
_PROBLEM_BASE_URI = "https://api.fortem.local/problems"


class ValidationIssue(BaseModel):
    location: list[str]
    message: str
    kind: str


class ProblemDetails(BaseModel):
    type: str
    title: str
    status: int
    detail: str
    instance: str
    code: str
    request_id: str = Field(serialization_alias="requestId")
    errors: list[ValidationIssue] | None = None


class ApiProblem(Exception):
    """An explicitly safe error that may be returned to an API client."""

    def __init__(
        self,
        status_code: int,
        code: str,
        title: str,
        detail: str,
        *,
        type_slug: str | None = None,
        errors: list[ValidationIssue] | None = None,
    ) -> None:
        super().__init__(code)
        self.status_code = status_code
        self.code = code
        self.title = title
        self.detail = detail
        self.type_slug = type_slug or code.replace(".", "-")
        self.errors = errors


def current_request_id() -> str:
    """Return the request ID set by middleware, or a safe ID outside a request."""

    return _request_id.get() or str(uuid4())


def current_api_version() -> str:
    from .config import Settings
    return _api_version.get() or Settings.from_environment().api_version


def request_id_from_request(request: Request) -> str:
    """Accept only UUID request IDs; retain the legacy correlation header as input."""

    candidate = request.headers.get("X-Request-ID") or request.headers.get("X-Correlation-ID")
    if candidate:
        try:
            return str(UUID(candidate))
        except ValueError:
            pass
    return str(uuid4())


def configure_problem_details(app: FastAPI) -> None:
    """Install safe error handlers, correlation middleware, and request logging."""

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request_id = request_id_from_request(request)
        token = _request_id.set(request_id)
        version_token = _api_version.set(app.version)
        request.state.request_id = request_id
        started = perf_counter()
        try:
            try:
                response = await call_next(request)
            except Exception as exc:
                response = await unexpected_error_handler(request, exc)
        finally:
            _request_id.reset(token)
            _api_version.reset(version_token)

        response.headers["X-Request-ID"] = request_id
        route = request.scope.get("route")
        route_path = getattr(route, "path", '<unmatched>')
        LOGGER.info(
            "api_response request_id=%s method=%s route=%s status=%s duration_ms=%.2f",
            request_id,
            request.method,
            route_path,
            response.status_code,
            (perf_counter() - started) * 1000,
        )
        return response

    @app.exception_handler(ApiProblem)
    async def api_problem_handler(request: Request, exc: ApiProblem) -> JSONResponse:
        return _problem_response(
            request,
            status_code=exc.status_code,
            code=exc.code,
            title=exc.title,
            detail=exc.detail,
            type_slug=exc.type_slug,
            errors=exc.errors,
        )

    @app.exception_handler(TenantActionForbidden)
    async def authority_error_handler(request: Request, exc: TenantActionForbidden) -> JSONResponse:
        return _problem_response(request, status_code=403, code='authorization.forbidden',
            title='Access denied', detail='The request is not permitted.', type_slug='access-denied')

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        return _problem_response(
            request,
            status_code=422,
            code="request.validation_failed",
            title="Request validation failed",
            detail="One or more request fields are invalid.",
            type_slug="request-validation",
            errors=[
                ValidationIssue(
                    location=[str(item) for item in error.get("loc", [])],
                    message=str(error.get("msg", "Invalid value.")),
                    kind=str(error.get("type", "validation_error")),
                )
                for error in exc.errors()
            ],
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        status_code, code, title, detail, type_slug = _safe_http_problem(exc.status_code)
        response = _problem_response(
            request,
            status_code=status_code,
            code=code,
            title=title,
            detail=detail,
            type_slug=type_slug,
        )
        for name, value in (exc.headers or {}).items():
            if name.lower() in {'allow', 'www-authenticate', 'retry-after'}:
                response.headers[name] = value
        return response

    @app.exception_handler(Exception)
    async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
        frames = [
            f"{frame.filename}:{frame.lineno}:{frame.name}"
            for frame in extract_tb(exc.__traceback__)
        ]
        LOGGER.error(
            "unhandled_api_exception request_id=%s exception_type=%s stack_frames=%s",
            request.state.request_id,
            type(exc).__name__,
            frames,
        )
        return _problem_response(
            request,
            status_code=500,
            code="internal.error",
            title="Internal server error",
            detail="The service could not complete the request.",
            type_slug="internal-error",
        )

    default_openapi = app.openapi

    def openapi_with_problems() -> dict[str, Any]:
        schema = default_openapi()
        if schema.get("x-problem-details-configured"):
            return schema

        components = schema.setdefault("components", {})
        schemas = components.setdefault("schemas", {})
        schemas["ValidationIssue"] = {
            "type": "object",
            "required": ["location", "message", "kind"],
            "properties": {
                "location": {"type": "array", "items": {"type": "string"}},
                "message": {"type": "string"},
                "kind": {"type": "string"},
            },
        }
        schemas["ProblemDetails"] = {
            "type": "object",
            "required": ["type", "title", "status", "detail", "instance", "code", "requestId"],
            "properties": {
                "type": {"type": "string", "format": "uri"},
                "title": {"type": "string"},
                "status": {"type": "integer"},
                "detail": {"type": "string"},
                "instance": {"type": "string"},
                "code": {"type": "string"},
                "requestId": {"type": "string", "format": "uuid"},
                "errors": {"type": "array", "items": {"$ref": "#/components/schemas/ValidationIssue"}},
            },
        }

        for path_item in schema.get("paths", {}).values():
            for method, operation in path_item.items():
                if method.lower() not in {"get", "put", "post", "delete", "patch", "head", "options"}:
                    continue
                responses = operation.setdefault("responses", {})
                for status_code, description in _OPENAPI_PROBLEM_RESPONSES.items():
                    response = responses.setdefault(str(status_code), {"description": description})
                    response.setdefault("description", description)
                    response.setdefault("content", {})["application/problem+json"] = {
                        "schema": {"$ref": "#/components/schemas/ProblemDetails"},
                    }

        schema["x-problem-details-configured"] = True
        return schema

    app.openapi = openapi_with_problems


def _problem_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    title: str,
    detail: str,
    type_slug: str,
    errors: list[ValidationIssue] | None = None,
) -> JSONResponse:
    problem = ProblemDetails(
        type=f"{_PROBLEM_BASE_URI}/{type_slug}",
        title=title,
        status=status_code,
        detail=detail,
        instance=request.url.path,
        code=code,
        request_id=request.state.request_id,
        errors=errors,
    )
    return JSONResponse(
        status_code=status_code,
        content=problem.model_dump(by_alias=True, exclude_none=True),
        media_type="application/problem+json",
        headers={'X-Request-ID': request.state.request_id},
    )


def _safe_http_problem(status_code: int) -> tuple[int, str, str, str, str]:
    mapping: dict[int, tuple[str, str, str, str]] = {
        400: ("request.invalid", "Invalid request", "The request could not be processed.", "invalid-request"),
        401: ("authentication.required", "Authentication required", "Authentication context is required.", "authentication-required"),
        403: ("authorization.forbidden", "Access denied", "The request is not permitted.", "access-denied"),
        404: ("resource.not_found", "Resource not found", "The requested resource was not found.", "resource-not-found"),
        409: ("request.conflict", "Request conflict", "The request conflicts with the current resource state.", "request-conflict"),
        422: ("request.validation_failed", "Request validation failed", "One or more request fields are invalid.", "request-validation"),
    }
    code, title, detail, type_slug = mapping.get(
        status_code,
        ("request.failed", "Request failed", "The request could not be completed.", "request-failed"),
    )
    return status_code, code, title, detail, type_slug


_OPENAPI_PROBLEM_RESPONSES = {
    400: "Invalid request",
    401: "Authentication required",
    403: "Access denied",
    404: "Resource not found",
    409: "Request conflict",
    413: "Request too large",
    422: "Request validation failed",
    500: "Internal server error",
}
