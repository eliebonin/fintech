"""Admission rejects excess work without truncating financial populations."""
from uuid import uuid4


def test_balance_trade_annotations_use_valuation_admission():
    from apps.reference_api.workload_admission import workload_kind
    assert workload_kind('GET','/v1/valuation/balance-trades')=='valuation'
import pytest


def test_local_slots_are_nonblocking_and_released_after_errors():
    from apps.reference_api.workload_admission import AdmissionController,WorkloadBusy
    from contextlib import contextmanager
    @contextmanager
    def coordination(tenant):yield
    controller=AdmissionController(coordination,process_limit=1)
    tenant=uuid4()
    with controller.enter(tenant):
        with pytest.raises(WorkloadBusy):
            with controller.enter(tenant):pytest.fail('excess work started')
    with pytest.raises(RuntimeError):
        with controller.enter(tenant):raise RuntimeError('synthetic failure')
    with controller.enter(tenant):pass


def test_classification_limits_expensive_work_without_blocking_ordinary_reads():
    from apps.reference_api.workload_admission import workload_kind
    assert workload_kind('POST','/v1/valuation/attempts')=='valuation'
    assert workload_kind('GET','/v1/strategies/'+str(uuid4())+'/measures')=='measures'
    assert workload_kind('GET','/v1/strategies') is None
    assert workload_kind('GET','/v1/trades') is None
    assert workload_kind('POST','/v1/trades') is None


def test_noncanonical_valid_uuid_paths_cannot_bypass_admission():
    from apps.reference_api.workload_admission import workload_kind
    identity=uuid4()
    for value in (identity.hex,'urn:uuid:'+str(identity),'{'+str(identity)+'}'):
        assert workload_kind('GET',f'/v1/strategies/{value}/measures')=='measures'
        assert workload_kind('POST',f'/v1/trades/imports/{value}/confirm')=='trade_import'


def test_first_concurrent_requests_create_one_owned_coordination_pool(monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from contextlib import contextmanager
    from threading import Barrier
    from time import sleep
    from apps.reference_api import workload_admission as a
    from apps.reference_api.config import Settings
    created=[];gate=Barrier(2)
    class Engine:
        def __init__(self):self.disposed=False
        def dispose(self):self.disposed=True
    def factory(*args):
        sleep(.02)
        result=Engine();created.append(result);return result
    @contextmanager
    def slots(*args,**kwargs):yield
    monkeypatch.setattr(a,'coordination_engine',factory);monkeypatch.setattr(a,'postgres_slots',slots)
    controller=a.controller_from_settings(Settings.from_environment())
    def work():
        with controller.enter(uuid4()):gate.wait(timeout=2)
    with ThreadPoolExecutor(max_workers=2) as workers:
        futures=[workers.submit(work) for _ in range(2)]
        for future in futures:future.result(timeout=3)
    controller.close()
    assert len(created)==1 and created[0].disposed
