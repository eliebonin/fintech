"""Operational evidence survives failed publication; terminal states stay final."""
from datetime import date
import pytest
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError
from apps.reference_api.db import get_engine
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS
from tests.test_market_data_ingestion import setup_dataset


def test_job_attempts_terminal_immutability_and_explicit_recovery():
    from market_data.jobs import start_job,start_attempt,finish_attempt,finish_job,abort_job
    with get_engine().connect() as c:
        tx=c.begin()
        try:
            dataset,namespace,_=setup_dataset(c)
            job=start_job(c,dataset,namespace,DEMO_IDS['tenant'],DEMO_IDS['demo_user_account'],['AAPL'],date(2026,10,5),date(2026,10,6))
            attempt=start_attempt(c,job,'AAPL',date(2026,10,5),date(2026,10,6))
            finish_attempt(c,attempt,'PARTIAL',{'accepted':2,'duplicates':0,'rejected':2})
            assert finish_job(c,job)=='PARTIAL'
            assert c.scalar(select(m.market_data_ingestion_job.c.status).where(m.market_data_ingestion_job.c.job_id==job))=='PARTIAL'
            with pytest.raises(ValueError,match='terminal'):
                finish_attempt(c,attempt,'COMPLETE',{})
            save=c.begin_nested()
            with pytest.raises(DBAPIError,match='terminal'):
                c.execute(m.market_data_ingestion_attempt.update().where(m.market_data_ingestion_attempt.c.attempt_id==attempt).values(status='COMPLETE'))
            save.rollback()
            interrupted=start_job(c,dataset,namespace,DEMO_IDS['tenant'],DEMO_IDS['demo_user_account'],['AAPL'],date(2026,10,5),date(2026,10,6))
            start_attempt(c,interrupted,'AAPL',date(2026,10,5),date(2026,10,6))
            with pytest.raises(ValueError,match='running'):
                finish_job(c,interrupted)
            abort_job(c,interrupted,DEMO_IDS['tenant'],DEMO_IDS['demo_user_account'],'Operator verified process is stopped')
            assert c.scalar(select(m.market_data_ingestion_job.c.status).where(m.market_data_ingestion_job.c.job_id==interrupted))=='ABORTED'
        finally:
            tx.rollback()


def test_history_review_requires_attributed_nonoverlapping_evidence():
    from market_data.history import review_history,history_status
    with get_engine().connect() as c:
        tx=c.begin()
        try:
            dataset,namespace,_=setup_dataset(c)
            mapping=c.scalar(select(m.external_object_mapping.c.external_object_mapping_id).where(m.external_object_mapping.c.external_id_namespace_id==namespace))
            assert history_status(c,mapping,date(2021,10,7),date(2026,10,6))=='REVIEW_REQUIRED'
            with pytest.raises(ValueError,match='evidence'):
                review_history(c,mapping,DEMO_IDS['tenant'],DEMO_IDS['demo_user_account'],date(2021,10,7),date(2026,10,6),'APPROVED',' ')
            original=review_history(c,mapping,DEMO_IDS['tenant'],DEMO_IDS['demo_user_account'],date(2021,10,7),date(2026,10,6),'APPROVED','Synthetic reviewer evidence only')
            assert history_status(c,mapping,date(2021,10,7),date(2026,10,6))=='REVIEWED'
            with pytest.raises(ValueError,match='overlap'):
                review_history(c,mapping,DEMO_IDS['tenant'],DEMO_IDS['demo_user_account'],date(2025,1,1),date(2026,1,1),'REJECTED','Conflicting synthetic evidence')
            assert history_status(c,mapping,date(2020,1,1),date(2026,10,6))=='REVIEW_REQUIRED'
            review_history(c,mapping,DEMO_IDS['tenant'],DEMO_IDS['demo_user_account'],date(2021,10,7),date(2026,10,6),
                'REJECTED','Synthetic correction to previous review',supersedes=original)
            assert history_status(c,mapping,date(2021,10,7),date(2026,10,6))=='REJECTED'
            assert c.scalar(select(m.market_data_mapping_history_review.c.decision).where(
                m.market_data_mapping_history_review.c.review_id==original))=='APPROVED'
        finally:
            tx.rollback()


def test_attempt_cannot_attach_delivery_from_another_namespace():
    from market_data.jobs import start_job,start_attempt,finish_attempt
    from tests.test_market_data_ingestion import ingest
    with get_engine().connect() as c:
        tx=c.begin()
        try:
            dataset,namespace,_=setup_dataset(c)
            report=ingest(c,dataset,namespace)
            job=start_job(c,dataset,namespace,DEMO_IDS['tenant'],DEMO_IDS['demo_user_account'],['MSFT'],date(2026,10,5),date(2026,10,6))
            attempt=start_attempt(c,job,'MSFT',date(2026,10,5),date(2026,10,6))
            with pytest.raises(ValueError,match='delivery'):
                finish_attempt(c,attempt,'COMPLETE',report,report['runId'])
        finally:
            tx.rollback()


def test_rejected_history_review_blocks_new_prices():
    from market_data.history import review_history
    from tests.test_market_data_ingestion import ingest
    with get_engine().connect() as c:
        tx=c.begin()
        try:
            dataset,namespace,_=setup_dataset(c)
            mapping=c.scalar(select(m.external_object_mapping.c.external_object_mapping_id).where(m.external_object_mapping.c.external_id_namespace_id==namespace))
            review_history(c,mapping,DEMO_IDS['tenant'],DEMO_IDS['demo_user_account'],date(2026,10,5),date(2026,10,6),'REJECTED','Synthetic identity conflict')
            report=ingest(c,dataset,namespace)
            assert report['accepted']==0 and report['historicalContinuity']=='REJECTED'
            assert 'Historical mapping' in report['rejections'][0]['reason']
        finally:
            tx.rollback()


def test_operational_column_descriptions_match_database_metadata():
    from sqlalchemy import inspect
    from apps.reference_api.db import get_engine
    from security_master_schema import models as m
    with get_engine().connect() as c:
        inspector=inspect(c)
        for table in (m.market_data_ingestion_job,m.market_data_ingestion_attempt,m.market_data_mapping_history_review):
            columns=inspector.get_columns(table.name,schema=table.schema)
            assert all(column['comment']==table.c[column['name']].comment for column in columns)

