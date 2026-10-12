"""Tenant/module scoped policy administration and read-only preview routes."""
from uuid import UUID
from fastapi import APIRouter,Depends,Header,Response
from .tenant_context import TenantContext,get_tenant_context
from .problem_details import ApiProblem
from .contracts import MarketDataResolutionSnapshotCreate
from .valuation_policy_contracts import PolicyCreate,PolicyView,PolicyOptions,ResolutionPreview,PolicyDataOptions,PolicyCompatibility
from . import valuation_policies as policies
from .repository import IdempotencyKeyConflict,RepositoryNotFound
from market_data.display_access import EvidenceDisplayDenied


def valuation_policy_router(connection_dependency,membership):
    router=APIRouter(prefix='/v1/market-data',tags=['pricing policies'])
    def run(c,context,action):
        actor=membership(c,context)
        try:
            policies.authority(c,context.tenant_id,actor)
            return action(actor)
        except IdempotencyKeyConflict as exc:
            raise ApiProblem(409,'idempotency.key_reused','Idempotency key conflict','Key already used for another policy request.') from exc
        except RepositoryNotFound as exc:
            raise ApiProblem(404,'resource.not_found','Policy not found','Policy or reference is not available.') from exc
        except EvidenceDisplayDenied as exc:
            raise ApiProblem(403,'market_data.evidence_forbidden','Evidence access denied',str(exc)) from exc
        except PermissionError as exc:
            raise ApiProblem(403,'market_data.forbidden','Market data access required','This action requires active MARKET_DATA authority.') from exc
        except ValueError as exc:
            raise ApiProblem(422,'market_data.invalid_context','Invalid pricing policy context',str(exc)) from exc

    @router.get('/valuation-policy-options',response_model=PolicyOptions)
    def options(context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return run(c,context,lambda actor:policies.options(c,context.tenant_id,actor))

    @router.get('/policy-data-options',response_model=PolicyDataOptions)
    def data_options(context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return run(c,context,lambda actor:policies.data_options(c,context.tenant_id,actor))

    @router.post('/policy-compatibility',response_model=PolicyCompatibility)
    def compatibility(payload:PolicyCreate,context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return run(c,context,lambda actor:policies.compatibility(c,context.tenant_id,actor,payload))

    @router.get('/valuation-policies/{policy_id}',response_model=PolicyView)
    def detail(policy_id:UUID,context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return run(c,context,lambda actor:policies.policy_view(c,context.tenant_id,policy_id))

    @router.post('/valuation-policies',response_model=PolicyView,status_code=201)
    def create(payload:PolicyCreate,response:Response,
        key:str=Header(alias='Idempotency-Key',min_length=1,max_length=255),
        context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        with c.begin_nested():
            result=run(c,context,lambda actor:policies.create_policy(c,context.tenant_id,actor,payload,key))
        response.headers['Location']=f'/v1/market-data/valuation-policies/{result.valuationPolicyId}'
        return result

    @router.post('/resolution-preview',response_model=ResolutionPreview)
    def preview(payload:MarketDataResolutionSnapshotCreate,context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return run(c,context,lambda actor:policies.preview(c,context.tenant_id,actor,payload))
    return router
