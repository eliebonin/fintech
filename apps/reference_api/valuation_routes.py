"""Tenant-scoped valuation transport; economic logic lives in valuation."""
from dataclasses import asdict
from uuid import UUID
from datetime import date
from typing import Literal
from fastapi import Depends,Header,Query,Request
from .request_audit import AuditRouter as APIRouter
from sqlalchemy import select,func,or_
from security_master_schema.strategy_access import request_strategy_predicate
from .tenant_context import TenantContext,get_tenant_context
from .problem_details import ApiProblem,current_request_id
from .valuation_contracts import ValuationCreate,ReviewComment,ValuationAttemptList,ValuationAttemptDetail,ValuationOptions
from .valuation_contracts import SelfPublicationRequest
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
from valuation.history import history_queries


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

    def detail(c,tenant,attempt_id,actor=None,real_operator_id=None):
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
            else:
                if actor:
                    from valuation.self_publication import publication_authority
                    batch['publicationAuthority']=publication_authority(c,tenant,batch,actor,real_operator_id)
                from .valuation_presentation import decorate_batch
                batch=decorate_batch(c,tenant,batch)
        from .valuation_presentation import decorate_runs
        attempt=decorate_runs(c,tenant,[dict(row)])[0]
        return canonical_payload(dict(attempt=attempt,events=[dict(event) for event in events],batch=batch))

    @router.get('/options',response_model=ValuationOptions)
    def options(context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        authorize(c,context)
        strategies=[dict(id=str(row.strategy_id),label=row.display_name if row.status=='ACTIVE' else f'{row.display_name} ({row.status.lower()})',currencyId=str(row.base_currency_id) if row.base_currency_id else None,canCalculate=row.status=='ACTIVE' and bool(row.can_calculate))
            for row in c.execute(select(m.strategy,request_strategy_predicate(c,context.tenant_id,'VALUATION_RUN',m.strategy.c.strategy_id).label('can_calculate')).where(m.strategy.c.tenant_id==context.tenant_id,request_strategy_predicate(c,context.tenant_id,'VALUATION_READ',m.strategy.c.strategy_id)).order_by(m.strategy.c.display_name))]
        # Display names are shared across immutable versions; never offer an
        # indistinguishable choice while submitting a version-specific ID.
        policies=[dict(id=str(row.valuation_policy_id),label=f'{row.display_name} · {row.policy_code} · v{row.version_no}',cutId=str(row.valuation_cut_id),strategyId=str(row.strategy_id) if row.strategy_id else None)
            for row in c.execute(select(m.valuation_policy).where(m.valuation_policy.c.tenant_id==context.tenant_id,m.valuation_policy.c.status=='ACTIVE',or_(m.valuation_policy.c.strategy_id.is_(None),request_strategy_predicate(c,context.tenant_id,'VALUATION_READ',m.valuation_policy.c.strategy_id))).order_by(m.valuation_policy.c.display_name,m.valuation_policy.c.policy_code,m.valuation_policy.c.version_no.desc(),m.valuation_policy.c.valuation_policy_id))]
        currencies=[dict(id=str(row.currency_id),label=row.currency_code) for row in c.execute(select(m.currency).where(m.currency.c.status=='ACTIVE').order_by(m.currency.c.currency_code))]
        return dict(strategies=strategies,policies=policies,currencies=currencies)

    from .valuation_contracts import ValuationChoicePage

    @router.get('/option-choices', response_model=ValuationChoicePage)
    def choices(kind:Literal['strategies','policies','currencies'], q:str=Query('',max_length=120),
            limit:int=Query(25,ge=1,le=100), offset:int=Query(0,ge=0), selected_id:UUID|None=None,
            strategy_id:UUID|None=None, for_calculation:bool=False,
            context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        actor,_=authorize(c,context)
        from .valuation_choices import option_choices
        return option_choices(c,context.tenant_id,actor,kind,q=q.strip(),limit=limit,offset=offset,
            selected_id=selected_id,strategy_id=strategy_id,for_calculation=for_calculation)

    @router.get('/attempts',response_model=ValuationAttemptList)
    def attempts(limit:int=Query(25,ge=1,le=100),offset:int=Query(0,ge=0,le=10000),
                 strategy_id:UUID|None=None,from_date:date|None=None,to_date:date|None=None,
                 calculation_status:Literal['RUNNING','COMPLETED','FAILED']|None=None,
                 publication_status:Literal['STAGED','PUBLISHED','SUPERSEDED','CANCELLED']|None=None,
                 results_only:bool=False,context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        actor,manage=authorize(c,context)
        if from_date and to_date and from_date>to_date:
            raise ApiProblem(422,'request.validation_failed','Invalid date range','From valuation date must not follow To valuation date.')
        query,count=history_queries(context.tenant_id,request_strategy_predicate(c,context.tenant_id,'VALUATION_READ',t.attempt.c.strategy_id),
            strategy_id=strategy_id,from_date=from_date,to_date=to_date,calculation_status=calculation_status,
            publication_status=publication_status,results_only=results_only,limit=limit,offset=offset)
        rows=[dict(row) for row in c.execute(query).mappings()]
        from valuation.ledger_impacts import source_health_statuses
        batches=storage.batch_disclosure_views(c,context.tenant_id,
            [row['batch_id'] for row in rows if row['batch_id']],include_evidence=results_only)
        health=source_health_statuses(c,list(batches.values()))
        for row in rows:
            if row['batch_id']:
                row['source_health_status']=health.get(row['batch_id'],'UNKNOWN_LEGACY')
                row['required_inputs_complete']=(batches.get(row['batch_id'],{}).get('summary') or {}).get('requiredInputsComplete',True)
        # Headline financial amounts require the same current DISPLAY evidence as
        # the detail endpoint. History metadata alone never releases those values.
        if results_only:
            for row in rows:
                batch=batches.get(row['batch_id'])
                if batch is None:
                    row['evidence_access']='DENIED'
                    continue
                try:assert_batch_display(c,context.tenant_id,batch)
                except PermissionError:row['evidence_access']='DENIED'
                else:
                    summary=batch['summary']
                    row['financial_summary']={key:summary[key] for key in ('netPnl','grossPnl','marketPnl','reportingCurrencyId','totalsBasis') if key in summary}
                    if summary.get('hasCalculatedContributions') is False:
                        row['financial_summary'].update(netPnl=None,grossPnl=None,marketPnl=None)
        total=c.scalar(count)
        from .valuation_presentation import decorate_runs
        decorate_runs(c,context.tenant_id,rows)
        return dict(items=canonical_payload([dict(row) for row in rows]),scope='SUPPORTED_ECONOMIC_ALPHA',total=total,canManage=manage,actorId=actor)

    @router.get('/attempts/{attempt_id}',response_model=ValuationAttemptDetail)
    def attempt(attempt_id:UUID,http_request:Request,context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        authorize(c,context)
        return detail(c,context.tenant_id,attempt_id,context.user_account_id,getattr(http_request.state,'real_actor_id',context.user_account_id))

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
        return detail(c,context.tenant_id,attempt_id,context.user_account_id,getattr(http_request.state,'real_actor_id',context.user_account_id))

    def review(c,context,batch_id,payload,publish,real_operator_id=None,self_publication=False):
        actor,_=authorize(c,context,True)
        try:
            candidate=storage.batch_view(c,context.tenant_id,batch_id)
            assert_batch_display(c,context.tenant_id,candidate)
            if publish: storage.publish(c,context.tenant_id,batch_id,actor,payload.comment,real_operator_id=real_operator_id,self_publication=self_publication)
            else:
                storage.batch_view(c,context.tenant_id,batch_id)
                c.execute(t.review_event.insert().values(batch_id=batch_id,actor_id=actor,action='EXPLANATION',comment=payload.comment))
            result=storage.batch_view(c,context.tenant_id,batch_id)
            from valuation.self_publication import publication_authority
            result['publicationAuthority']=publication_authority(c,context.tenant_id,result,actor,real_operator_id)
            from .valuation_presentation import decorate_batch
            return canonical_payload(decorate_batch(c,context.tenant_id,result))
        except PermissionError as exc: raise ApiProblem(403,'valuation.evidence_forbidden','Evidence access denied',str(exc)) from exc
        except LookupError as exc: raise ApiProblem(404,'resource.not_found','Not found','Review batch not found.') from exc
        except ValueError as exc: raise ApiProblem(409,'valuation.review_conflict','Review cannot proceed',str(exc)) from exc

    @router.post('/batches/{batch_id}/explanations',response_model=dict[str,object])
    def explain(batch_id:UUID,payload:ReviewComment,http_request:Request,context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return review(c,context,batch_id,payload,False,getattr(http_request.state,'real_actor_id',context.user_account_id))

    @router.post('/batches/{batch_id}/publish',response_model=dict[str,object])
    def publish(batch_id:UUID,payload:ReviewComment,http_request:Request,context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return review(c,context,batch_id,payload,True,getattr(http_request.state,'real_actor_id',context.user_account_id))

    @router.post('/batches/{batch_id}/self-publish',response_model=dict[str,object])
    def self_publish(batch_id:UUID,payload:SelfPublicationRequest,http_request:Request,context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return review(c,context,batch_id,payload,True,getattr(http_request.state,'real_actor_id',context.user_account_id),True)
    from .valuation_reassessment_routes import register_reassessment_routes
    register_reassessment_routes(router,authorize,connection_dependency,engine_factory,configure_transaction)
    from .mark_override_routes import mark_override_router
    router.include_router(mark_override_router(connection_dependency,authorize))
    return router
