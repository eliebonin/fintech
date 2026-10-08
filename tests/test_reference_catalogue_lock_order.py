"""A blocked reference-type phase must not retain a later product-type lock."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from time import monotonic, sleep
from uuid import uuid4
import pytest
from sqlalchemy import select, text
from apps.reference_api.db import get_engine
from apps.reference_api import repository as r
from apps.reference_api.contracts import EtpProposalRequest
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from tests.test_cash_booking_integrity import book


@pytest.mark.parametrize('writer', ['cash', 'etp'])
def test_reference_type_lock_precedes_product_type_lock(writer):
    proposal_id = None
    if writer == 'etp':
        with get_engine().begin() as setup:
            request = EtpProposalRequest(canonicalName='Lock order '+str(uuid4()), effectiveFrom='2026-09-01',
                etpKind='ETF', legalForm='FUND', redemptionModel='CASH', baseCurrencyId=ids['eur_currency'],
                referenceNodeId=ids['hsbc_instrument_node'])
            proposal_id = r.submit_etp_proposal(setup, ids['tenant'], ids['demo_user_account'], request).proposal_id
    ready = Event()
    pid = []
    def execute():
        with get_engine().connect() as worker:
            transaction = worker.begin()
            try:
                pid.append(worker.scalar(text('SELECT pg_backend_pid()')))
                ready.set()
                if writer == 'cash':
                    book(worker)
                else:
                    r.decide_etp_proposal(worker, ids['tenant'], ids['demo_user_account'], proposal_id, 'APPROVED', 'Lock ordering test')
            finally:
                transaction.rollback()
    with get_engine().connect() as blocker, ThreadPoolExecutor(max_workers=1) as pool:
        transaction = blocker.begin()
        future = None
        try:
            blocker.execute(select(m.reference_node_type).where(m.reference_node_type.c.type_code == 'INSTRUMENT').with_for_update()).all()
            future = pool.submit(execute)
            assert ready.wait(5)
            deadline = monotonic() + 5
            with get_engine().begin() as observer:
                while monotonic() < deadline:
                    if observer.scalar(text('SELECT cardinality(pg_blocking_pids(:pid))'), {'pid':pid[0]}):
                        break
                    sleep(0.01)
                else:
                    pytest.fail('Writer did not wait for reference-type catalogue lock')
                # If held already, a reverse-order catalogue writer could deadlock.
                observer.execute(select(m.instrument_type).where(m.instrument_type.c.type_code == 'EQUITY').with_for_update(nowait=True)).all()
        finally:
            transaction.rollback()
            if future is not None:
                future.result(timeout=10)
