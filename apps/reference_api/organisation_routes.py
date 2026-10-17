"""Trading-only organisation management; no global-reference mutation authority."""
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID
from fastapi import Depends, Query
from pydantic import BaseModel, ConfigDict, Field, StrictBool, model_validator
from security_master_schema.tenant_workspace import TenantActionForbidden
from .request_audit import AuditRouter
from .tenant_context import TenantContext, get_tenant_context, require_actor
from .problem_details import ApiProblem
from .trade_configuration import ConfigurationConflict
from . import tenant_organisations as service

OrganisationRole = Literal['COUNTERPARTY','EXECUTING_BROKER']
Revision = Annotated[int, Field(ge=0)]

class OrganisationPolicy(BaseModel):
    mode: Literal['LEGACY','CURATED']
    versionNo: int

class OrganisationRow(BaseModel):
    organisationId: UUID
    displayName: str
    legalName: str
    status: str
    leis: list[str]
    label: str | None
    internalCode: str | None
    notes: str | None
    versionNo: int
    roles: dict[OrganisationRole,bool]

class OrganisationHistory(BaseModel):
    eventId: UUID
    actorId: UUID
    reason: str
    recordedAtUtc: datetime
    changes: dict

class OrganisationDetail(OrganisationRow):
    policies: dict[OrganisationRole,OrganisationPolicy]
    history: list[OrganisationHistory]

class OrganisationPage(BaseModel):
    items: list[OrganisationRow]
    total: int
    limit: int
    offset: int
    policies: dict[OrganisationRole,OrganisationPolicy]

class OrganisationPageResponse(BaseModel):
    data: OrganisationPage

class OrganisationDetailResponse(BaseModel):
    data: OrganisationDetail

class OrganisationPoliciesResponse(BaseModel):
    data: dict[OrganisationRole,OrganisationPolicy]

class OrganisationCommand(BaseModel):
    idempotencyKey: UUID
    reason: str = Field(min_length=1,max_length=2000)
    model_config=ConfigDict(extra='forbid')

class OrganisationSave(OrganisationCommand):
    expectedVersion: Revision
    expectedRoleVersions: dict[OrganisationRole,Revision]
    label: str | None = Field(default=None,max_length=250)
    internalCode: str | None = Field(default=None,max_length=100)
    notes: str | None = Field(default=None,max_length=2000)
    roles: dict[OrganisationRole,StrictBool] = Field(default_factory=dict)

    @model_validator(mode='after')
    def role_revisions(self):
        if set(self.expectedRoleVersions)!=set(service.ROLES):
            raise ValueError('Both role revisions are required')
        return self

class OrganisationRoleActivation(OrganisationCommand):
    expectedVersion: Literal[0]
    # Bounded command size, not an organisation-population quota. Further members
    # can be added incrementally after activation.
    ids: list[UUID] = Field(default_factory=list,max_length=100)

def organisation_router(connection_dependency):
    router=AuditRouter(tags=['Tenant organisations'])

    def execute(c,context,command,*args,**kwargs):
        actor=require_actor(context)
        try:
            with c.begin_nested():return command(c,context.tenant_id,actor,*args,**kwargs)
        except TenantActionForbidden as e:
            raise ApiProblem(403,'authorization.denied','Forbidden','Trade configuration permission in Trading is required.') from e
        except LookupError as e:
            raise ApiProblem(404,'organisation.not_found','Not found','Organisation not found.') from e
        except ConfigurationConflict as e:
            raise ApiProblem(409,'organisation.conflict','Configuration conflict',str(e)) from e
        except ValueError as e:
            raise ApiProblem(422,'request.validation_failed','Invalid organisation configuration',str(e)) from e

    @router.get('/organisations',response_model=OrganisationPageResponse)
    def register(q:str=Query(default='',max_length=250),offset:int=Query(default=0,ge=0),
        limit:int=Query(default=25,ge=1,le=100),role:OrganisationRole|None=None,
        context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return dict(data=execute(c,context,service.list_organisations,q,offset,limit,role))

    @router.get('/organisations/candidates',response_model=OrganisationPageResponse)
    def candidates(q:str=Query(default='',max_length=250),offset:int=Query(default=0,ge=0),
        limit:int=Query(default=25,ge=1,le=100),context:TenantContext=Depends(get_tenant_context),
        c=Depends(connection_dependency,scope='function')):
        return dict(data=execute(c,context,service.list_organisations,q,offset,limit,candidates=True))

    @router.get('/organisations/{identifier}',response_model=OrganisationDetailResponse)
    def detail(identifier:UUID,context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return dict(data=execute(c,context,service.organisation_detail,identifier))

    @router.post('/organisations/{identifier}',response_model=OrganisationDetailResponse)
    def save(identifier:UUID,request:OrganisationSave,context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return dict(data=execute(c,context,service.save_organisation,identifier,request.model_dump(mode='json')))

    @router.post('/organisation-roles/{role}',response_model=OrganisationPoliciesResponse)
    def activate(role:OrganisationRole,request:OrganisationRoleActivation,context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return dict(data=execute(c,context,service.activate_role,role,request.model_dump(mode='json')))

    return router
