"""Audited, strategy-scoped NEW trade import commands and private receipts."""
import csv
from io import StringIO
from uuid import UUID
from typing import Annotated
from fastapi import Depends,Header,Query,Response
from pydantic import BaseModel,ConfigDict,Field
from sqlalchemy import select
from .request_audit import AuditRouter
from .tenant_context import TenantContext,get_tenant_context
from .problem_details import ApiProblem,current_request_id
from .booking_errors import RepositoryNotFound
from security_master_schema.tenant_workspace import TenantActionForbidden
from security_master_schema.strategy_access import strategy_predicate
from security_master_schema import models as m
from . import import_service as service
from data_imports.formats import render_template
from .import_adapters.trades import descriptor


class ImportCreate(BaseModel):
    strategy_id: UUID=Field(alias='strategyId')
    source: str=Field(min_length=1,max_length=100,pattern=r'^[A-Za-z0-9][A-Za-z0-9_.-]*$')
    filename: str=Field(min_length=1,max_length=200)
    content_base64: str=Field(alias='contentBase64',min_length=1,max_length=700000)
    model_config=ConfigDict(extra='forbid')


class ImportConfirm(BaseModel):
    review_hash: str=Field(alias='reviewHash',pattern=r'^[0-9a-f]{64}$')
    model_config=ConfigDict(extra='forbid')


def import_router(connection_dependency,membership):
    router=AuditRouter(prefix='/v1/trades/imports',tags=['trade imports'])

    def call(c,context,operation):
        actor=membership(c,context)
        try:return operation(actor)
        except (TenantActionForbidden,PermissionError) as exc:
            raise ApiProblem(403,'import.forbidden','Import access denied','Current strategy and trade permissions are required.') from exc
        except RepositoryNotFound as exc:raise ApiProblem(404,'import.not_found','Import unavailable','Import or reference not found in the current scope.') from exc
        except service.ImportConflict as exc:raise ApiProblem(409,'import.conflict','Import needs review',str(exc)) from exc
        except ValueError as exc:raise ApiProblem(422,'import.invalid','Invalid import',str(exc)) from exc

    @router.get('/options',response_model=dict[str,object])
    def options(context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        def read(actor):
            predicate=strategy_predicate(c,context.tenant_id,actor,'TRADE_WRITE',m.strategy.c.strategy_id)
            rows=c.execute(select(m.strategy.c.strategy_id,m.strategy.c.display_name).where(m.strategy.c.tenant_id==context.tenant_id,
                m.strategy.c.status=='ACTIVE',predicate).order_by(m.strategy.c.display_name,m.strategy.c.strategy_id))
            return dict(strategies=[dict(id=str(r[0]),label=r[1]) for r in rows],maxRows=500,maxBytes=524288,products=['EQUITY','ETF','FUND','FUND_SHARE_CLASS'])
        return call(c,context,read)

    @router.get('/template')
    def template(strategyId:UUID,context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        data=call(c,context,lambda actor:render_template(descriptor(c,context.tenant_id,actor,strategyId)))
        return Response(data,media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={'Content-Disposition':'attachment; filename="trade-upload-template.xlsx"','Cache-Control':'private, no-store'})

    @router.get('',response_model=dict[str,object])
    def history(offset:int=Query(0,ge=0),limit:int=Query(25,ge=1,le=100),context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return call(c,context,lambda actor:service.listing(c,context.tenant_id,actor,offset,limit))

    @router.post('',status_code=201,response_model=dict[str,object])
    def create(payload:ImportCreate,key:str=Header(alias='Idempotency-Key',min_length=1,max_length=255),
        context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return call(c,context,lambda actor:service.submit(c,context.tenant_id,actor,payload,key))

    @router.get('/{job_id}',response_model=dict[str,object])
    def detail(job_id:UUID,offset:int=Query(0,ge=0),limit:int=Query(50,ge=1,le=100),
        context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return call(c,context,lambda actor:service.view(service.load(c,context.tenant_id,actor,job_id),offset,limit))

    @router.post('/{job_id}/validate',response_model=dict[str,object])
    def validate(job_id:UUID,context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return call(c,context,lambda actor:service.validate(c,context.tenant_id,actor,job_id))

    @router.post('/{job_id}/confirm',response_model=dict[str,object])
    def confirm(job_id:UUID,payload:ImportConfirm,key:str=Header(alias='Idempotency-Key',min_length=1,max_length=255),
        context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return call(c,context,lambda actor:service.confirm(c,context.tenant_id,actor,job_id,payload.review_hash,current_request_id()))

    @router.get('/{job_id}/errors')
    def errors(job_id:UUID,context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        item=call(c,context,lambda actor:service.load(c,context.tenant_id,actor,job_id))
        out=StringIO();writer=csv.writer(out);writer.writerow(['Sheet','Row','Source trade ID','Field','Code','Message'])
        def safe(value):
            value=str(value)
            return "'"+value if value.lstrip().startswith(('=','+','-','@','\t','\r')) else value
        for row in item['report'].get('rows',[]):
            for issue in row.get('errors',[]):writer.writerow([safe(v) for v in ['Trades',row['row'],row['sourceTradeId'],issue['field'],issue['code'],issue['message']]])
        return Response(out.getvalue(),media_type='text/csv',headers={'Content-Disposition':'attachment; filename="trade-import-errors.csv"','Cache-Control':'private, no-store'})

    @router.get('/{job_id}/artifact')
    def artifact(job_id:UUID,context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        item=call(c,context,lambda actor:service.load(c,context.tenant_id,actor,job_id))
        extension='xlsx' if item['filename'].lower().endswith('.xlsx') else 'csv'
        return Response(item['artifact'],media_type='application/octet-stream',headers={
            'Content-Disposition':f'attachment; filename="original-trades.{extension}"','Cache-Control':'private, no-store',
            'X-Content-Type-Options':'nosniff'})
    return router
