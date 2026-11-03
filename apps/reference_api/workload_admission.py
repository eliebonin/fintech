"""Nonblocking expensive-work admission; no limits on financial populations."""
from contextlib import contextmanager
from hashlib import sha256
import json
import logging
import re
from threading import BoundedSemaphore,Lock
from time import perf_counter

from anyio import CancelScope
from sqlalchemy import create_engine,text
from sqlalchemy.exc import DBAPIError,TimeoutError as PoolTimeout
from starlette.concurrency import run_in_threadpool
from starlette.requests import Request

LOGGER=logging.getLogger('apps.reference_api.workload')
# Routing owns UUID validation. Classify every spelling accepted by its parser,
# including compact/URN/braced UUIDs; a 36-character regex would be bypassable.
_ID=r'[^/]+'


def workload_kind(method,path):
    if method=='POST':
        if path in {'/v1/valuation/attempts','/v1/valuation/reassessments/recalculate','/v1/valuation/balance-history-refresh','/v1/valuation/interest-review'}:return 'valuation'
        if path in {'/v1/regulatory-reporting/prepare','/v1/regulatory-reporting/exports'}:return 'regulatory'
        if path=='/v1/trades/imports' or re.fullmatch(rf'/v1/trades/imports/{_ID}/(?:validate|confirm)',path):return 'trade_import'
    if method=='GET':
        if path in {'/v1/valuation/interest-review','/v1/valuation/balance-trades'}:return 'valuation'
        if re.fullmatch(rf'/v1/strategies/{_ID}/measures',path):return 'measures'
        if path=='/v1/regulatory-reporting/export-preview' or re.fullmatch(rf'/v1/regulatory-reporting/exports/{_ID}',path):return 'regulatory'
        if path=='/v1/trades/imports/template' or re.fullmatch(rf'/v1/trades/imports/{_ID}/(?:errors|artifact)',path):return 'trade_import'
    return None


class WorkloadBusy(RuntimeError):
    def __init__(self,reason='CAPACITY'):self.reason=reason


class WorkloadUnavailable(RuntimeError):
    reason='COORDINATION_UNAVAILABLE'


class AdmissionController:
    def __init__(self,coordination,*,process_limit=2,cleanup=None):
        if process_limit<1:raise ValueError('Workload limits must be positive')
        self.coordination=coordination
        self.slots=BoundedSemaphore(process_limit)
        self.cleanup=cleanup

    def close(self):
        if self.cleanup:self.cleanup()

    @contextmanager
    def enter(self,tenant):
        if not self.slots.acquire(blocking=False):raise WorkloadBusy('PROCESS_CAPACITY')
        try:
            with self.coordination(tenant):yield
        finally:self.slots.release()


def coordination_engine(database_url,process_limit):
    if not database_url:raise RuntimeError('Explicit workload coordination database required')
    # Independent small pool: never reserve a connection from the business pool
    # while waiting for its own one-connection snapshot/release workflow.
    return create_engine(database_url,pool_size=process_limit,max_overflow=0,
        pool_timeout=0.1,pool_pre_ping=True,connect_args={'connect_timeout':3,'application_name':'platform_workload_admission'},hide_parameters=True)


def _lock_key(scope,slot):
    return int.from_bytes(sha256(f'platform-workload-v1:{scope}:{slot}'.encode()).digest()[:8],'big',signed=True)


