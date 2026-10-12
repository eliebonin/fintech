"""Central permission enforcement ahead of request parsing and business writes.

The local API trusts its private BFF header boundary, as before. An opaque local
session additionally pins actor, subject and tenant; mismatching headers fail.
This is not a substitute for production identity-provider authentication.
"""
from datetime import date
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
    if resource=='strategies': return 'STRATEGY_READ' if read else 'STRATEGY_WRITE'
    if resource=='trades':
        if read:return 'TRADE_READ'
        return 'TRADE_CORRECT' if path.endswith(('/cancel-booking','/fx-delivery')) else 'TRADE_WRITE'
    if resource=='trade-configuration': return 'TRADE_CONFIGURE'
    if resource=='valuation':
        if read:return 'VALUATION_READ'
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


def install_access_boundary(app,engine_factory,environment):
    @app.middleware('http')
    async def authorization_boundary(request,call_next):
        path=request.url.path
        if not path.startswith('/v1/') or path.startswith('/v1/local-session'):
            return await call_next(request)
        try:
            tenant=None
            action=None
            raw_actor=request.headers.get('x-user-account-id')
            if not raw_actor:
                return denied(401,'Authentication context is required',request)
            actor=UUID(raw_actor)
            with engine_factory().begin() as c:
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
                    workspace=resolve_tenant_workspace(c,tenant,actor,date.today())
                    if path!='/v1/tenant-workspace':
                        action=required_action(path,request.method)
                        if action=='CATALOGUE_READ':
                            if not workspace.permission_codes - {'ACCESS_MANAGE'}:
                                raise PermissionError('No module access is granted to this user')
                        elif action is None:
                            raise PermissionError('No permission policy exists for this endpoint')
                        else:
                            require_tenant_action(workspace,action)
                    request.state.real_actor_id=UUID(context['actorId']) if context else actor
                    if action=='VALUATION_REVIEW':
                        targets=re.findall(r'[0-9a-fA-F]{8}-[0-9a-fA-F-]{27}',path)
                        for target in targets:
                            assert_independent_operator(c,tenant,request.state.real_actor_id,target.lower())
        except (PermissionError,ValueError) as exc:
            return denied(403,str(exc),request)
        response=await call_next(request)
        if request.method not in {'GET','HEAD','OPTIONS'} and response.status_code<400 and tenant:
            # Capture only result identifiers, never price values or credentials.
            body=b''.join([chunk async for chunk in response.body_iterator])
            try: ids=sorted(resource_ids(json.loads(body)))
            except (ValueError,TypeError):ids=[]
            with engine_factory().begin() as c:
                access_management.audit(c,UUID(context['actorId']) if context else actor,tenant,'TENANT_REQUEST',
                    {'path':path,'method':request.method,'permission':action,'resourceIds':ids,
                     'requestId':response.headers.get('X-Request-Id')},actor)
            response=Response(body,status_code=response.status_code,headers=dict(response.headers),media_type=response.media_type,
                              background=response.background)
        response.headers['Cache-Control']='no-store'
        return response


def denied(status,message,request):
    """Use the common problem contract while retaining the local UI error alias."""
    from .problem_details import _problem_response,_safe_http_problem
    _,code,title,detail,slug=_safe_http_problem(status)
    response=_problem_response(request,status_code=status,code=code,title=title,detail=detail,type_slug=slug)
    body=json.loads(response.body)
    # Older local-session consumers read error.message. Keep this compatibility
    # field; top-level code/detail remain the documented API problem contract.
    body['error']={'code':'access.forbidden' if status==403 else code,'message':message}
    return JSONResponse(body,status_code=status,media_type='application/problem+json',
        headers={'X-Request-ID':request.state.request_id,'Cache-Control':'no-store'})
