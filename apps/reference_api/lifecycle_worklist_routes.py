"""Read-only audited adapter; discovery never prepares, books or acknowledges."""
from typing import Annotated
from uuid import UUID
from pydantic import Field
from .instrument_display_contracts import InstrumentDisplayView
from .instrument_display import load_instrument_displays
from fastapi import Depends,Query
from .request_audit import AuditRouter
from .tenant_context import get_tenant_context,require_actor
from .problem_details import ApiProblem
from lifecycle.worklist import list_worklist,strategy_options
from lifecycle.worklist_contracts import WorklistQuery,WorklistResponse,WorklistOptions,CouponInspection,FutureInspection,OptionInspection,StructuredInspection


class WorklistView(WorklistResponse):
    instrumentDisplays:dict[str,InstrumentDisplayView]=Field(default_factory=dict)

def lifecycle_worklist_router(connection_dependency):
    router=AuditRouter(prefix='/v1/lifecycle/worklist',tags=['Lifecycle worklist'])
    def run(read):
        try:return read()
        except PermissionError as exc:raise ApiProblem(403,'lifecycle.worklist_denied','Lifecycle worklist unavailable',str(exc)) from exc
        except LookupError as exc:raise ApiProblem(404,'lifecycle.not_found','Lifecycle context unavailable',str(exc)) from exc
        except ValueError as exc:raise ApiProblem(422,'lifecycle.invalid','Invalid worklist request',str(exc)) from exc
    @router.get('/options',response_model=WorklistOptions)
    def options(q:str=Query('',max_length=250),offset:int=Query(0,ge=0),limit:int=Query(25,ge=1,le=100),context=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return run(lambda:strategy_options(c,context.tenant_id,require_actor(context),q,offset,limit))
    @router.get('/coupon',response_model=CouponInspection)
    def coupon(strategyId:UUID,periodId:UUID,context=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        from lifecycle.worklist_coupons import inspect_coupon
        return run(lambda:inspect_coupon(c,context.tenant_id,require_actor(context),strategyId,periodId))
    @router.get('/future',response_model=FutureInspection)
    def future(strategyId:UUID,instrumentId:UUID,milestoneKind:str=Query(max_length=40),context=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        from lifecycle.worklist_futures import inspect_future
        return run(lambda:inspect_future(c,context.tenant_id,require_actor(context),strategyId,instrumentId,milestoneKind))
    @router.get('/option',response_model=OptionInspection)
    def option(strategyId:UUID,instrumentId:UUID,milestoneKind:str=Query(max_length=40),context=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        from lifecycle.worklist_options import inspect_option
        return run(lambda:inspect_option(c,context.tenant_id,require_actor(context),strategyId,instrumentId,milestoneKind))
    @router.get('/structured',response_model=StructuredInspection)
    def structured(strategyId:UUID,instrumentId:UUID,eventKey:str=Query(max_length=400),context=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        from lifecycle.worklist_structured import inspect_structured
        return run(lambda:inspect_structured(c,context.tenant_id,require_actor(context),strategyId,instrumentId,eventKey))
    @router.get('',response_model=WorklistView)
    def events(query:Annotated[WorklistQuery,Query()],context=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        def read():
            result=list_worklist(c,context.tenant_id,require_actor(context),query)
            result['instrumentDisplays']=load_instrument_displays(c,context.tenant_id,[row['instrumentId'] for row in result['items']])
            return result
        return run(read)
    return router
