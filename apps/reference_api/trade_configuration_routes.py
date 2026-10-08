"""Typed tenant-administrator endpoints for custom trade-field lifecycle."""
from datetime import datetime
from typing import Literal
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field, StrictBool
from .tenant_context import TenantContext, get_tenant_context, require_actor
from .problem_details import ApiProblem
from .trade_configuration import create_property, list_properties, retire_property, replace_property, ConfigurationConflict
from security_master_schema.tenant_workspace import TenantActionForbidden
from . import governed_trade_configuration as governed

class CatalogueCreate(BaseModel):
    code: str = Field(min_length=1,max_length=100)
    label: str = Field(min_length=1,max_length=250)
    description: str | None = Field(default=None,max_length=2000)
    reason: str = Field(min_length=1,max_length=2000)
    model_config = ConfigDict(extra="forbid")

class Reason(BaseModel):
    reason: str = Field(min_length=1,max_length=2000)
    model_config = ConfigDict(extra="forbid")

class RecordCorrection(Reason):
    label: str = Field(min_length=1,max_length=250)
    description: str | None = Field(default=None,max_length=2000)

class SelectionPublish(Reason):
    ids: list[UUID] = Field(max_length=1000)
    expectedVersion: int = Field(ge=0)

class CatalogueView(BaseModel):
    catalogueId: UUID
    code: str
    label: str
    description: str | None
    status: Literal["DRAFT","ACTIVE","RETIRED"]

class RecordView(BaseModel):
    recordVersionId: UUID
    recordId: UUID
    code: str
    label: str
    description: str | None
    versionNo: int
    status: Literal["ACTIVE","RETIRED"]

class CandidateView(BaseModel):
    id: UUID
    label: str

class SelectionView(BaseModel):
    role: Literal["COUNTERPARTY","EXECUTING_BROKER","TRADER"]
    mode: Literal["LEGACY","CURATED"]
    versionNo: int
    records: list[CandidateView]

class EventView(BaseModel):
    eventId: UUID
    action: str
    reason: str
    actorId: UUID
    recordedAtUtc: datetime
    payload: dict

class CatalogueResponse(BaseModel):
    data: CatalogueView

class CataloguesResponse(BaseModel):
    data: list[CatalogueView]

class RecordResponse(BaseModel):
    data: RecordView

class RecordsResponse(BaseModel):
    data: list[RecordView]

class SelectionResponse(BaseModel):
    data: SelectionView

class CandidatesResponse(BaseModel):
    data: list[CandidateView]

class EventsResponse(BaseModel):
    data: list[EventView]

Role = Literal["COUNTERPARTY","EXECUTING_BROKER","TRADER"]

class PropertyCreate(BaseModel):
    code:str=Field(min_length=1,max_length=100)
    label:str=Field(min_length=1,max_length=250)
    description:str|None=Field(default=None,max_length=2000)
    value_type:Literal["TEXT","INTEGER","DECIMAL","DATE","BOOLEAN","REFERENCE"]=Field(alias="valueType")
    catalogue_id:UUID|None=Field(default=None,alias="catalogueId")
    required:StrictBool=False
    choices:list[str]=Field(default_factory=list,max_length=100)
    acknowledge_required_impact:StrictBool=Field(default=False,alias="acknowledgeRequiredImpact")
    model_config=ConfigDict(extra="forbid",populate_by_name=True)

class PropertyView(BaseModel):
    definitionId:UUID
    code:str
    label:str
    description:str|None
    valueType:str
    catalogueId:UUID|None
    required:bool
    choices:list[str]
    versionNo:int
    status:Literal["ACTIVE","RETIRED"]
    createdByUserAccountId:UUID
    createdAtUtc:datetime
    retiredByUserAccountId:UUID|None
    retiredAtUtc:datetime|None

class ConfigurationPagination(BaseModel):
    limit:int
    offset:int
    total:int

class PropertiesResponse(BaseModel):
    data:list[PropertyView]
    pagination:ConfigurationPagination

class PropertyResponse(BaseModel):
    data:PropertyView