@contextmanager
def postgres_slots(engine,tenant,*,global_limit=2,tenant_limit=1):
    """Shared across API workers; session loss releases PostgreSQL's locks."""
    if min(global_limit,tenant_limit)<1:raise ValueError('Workload limits must be positive')
    connection=None;held=[]
    try:
        try:
            connection=engine.connect()
            connection.execute(text("SELECT set_config('statement_timeout','3000',false),set_config('lock_timeout','1000',false)"))
            for scope,limit,reason in [('global',global_limit,'GLOBAL_CAPACITY'),(f'tenant:{tenant}',tenant_limit,'TENANT_CAPACITY')]:
                for index in range(limit):
                    key=_lock_key(scope,index)
                    if connection.scalar(text('SELECT pg_try_advisory_lock(:key)'),{'key':key}):
                        held.append(key);break
                else:raise WorkloadBusy(reason)
            # Session locks survive commit. Do not retain an idle transaction
            # while the domain calculation or response is running.
            connection.commit()
        except (DBAPIError,PoolTimeout) as exc:
            raise WorkloadUnavailable() from exc
        yield connection
    finally:
        if connection is not None:
            try:
                # Rollback alone does not release session advisory locks. Return
                # only a clean unlocked connection; otherwise destroy its session.
                connection.rollback()
                for key in reversed(held):
                    if not connection.scalar(text('SELECT pg_advisory_unlock(:key)'),{'key':key}):
                        raise RuntimeError('Workload lock ownership lost')
                connection.rollback()
            except Exception:
                connection.invalidate()
                LOGGER.warning('{"event":"workload_coordination_reset"}')
            finally:connection.close()


def controller_from_settings(settings):
    opened=[];initialization=Lock()
    @contextmanager
    def coordinate(tenant):
        with initialization:
            if not opened:opened.append(coordination_engine(settings.database_url,settings.workload_process_limit))
            engine=opened[0]
        with postgres_slots(engine,tenant,global_limit=settings.workload_global_limit,
                tenant_limit=settings.workload_tenant_limit):yield
    def cleanup():
        with initialization:
            engines=list(opened);opened.clear()
        for engine in engines:engine.dispose()
    return AdmissionController(coordinate,process_limit=settings.workload_process_limit,cleanup=cleanup)


class WorkloadAdmission:
    """Inside verified identity, outside routing/dependencies and full body send."""
    def __init__(self,app,*,controller,retry_after=5):
        self.app=app;self.controller=controller;self.retry_after=retry_after

    async def __call__(self,scope,receive,send):
        if scope['type']!='http':return await self.app(scope,receive,send)
        request=Request(scope)
        kind=workload_kind(request.method,request.url.path)
        tenant=getattr(request.state,'tenant_context',None)
        if not kind or tenant is None:return await self.app(scope,receive,send)
        entered=False;started=perf_counter();context=self.controller.enter(tenant.tenant_id)
        fields={'requestId':getattr(request.state,'request_id',None),'tenantId':str(tenant.tenant_id),'kind':kind}
        try:
            try:
                # Cleanup ownership is established before cancellation is allowed.
                with CancelScope(shield=True):
                    await run_in_threadpool(context.__enter__);entered=True
            except (WorkloadBusy,WorkloadUnavailable) as exc:
                from .problem_details import _problem_response
                from starlette.responses import JSONResponse
                status=429 if isinstance(exc,WorkloadBusy) else 503
                response=_problem_response(request,status_code=status,code='workload.busy' if status==429 else 'workload.unavailable',
                    title='Service capacity is busy' if status==429 else 'Workload admission unavailable',
                    detail=f'This submission was not started. An earlier submission with the same key may still be running; check run or request history. Retry unchanged after {self.retry_after} seconds.',type_slug='workload-capacity')
                body=json.loads(response.body)
                body.update(retryable=True,notStarted=True,retryAfterSeconds=self.retry_after)
                LOGGER.warning(json.dumps(dict(event='workload_rejected',reason=exc.reason,**fields)))
                return await JSONResponse(body,status_code=status,media_type='application/problem+json',
                    headers={'Retry-After':str(self.retry_after),'Cache-Control':'no-store','X-Request-ID':request.state.request_id})(scope,receive,send)
            LOGGER.info(json.dumps(dict(event='workload_admitted',**fields)))
            return await self.app(scope,receive,send)
        finally:
            if entered:
                with CancelScope(shield=True):await run_in_threadpool(context.__exit__,None,None,None)
                LOGGER.info(json.dumps(dict(event='workload_released',elapsedMs=int((perf_counter()-started)*1000),**fields)))
