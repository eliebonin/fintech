"""HTTP adapter for governed instrument-creation configuration."""
from datetime import date
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from security_master_schema.creation_options import equity_creation_options
from security_master_schema.reference_authority import require_reference_action
from security_master_schema.tenant_workspace import TenantActionForbidden
from .tenant_context import TenantContext, get_tenant_context, require_actor
from .problem_details import ApiProblem


class EquityCreationOption(BaseModel):
    sourceSystemId: UUID
    sourceName: str
    sourceNamespace: str
    policyCode: str
    policyName: str
    policyVersion: int


class EquityCreationOptionsResponse(BaseModel):
    data: list[EquityCreationOption]


def reference_creation_router(connection_dependency):
    router=APIRouter(tags=['Instrument creation'])

    @router.get('/v1/equity-creation-options',response_model=EquityCreationOptionsResponse)
    def choices(effectiveDate:date=Query(),context:TenantContext=Depends(get_tenant_context),
        c=Depends(connection_dependency,scope='function')):
        try:require_reference_action(c,context.tenant_id,require_actor(context))
        except TenantActionForbidden as exc:raise ApiProblem(403,'authorization.denied','Forbidden','Instrument proposal permission is required.') from exc
        return dict(data=equity_creation_options(c,context.tenant_id,effectiveDate))

    return router
