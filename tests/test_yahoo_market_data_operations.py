"""Exercise the real CLI flow and DB, replacing only external Yahoo HTTP."""
from datetime import date
import json
import sys
import pytest
from contextlib import contextmanager
from sqlalchemy import select,func
import httpx
from apps.reference_api.db import get_engine
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS
from security_master_schema.index_universe_seed import seed
from market_data.providers.yahoo.onboarding import enable_personal_research
from tests.test_yahoo_market_data import chart


@pytest.fixture
def operator_engine():
    # Real SQL with independent savepoints; CLI commits cannot pollute other tests.
    connection=get_engine().connect()
    transaction=connection.begin()
    class Connection:
        def begin(self):
            return connection.begin_nested()
        def __getattr__(self,name):
            return getattr(connection,name)
    class Engine:
        @contextmanager
        def begin(self):
            with connection.begin_nested():
                yield connection
        @contextmanager
        def connect(self):
            yield Connection()
        def dispose(self):
            pass
    try:
        yield Engine()
    finally:
        transaction.rollback()
        connection.close()


def prepare(monkeypatch,extra,engine):
    from apps.market_data_ingestor import yahoo
    with engine.begin() as c:
        seed(c,DEMO_IDS['demo_user_account'])
        result=enable_personal_research(c,DEMO_IDS['tenant'],DEMO_IDS['demo_user_account'],'Synthetic operator test approval')
    # Keep CLI's operating-target guard real while directing its SQL to the isolated engine.
    from types import SimpleNamespace
    monkeypatch.setattr(yahoo.IngestorSettings,'from_environment',lambda:SimpleNamespace(environment='local',database_url='postgresql+psycopg://unused:unused@localhost:54329/fortem_secm'))
    monkeypatch.setattr(yahoo,'create_engine',lambda *a,**kw:engine)
    monkeypatch.setattr(sys,'argv',['ingestor','--apply','--acknowledge-personal-access','--declaration','Synthetic tests only','--symbols','AAPL','--limit','1',*extra])
    return yahoo,engine,result


def test_partial_resume_and_exact_gap_retry_remain_partial(monkeypatch,capsys,operator_engine):
    yahoo,engine,ids=prepare(monkeypatch,['--start','2026-10-05','--through','2026-10-06'],operator_engine)
    payload=chart()
    payload['chart']['result'][0]['indicators']['quote'][0]['close'][1]=None
    payload['chart']['result'][0]['indicators']['adjclose'][0]['adjclose'][1]=None
    monkeypatch.setattr(yahoo,'fetch_chart',lambda *a,**kw:json.dumps(payload))
    assert yahoo.main()==3
    assert json.loads(capsys.readouterr().out.splitlines()[-1])['outcome']=='PARTIAL'
    def unexpected(*a,**kw): raise AssertionError('Resume must not refetch the complete window')
    monkeypatch.setattr(yahoo,'fetch_chart',unexpected)
    assert yahoo.main()==3
    capsys.readouterr()
    # Exact dated retry only; preserve duplicates and ignore prices outside the retry date.
    partial=chart()
    result=partial['chart']['result'][0]
    result['timestamp']=result['timestamp'][1:]
    for block,key in ((result['indicators']['quote'][0],'close'),(result['indicators']['adjclose'][0],'adjclose')):
        block[key]=[None]
    def retry(client,symbol,start,end,**kw):
        assert symbol=='AAPL' and start==end==date(2026,10,6)
        return json.dumps(partial)
    monkeypatch.setattr(yahoo,'fetch_chart',retry)
    monkeypatch.setattr(sys,'argv',sys.argv+['--retry-gaps'])
    assert yahoo.main()==3
    with engine.connect() as c:
        assert c.scalar(select(func.count()).select_from(m.market_data_ingestion_job).where(m.market_data_ingestion_job.c.status=='PARTIAL'))==3
        assert c.scalar(select(func.count()).select_from(m.market_data_ingestion_attempt).where(m.market_data_ingestion_attempt.c.status=='RUNNING'))==0
    capsys.readouterr()
    result['indicators']['quote'][0]['close']=[252]
    result['indicators']['adjclose'][0]['adjclose']=[252]
    # Source gaps are resolved, but this synthetic response has no certified
    # split-adjustment anchor. RAW readiness must remain partial, not be invented.
    assert yahoo.main()==3
    final=json.loads(capsys.readouterr().out.splitlines()[-1])
    assert final['sourceOutcome']=='COMPLETE' and final['outcome']=='PARTIAL'
    assert final['normalization']['status']!='COMPLETE'
    with engine.connect() as c:
        # The original partial report stays immutable even after its missing date is filled.
        original=c.execute(select(m.market_data_ingestion_run.c.report).where(
            m.market_data_ingestion_run.c.dataset_id==ids['datasetId'],
            m.market_data_ingestion_run.c.report['request']['start'].as_string()=='2026-10-05')).scalars().first()
        assert original['rejected']==2


