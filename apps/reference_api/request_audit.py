"""Capture typed endpoint results before function-scoped transaction teardown."""
from functools import wraps
from inspect import iscoroutinefunction, signature
from fastapi import APIRouter
from fastapi.encoders import jsonable_encoder
from fastapi.routing import APIRoute
from security_master_schema.command_audit import capture_result, current_command


class AuditedRoute(APIRoute):
    def __init__(self, path, endpoint, **kwargs):
        def capture(result):
            if current_command() is not None:
                capture_result(jsonable_encoder(result))
            return result
        if iscoroutinefunction(endpoint):
            @wraps(endpoint)
            async def wrapped(*args, **kw):
                return capture(await endpoint(*args, **kw))
        else:
            @wraps(endpoint)
            def wrapped(*args, **kw):
                return capture(endpoint(*args, **kw))
        # Resolve postponed annotations in the endpoint's own module, not this
        # adapter's globals. FastAPI still owns validation and serialization.
        wrapped.__signature__ = signature(endpoint, eval_str=True)
        super().__init__(path, wrapped, **kwargs)


class AuditRouter(APIRouter):
    def __init__(self, **kwargs):
        kwargs.setdefault('route_class', AuditedRoute)
        super().__init__(**kwargs)
