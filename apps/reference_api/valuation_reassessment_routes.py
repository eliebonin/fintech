"""Strategy-scoped reassessment metadata and explicit staged recalculation."""
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict, field_validator
from fastapi import Depends, Header, Query, Request
from sqlalchemy import select, func, or_, exists
from valuation import tables as t, storage
from valuation.ledger_impacts import source_health
from valuation.reassessment import recalculate
from security_master_schema import models as m
from security_master_schema.strategy_access import request_strategy_predicate, require_strategy_action
from .tenant_context import get_tenant_context, TenantContext
from .problem_details import ApiProblem, current_request_id


class RecalculateSelection(BaseModel):
    batchIds:list[UUID]=Field(min_length=1,max_length=25)
    reason:str=Field(min_length=1,max_length=2000)
    confirmRecalculation:Literal[True]
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)

    @field_validator('batchIds')
    @classmethod
    def unique(cls, values):
        if len(set(values))!=len(values): raise ValueError('Select each batch once')
        return values

    @field_validator('reason')
    @classmethod
    def explained(cls,value):
        if not value: raise ValueError('Reason required')
        return value


def register_reassessment_routes(router,authorize,connection_dependency,engine_factory,configure_transaction):
    @router.get('/reassessments',response_model=dict[str,object])
    def listing(limit:int=Query(25,ge=1,le=100),offset:int=Query(0,ge=0,le=10000),strategy_id:UUID|None=None,
                context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        actor,_=authorize(c,context)
        b=t.batch; change=t.ledger_change
        stale=exists(select(change.c.change_id).where(change.c.tenant_id==b.c.tenant_id,change.c.strategy_id==b.c.strategy_id,
            change.c.economic_from<=b.c.value_date,change.c.revision>func.coalesce(b.c.summary['ledgerSource']['revision'].as_integer(),-1)))
        from valuation.cash_fx_health import cash_reassessment_predicate
        from valuation.accrued_balance_health import balance_reassessment_predicate
        where=[b.c.tenant_id==context.tenant_id,b.c.status.in_(['STAGED','PUBLISHED']),
            request_strategy_predicate(c,context.tenant_id,'VALUATION_READ',b.c.strategy_id),
            or_(b.c.summary['ledgerSource']['revision'].as_integer().is_(None),stale,cash_reassessment_predicate(b),balance_reassessment_predicate(b))]
        if strategy_id: where.append(b.c.strategy_id==strategy_id)
        rows=c.execute(select(b,m.strategy.c.display_name.label('strategy_name'),m.strategy.c.strategy_code).join(
            m.strategy,m.strategy.c.strategy_id==b.c.strategy_id).where(*where,m.strategy.c.tenant_id==context.tenant_id)
            .order_by(b.c.value_date.desc(),b.c.batch_id.desc()).limit(limit).offset(offset)).mappings()
        return dict(items=[dict(batchId=str(row['batch_id']),strategyId=str(row['strategy_id']),valueDate=row['value_date'].isoformat(),
            strategyLabel=f"{row['strategy_name']} · {row['strategy_code']}",publicationStatus=row['status'],sourceHealth=source_health(c,row)) for row in rows],
            total=c.scalar(select(func.count()).select_from(b).where(*where)))

    @router.post('/reassessments/recalculate',response_model=dict[str,object])
    def recalc(payload:RecalculateSelection,http_request:Request,key:str=Header(alias='Idempotency-Key',min_length=1,max_length=255),
               context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        actor,_=authorize(c,context,True)
        batches=[]
        scopes=set()
        from valuation.evidence_access import assert_batch_display
        for identity in payload.batchIds:
            row=c.execute(select(t.batch).where(t.batch.c.tenant_id==context.tenant_id,t.batch.c.batch_id==identity,
                request_strategy_predicate(c,context.tenant_id,'VALUATION_READ',t.batch.c.strategy_id))).mappings().one_or_none()
            if row is None: raise ApiProblem(404,'resource.not_found','Not found','Batch unavailable')
            scope=(row['strategy_id'],row['value_date'])
            if scope in scopes: raise ApiProblem(409,'valuation.request_conflict','Duplicate valuation date','Select only one base revision per strategy and valuation date.')
            scopes.add(scope)
            try:
                require_strategy_action(c,context.tenant_id,actor,'VALUATION_RUN',row['strategy_id'])
                batch=storage.batch_view(c,context.tenant_id,identity);assert_batch_display(c,context.tenant_id,batch)
            except PermissionError as error: raise ApiProblem(403,'valuation.forbidden','Recalculation unavailable','Calculation and current evidence access required') from error
            batches.append(batch)
        try:
            return recalculate(engine_factory(),context.tenant_id,actor,batches,payload.reason,key,current_request_id(),
                operator=getattr(http_request.state,'real_actor_id',actor),configure_transaction=configure_transaction)
        except ValueError as error: raise ApiProblem(409,'valuation.request_conflict','Recalculation conflict',str(error)) from error