def configuration_router(connection_dependency):
    router=APIRouter(prefix="/v1/trade-configuration",tags=["Trade configuration"])
    def execute(connection,context,command,*args):
        actor=require_actor(context)
        try:
            with connection.begin_nested(): return command(connection,context.tenant_id,actor,*args)
        except TenantActionForbidden as error: raise ApiProblem(403,"authorization.denied","Forbidden","Tenant administrator and TRADING access are required.") from error
        except LookupError as error: raise ApiProblem(404,"configuration.not_found","Not found",str(error)) from error
        except ConfigurationConflict as error: raise ApiProblem(409,"configuration.conflict","Configuration conflict",str(error)) from error
        except ValueError as error: raise ApiProblem(422,"request.validation_failed","Invalid field definition",str(error)) from error

    @router.get("/properties",response_model=PropertiesResponse)
    def get_properties(limit:int=Query(default=1000,ge=1,le=1000),offset:int=Query(default=0,ge=0,le=10000),context:TenantContext=Depends(get_tenant_context),connection=Depends(connection_dependency, scope='function')):
        from sqlalchemy import select,func
        from security_master_schema import models as m
        data=execute(connection,context,list_properties,limit,offset)
        total=connection.scalar(select(func.count()).select_from(m.trade_property_definition).where(m.trade_property_definition.c.tenant_id==context.tenant_id))
        return {"data":data,"pagination":{"limit":limit,"offset":offset,"total":total}}

    @router.post("/properties",response_model=PropertyResponse,status_code=201)
    def post_property(request:PropertyCreate,context:TenantContext=Depends(get_tenant_context),connection=Depends(connection_dependency, scope='function')):
        return {"data":execute(connection,context,create_property,request.model_dump(by_alias=True))}

    @router.post("/properties/{definition_id}/retire",response_model=PropertyResponse)
    def retire(definition_id:UUID,context:TenantContext=Depends(get_tenant_context),connection=Depends(connection_dependency, scope='function')):
        return {"data":execute(connection,context,retire_property,definition_id)}

    @router.post("/properties/{definition_id}/replace",response_model=PropertyResponse,status_code=201)
    def replace(definition_id:UUID,request:PropertyCreate,context:TenantContext=Depends(get_tenant_context),connection=Depends(connection_dependency, scope='function')):
        return {"data":execute(connection,context,replace_property,definition_id,request.model_dump(by_alias=True))}
    @router.get("/catalogues", response_model=CataloguesResponse)
    def catalogues(q:str=Query(default="",max_length=250),offset:int=Query(default=0,ge=0),limit:int=Query(default=25,ge=1,le=100),context:TenantContext=Depends(get_tenant_context),connection=Depends(connection_dependency, scope='function')):
        return {"data":execute(connection,context,governed.list_catalogues,q,offset,limit)}

    @router.get("/catalogues/{catalogue_id}", response_model=CatalogueResponse)
    def catalogue(catalogue_id:UUID,context:TenantContext=Depends(get_tenant_context),connection=Depends(connection_dependency, scope='function')):
        return {"data":execute(connection,context,governed.get_catalogue,catalogue_id)}

    @router.post("/catalogues", response_model=CatalogueResponse, status_code=201)
    def new_catalogue(request:CatalogueCreate,context:TenantContext=Depends(get_tenant_context),connection=Depends(connection_dependency, scope='function')):
        return {"data":execute(connection,context,governed.create_catalogue,request.model_dump())}

    @router.post("/catalogues/{catalogue_id}/publish", response_model=CatalogueResponse)
    def publish_catalogue(catalogue_id:UUID,request:Reason,context:TenantContext=Depends(get_tenant_context),connection=Depends(connection_dependency, scope='function')):
        return {"data":execute(connection,context,governed.catalogue_lifecycle,catalogue_id,"ACTIVE",request.reason)}

    @router.post("/catalogues/{catalogue_id}/retire", response_model=CatalogueResponse)
    def retire_catalogue(catalogue_id:UUID,request:Reason,context:TenantContext=Depends(get_tenant_context),connection=Depends(connection_dependency, scope='function')):
        return {"data":execute(connection,context,governed.catalogue_lifecycle,catalogue_id,"RETIRED",request.reason)}

    @router.get("/catalogues/{catalogue_id}/records", response_model=RecordsResponse)
    def records(catalogue_id:UUID,q:str=Query(default="",max_length=250),offset:int=Query(default=0,ge=0),limit:int=Query(default=25,ge=1,le=100),history:bool=False,context:TenantContext=Depends(get_tenant_context),connection=Depends(connection_dependency, scope='function')):
        return {"data":execute(connection,context,governed.list_records,catalogue_id,q,offset,limit,history)}

    @router.post("/catalogues/{catalogue_id}/records", response_model=RecordResponse,status_code=201)
    def new_record(catalogue_id:UUID,request:CatalogueCreate,context:TenantContext=Depends(get_tenant_context),connection=Depends(connection_dependency, scope='function')):
        return {"data":execute(connection,context,governed.create_record,catalogue_id,request.model_dump())}

    @router.post("/catalogues/{catalogue_id}/records/{record_id}/correct", response_model=RecordResponse)
    def correct_record(catalogue_id:UUID,record_id:UUID,request:RecordCorrection,context:TenantContext=Depends(get_tenant_context),connection=Depends(connection_dependency, scope='function')):
        return {"data":execute(connection,context,governed.change_record,catalogue_id,record_id,request.model_dump(),request.reason)}

    @router.post("/catalogues/{catalogue_id}/records/{record_id}/retire", response_model=RecordResponse)
    def retire_record(catalogue_id:UUID,record_id:UUID,request:Reason,context:TenantContext=Depends(get_tenant_context),connection=Depends(connection_dependency, scope='function')):
        return {"data":execute(connection,context,governed.change_record,catalogue_id,record_id,None,request.reason)}

    @router.get("/selections/{role}",response_model=SelectionResponse)
    def selections(role:Role,context:TenantContext=Depends(get_tenant_context),connection=Depends(connection_dependency, scope='function')):
        return {"data":execute(connection,context,governed.selection_view,role)}

    @router.post("/selections/{role}",response_model=SelectionResponse)
    def publish_selections(role:Role,request:SelectionPublish,context:TenantContext=Depends(get_tenant_context),connection=Depends(connection_dependency, scope='function')):
        return {"data":execute(connection,context,governed.publish_selection,role,request.ids,request.expectedVersion,request.reason)}

    @router.get("/candidates/{role}",response_model=CandidatesResponse)
    def candidates(role:Role,q:str=Query(default="",max_length=250),curated:bool=True,context:TenantContext=Depends(get_tenant_context),connection=Depends(connection_dependency, scope='function')):
        return {"data":execute(connection,context,governed.selection_candidates,role,q,curated)}

    @router.get("/audit",response_model=EventsResponse)
    def events(offset:int=Query(default=0,ge=0),context:TenantContext=Depends(get_tenant_context),connection=Depends(connection_dependency, scope='function')):
        return {"data":execute(connection,context,governed.list_events,offset)}
    return router
