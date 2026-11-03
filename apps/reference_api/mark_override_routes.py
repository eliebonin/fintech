"""Audited transport for domain-owned reviewed manual marks."""
from uuid import UUID
from fastapi import Depends,Header,Request
from .request_audit import AuditRouter
from .tenant_context import TenantContext,get_tenant_context
from .problem_details import ApiProblem
from valuation.mark_override_contracts import MarkOverrideCreate,MarkOverrideDecision,MarkOverrideReviewView
from valuation import mark_overrides


def mark_override_router(connection_dependency,authorize):
    router=AuditRouter(tags=['valuation and P&L'])
    def run(fn):
        try:return fn()
        except PermissionError as exc:raise ApiProblem(403,'valuation.mark_forbidden','Manual mark access denied',str(exc)) from exc
        except LookupError as exc:raise ApiProblem(404,'resource.not_found','Not found','Manual mark or valuation input not found.') from exc
        except ValueError as exc:raise ApiProblem(409,'valuation.mark_conflict','Manual mark cannot proceed',str(exc)) from exc

    @router.get('/batches/{batch_id}/mark-overrides',response_model=MarkOverrideReviewView)
    def review(batch_id:UUID,request:Request,context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        actor,_=authorize(c,context)
        return run(lambda:mark_overrides.review_view(c,context.tenant_id,actor,batch_id,real_operator_id=getattr(request.state,'real_actor_id',actor)))

    @router.post('/mark-overrides',response_model=dict[str,UUID],status_code=201)
    def create(payload:MarkOverrideCreate,request:Request,key:str=Header(alias='Idempotency-Key',min_length=1,max_length=255),
               context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        actor,_=authorize(c,context,True)
        return run(lambda:dict(requestId=mark_overrides.request_mark(c,context.tenant_id,actor,payload,key,real_operator_id=getattr(request.state,'real_actor_id',actor))))

    def decide(request_id,payload,request,context,c,action):
        actor,_=authorize(c,context,True)
        return run(lambda:dict(decisionId=mark_overrides.decide_mark(c,context.tenant_id,request_id,actor,action,payload.comment,
            real_operator_id=getattr(request.state,'real_actor_id',actor))))

    @router.post('/mark-overrides/{request_id}/approve',response_model=dict[str,UUID])
    def approve(request_id:UUID,payload:MarkOverrideDecision,request:Request,context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return decide(request_id,payload,request,context,c,'APPROVED')

    @router.post('/mark-overrides/{request_id}/reject',response_model=dict[str,UUID])
    def reject(request_id:UUID,payload:MarkOverrideDecision,request:Request,context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return decide(request_id,payload,request,context,c,'REJECTED')

    @router.post('/mark-overrides/{request_id}/withdraw',response_model=dict[str,UUID])
    def withdraw(request_id:UUID,payload:MarkOverrideDecision,request:Request,context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return decide(request_id,payload,request,context,c,'WITHDRAWN')
    return router
