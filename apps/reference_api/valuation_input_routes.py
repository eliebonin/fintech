"""Tenant-scoped immutable daily input versions. No market-data rights grants."""
from datetime import date,datetime,time,timedelta,timezone
from uuid import UUID
from fastapi import APIRouter,Depends,Header,Query
from sqlalchemy import select
from security_master_schema import models as m
from security_master_schema.tenancy import assert_tenant_owns_strategy
from security_master_schema.tenant_workspace import resolve_tenant_workspace
from market_data.display_access import assert_dataset_display
from valuation.accruals import record_accrual,read_accruals,accrual_amounts
from valuation.economics import canonical_payload,evidence_hash
from valuation.fx import resolve_fx
from valuation.service import ValuationRequest
from valuation import tables as t
from .valuation_input_contracts import AccrualCreate,EconomicFlowCreate,EconomicFlowCancel
from .tenant_context import TenantContext,get_tenant_context
from .valuation_policies import authority
from .resource_limits import governance_date
from .problem_details import ApiProblem


def input_authority(c,context,membership,write=False):
    actor=membership(c,context)
    try:
        authority(c,context.tenant_id,actor,False)
        workspace=resolve_tenant_workspace(c,context.tenant_id,actor,governance_date())
        if write and not {'VALUATION_RUN','VALUATION_REVIEW'} & workspace.permission_codes:
            raise PermissionError('Valuation input action permission required')
        if 'VALUATION' not in workspace.module_codes: raise PermissionError('VALUATION required')
    except PermissionError as exc:
        raise ApiProblem(403,'valuation.forbidden','Valuation access denied','VALUATION and MARKET_DATA access required; writes need the applicable valuation action permission.') from exc
    return actor


def assert_input_display(c,tenant,rows):
    contexts=[]
    for row in rows:
        for evidence in row['payload'].get('fxEvidence',[]):
            selection=evidence.get('selection')
            if selection:
                contexts.append((UUID(selection['dataset_id']),UUID(selection['market_data_series_id'])))
    assert_dataset_display(c,tenant,{dataset for dataset,_ in contexts},series_contexts=contexts)


