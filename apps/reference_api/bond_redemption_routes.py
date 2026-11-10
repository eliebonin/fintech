from tenant_reference.errors import ConfigurationConflict
"""Ops-triggered principal maturity closing, not payment confirmation."""
from typing import Literal,Annotated
from uuid import UUID
from fastapi import Depends,Header,Query,Request
from .request_audit import AuditRouter as APIRouter
from pydantic import BaseModel,ConfigDict,Field
from sqlalchemy import select,func
from security_master_schema import models as m
from security_master_schema.strategy_access import require_strategy_action,request_strategy_predicate
from lifecycle import bond_service as service
from valuation.economics import canonical_payload
from .tenant_context import TenantContext,get_tenant_context
from .problem_details import ApiProblem


class Target(BaseModel):
    strategyId:UUID
    instrumentId:UUID
    model_config=ConfigDict(extra='forbid')


class RateOverride(BaseModel):
    rate:str=Field(min_length=1,max_length=64)
    sourceReference:str=Field(min_length=1,max_length=2000)
    reason:str=Field(min_length=1,max_length=2000)
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)


from trading.booking_contracts import TradePropertyInput

class Preview(Target):
    allocationInputs:dict[Annotated[str,Field(pattern="^[0-9a-f]{64}$")],list[TradePropertyInput]]|None=None
    rateOverride:RateOverride|None=None


class Preparation(Preview):
    expectedFingerprint:str=Field(pattern='^[0-9a-f]{64}$')


class Closing(Preparation):
    proposalId:UUID|None=None
    confirmBooking:Literal[True]


class ModeChange(BaseModel):
    strategyId:UUID
    mode:Literal['DIRECT','REVIEW','MANUAL']
    expectedRevision:int=Field(ge=0,strict=True)
    reason:str=Field(min_length=1,max_length=2000)
    confirmChange:Literal[True]
    pricingPolicyId:UUID|None=None
    pricingCutId:UUID|None=None
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)


class Cancel(BaseModel):
    strategyId:UUID
    postingId:UUID
    reason:str=Field(min_length=1,max_length=2000)
    confirmCancel:Literal[True]
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)


