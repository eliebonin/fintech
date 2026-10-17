"""Central permission enforcement ahead of request parsing and business writes.

The local API trusts its private BFF header boundary, as before. An opaque local
session additionally pins actor, subject and tenant; mismatching headers fail.
This is not a substitute for production identity-provider authentication.
"""
from security_master_schema.governance_clock import governance_date, governance_scope
from starlette.concurrency import run_in_threadpool
from .config import Settings
from .resource_limits import configure_transaction_budget
from security_master_schema.command_audit import CommandAudit, command_scope
from uuid import UUID
import json
import re
from sqlalchemy import select
from starlette.responses import JSONResponse, Response
from security_master_schema import access_sessions, access_management, models as m
from security_master_schema.tenant_workspace import resolve_tenant_workspace, require_tenant_action

GLOBAL_CATALOGUES={'currencies','market-venues','day-count-conventions','return-profiles','index-kind-catalogue','organisations','index-families','future-families'}


def assert_independent_operator(c,tenant,actor,resource):
    prior=c.scalar(select(m.access_audit_event.c.event_id).where(m.access_audit_event.c.tenant_id==tenant,
        m.access_audit_event.c.actor_id==actor,m.access_audit_event.c.action=='TENANT_REQUEST',
        m.access_audit_event.c.details['permission'].astext=='VALUATION_RUN',
        m.access_audit_event.c.details['resourceIds'].contains([resource])))
    if prior:
        raise PermissionError('Independent review requires a different real operator, not merely a different selected user')
    from valuation import tables as t
    from valuation.review_authority import assert_batch_independent
    identity=UUID(resource)
    if c.scalar(select(t.batch.c.batch_id).where(t.batch.c.tenant_id==tenant,t.batch.c.batch_id==identity)):
        assert_batch_independent(c,tenant,identity,actor)


def resource_ids(value):
    result=set()
    if isinstance(value,dict):
        for child in value.values():result.update(resource_ids(child))
    elif isinstance(value,list):
        for child in value:result.update(resource_ids(child))
    elif isinstance(value,str):
        try:result.add(str(UUID(value)))
        except ValueError:pass
    return result


def required_action(path,method):
    read=method in {'GET','HEAD'}
    resource=path.removeprefix('/v1/').split('/')[0]
    if resource=='access': return 'ACCESS_MANAGE'
    if resource=='strategies':
        if read and '/positions' in path:return 'TRADE_READ'
        if read and path.endswith('/calendars'):return 'CALENDAR_READ'
        if path=='/v1/strategies/access-options': return 'STRATEGY_CREATE'
        return 'STRATEGY_READ' if read else ('STRATEGY_CREATE' if path=='/v1/strategies' else 'STRATEGY_WRITE')
    if resource=='trades':
        if read:return 'TRADE_READ'
        return 'TRADE_CORRECT' if path.endswith(('/cancel-booking','/fx-delivery')) else 'TRADE_WRITE'
    if resource=='trade-configuration': return 'TRADE_CONFIGURE'
    if resource=='lifecycle':
        if read or path.endswith('/preview'): return 'LIFECYCLE_READ'
        if path.startswith('/v1/lifecycle/coupons/'):
            return {'/v1/lifecycle/coupons/schedules':'REFERENCE_APPROVE',
                '/v1/lifecycle/coupons/payments':'LIFECYCLE_BOOK',
                '/v1/lifecycle/coupons/payments/correct':'TRADE_CORRECT',
                '/v1/lifecycle/coupons/payments/reverse':'TRADE_CORRECT'}.get(path)
        if path.startswith('/v1/lifecycle/fx-forward/'):
            return {'/v1/lifecycle/fx-forward/policy':'LIFECYCLE_CONFIGURE',
                '/v1/lifecycle/fx-forward/closures/prepare':'LIFECYCLE_PREPARE',
                '/v1/lifecycle/fx-forward/closures/book':'LIFECYCLE_BOOK',
                '/v1/lifecycle/fx-forward/closures/approve':'LIFECYCLE_APPROVE',
                '/v1/lifecycle/fx-forward/closures/cancel':'TRADE_CORRECT'}.get(path)
        return {'/v1/lifecycle/policy':'LIFECYCLE_CONFIGURE','/v1/lifecycle/bond-redemptions/prepare':'LIFECYCLE_PREPARE',
            '/v1/lifecycle/bond-redemptions/book':'LIFECYCLE_BOOK','/v1/lifecycle/bond-redemptions/approve':'LIFECYCLE_APPROVE',
            '/v1/lifecycle/bond-redemptions/cancel':'TRADE_CORRECT'}.get(path)
    if resource=='valuation':
        if path=='/v1/valuation/cash-balance-preview':return 'VALUATION_READ'
        if read:return 'VALUATION_READ'
        if path.endswith('/self-publish'):return 'VALUATION_SELF_PUBLISH'
        if path.startswith('/v1/valuation/economic-flows/') and path.endswith('/cancel'):
            return 'TRADE_CORRECT'
        return 'VALUATION_REVIEW' if path.endswith(('/publish','/approve','/reject')) else 'VALUATION_RUN'
    if resource=='market-data' or resource=='market-data-resolution-snapshots':
        if '/calendars' in path:return 'CALENDAR_READ' if read else 'CALENDAR_MANAGE'
        return 'MARKET_DATA_READ' if read or path.endswith(('/resolution-preview','/policy-compatibility')) else 'MARKET_DATA_MANAGE'
    if resource in GLOBAL_CATALOGUES:return 'CATALOGUE_READ'
    if resource in {'instruments','reference-nodes','work-queue'} or resource.endswith('-proposals'):
        if read:return 'REFERENCE_READ'
        return 'REFERENCE_APPROVE' if path.endswith('/decision') else 'REFERENCE_PROPOSE'
    if resource=='portfolios':return 'VALUATION_READ'
    return None