def valuation_input_router(connection_dependency,membership):
    router=APIRouter(prefix='/v1/valuation',tags=['valuation daily inputs'])

    def flow_action(c,context,operation,*,correction=False):
        from .booking_errors import IdempotencyKeyConflict
        from security_master_schema.tenant_workspace import TenantActionForbidden
        actor=input_authority(c,context,membership,not correction)
        try: return {'tradeId':str(operation(actor))}
        except (PermissionError,TenantActionForbidden) as exc: raise ApiProblem(403,'valuation.forbidden','Access denied','Trade booking authority required.') from exc
        except LookupError as exc: raise ApiProblem(404,'resource.not_found','Not found','Economic flow reference unavailable.') from exc
        except IdempotencyKeyConflict as exc: raise ApiProblem(409,'idempotency.key_reused','Idempotency conflict',str(exc)) from exc
        except ValueError as exc: raise ApiProblem(422,'valuation.invalid_input','Invalid economic flow',str(exc)) from exc

    @router.post('/economic-flows',status_code=201,response_model=dict[str,str])
    def create_flow(payload:EconomicFlowCreate,key:str=Header(alias='Idempotency-Key',min_length=1,max_length=255),
        context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        from valuation.flows import book_flow
        return flow_action(c,context,lambda actor:book_flow(c,context.tenant_id,actor,payload.model_dump(by_alias=True),key))

    @router.post('/economic-flows/{trade_id}/cancel',response_model=dict[str,str])
    def remove_flow(trade_id:UUID,payload:EconomicFlowCancel,key:str=Header(alias='Idempotency-Key',min_length=1,max_length=255),
        context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        from valuation.flows import cancel_flow
        return flow_action(c,context,lambda actor:cancel_flow(c,context.tenant_id,actor,trade_id,payload.reason,key),correction=True)

    @router.post('/accrual-inputs',status_code=201,response_model=dict[str,object])
    def create(payload:AccrualCreate,key:str=Header(alias='Idempotency-Key',min_length=1,max_length=255),
        context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        actor=input_authority(c,context,membership,True);tenant=context.tenant_id
        try: assert_tenant_owns_strategy(c,tenant,payload.strategy_id)
        except (PermissionError,ValueError) as exc: raise ApiProblem(404,'resource.not_found','Not found','Strategy not found in tenant.') from exc
        fingerprint=evidence_hash(payload.model_dump(mode='json'))
        old=c.execute(select(t.accrual_input).where(t.accrual_input.c.tenant_id==tenant,t.accrual_input.c.submission_key==key)).mappings().one_or_none()
        if old:
            if old['request_hash']!=fingerprint: raise ApiProblem(409,'valuation.input_conflict','Input conflict','Accrual request key reused for different inputs.')
            assert_input_display(c,tenant,[old])
            return canonical_payload(dict(old))
        try:
            from .product_booking import require_visible
            require_visible(c,tenant,payload.instrument_id)
            currency=c.scalar(select(m.instrument.c.base_currency_id).where(m.instrument.c.instrument_node_id==payload.instrument_id))
            now=datetime.now(timezone.utc)
            if payload.value_date>now.date(): raise ValueError('Future accrued-interest inputs are not supported')
            policy=c.execute(select(m.valuation_policy).where(m.valuation_policy.c.valuation_policy_id==payload.policy_id,
                m.valuation_policy.c.tenant_id==tenant,m.valuation_policy.c.status=='ACTIVE')).mappings().one_or_none()
            if not policy or policy['strategy_id'] not in (None,payload.strategy_id): raise ValueError('Active tenant pricing policy required')
            r=ValuationRequest(tenant,payload.strategy_id,payload.policy_id,payload.cut_id,payload.reporting_currency_id,
                datetime.combine(payload.value_date-timedelta(days=1),time.max,timezone.utc),datetime.combine(payload.value_date,time.max,timezone.utc),now)
            opening=resolve_fx(c,r,currency,payload.reporting_currency_id,payload.value_date-timedelta(days=1))
            closing=resolve_fx(c,r,currency,payload.reporting_currency_id,payload.value_date)
            inputs=dict(openingBalance=payload.opening_balance,dailyEarned=payload.daily_earned,closingBalance=payload.closing_balance,
                balanceMovements=payload.balance_movements,openingFx=opening.rate,closingFx=closing.rate)
            data=dict(strategyId=payload.strategy_id,instrumentId=payload.instrument_id,valueDate=payload.value_date,inputType='DAILY_INTEREST',
                policyId=payload.policy_id,cutId=payload.cut_id,
                currencyId=currency,reportingCurrencyId=payload.reporting_currency_id,eligibleNominal=payload.eligible_nominal,
                eligibilityConvention=payload.eligibility_convention,sourceReference=payload.source_reference,supersedesInputId=payload.supersedes_input_id,
                inputs=inputs,amounts=accrual_amounts(inputs),fxEvidence=[opening.evidence,closing.evidence])
            identity=record_accrual(c,tenant,actor,data,key,request_hash=fingerprint)
            row=c.execute(select(t.accrual_input).where(t.accrual_input.c.input_id==identity)).mappings().one()
            assert_input_display(c,tenant,[row]);return canonical_payload(dict(row))
        except PermissionError as exc: raise ApiProblem(403,'valuation.evidence_forbidden','Evidence access denied',str(exc)) from exc
        except LookupError as exc: raise ApiProblem(404,'resource.not_found','Not found','Input reference unavailable.') from exc
        except ValueError as exc: raise ApiProblem(422,'valuation.invalid_input','Invalid accrued-interest input',str(exc)) from exc

    @router.get('/accrual-inputs',response_model=dict[str,object])
    def history(strategy_id:UUID=Query(alias='strategyId'),start:date=Query(alias='fromDate'),end:date=Query(alias='toDate'),
        context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        input_authority(c,context,membership)
        if end<start or (end-start).days>366: raise ApiProblem(422,'valuation.invalid_input','Invalid dates','Use an ordered interval of at most 366 days.')
        try:
            rows=read_accruals(c,context.tenant_id,strategy_id,start,end,datetime.now(timezone.utc))
            assert_input_display(c,context.tenant_id,rows)
            return {'items':canonical_payload(rows)}
        except PermissionError as exc: raise ApiProblem(403,'valuation.evidence_forbidden','Evidence access denied',str(exc)) from exc
        except ValueError as exc: raise ApiProblem(404,'resource.not_found','Not found','Strategy unavailable.') from exc
    return router
