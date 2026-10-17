"""Tenant/strategy-scoped cash register and policy-backed translated preview."""
from datetime import date
from uuid import UUID
from fastapi import Depends,Header,Query
from .request_audit import AuditRouter as APIRouter
from sqlalchemy import select
from security_master_schema import models as m
from valuation import cash_snapshots as cash
from valuation.economics import canonical_payload
from .cash_snapshot_contracts import CashAccountCreate,CashUpload,CashPreview
from .tenant_context import TenantContext,get_tenant_context
from .valuation_input_routes import input_authority
from .problem_details import ApiProblem


def cash_snapshot_router(connection_dependency,membership):
    router=APIRouter(prefix='/v1/valuation',tags=['dated cash snapshots'])

    def run(c,context,operation,write=False):
        actor=input_authority(c,context,membership,write)
        try: return canonical_payload(operation(actor))
        except cash.CashConflict as exc: raise ApiProblem(409,'cash.revision_conflict','Cash input conflict',str(exc)) from exc
        except PermissionError as exc: raise ApiProblem(403,'cash.forbidden','Access denied',str(exc)) from exc
        except LookupError as exc: raise ApiProblem(404,'resource.not_found','Not found',str(exc)) from exc
        except ValueError as exc: raise ApiProblem(422,'cash.invalid_input','Invalid cash input',str(exc)) from exc

    @router.get('/cash-accounts',response_model=dict[str,object])
    def list_accounts(strategy:UUID=Query(alias='strategyId'),context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return run(c,context,lambda actor:{'items':cash.accounts(c,context.tenant_id,actor,strategy)})

    @router.get('/cash-options',response_model=dict[str,object])
    def options(context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return run(c,context,lambda actor:{'companies':[dict(id=str(r.organisation_id),label=r.display_name)
            for r in c.execute(select(m.organisation.c.organisation_id,m.organisation.c.display_name).where(
                m.organisation.c.status=='ACTIVE').order_by(m.organisation.c.display_name))]})

    @router.post('/cash-accounts',status_code=201,response_model=dict[str,object])
    def account(payload:CashAccountCreate,context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return run(c,context,lambda actor:{'accountId':cash.create_account(c,context.tenant_id,actor,payload)},True)

    @router.post('/cash-balances',status_code=201,response_model=dict[str,object])
    def balances(payload:CashUpload,key:str=Header(alias='Idempotency-Key',min_length=1,max_length=200),
        context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return run(c,context,lambda actor:{'items':cash.upload(c,context.tenant_id,actor,payload,key)},True)

    @router.get('/cash-balances',response_model=dict[str,object])
    def register(strategy:UUID=Query(alias='strategyId'),day:date=Query(alias='valueDate'),
        context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        def view(actor):
            rows=cash.read(c,context.tenant_id,actor,strategy,day)
            return {'items':cash.latest_on_date(rows,day),'revisions':rows,'valueDate':day,'carryForward':False}
        return run(c,context,view)

    @router.post('/cash-balance-preview',response_model=dict[str,object])
    def value(payload:CashPreview,context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return run(c,context,lambda actor:cash.preview(c,context.tenant_id,actor,payload))
    return router
