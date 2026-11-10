"""Thin audited transport for paid ceilings and tenant-owned assistance choices."""
from uuid import UUID
from fastapi import Depends,Request,Query
from .request_audit import AuditRouter
from .tenant_context import get_actor_context,get_tenant_context,require_actor
from .problem_details import ApiProblem
from lifecycle import entitlements as e,assistance as a,assistance_transitions as transitions
from lifecycle.assistance_contracts import (EventType,SubscriptionPreview,SubscriptionChange,SubscriptionView,SubscriptionChangePreview,AssistanceChange,AssistanceView,AssistanceOptions,TransitionPreview,TransitionApply,AssistanceTransitionPreview,AssistanceTransitionResult)
from security_master_schema.access_management import require_platform


def lifecycle_assistance_router(connection_dependency):
    router=AuditRouter(tags=['Lifecycle assistance'])
    def run(command):
        try:return command()
        except e.AssistanceConflict as exc:raise ApiProblem(409,'lifecycle.configuration_changed','Lifecycle configuration changed',str(exc)) from exc
        except PermissionError as exc:raise ApiProblem(403,'lifecycle.assistance_denied','Lifecycle action unavailable',str(exc)) from exc
        except LookupError as exc:raise ApiProblem(404,'lifecycle.not_found','Lifecycle configuration unavailable',str(exc)) from exc
        except ValueError as exc:raise ApiProblem(422,'lifecycle.invalid','Invalid lifecycle configuration',str(exc)) from exc
    def operator(request,actor):return getattr(request.state,'real_actor_id',actor)
    @router.get('/v1/platform/tenants/{tenant_id}/lifecycle-subscription',response_model=SubscriptionView)
    def subscription(tenant_id:UUID,actor=Depends(get_actor_context),c=Depends(connection_dependency,scope='function')):
        def read():require_platform(c,actor.user_account_id);return e.lifecycle_subscription_view(c,tenant_id)
        return run(read)
    @router.post('/v1/platform/tenants/{tenant_id}/lifecycle-subscription/preview',response_model=SubscriptionChangePreview)
    def preview(tenant_id:UUID,payload:SubscriptionPreview,actor=Depends(get_actor_context),c=Depends(connection_dependency,scope='function')):
        return run(lambda:e.preview_subscription_change(c,actor.user_account_id,tenant_id,payload.maximumTier,payload.expectedRevision))
    @router.put('/v1/platform/tenants/{tenant_id}/lifecycle-subscription',response_model=SubscriptionView)
    def change(tenant_id:UUID,payload:SubscriptionChange,request:Request,actor=Depends(get_actor_context),c=Depends(connection_dependency,scope='function')):
        return run(lambda:e.change_subscription(c,actor.user_account_id,operator(request,actor.user_account_id),tenant_id,payload))
    @router.get('/v1/lifecycle/assistance/options',response_model=AssistanceOptions)
    def options(q:str=Query(default='',max_length=250),offset:int=Query(default=0,ge=0),limit:int=Query(default=25,ge=1,le=100),context=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return run(lambda:a.assistance_options(c,context.tenant_id,require_actor(context),q,offset,limit))
    @router.get('/v1/lifecycle/assistance',response_model=AssistanceView)
    def assistance(strategyId:UUID,eventType:EventType,context=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return run(lambda:a.assistance_view(c,context.tenant_id,require_actor(context),strategyId,eventType))
    @router.post('/v1/lifecycle/assistance',response_model=AssistanceView)
    def configure(payload:AssistanceChange,request:Request,context=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        actor=require_actor(context)
        return run(lambda:a.configure_assistance(c,context.tenant_id,actor,operator(request,actor),payload))
    @router.post('/v1/lifecycle/assistance/transitions/preview',response_model=AssistanceTransitionPreview)
    def transition_preview(payload:TransitionPreview,context=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return run(lambda:transitions.preview_assistance_transition(c,context.tenant_id,require_actor(context),payload))
    @router.post('/v1/lifecycle/assistance/transitions/apply',response_model=AssistanceTransitionResult)
    def transition_apply(payload:TransitionApply,request:Request,context=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        actor=require_actor(context)
        return run(lambda:transitions.apply_assistance_transition(c,context.tenant_id,actor,operator(request,actor),payload))
    return router