def _authorize_request(request,body,engine_factory,environment,settings):
    path=request.url.path
    actor=UUID(request.headers['x-user-account-id'])
    tenant=None
    action=None
    with engine_factory().begin() as c:
        configure_transaction_budget(c,settings)
        token=request.headers.get('x-local-access-token')
        context=access_sessions.resolve(c,token,environment=environment) if token else None
        if context and (context['userId']!=str(actor) or context['tenantId']!=request.headers.get('x-tenant-id')):
            raise PermissionError('Request does not match the selected testing context')
        if path.startswith('/v1/platform/'):
            if context and context['tenantId']:
                raise PermissionError('Return to platform mode before administering tenants')
            access_management.require_platform(c,actor)
        elif path=='/v1/session/memberships':
            if c.scalar(select(m.user_account.c.user_account_id).where(m.user_account.c.user_account_id==actor,
                m.user_account.c.status=='ACTIVE')) is None:raise PermissionError('Account is inactive')
        else:
            tenant=UUID(request.headers.get('x-tenant-id',''))
            workspace=resolve_tenant_workspace(c,tenant,actor,governance_date())
            membership_read = request.method in {'GET','HEAD'} and path in {
                '/v1/tenant-workspace', '/v1/tenant-workspace/effective-access'}
            if not membership_read:
                action=required_action(path,request.method)
                if path=='/v1/strategies' and request.method=='GET' and request.query_params.get('forAction') in {
                    'STRATEGY_READ','TRADE_READ','TRADE_WRITE','VALUATION_READ','VALUATION_RUN'}:
                    action=request.query_params['forAction']
                if action=='CATALOGUE_READ':
                    if not workspace.permission_codes - {'ACCESS_MANAGE'}:
                        raise PermissionError('No module access is granted to this user')
                elif action is None:
                    raise PermissionError('No permission policy exists for this endpoint')
                else:
                    require_tenant_action(workspace,action)
            from .strategy_boundary import enforce_targets
            if action and action!='ACCESS_MANAGE':
                enforce_targets(c,tenant,actor,action,path,dict(request.query_params),body)
            request.state.permission_action=action
            request.state.effective_actor_id=actor
            request.state.real_actor_id=UUID(context['actorId']) if context else actor
            if action=='VALUATION_REVIEW':
                targets=re.findall(r'[0-9a-fA-F]{8}-[0-9a-fA-F-]{27}',path)
                for target in targets:
                    assert_independent_operator(c,tenant,request.state.real_actor_id,target.lower())
    return tenant,actor,action,context


def install_access_boundary(app,engine_factory,environment,settings=None):
    settings=settings or Settings.from_environment()
    @app.middleware('http')
    async def authorization_boundary(request,call_next):
        with governance_scope():
            return await dispatch(request,call_next)

    async def dispatch(request,call_next):
        path=request.url.path
        if not path.startswith('/v1/') or path.startswith('/v1/local-session'):
            return await call_next(request)
        if not request.headers.get('x-user-account-id'):
            return denied(401,'Authentication context is required',request)
        body={}
        if request.method not in {'GET','HEAD','OPTIONS'}:
            try:
                parsed=await request.json()
                if isinstance(parsed,dict):body=parsed
            except (ValueError,UnicodeDecodeError):pass
        try:
            tenant,actor,action,context=await run_in_threadpool(
                _authorize_request,request,body,engine_factory,environment,settings)
        except (PermissionError,ValueError) as exc:
            return denied(403,str(exc),request)
        command = CommandAudit(tenant, UUID(context['actorId']) if context else actor, actor,
            action, path, request.method, getattr(request.state,'request_id',None)) if (
                tenant and request.method not in {'GET','HEAD','OPTIONS'}) else None
        with command_scope(command):
            response=await call_next(request)
        response.headers['Cache-Control']='no-store'
        return response


def denied(status,message,request):
    """Common safe problem contract, retaining the local UI message alias."""
    from .problem_details import _problem_response,_safe_http_problem
    _,code,title,detail,slug=_safe_http_problem(status)
    response=_problem_response(request,status_code=status,code=code,title=title,detail=detail,type_slug=slug)
    body=json.loads(response.body)
    body['error']={'code':'access.forbidden' if status==403 else code,'message':message}
    return JSONResponse(body,status_code=status,media_type='application/problem+json',
        headers={'X-Request-ID':request.state.request_id,'Cache-Control':'no-store'})
