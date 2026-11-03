"""Independent coordinators/workers share capacity without using domain pools."""
import asyncio
from contextlib import contextmanager
import json
import os
import subprocess
import signal
import sys
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from apps.reference_api.workload_admission import AdmissionController,WorkloadBusy,WorkloadAdmission,postgres_slots


def test_independent_coordinators_enforce_global_and_tenant_capacity_and_release():
    engines=[create_engine(os.environ['DATABASE_URL'],pool_size=2,max_overflow=0) for _ in range(2)]
    tenant,other,third=uuid4(),uuid4(),uuid4()
    try:
        with postgres_slots(engines[0],tenant,global_limit=2,tenant_limit=1) as control:
            assert not control.in_transaction()
            with pytest.raises(WorkloadBusy) as error:
                with postgres_slots(engines[1],tenant,global_limit=2,tenant_limit=1):pytest.fail('same tenant admitted')
            assert error.value.reason=='TENANT_CAPACITY'
            with postgres_slots(engines[1],other,global_limit=2,tenant_limit=1):
                with pytest.raises(WorkloadBusy) as full:
                    with postgres_slots(engines[0],third,global_limit=2,tenant_limit=1):pytest.fail('global overrun')
                assert full.value.reason=='GLOBAL_CAPACITY'
        # Reusing pooled sessions cannot leave reentrant advisory locks behind.
        with postgres_slots(engines[1],tenant,global_limit=1,tenant_limit=1):pass
    finally:
        for engine in engines:engine.dispose()


def test_worker_exit_releases_distributed_slot():
    from concurrent.futures import ThreadPoolExecutor
    code='''import os,sys
from uuid import UUID
from sqlalchemy import create_engine
from apps.reference_api.workload_admission import postgres_slots
assert "platform_isolated_tests_" in os.environ["DATABASE_URL"]
engine=create_engine(os.environ["DATABASE_URL"],connect_args={"connect_timeout":3})
with postgres_slots(engine,UUID(sys.argv[1]),global_limit=1,tenant_limit=1):
 print("READY:"+str(os.getpid()),flush=True)
 sys.stdin.readline()
'''
    tenant=uuid4();engine=create_engine(os.environ['DATABASE_URL'])
    child=subprocess.Popen([sys.executable,'-u','-c',code,str(tenant)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    try:
        with ThreadPoolExecutor(max_workers=1) as reader:
            ready=reader.submit(child.stdout.readline).result(timeout=10).strip()
            assert ready.startswith('READY:')
            worker=int(ready.split(':')[1])
        with pytest.raises(WorkloadBusy):
            with postgres_slots(engine,tenant,global_limit=1,tenant_limit=1):pytest.fail('child slot ignored')
        # On Windows a venv launcher can have a separate interpreter child.
        # Kill the exact PID returned by this owned worker, not just its launcher.
        os.kill(worker,signal.SIGTERM);child.wait(timeout=5)
        with postgres_slots(engine,tenant,global_limit=1,tenant_limit=1):pass
    finally:
        if child.poll() is None:child.kill();child.wait(timeout=5)
        for pipe in (child.stdin,child.stdout,child.stderr):pipe.close()
        engine.dispose()


def test_middleware_keeps_status_reads_open_and_holds_capacity_through_body_send_and_cancellation():
    @contextmanager
    def coordinate(tenant):yield
    controller=AdmissionController(coordinate,process_limit=1)
    async def scenario(cancel):
        started=asyncio.Event();release=asyncio.Event();tenant=uuid4();calls=[]
        async def app(scope,receive,send):
            calls.append(scope['path'])
            await send({'type':'http.response.start','status':200,'headers':[]})
            if scope['path']=='/v1/valuation/attempts' and scope['method']=='POST':
                started.set();await release.wait()
            await send({'type':'http.response.body','body':b'{}'})
        middleware=WorkloadAdmission(app,controller=controller,retry_after=5)
        def scope(method,path):return {'type':'http','asgi':{'version':'3.0'},'method':method,'path':path,'raw_path':path.encode(),'query_string':b'',
            'headers':[],'scheme':'http','server':('test',80),'state':{'request_id':str(uuid4()),'tenant_context':SimpleNamespace(tenant_id=tenant)}}
        async def receive():return {'type':'http.request','body':b''}
        first=[];blocked=[];normal=[]
        async def output(target,message):target.append(message)
        task=asyncio.create_task(middleware(scope('POST','/v1/valuation/attempts'),receive,lambda message:output(first,message)))
        await asyncio.wait_for(started.wait(),3)
        await middleware(scope('POST','/v1/valuation/attempts'),receive,lambda message:output(blocked,message))
        assert blocked[0]['status']==429
        body=json.loads(blocked[-1]['body']);assert body['notStarted'] is True and body['retryAfterSeconds']==5
        assert (b'retry-after',b'5') in blocked[0]['headers']
        await middleware(scope('GET','/v1/valuation/attempts'),receive,lambda message:output(normal,message))
        assert normal[0]['status']==200 and calls.count('/v1/valuation/attempts')==2
        if cancel:
            task.cancel()
            with pytest.raises(asyncio.CancelledError):await task
        else:release.set();await task
        with controller.enter(tenant):pass
    asyncio.run(scenario(False));asyncio.run(scenario(True))


def test_cancelled_http_request_does_not_release_a_still_running_sync_calculation():
    from threading import Event
    from fastapi import FastAPI,Request
    from httpx import AsyncClient,ASGITransport
    from apps.reference_api.request_audit import AuditedRoute
    started,release,finished=Event(),Event(),Event()
    @contextmanager
    def coordinate(tenant):yield
    tenant=uuid4();controller=AdmissionController(coordinate,process_limit=1)
    app=FastAPI();app.router.route_class=AuditedRoute
    @app.post('/v1/valuation/attempts')
    def calculate():
        started.set()
        try:assert release.wait(5),'Synthetic worker was not released'
        finally:finished.set()
        return {'done':True}
    app.add_middleware(WorkloadAdmission,controller=controller)
    @app.middleware('http')
    async def fixture_identity(request:Request,call_next):
        # This fixture isolates cancellation/resource ownership, not identity.
        request.state.tenant_context=SimpleNamespace(tenant_id=tenant)
        request.state.request_id=str(uuid4())
        return await call_next(request)
    async def scenario():
        async with AsyncClient(transport=ASGITransport(app=app),base_url='http://test') as client:
            task=asyncio.create_task(client.post('/v1/valuation/attempts'))
            try:
                assert await asyncio.to_thread(started.wait,3)
                task.cancel()
                # Observe capacity concurrently, while physical work is still
                # running. Awaiting the cancelled HTTP task can join that worker.
                await asyncio.sleep(0.05)
                assert not finished.is_set()
                with pytest.raises(WorkloadBusy):
                    with controller.enter(tenant):pytest.fail('A disconnected client released a still-running calculation slot')
            finally:
                release.set();assert await asyncio.to_thread(finished.wait,3)
                with pytest.raises(asyncio.CancelledError):await task
    asyncio.run(scenario())
