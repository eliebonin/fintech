"""Platform registry and tenant-local delegated access management."""
from uuid import UUID
from fastapi import APIRouter, Depends, Header
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from security_master_schema import access_management as service, access_sessions as sessions, models as m
from .tenant_context import get_actor_context, get_tenant_context
from .problem_details import ApiProblem
from .access_contracts import ModuleChange,UserCreate,UserChange,UserGroups,GroupSave,ContextSelect,TenantUpdate


def access_router(connection_dependency, environment):
    router=APIRouter(tags=['access administration'])

    def run(action):
        try:
            return action()
        except PermissionError as exc:
            raise ApiProblem(403,'access.forbidden','Access denied',str(exc)) from exc
        except service.TenantProfileConflict as exc:
            raise ApiProblem(409,'tenant.profile_conflict','Tenant details changed',str(exc)) from exc
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
        return run(lambda: {'groupId':str(service.save_group(c,context.tenant_id,context.user_account_id,
            code=payload.code,name=payload.name,actions=payload.actions,status=payload.status,description=payload.description,group_id=group_id))})

    @router.post('/v1/access/groups',status_code=201)
    def group_create(payload:GroupSave,context=Depends(get_tenant_context),c=Depends(connection_dependency,scope='function')):
        return save_group(c,context,payload)

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
            if token:
                old=sessions.resolve(c,token,environment=environment)
                if old['actorId']!=str(actor.user_account_id):
                    raise PermissionError('Only the real platform operator can change this testing context')
            new=sessions.start(c,actor.user_account_id,payload.tenantId,payload.userId,environment=environment)
            if token:
                sessions.revoke(c,token,environment=environment)
            return {'token':new,'context':sessions.resolve(c,new,environment=environment)}
        return run(command)

    @router.get('/v1/local-session')
    def current(token:str=Header(alias='X-Local-Access-Token'),c=Depends(connection_dependency,scope='function')):
        return run(lambda: sessions.resolve(c,token,environment=environment))

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
            if token and sessions.resolve(c,token,environment=environment)['actorId']!=str(actor.user_account_id):
                raise PermissionError('Only the real platform operator can select contexts')
            return service.platform_view(c,actor.user_account_id)
        return run(read)

    return router
