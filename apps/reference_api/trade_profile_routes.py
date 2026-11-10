"""Audited HTTP adapter for reusable profiles and explicitly reviewed adoption."""
from datetime import datetime
from uuid import UUID
from fastapi import Depends,Query
from pydantic import BaseModel,ConfigDict,Field
from tenant_reference.errors import ConfigurationConflict
from trading.profiles import configuration as commands,management
from trading.profiles.contracts import ProfileVersionInput,FieldRule,ConfigurationView
from .request_audit import AuditRouter
from .tenant_context import TenantContext,get_tenant_context,require_actor
from .problem_details import ApiProblem


class CreateProfile(ProfileVersionInput):
    code:str=Field(min_length=1,max_length=100)

class VersionView(BaseModel):
    profileStatus:str
    versionId:UUID
    profileId:UUID
    versionNo:int
    label:str
    description:str|None
    reason:str
    contentHash:str
    fields:list[FieldRule]
    fieldLabels:dict[str,str]
    publishedAt:datetime

class ProfileRow(BaseModel):
    profileId:UUID
    code:str
    status:str
    versionId:UUID|None
    versionNo:int|None
    label:str

class ProfilePage(BaseModel):
    items:list[ProfileRow]
    total:int
    offset:int
    limit:int

class PagedRows(BaseModel):
    items:list[dict[str,object]]
    total:int
    offset:int
    limit:int

class DefaultInput(BaseModel):
    profileVersionId:UUID
    expectedRevision:int=Field(ge=0,strict=True)
    reason:str=Field(min_length=1,max_length=2000)
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)

class PreviewInput(BaseModel):
    profileVersionId:UUID
    model_config=ConfigDict(extra='forbid')

class AdoptInput(DefaultInput):
    inputHash:str=Field(pattern=r'^[a-f0-9]{64}$')

class BatchPreviewInput(BaseModel):
    profileVersionId:UUID
    strategyIds:list[UUID]=Field(min_length=1,max_length=1000)
    model_config=ConfigDict(extra='forbid')

class BatchAssignment(BaseModel):
    strategyId:UUID
    expectedRevision:int=Field(ge=0,strict=True)
    inputHash:str=Field(pattern=r'^[a-f0-9]{64}$')
    model_config=ConfigDict(extra='forbid')

class BatchApplyInput(BaseModel):
    profileVersionId:UUID
    assignments:list[BatchAssignment]=Field(min_length=1,max_length=1000)
    reason:str=Field(min_length=1,max_length=2000)
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)

class ReasonInput(BaseModel):
    reason:str=Field(min_length=1,max_length=2000)
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)

class PreviewView(BaseModel):
    strategyId:UUID
    allowed:bool
    issues:list[str]
    affectedTradeCount:int
    inputHash:str
    assignmentRevision:int

class AssignmentView(BaseModel):
    strategyId:UUID
    profileVersionId:UUID
    revision:int

class DefaultView(BaseModel):
    profileVersionId:UUID|None
    revision:int
    profileId:UUID|None=None
    label:str|None=None
    versionNo:int|None=None
    reason:str|None=None



