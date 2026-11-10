"""Thin read adapters for typed tenant reference sources."""
from typing import Literal
from uuid import UUID
from fastapi import Depends,Query
from pydantic import BaseModel
from .request_audit import AuditRouter
from .tenant_context import TenantContext,get_tenant_context,require_actor
from .problem_details import ApiProblem
from tenant_reference import sources

class SourceView(BaseModel):
    sourceKey:str
    kind:Literal['CANONICAL','CUSTOM']
    code:str
    label:str
    status:str
    activeEntryCount:int
    fieldCount:int

class SourcePage(BaseModel):
    items:list[SourceView]
    total:int
    limit:int
    offset:int

class OptionView(BaseModel):
    id:UUID
    label:str
    recordId:UUID|None=None
    code:str|None=None
    versionNo:int|None=None

class OptionPage(BaseModel):
    items:list[OptionView]
    total:int
    limit:int
    offset:int
    selected:list[OptionView]


def tenant_reference_router(connection_dependency):
    router=AuditRouter(prefix='/v1/tenant-reference',tags=['Tenant reference data'])
    def call(function,c,context,*args,**kwargs):
        try:return function(c,context.tenant_id,require_actor(context),*args,**kwargs)
        except PermissionError as exc:raise ApiProblem(403,'authorization.denied','Forbidden','This reference-data action is not permitted.') from exc
        except LookupError as exc:raise ApiProblem(404,'reference.not_found','Not found',str(exc)) from exc
        except ValueError as exc:raise ApiProblem(422,'reference.invalid','Invalid reference query',str(exc)) from exc
    @router.get('/sources',response_model=SourcePage)
    def listing(q:str=Query(default='',max_length=250),offset:int=Query(default=0,ge=0),limit:int=Query(default=25,ge=1,le=100),context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return call(sources.list_sources,c,context,q,offset,limit)
    @router.get('/sources/{source_key}',response_model=dict[str,object])
    def detail(source_key:str,context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return call(sources.source_detail,c,context,source_key)
    @router.get('/sources/{source_key}/entries',response_model=dict[str,object])
    def entries(source_key:str,q:str=Query(default='',max_length=250),offset:int=Query(default=0,ge=0),limit:int=Query(default=25,ge=1,le=100),history:bool=False,context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return call(sources.source_entries,c,context,source_key,query=q,offset=offset,limit=limit,history=history)
    @router.get('/sources/{source_key}/usage',response_model=dict[str,object])
    def usage(source_key:str,q:str=Query(default='',max_length=250),offset:int=Query(default=0,ge=0),limit:int=Query(default=25,ge=1,le=100),context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return call(sources.source_usage,c,context,source_key,query=q,offset=offset,limit=limit)
    @router.get('/sources/{source_key}/history',response_model=dict[str,object])
    def history(source_key:str,q:str=Query(default='',max_length=250),offset:int=Query(default=0,ge=0),limit:int=Query(default=25,ge=1,le=100),context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return call(sources.source_history,c,context,source_key,query=q,offset=offset,limit=limit)
    @router.get('/options',response_model=OptionPage)
    def options(sourceKey:str=Query(max_length=100),consumer:Literal['maintenance','booking','lifecycle']='maintenance',strategyId:UUID|None=None,q:str=Query(default='',max_length=250),offset:int=Query(default=0,ge=0),limit:int=Query(default=25,ge=1,le=100),selectedIds:list[UUID]=Query(default=[],max_length=20),context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        scope=None if consumer=='maintenance' else ('TRADE_WRITE' if consumer=='booking' else 'LIFECYCLE_READ',strategyId)
        return call(sources.list_source_options,c,context,sourceKey,consumer_context=scope,query=q,offset=offset,limit=limit,selected_ids=selectedIds)
    return router
