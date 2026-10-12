"""Review actions enforce tenant, entitlement and independent approval."""
from uuid import UUID
from fastapi import APIRouter,Depends,Header,Request
from sqlalchemy import select
from valuation import tables as t,storage
from valuation.amendments import request_component_change,approve_component_change,reject_component_change
from valuation.evidence_access import assert_batch_display
from valuation.economics import canonical_payload
from .valuation_input_routes import input_authority
from .valuation_amendment_contracts import ComponentChange
from .valuation_contracts import ReviewComment
from .tenant_context import TenantContext,get_tenant_context
from .problem_details import ApiProblem


def valuation_amendment_router(connection_dependency,membership):
    router=APIRouter(prefix='/v1/valuation',tags=['valuation amendments'])

    def action(c,context,operation):
        actor=input_authority(c,context,membership,True)
        try: return operation(actor)
        except PermissionError as exc: raise ApiProblem(403,'valuation.evidence_forbidden','Evidence access denied',str(exc)) from exc
        except LookupError as exc: raise ApiProblem(404,'resource.not_found','Not found','Amendment reference unavailable.') from exc
        except ValueError as exc: raise ApiProblem(409,'valuation.amendment_conflict','Amendment cannot proceed',str(exc)) from exc

    @router.get('/batches/{batch_id}/amendments',response_model=dict[str,object])
    def history(batch_id:UUID,context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        input_authority(c,context,membership)
        try:
            base=storage.batch_view(c,context.tenant_id,batch_id);assert_batch_display(c,context.tenant_id,base)
            rows=c.execute(select(t.amendment).where(t.amendment.c.tenant_id==context.tenant_id,
                (t.amendment.c.base_batch_id==batch_id)|(t.amendment.c.applied_batch_id==batch_id))
                .order_by(t.amendment.c.created_at,t.amendment.c.request_id)).mappings().all()
            return {'items':canonical_payload([dict(row) for row in rows])}
        except PermissionError as exc: raise ApiProblem(403,'valuation.evidence_forbidden','Evidence access denied',str(exc)) from exc
        except LookupError as exc: raise ApiProblem(404,'resource.not_found','Not found','Review batch not found.') from exc

    @router.post('/batches/{batch_id}/amendments',status_code=201,response_model=dict[str,str])
    def create(batch_id:UUID,payload:ComponentChange,http_request:Request,key:str=Header(alias='Idempotency-Key',min_length=1,max_length=255),
        context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return action(c,context,lambda actor:{'requestId':str(request_component_change(c,context.tenant_id,batch_id,payload.attribution_id,
            actor,payload.model_dump(by_alias=True,exclude={'attribution_id'}),key,
            real_operator_id=getattr(http_request.state,'real_actor_id',actor)))})

    @router.post('/amendments/{request_id}/approve',response_model=dict[str,object])
    def approve(request_id:UUID,payload:ReviewComment,http_request:Request,context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        def apply(actor):
            batch=approve_component_change(c,context.tenant_id,request_id,actor,payload.comment,
                real_operator_id=getattr(http_request.state,'real_actor_id',actor))
            return {'status':'APPLIED' if batch else 'STALE','batch':canonical_payload(storage.batch_view(c,context.tenant_id,batch)) if batch else None}
        return action(c,context,apply)

    @router.post('/amendments/{request_id}/reject',response_model=dict[str,str])
    def reject(request_id:UUID,payload:ReviewComment,http_request:Request,context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return action(c,context,lambda actor:{'requestId':str(reject_component_change(c,context.tenant_id,request_id,actor,payload.comment,
            real_operator_id=getattr(http_request.state,'real_actor_id',actor))),'status':'REJECTED'})
    return router
