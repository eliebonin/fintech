"""Selected-tenant calendar management and read-only schedule inspection."""
from datetime import date
from uuid import UUID
from fastapi import APIRouter, Depends, Header
from .tenant_context import TenantContext,get_tenant_context
from .problem_details import ApiProblem
from .calendar_contracts import CalendarPublish,CalendarView,CalendarDaysView,CalendarOptions,CalendarAssignmentCreate,CalendarAssignmentView
from . import calendar_service as service
from .repository import RepositoryNotFound,IdempotencyKeyConflict

def calendar_router(connection_dependency,membership):
    router=APIRouter(prefix='/v1/market-data/calendars',tags=['calendars'])
    def run(c,context,action):
        actor=membership(c,context)
        try:
            service.authority(c,context.tenant_id,actor)
            return action(actor)
        except RepositoryNotFound as exc: raise ApiProblem(404,'resource.not_found','Calendar not found','Calendar is not available.') from exc
        except IdempotencyKeyConflict as exc: raise ApiProblem(409,'idempotency.key_reused','Submission key conflict','Retry unchanged or use a new submission key.') from exc
        except PermissionError as exc: raise ApiProblem(403,'market_data.forbidden','Calendar authority required',str(exc)) from exc
        except ValueError as exc: raise ApiProblem(422,'calendar.invalid_context','Invalid calendar configuration',str(exc)) from exc
    @router.get('/options',response_model=CalendarOptions)
    def options(context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return run(c,context,lambda actor:service.options(c,context.tenant_id,actor))
    @router.post('',response_model=CalendarView,status_code=201)
    def publish(payload:CalendarPublish,key:str=Header(alias='Idempotency-Key',min_length=1,max_length=255),context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        with c.begin_nested(): return run(c,context,lambda actor:service.publish_calendar(c,context.tenant_id,actor,payload,key))
    @router.post('/assignments',response_model=CalendarAssignmentView,status_code=201)
    def assign(payload:CalendarAssignmentCreate,key:str=Header(alias='Idempotency-Key',min_length=1,max_length=255),context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        with c.begin_nested(): return run(c,context,lambda actor:service.assign_calendar(c,context.tenant_id,actor,payload,key))
    @router.get('/{calendar_id}',response_model=CalendarView)
    def detail(calendar_id:UUID,context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return run(c,context,lambda actor:service.calendar_view(c,context.tenant_id,calendar_id))
    @router.get('/{calendar_id}/days',response_model=CalendarDaysView)
    def days(calendar_id:UUID,fromDate:date,toDate:date,context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return run(c,context,lambda actor:dict(calendarId=calendar_id,days=service.calendar_days(c,service.get_calendar(c,context.tenant_id,calendar_id),fromDate,toDate)))
    return router
