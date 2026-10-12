"""Safe catalogue reads and administrator-only source preference commands."""
from fastapi import APIRouter, Depends, Header
from .tenant_context import TenantContext, get_tenant_context
from .problem_details import ApiProblem
from .repository import IdempotencyKeyConflict
from .market_data_source_contracts import SourceCatalogueView, SourcePriorityInput, PriorityView
from . import market_data_sources as sources


def market_data_source_router(connection_dependency, membership):
    router = APIRouter(prefix='/v1/market-data', tags=['market data sources'])
    def run(c, context, action):
        actor = membership(c, context)
        try:
            return action(actor)
        except IdempotencyKeyConflict as exc:
            raise ApiProblem(409, 'market_data.priority_conflict', 'Source priority conflict', str(exc)) from exc
        except PermissionError as exc:
            raise ApiProblem(403, 'market_data.forbidden', 'Market data authority required', 'Active market data access and appropriate administrator authority are required.') from exc
        except ValueError as exc:
            raise ApiProblem(422, 'market_data.invalid_sources', 'Invalid source priorities', str(exc)) from exc

    @router.get('/sources', response_model=SourceCatalogueView)
    def catalogue(context: TenantContext = Depends(get_tenant_context), c=Depends(connection_dependency, scope='function')):
        return run(c, context, lambda actor: sources.catalogue(c, context.tenant_id, actor))

    @router.post('/source-priorities', response_model=PriorityView, status_code=201)
    def save(payload: SourcePriorityInput, key: str = Header(alias='Idempotency-Key', min_length=1, max_length=255),
             context: TenantContext = Depends(get_tenant_context), c=Depends(connection_dependency, scope='function')):
        with c.begin_nested():
            return run(c, context, lambda actor: sources.save_priority(c, context.tenant_id, actor, payload, key))
    return router
