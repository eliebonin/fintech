"""Platform registry and tenant-local delegated access management."""
from uuid import UUID
from fastapi import Depends, Header, Query,Request
from .request_audit import AuditRouter as APIRouter
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from security_master_schema import access_management as service, access_sessions as sessions, models as m
from .tenant_context import get_actor_context, get_tenant_context
from .problem_details import ApiProblem
from .access_contracts import ModuleChange,UserCreate,UserChange,UserGroups,GroupSave,GroupPreview,ContextSelect,TenantUpdate
from .access_contracts import PublicationPolicyChange


def access_router(connection_dependency, environment):
    router=APIRouter(tags=['access administration'])

    def run(action):
        try:
            return action()
        except PermissionError as exc:
            raise ApiProblem(403,'access.forbidden','Access denied',str(exc)) from exc
        except service.TenantProfileConflict as exc:
            raise ApiProblem(409,'tenant.profile_conflict','Tenant details changed',str(exc)) from exc
        except service.AccessVersionConflict as exc:
            raise ApiProblem(409,'access.version_conflict','Access configuration changed',str(exc)) from exc
        except service.TenantNotFound as exc:
            raise ApiProblem(404,'tenant.not_found','Tenant not found',str(exc)) from exc
        except ValueError as exc:
            raise ApiProblem(422,'access.invalid','Invalid access configuration',str(exc)) from exc
        except IntegrityError as exc:
            raise ApiProblem(409,'access.conflict','Access configuration conflict','This code or assignment already exists.') from exc

    @router.get('/v1/platform/tenants')
    def tenants(actor=Depends(get_actor_context),c=Depends(connection_dependency,scope='function')):
        return run(lambda: service.platform_view(c,actor.user_account_id))

    @router.put('/v1/platform/tenants/{tenant_id}/modules/{module_code}')
    def module_change(tenant_id:UUID,module_code:str,payload:ModuleChange,
            actor=Depends(get_actor_context),c=Depends(connection_dependency,scope='function')):
        def command():
            service.set_module(c,tenant_id,actor.user_account_id,module_code,payload.enabled)
            return {'updated':True}
        return run(command)

    @router.put('/v1/platform/tenants/{tenant_id}')
    def tenant_update(tenant_id:UUID,payload:TenantUpdate,
            actor=Depends(get_actor_context),c=Depends(connection_dependency,scope='function')):
        return run(lambda: service.update_tenant(c,tenant_id,actor.user_account_id,payload))

    @router.get('/v1/access')
    def access(context=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return run(lambda: service.tenant_access_view(c,context.tenant_id,context.user_account_id))

    @router.get('/v1/access/valuation-publication-policy')
    def publication_policy(context=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        from valuation.self_publication import policy_view
        def view():
            service.require_admin(c,context.tenant_id,context.user_account_id)
            return policy_view(c,context.tenant_id)
        return run(view)

    @router.put('/v1/access/valuation-publication-policy')
    def publication_policy_change(payload:PublicationPolicyChange,http_request:Request,context=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        from valuation.self_publication import change_policy
        return run(lambda:change_policy(c,context.tenant_id,context.user_account_id,payload,getattr(http_request.state,'real_actor_id',context.user_account_id)))

    @router.get('/v1/tenant-workspace/effective-access')
    def effective_access(user_id:UUID|None=Query(default=None,alias='userId'),
            context=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        from security_master_schema.access_explanations import effective_access_view
        return run(lambda: effective_access_view(c,context.tenant_id,context.user_account_id,user_id))

    @router.post('/v1/access/users',status_code=201)
    def user_add(payload:UserCreate,context=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return run(lambda: {'userId':str(service.add_user(c,context.tenant_id,context.user_account_id,name=payload.name,role=payload.role))})

    @router.put('/v1/access/users/{user_id}')
    def user_change(user_id:UUID,payload:UserChange,context=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        def command():
            service.set_user_status(c,context.tenant_id,context.user_account_id,user_id,payload.status,payload.role)
            return {'updated':True}
        return run(command)

    @router.put('/v1/access/users/{user_id}/groups')
    def user_groups(user_id:UUID,payload:UserGroups,context=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        def command():
            service.set_user_groups(c,context.tenant_id,context.user_account_id,user_id,payload.groupIds)
            return {'updated':True}
        return run(command)

    def save_group(c,context,payload,group_id=None):
        if group_id and payload.expectedVersion is None:
            raise ApiProblem(422,'access.version_required','Revision required','Refresh group configuration before saving.')
        return run(lambda: {'groupId':str(service.save_group(c,context.tenant_id,context.user_account_id,
            code=payload.code,name=payload.name,actions=payload.actions,status=payload.status,description=payload.description,group_id=group_id,
            scope_mode=payload.scopeMode,strategy_ids=payload.strategyIds,expected_version=payload.expectedVersion,impact_hash=payload.expectedImpactHash))})

    @router.post('/v1/access/groups',status_code=201)
    def group_create(payload:GroupSave,context=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return save_group(c,context,payload)

    @router.post('/v1/access/groups/preview')
    def group_preview(payload:GroupPreview,context=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        from security_master_schema.strategy_access_admin import preview
        if payload.groupId and payload.expectedVersion is None:
            raise ApiProblem(422,'access.version_required','Revision required','Refresh before previewing.')
        return run(lambda: preview(c,context.tenant_id,context.user_account_id,payload))

    @router.get('/v1/access/strategy-matrix')
    def strategy_matrix(strategy_id:UUID|None=Query(default=None,alias='strategyId'),
            context=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        from security_master_schema.strategy_access_admin import matrix
        return run(lambda: matrix(c,context.tenant_id,context.user_account_id,strategy_id))

    @router.put('/v1/access/groups/{group_id}')
    def group_change(group_id:UUID,payload:GroupSave,context=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return save_group(c,context,payload,group_id)

    @router.get('/v1/access/audit')
    def audit(context=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        def read():
            service.require_admin(c,context.tenant_id,context.user_account_id)
            rows=c.execute(select(m.access_audit_event).where(m.access_audit_event.c.tenant_id==context.tenant_id)
                .order_by(m.access_audit_event.c.recorded_at_utc.desc()).limit(100)).mappings().all()
            return {'events':[dict(row) for row in rows]}
        return run(read)

    @router.get('/v1/platform/audit')
    def platform_audit(actor=Depends(get_actor_context),c=Depends(connection_dependency,scope='function')):
        def read():
            service.require_platform(c,actor.user_account_id)
            return {'events':[dict(row) for row in c.execute(select(m.access_audit_event)
                .order_by(m.access_audit_event.c.recorded_at_utc.desc()).limit(100)).mappings()]}
        return run(read)

    @router.post('/v1/local-session',status_code=201)
    def select_context(payload:ContextSelect,actor=Depends(get_actor_context),
            token:str|None=Header(default=None,alias='X-Local-Access-Token'),c=Depends(connection_dependency,scope='function')):
        def command():
            new=sessions.start(c,actor.user_account_id,payload.tenantId,payload.userId,environment=environment)
            if token:
                sessions.end(c,actor.user_account_id,token,environment=environment)
            return {'token':new,'context':sessions.resolve(c,new,environment=environment)}
        return run(command)

    @router.get('/v1/local-session')
    def current(token:str=Header(alias='X-Local-Access-Token'),c=Depends(connection_dependency,scope='function')):
        try:
            return sessions.resolve(c,token,environment=environment)
        except PermissionError as exc:
            raise ApiProblem(401,'authentication.required','Authentication required',
                'Testing session expired, revoked or invalid; select a context again') from exc

    @router.delete('/v1/local-session')
    def end_context(actor=Depends(get_actor_context),token:str|None=Header(default=None,alias='X-Local-Access-Token'),
            c=Depends(connection_dependency,scope='function')):
        def command():
            sessions.end(c,actor.user_account_id,token,environment=environment)
            return {'ended':True}
        return run(command)

    @router.get('/v1/local-session/options')
    def context_options(actor=Depends(get_actor_context),token:str|None=Header(default=None,alias='X-Local-Access-Token'),
            c=Depends(connection_dependency,scope='function')):
        def read():
            sessions.local_only(environment)
            return service.platform_view(c,actor.user_account_id)
        return run(read)

    return router