def test_network_failure_is_durable_and_audit_never_downloads(monkeypatch,capsys,operator_engine):
    yahoo,engine,ids=prepare(monkeypatch,['--days','2','--through','2026-10-04'],operator_engine)
    def offline(*a,**kw): raise httpx.ConnectError('Synthetic network unavailable')
    monkeypatch.setattr(yahoo,'fetch_chart',offline)
    assert yahoo.main()==1
    with engine.connect() as c:
        assert c.scalar(select(func.count()).select_from(m.market_data_ingestion_attempt).where(m.market_data_ingestion_attempt.c.status=='FAILED'))>=1
    capsys.readouterr()
    monkeypatch.setattr(sys,'argv',['ingestor','--declaration','Synthetic audit only','--audit-only','--symbols','AAPL','--limit','1','--days','2','--through','2026-10-04'])
    assert yahoo.main()==0
    report=json.loads(capsys.readouterr().out.splitlines()[-1])
    assert report['pricesModified'] is False and report['listingCount']==1


def test_revoked_storage_blocks_even_history_resume(monkeypatch,capsys,operator_engine):
    yahoo,engine,ids=prepare(monkeypatch,['--start','2026-10-05','--through','2026-10-06'],operator_engine)
    monkeypatch.setattr(yahoo,'fetch_chart',lambda *a,**kw:json.dumps(chart()))
    assert yahoo.main() in {0,3}
    capsys.readouterr()
    with engine.begin() as c:
        c.execute(m.licence_activity_grant.update().where(m.licence_activity_grant.c.activity=='STORE',
            m.licence_activity_grant.c.dataset_licence_assignment_id.in_(select(m.dataset_licence_assignment.c.dataset_licence_assignment_id).where(
                m.dataset_licence_assignment.c.dataset_id==ids['datasetId']))).values(status='SUSPENDED'))
    def no_source(*a,**kw): raise AssertionError('Revoked rights must never contact source')
    monkeypatch.setattr(yahoo,'fetch_chart',no_source)
    try:
        assert yahoo.main()==1
        assert json.loads(capsys.readouterr().out.splitlines()[-1])['outcome']=='BLOCKED'
    finally:
        with engine.begin() as c:
            c.execute(m.licence_activity_grant.update().where(m.licence_activity_grant.c.activity=='STORE',
                m.licence_activity_grant.c.dataset_licence_assignment_id.in_(select(m.dataset_licence_assignment.c.dataset_licence_assignment_id).where(
                    m.dataset_licence_assignment.c.dataset_id==ids['datasetId']))).values(status='ACTIVE'))


def test_publication_database_failure_rolls_back_prices_but_retains_attempt(monkeypatch,capsys,operator_engine):
    from sqlalchemy import event
    from sqlalchemy.exc import OperationalError
    yahoo,engine,ids=prepare(monkeypatch,['--start','2026-10-05','--through','2026-10-06'],operator_engine)
    monkeypatch.setattr(yahoo,'fetch_chart',lambda *a,**kw:json.dumps(chart()))
    with engine.connect() as c:
        sql_engine=c.engine
        before=c.scalar(select(func.count()).select_from(m.market_data_observation))
    def fail_insert(conn,cursor,statement,parameters,context,executemany):
        if statement.lstrip().upper().startswith('INSERT INTO MD.MARKET_DATA_OBSERVATION'):
            raise OperationalError(statement,parameters,RuntimeError('Synthetic driver failure'))
    event.listen(sql_engine,'before_cursor_execute',fail_insert)
    try:
        assert yahoo.main()==1
    finally:
        event.remove(sql_engine,'before_cursor_execute',fail_insert)
    assert json.loads(capsys.readouterr().out.splitlines()[-1])['outcome']=='FAILED'
    with engine.connect() as c:
        assert c.scalar(select(func.count()).select_from(m.market_data_observation))==before
        failed=c.execute(select(m.market_data_ingestion_attempt).where(
            m.market_data_ingestion_attempt.c.status=='FAILED')).mappings().one()
        assert failed['report']['error']=='OperationalError'
        assert failed['delivery_run_id'] is None
