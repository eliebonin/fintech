"""HTTP adapter for exact, retained Ops interest reviews."""
from datetime import date,datetime,timedelta,timezone
from uuid import UUID
from fastapi import Depends,Header,Query
from security_master_schema.command_audit import current_command
from valuation import interest_review as service
from valuation.interest_review_contracts import ReviewCommand
from valuation.economics import canonical_payload
from valuation.accruals import read_accruals
from .request_audit import AuditRouter
from .tenant_context import TenantContext,get_tenant_context
from .valuation_input_routes import input_authority,assert_input_display
from .problem_details import ApiProblem


def interest_review_router(connection_dependency,membership):
    router=AuditRouter(prefix='/v1/valuation',tags=['daily interest operations'])

    def operation(c,context,strategy,day,fn,write=False):
        actor=input_authority(c,context,membership,write)
        try:
            service.balances.authorize(c,context.tenant_id,actor,strategy,write)
            if day<=date.min+timedelta(days=40):raise ValueError('Value date needs preceding benchmark history')
            assert_input_display(c,context.tenant_id,read_accruals(c,context.tenant_id,strategy,day-timedelta(days=40),day,datetime.now(timezone.utc)))
            return canonical_payload(fn(actor))
        except PermissionError as exc:raise ApiProblem(403,'valuation.forbidden','Access denied',str(exc)) from exc
        except ValueError as exc:raise ApiProblem(422,'valuation.invalid_review','Review cannot proceed',str(exc)) from exc

    @router.get('/interest-review',response_model=dict[str,object])
    def view(strategy:UUID=Query(alias='strategyId'),day:date=Query(alias='valueDate'),stage:str=Query(default='DAILY',pattern='^(DAILY|BALANCE)$'),
        context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return operation(c,context,strategy,day,lambda actor:service.review_view(c,context.tenant_id,actor,strategy,day,stage))

    @router.post('/interest-review',status_code=201,response_model=dict[str,object])
    def save(payload:ReviewCommand,key:str=Header(alias='Idempotency-Key',min_length=1,max_length=180),
        context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        def command(actor):
            audit=current_command()
            operator=audit.operator if audit else actor
            return service.save_review(c,context.tenant_id,actor,operator,payload,key)
        return operation(c,context,payload.strategy_id,payload.value_date,command,True)
    return router
