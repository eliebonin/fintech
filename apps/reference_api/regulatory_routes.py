"""Audited HTTP adapters for regulatory preparation, not submission transport."""
from datetime import date
from typing import Literal
from uuid import UUID
from fastapi import Depends,Query,Header
from sqlalchemy import select
from security_master_schema import models as m
from security_master_schema.strategy_access import strategy_predicate
from regulatory_reporting import service as s
from regulatory_reporting.contracts import ProfileCreate,Prepare,Review,Export
from regulatory_reporting.source import canonical
from .request_audit import AuditRouter
from .tenant_context import TenantContext,get_tenant_context
from .problem_details import ApiProblem

def regulatory_router(connection_dependency,membership):
    router=AuditRouter(prefix='/v1/regulatory-reporting',tags=['Regulatory Reporting'])
    def run(c,ctx,operation):
        actor=membership(c,ctx)
        try:return canonical(operation(actor))
        except s.Conflict as exc:raise ApiProblem(409,'reporting.conflict','Reporting state changed',str(exc)) from exc
        except PermissionError as exc:raise ApiProblem(403,'reporting.forbidden','Access denied',str(exc)) from exc
        except LookupError as exc:raise ApiProblem(404,'resource.not_found','Not found',str(exc)) from exc
        except ValueError as exc:raise ApiProblem(422,'reporting.invalid','Invalid reporting input',str(exc)) from exc

    @router.get('/options',response_model=dict[str,object])
    def options(for_action:Literal['REPORTING_READ','REPORTING_PREPARE','REPORTING_EXPORT']=Query('REPORTING_READ',alias='forAction'),
        ctx:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        def operation(actor):
            s.authority(c,ctx.tenant_id,actor,for_action)
            return dict(profiles=s.profiles(c,ctx.tenant_id,actor),strategies=[dict(id=str(r.strategy_id),name=r.display_name)
                for r in c.execute(select(m.strategy.c.strategy_id,m.strategy.c.display_name).where(m.strategy.c.tenant_id==ctx.tenant_id,
                    strategy_predicate(c,ctx.tenant_id,actor,for_action,m.strategy.c.strategy_id)).order_by(m.strategy.c.display_name))])
        return run(c,ctx,operation)

    @router.get('/profiles',response_model=dict[str,object])
    def profiles(ctx:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return run(c,ctx,lambda actor:dict(items=s.profiles(c,ctx.tenant_id,actor)))

    @router.post('/profiles',status_code=201,response_model=dict[str,object])
    def create_profile(data:ProfileCreate,ctx:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return run(c,ctx,lambda actor:s.save_profile(c,ctx.tenant_id,actor,data))

    @router.post('/profiles/{profile_id}',response_model=dict[str,object])
    def update_profile(profile_id:UUID,data:ProfileCreate,ctx:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return run(c,ctx,lambda actor:s.save_profile(c,ctx.tenant_id,actor,data,profile_id))

    @router.post('/prepare',response_model=dict[str,object])
    def prepare(data:Prepare,ctx:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return run(c,ctx,lambda actor:s.prepare(c,ctx.tenant_id,actor,data))

    def scope(profile_id:UUID=Query(alias='profileId'),strategy_id:UUID=Query(alias='strategyId'),
        start:date=Query(alias='fromDate'),end:date=Query(alias='toDate')):
        if start>end:raise ApiProblem(422,'reporting.invalid','Invalid reporting period','Opening date must not follow closing date')
        return Prepare(profileId=profile_id,strategyId=strategy_id,fromDate=start,toDate=end)

    @router.get('/candidates',response_model=dict[str,object])
    def candidates(data:Prepare=Depends(scope),status:Literal['ALL','READY','HELD','NOT_REPORTABLE','NEEDS_ATTENTION']='ALL',
        limit:int=Query(25,ge=1,le=100),offset:int=Query(0,ge=0),ctx:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return run(c,ctx,lambda actor:s.candidates(c,ctx.tenant_id,actor,data,status=status,limit=limit,offset=offset))

    @router.get('/candidates/{candidate_id}',response_model=dict[str,object])
    def detail(candidate_id:UUID,ctx:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return run(c,ctx,lambda actor:s.detail(c,ctx.tenant_id,actor,candidate_id))

    @router.post('/candidates/{candidate_id}/review',response_model=dict[str,object])
    def review(candidate_id:UUID,data:Review,ctx:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return run(c,ctx,lambda actor:s.review(c,ctx.tenant_id,actor,candidate_id,data))

    @router.get('/export-preview',response_model=dict[str,object])
    def preview(data:Prepare=Depends(scope),ctx:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return run(c,ctx,lambda actor:s.export_preview(c,ctx.tenant_id,actor,data))

    @router.post('/exports',status_code=201,response_model=dict[str,object])
    def export(data:Export,key:str=Header(alias='Idempotency-Key',min_length=1,max_length=200),
        ctx:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return run(c,ctx,lambda actor:s.create_export(c,ctx.tenant_id,actor,data,key))

    @router.get('/exports',response_model=dict[str,object])
    def exports(limit:int=Query(25,ge=1,le=100),offset:int=Query(0,ge=0),ctx:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return run(c,ctx,lambda actor:s.exports(c,ctx.tenant_id,actor,limit=limit,offset=offset))

    @router.get('/exports/{export_id}',response_model=dict[str,object])
    def download(export_id:UUID,ctx:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return run(c,ctx,lambda actor:s.download(c,ctx.tenant_id,actor,export_id))
    return router