def profile_router(connection_dependency):
    router=AuditRouter(prefix='/v1/trade-profiles',tags=['Trade profiles'])

    def call(function,c,context,*args,**kwargs):
        try:return function(c,context.tenant_id,require_actor(context),*args,**kwargs)
        except PermissionError as exc:raise ApiProblem(403,'authorization.denied','Forbidden','This profile action is not permitted.') from exc
        except ConfigurationConflict as exc:raise ApiProblem(409,'profile.changed','Review required',str(exc)) from exc
        except LookupError as exc:raise ApiProblem(404,'profile.not_found','Not found',str(exc)) from exc
        except ValueError as exc:raise ApiProblem(422,'profile.invalid','Invalid profile',str(exc)) from exc

    @router.get('',response_model=ProfilePage)
    def listing(q:str=Query(default='',max_length=250),offset:int=Query(default=0,ge=0),limit:int=Query(default=25,ge=1,le=100),context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return call(commands.list_profiles,c,context,q,offset,limit)

    @router.post('',response_model=VersionView,status_code=201)
    def create(request:CreateProfile,context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        # One transaction/savepoint: no orphan identity after failed publication.
        with c.begin_nested():
            identity=call(commands.create_profile,c,context,request.code,request.label,request.reason)
            return call(commands.publish_profile_version,c,context,identity['profileId'],request.model_dump(exclude={'code'},by_alias=True))

    @router.get('/field-library',response_model=PagedRows)
    def fields(history:bool=False,q:str=Query(default='',max_length=250),offset:int=Query(default=0,ge=0),limit:int=Query(default=25,ge=1,le=100),context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return call(management.field_library,c,context,q,offset,limit,history)

    @router.get('/assignment-targets',response_model=PagedRows)
    def targets(q:str=Query(default='',max_length=250),offset:int=Query(default=0,ge=0),limit:int=Query(default=25,ge=1,le=100),context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return call(management.assignment_targets,c,context,q,offset,limit)

    @router.post('/assignments/preview',response_model=dict[str,object])
    def batch_preview(request:BatchPreviewInput,context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return call(management.preview_assignments,c,context,request.strategyIds,request.profileVersionId)

    @router.post('/assignments',response_model=dict[str,object])
    def batch_apply(request:BatchApplyInput,context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return call(management.adopt_assignments,c,context,request.profileVersionId,[row.model_dump() for row in request.assignments],request.reason)

    @router.get('/creation-default',response_model=DefaultView)
    def creation_default(context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return call(management.creation_default,c,context)

    @router.get('/default',response_model=DefaultView)
    def default(context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return call(management.default_profile,c,context)

    @router.post('/default',response_model=DefaultView)
    def set_default(request:DefaultInput,context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return call(management.set_default,c,context,request.profileVersionId,request.expectedRevision,request.reason)

    @router.get('/strategies/{strategy_id}',response_model=ConfigurationView)
    def strategy(strategy_id:UUID,context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return call(management.strategy_configuration,c,context,strategy_id)

    @router.post('/strategies/{strategy_id}/preview',response_model=PreviewView)
    def preview(strategy_id:UUID,request:PreviewInput,context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return call(management.preview_assignment,c,context,strategy_id,request.profileVersionId)

    @router.post('/strategies/{strategy_id}',response_model=AssignmentView)
    def adopt(strategy_id:UUID,request:AdoptInput,context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return call(management.adopt_assignment,c,context,strategy_id,request.profileVersionId,request.expectedRevision,request.inputHash,request.reason)

    @router.get('/versions/{version_id}',response_model=VersionView)
    def version(version_id:UUID,context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return call(commands.profile_version,c,context,version_id)

    @router.get('/{profile_id}/versions',response_model=PagedRows)
    def versions(profile_id:UUID,offset:int=Query(default=0,ge=0),limit:int=Query(default=25,ge=1,le=100),context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return call(management.list_versions,c,context,profile_id,offset,limit)

    @router.post('/{profile_id}/versions',response_model=VersionView,status_code=201)
    def publish(profile_id:UUID,request:ProfileVersionInput,context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return call(commands.publish_profile_version,c,context,profile_id,request)

    @router.get('/{profile_id}/usage',response_model=PagedRows)
    def usage(profile_id:UUID,q:str=Query(default='',max_length=250),offset:int=Query(default=0,ge=0),limit:int=Query(default=25,ge=1,le=100),context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return call(management.profile_usage,c,context,profile_id,q,offset,limit)

    @router.get('/{profile_id}/history',response_model=PagedRows)
    def history(profile_id:UUID,offset:int=Query(default=0,ge=0),limit:int=Query(default=25,ge=1,le=100),context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return call(management.profile_history,c,context,profile_id,offset,limit)

    @router.post('/{profile_id}/retire',response_model=dict[str,object])
    def retire(profile_id:UUID,request:ReasonInput,context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return call(management.retire_profile,c,context,profile_id,request.reason)
    return router
