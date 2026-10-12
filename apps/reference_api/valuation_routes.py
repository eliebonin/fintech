"""Tenant-scoped valuation transport; economic logic lives in valuation."""
from dataclasses import asdict
from uuid import UUID
from fastapi import APIRouter,Depends,Header,Query,Request
from sqlalchemy import select,func
from .tenant_context import TenantContext,get_tenant_context
from .problem_details import ApiProblem,current_request_id
from .valuation_contracts import ValuationCreate,ReviewComment,ValuationAttemptList,ValuationAttemptDetail,ValuationOptions
from .valuation_policies import authority
from .resource_limits import governance_date
from security_master_schema.tenant_workspace import resolve_tenant_workspace
from security_master_schema import models as m
from security_master_schema.tenancy import assert_tenant_owns_strategy
from valuation import tables as t,storage
from valuation.economics import canonical_payload
from valuation.service import ValuationRequest,ValuationBlocked
from valuation.runner import execute,ValuationInProgress
from valuation.evidence_access import assert_batch_display


def valuation_router(connection_dependency,membership,engine_factory,configure_transaction=None):
    router=APIRouter(prefix='/v1/valuation',tags=['valuation and P&L'])
    def authorize(c,context,write=False):
        actor=membership(c,context)
        try:
            authority(c,context.tenant_id,actor,False)
            workspace=resolve_tenant_workspace(c,context.tenant_id,actor,governance_date())
            can_manage=bool({'VALUATION_RUN','VALUATION_REVIEW'} & workspace.permission_codes)
            if write and not can_manage:raise PermissionError('Valuation action permission required')
            if 'VALUATION' not in workspace.module_codes: raise PermissionError('VALUATION module required')
        except PermissionError as exc: raise ApiProblem(403,'valuation.forbidden','Valuation access denied','VALUATION and MARKET_DATA access are required; writes also require the applicable valuation action permission.') from exc
        return actor,can_manage

    def detail(c,tenant,attempt_id):
        row=c.execute(select(t.attempt).where(t.attempt.c.attempt_id==attempt_id,t.attempt.c.tenant_id==tenant)).mappings().one_or_none()
        if row is None: raise ApiProblem(404,'resource.not_found','Not found','Valuation attempt not found.')
        events=c.execute(select(t.run_event).where(t.run_event.c.attempt_id==attempt_id).order_by(t.run_event.c.recorded_at,t.run_event.c.event_id)).mappings().all()
        batch_id=c.scalar(select(t.batch.c.batch_id).where(t.batch.c.attempt_id==attempt_id,t.batch.c.tenant_id==tenant).order_by(t.batch.c.created_at.desc()).limit(1))
        if batch_id is None:
            # An idempotent run may reuse an existing reviewed batch.
            for event in reversed(events):
                if event['details'].get('batchId'): batch_id=UUID(event['details']['batchId']);break
        batch=storage.batch_view(c,tenant,batch_id) if batch_id else None
        if batch:
            try: assert_batch_display(c,tenant,batch)
            except PermissionError:
                # Keep safe operational status inspectable without releasing
                # raw prices, inferred prices via components, or derived totals.
                batch=dict(batch_id=batch_id,status=batch['status'],items=[],reviews=[],
                    summary={'scope':'MARKET_ONLY','evidenceAccess':'DENIED',
                        'reason':'Current dataset DISPLAY rights and tenant reporting entitlement are required.'})
        return canonical_payload(dict(attempt=dict(row),events=[dict(event) for event in events],batch=batch))

    @router.get('/options',response_model=ValuationOptions)
    def options(context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        authorize(c,context)
        strategies=[dict(id=str(row.strategy_id),label=row.display_name,currencyId=str(row.base_currency_id) if row.base_currency_id else None)
            for row in c.execute(select(m.strategy).where(m.strategy.c.tenant_id==context.tenant_id,m.strategy.c.status=='ACTIVE').order_by(m.strategy.c.display_name).limit(500))]
        # Display names are shared across immutable versions; never offer an
        # indistinguishable choice while submitting a version-specific ID.
        policies=[dict(id=str(row.valuation_policy_id),label=f'{row.display_name} · {row.policy_code} · v{row.version_no}',cutId=str(row.valuation_cut_id),strategyId=str(row.strategy_id) if row.strategy_id else None)
            for row in c.execute(select(m.valuation_policy).where(m.valuation_policy.c.tenant_id==context.tenant_id,m.valuation_policy.c.status=='ACTIVE').order_by(m.valuation_policy.c.display_name,m.valuation_policy.c.policy_code,m.valuation_policy.c.version_no.desc(),m.valuation_policy.c.valuation_policy_id).limit(500))]
        currencies=[dict(id=str(row.currency_id),label=row.currency_code) for row in c.execute(select(m.currency).where(m.currency.c.status=='ACTIVE').order_by(m.currency.c.currency_code).limit(500))]
        return dict(strategies=strategies,policies=policies,currencies=currencies)

    @router.get('/attempts',response_model=ValuationAttemptList)
    def attempts(limit:int=Query(25,ge=1,le=100),offset:int=Query(0,ge=0,le=10000),context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        actor,manage=authorize(c,context)
        where=t.attempt.c.tenant_id==context.tenant_id
        rows=c.execute(select(t.attempt).where(where).order_by(t.attempt.c.started_at.desc(),t.attempt.c.attempt_id.desc()).limit(limit).offset(offset)).mappings().all()
        total=c.scalar(select(func.count()).select_from(t.attempt).where(where))
        return dict(items=canonical_payload([dict(row) for row in rows]),scope='SUPPORTED_ECONOMIC_ALPHA',total=total,canManage=manage,actorId=actor)

    @router.get('/attempts/{attempt_id}',response_model=ValuationAttemptDetail)
    def attempt(attempt_id:UUID,context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        authorize(c,context)
        return detail(c,context.tenant_id,attempt_id)

    @router.post('/attempts',response_model=ValuationAttemptDetail,status_code=201)
    def create(payload:ValuationCreate,http_request:Request,key:str=Header(alias='Idempotency-Key',min_length=1,max_length=255),
               context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        actor,_=authorize(c,context,True)
        try: assert_tenant_owns_strategy(c,context.tenant_id,payload.strategy_id)
        except (PermissionError,ValueError) as exc: raise ApiProblem(404,'resource.not_found','Not found','Strategy not found in this tenant.') from exc
        opening,closing=payload.resolved_cutoffs()
        request=ValuationRequest(tenant_id=context.tenant_id,**payload.model_dump(exclude={'opening_date','closing_date','opening_cutoff','closing_cutoff'}),
            opening_cutoff=opening,closing_cutoff=closing,daily=payload.daily)
        try: attempt_id=execute(engine_factory(),request,actor,key,current_request_id(),configure_transaction=configure_transaction,
            real_operator_id=getattr(http_request.state,'real_actor_id',actor))
        except ValuationInProgress as exc: raise ApiProblem(409,'valuation.in_progress','Valuation is already running',str(exc)) from exc
        except ValuationBlocked as exc: raise ApiProblem(422,'valuation.blocked','Valuation could not be calculated',str(exc)) from exc
        except ValueError as exc: raise ApiProblem(409,'valuation.request_conflict','Valuation request conflict',str(exc)) from exc
        return detail(c,context.tenant_id,attempt_id)

    def review(c,context,batch_id,payload,publish,real_operator_id=None):
        actor,_=authorize(c,context,True)
        try:
            candidate=storage.batch_view(c,context.tenant_id,batch_id)
            assert_batch_display(c,context.tenant_id,candidate)
            if publish: storage.publish(c,context.tenant_id,batch_id,actor,payload.comment,real_operator_id=real_operator_id)
            else:
                storage.batch_view(c,context.tenant_id,batch_id)
                c.execute(t.review_event.insert().values(batch_id=batch_id,actor_id=actor,action='EXPLANATION',comment=payload.comment))
            return canonical_payload(storage.batch_view(c,context.tenant_id,batch_id))
        except PermissionError as exc: raise ApiProblem(403,'valuation.evidence_forbidden','Evidence access denied',str(exc)) from exc
        except LookupError as exc: raise ApiProblem(404,'resource.not_found','Not found','Review batch not found.') from exc
        except ValueError as exc: raise ApiProblem(409,'valuation.review_conflict','Review cannot proceed',str(exc)) from exc

    @router.post('/batches/{batch_id}/explanations',response_model=dict[str,object])
    def explain(batch_id:UUID,payload:ReviewComment,context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return review(c,context,batch_id,payload,False)

    @router.post('/batches/{batch_id}/publish',response_model=dict[str,object])
    def publish(batch_id:UUID,payload:ReviewComment,http_request:Request,context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return review(c,context,batch_id,payload,True,getattr(http_request.state,'real_actor_id',context.user_account_id))
    return router