def bond_redemption_router(connection_dependency,membership,*,service_module=None,prefix='/v1/lifecycle'):
    service=service_module or globals()['service']
    fx=service_module is not None
    policy_table,proposal_table,posting_table=getattr(service,'tables',(m.bond_redemption_policy,m.bond_redemption_proposal,m.bond_redemption_posting))
    router=APIRouter(prefix=prefix,tags=['FX forward maturity' if fx else 'plain bond maturity'])
    collection='/closures' if fx else '/bond-redemptions'

    def override_args(payload):
        value=payload.rateOverride.model_dump() if payload.rateOverride else None
        if not fx and value is not None:raise ApiProblem(422,'lifecycle.invalid','Unsupported override','Bond redemption price comes from contractual terms.')
        result={'rate_override':value} if fx else {}
        if payload.allocationInputs is not None:result['annotation_inputs']={key:[p.model_dump(by_alias=True,mode='json') for p in properties] for key,properties in payload.allocationInputs.items()}
        return result

    def call(c,context,http_request,operation):
        actor=membership(c,context);operator=getattr(http_request.state,'real_actor_id',actor)
        try:return canonical_payload(operation(actor,operator))
        except PermissionError as exc:raise ApiProblem(403,'lifecycle.forbidden','Access denied',str(exc)) from exc
        except LookupError as exc:raise ApiProblem(404,'resource.not_found','Not found',str(exc)) from exc
        except service.RedemptionConflict as exc:raise ApiProblem(409,'lifecycle.stale','Closing inputs changed',str(exc)) from exc
        except ConfigurationConflict as exc:raise ApiProblem(409,'configuration.changed','Configuration review required',str(exc)) from exc
        except ValueError as exc:raise ApiProblem(422,'lifecycle.invalid','Unsupported redemption',str(exc)) from exc

    @router.get('/annotation-options',response_model=dict[str,object])
    def annotation_options(http_request:Request,strategyId:UUID,catalogueId:UUID,q:str=Query('',max_length=250),offset:int=Query(0,ge=0),limit:int=Query(26,ge=1,le=100),context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        from lifecycle.allocations import reference_options
        return call(c,context,http_request,lambda actor,operator:reference_options(c,context.tenant_id,actor,strategyId,catalogueId,q,offset,limit))

    @router.get('/options',response_model=dict[str,object])
    def options(http_request:Request,strategyId:UUID|None=None,context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        def read(actor,operator):
            rows=c.execute(select(m.strategy.c.strategy_id,m.strategy.c.display_name).where(m.strategy.c.tenant_id==context.tenant_id,
                request_strategy_predicate(c,context.tenant_id,'LIFECYCLE_READ',m.strategy.c.strategy_id)).order_by(m.strategy.c.display_name)).all()
            bonds=[];policy=None
            if strategyId:
                require_strategy_action(c,context.tenant_id,actor,'LIFECYCLE_READ',strategyId)
                subjects=select(m.trade.c.reference_instrument_node_id).where(m.trade.c.strategy_id==strategyId).distinct()
                bonds=[dict(id=r.reference_node_id,label=r.canonical_name) for r in c.execute(select(m.financial_reference_node).join(m.instrument,
                    m.instrument.c.instrument_node_id==m.financial_reference_node.c.reference_node_id).join(m.instrument_type).where(
                        m.instrument_type.c.type_code==('FX_FORWARD' if fx else 'BOND'),m.instrument.c.instrument_node_id.in_(subjects))).mappings()]
                policy=service.policy(c,context.tenant_id,strategyId)
            permissions={}
            if strategyId:
                for action in ('LIFECYCLE_PREPARE','LIFECYCLE_BOOK','LIFECYCLE_APPROVE','LIFECYCLE_CONFIGURE','TRADE_WRITE','TRADE_CORRECT','MARKET_DATA_READ'):
                    try:require_strategy_action(c,context.tenant_id,actor,action,strategyId)
                    except PermissionError:permissions[action]=False
                    else:permissions[action]=True
            choices=[]
            if fx and strategyId:
                p=m.valuation_policy
                from sqlalchemy import or_
                choices=[dict(id=r.valuation_policy_id,label=f'{r.display_name} · {r.policy_code} v{r.version_no}',cutId=r.valuation_cut_id)
                    for r in c.execute(select(p).where(p.c.tenant_id==context.tenant_id,p.c.status=='ACTIVE',or_(p.c.strategy_id.is_(None),p.c.strategy_id==strategyId))).mappings()]
            from lifecycle.assistance import assistance_view
            return dict(strategies=[dict(id=r.strategy_id,label=r.display_name) for r in rows],instruments=bonds,policy=policy,permissions=permissions,pricingPolicies=choices,assistance=assistance_view(c,context.tenant_id,actor,strategyId,'FX_FORWARD_MATURITY' if fx else 'BOND_MATURITY') if strategyId else None)
        return call(c,context,http_request,read)

    @router.post('/policy',response_model=dict[str,object])
    def configure(payload:ModeChange,http_request:Request,context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        if fx:
            if payload.pricingPolicyId is None or payload.pricingCutId is None:raise ApiProblem(422,'lifecycle.invalid','Pricing policy required','Select a maturity pricing policy and its cut.')
            return call(c,context,http_request,lambda actor,operator:service.configure(c,context.tenant_id,actor,operator,payload.strategyId,
                payload.mode,payload.expectedRevision,payload.reason,payload.pricingPolicyId,payload.pricingCutId))
        if payload.pricingPolicyId is not None or payload.pricingCutId is not None:raise ApiProblem(422,'lifecycle.invalid','Unexpected pricing policy','Bond principal price comes from contractual terms.')
        return call(c,context,http_request,lambda actor,operator:service.configure(c,context.tenant_id,actor,operator,payload.strategyId,
            payload.mode,payload.expectedRevision,payload.reason))

    @router.post(collection+'/preview',response_model=dict[str,object])
    def preview(payload:Preview,http_request:Request,context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        def view(actor,operator):
            require_strategy_action(c,context.tenant_id,actor,'LIFECYCLE_READ',payload.strategyId)
            if fx:require_strategy_action(c,context.tenant_id,actor,'MARKET_DATA_READ',payload.strategyId)
            data,fingerprint,_,_=service.candidate(c,context.tenant_id,payload.strategyId,payload.instrumentId,**override_args(payload))
            return dict(inputs=data,inputHash=fingerprint)
        return call(c,context,http_request,view)

    @router.post(collection+'/prepare',status_code=201,response_model=dict[str,object])
    def prepare(payload:Preparation,http_request:Request,context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return call(c,context,http_request,lambda actor,operator:service.prepare(c,context.tenant_id,actor,operator,payload.strategyId,payload.instrumentId,payload.expectedFingerprint,**override_args(payload)))

    @router.post(collection+'/book',status_code=201,response_model=dict[str,object])
    def book(payload:Closing,http_request:Request,key:str=Header(alias='Idempotency-Key',min_length=1,max_length=255),
        context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        if payload.proposalId is not None:raise ApiProblem(422,'lifecycle.invalid','Invalid direct booking','Use approval for a prepared entry.')
        return call(c,context,http_request,lambda actor,operator:service.post(c,context.tenant_id,actor,operator,payload.strategyId,payload.instrumentId,payload.expectedFingerprint,key,**override_args(payload)))

    @router.post(collection+'/confirm',status_code=201,response_model=dict[str,object])
    def confirm(payload:Closing,http_request:Request,key:str=Header(alias='Idempotency-Key',min_length=1,max_length=255),context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        if payload.proposalId is None:raise ApiProblem(422,'lifecycle.invalid','Missing proposal','Select a retained prepared entry.')
        def confirm_entry(actor,operator):
            if service.policy(c,context.tenant_id,payload.strategyId)['mode']=='REVIEW':raise PermissionError('Independent approval is required; use the approval action.')
            return service.post(c,context.tenant_id,actor,operator,payload.strategyId,payload.instrumentId,payload.expectedFingerprint,key,proposal_id=payload.proposalId,**override_args(payload))
        return call(c,context,http_request,confirm_entry)

    @router.post(collection+'/approve',status_code=201,response_model=dict[str,object])
    def approve(payload:Closing,http_request:Request,key:str=Header(alias='Idempotency-Key',min_length=1,max_length=255),
        context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        if payload.proposalId is None:raise ApiProblem(422,'lifecycle.invalid','Missing proposal','Select a prepared entry.')
        return call(c,context,http_request,lambda actor,operator:service.post(c,context.tenant_id,actor,operator,payload.strategyId,payload.instrumentId,
            payload.expectedFingerprint,key,proposal_id=payload.proposalId,**override_args(payload)))

    @router.get(collection,response_model=dict[str,object])
    def proposals(http_request:Request,strategyId:UUID,limit:int=Query(25,ge=1,le=100),offset:int=Query(0,ge=0,le=10000),
        context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        def read(actor,operator):
            require_strategy_action(c,context.tenant_id,actor,'LIFECYCLE_READ',strategyId)
            if fx:require_strategy_action(c,context.tenant_id,actor,'MARKET_DATA_READ',strategyId)
            p=proposal_table;where=(p.c.tenant_id==context.tenant_id)&(p.c.strategy_id==strategyId)
            rows=[dict(r) for r in c.execute(select(p).where(where).order_by(p.c.recorded_at.desc(),p.c.proposal_id).limit(limit).offset(offset)).mappings()]
            current=service.policy(c,context.tenant_id,strategyId)
            from lifecycle.entitlements import lifecycle_subscription_view
            from lifecycle.assistance import selection
            subscription=lifecycle_subscription_view(c,context.tenant_id)
            chosen=selection(c,context.tenant_id,strategyId,'FX_FORWARD_MATURITY' if fx else 'BOND_MATURITY')
            for row in rows:
                posted=c.execute(select(posting_table).where(posting_table.c.proposal_id==row['proposal_id'],
                    posting_table.c.tenant_id==context.tenant_id)).mappings().one_or_none()
                if posted:
                    states=list(c.scalars(select(m.trade.c.lifecycle_status).where(m.trade.c.trade_id.in_([UUID(i) for i in posted['trade_ids']]))))
                    row['status']='CANCELLED' if states and all(s=='CANCELLED' for s in states) else 'BOOKED'
                else:
                    proof=row['inputs'].get('lifecycleAssistance',{})
                    stale=proof.get('subscriptionRevision')!=subscription['revision'] or proof.get('assistanceRevision')!=(chosen['revision'] if chosen else 0) or proof.get('entitlementFingerprint')!=subscription['entitlementFingerprint'] or not chosen or chosen['selected_tier']>subscription['maximumTier']
                    row['status']='STALE_POLICY' if row['policy_revision']!=current['revision'] else 'STALE_ASSISTANCE' if stale else 'PREPARED'
            return dict(items=rows,total=c.scalar(select(func.count()).select_from(p).where(where)))
        return call(c,context,http_request,read)

    @router.get(collection+'/postings',response_model=dict[str,object])
    def postings(http_request:Request,strategyId:UUID,limit:int=Query(25,ge=1,le=100),offset:int=Query(0,ge=0,le=10000),
        context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        def read(actor,operator):
            require_strategy_action(c,context.tenant_id,actor,'LIFECYCLE_READ',strategyId)
            if fx:require_strategy_action(c,context.tenant_id,actor,'MARKET_DATA_READ',strategyId)
            p=posting_table;where=(p.c.tenant_id==context.tenant_id)&(p.c.strategy_id==strategyId)
            rows=[dict(r) for r in c.execute(select(p).where(where).order_by(p.c.recorded_at.desc(),p.c.posting_id).limit(limit).offset(offset)).mappings()]
            for row in rows:
                row['tradeStates']={str(r.trade_id):r.lifecycle_status for r in c.execute(select(m.trade.c.trade_id,m.trade.c.lifecycle_status).where(m.trade.c.trade_id.in_([UUID(i) for i in row['trade_ids']]))) }
            return dict(items=rows,total=c.scalar(select(func.count()).select_from(p).where(where)))
        return call(c,context,http_request,read)

    @router.post(collection+'/cancel',response_model=dict[str,object])
    def cancel(payload:Cancel,http_request:Request,key:str=Header(alias='Idempotency-Key',min_length=1,max_length=255),
        context:TenantContext=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return call(c,context,http_request,lambda actor,operator:service.cancel(c,context.tenant_id,actor,operator,payload.strategyId,payload.postingId,payload.reason,key))
    return router
