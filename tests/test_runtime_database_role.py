"""A real runtime role can do normal business DML but cannot own/erase schema."""
import os
from uuid import uuid4
import pytest
from sqlalchemy import create_engine,text
from sqlalchemy.exc import DBAPIError
from security_master_schema.database_security import assert_runtime_role,grant_runtime_access


def test_non_owner_role_has_dml_but_no_administrative_or_audit_mutation_rights():
    engine=create_engine(os.environ['DATABASE_URL'])
    role='synthetic_runtime_'+uuid4().hex
    with engine.connect() as c:
        tx=c.begin()
        try:
            with pytest.raises(RuntimeError,match='non-owner'):assert_runtime_role(c)
            c.exec_driver_sql(f'CREATE ROLE {role} NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS')
            grant_runtime_access(c,role)
            c.exec_driver_sql(f'SET LOCAL ROLE {role}')
            assert_runtime_role(c)
            from tests.api_client import FixtureTestClient,ConnectionEngine
            from apps.reference_api.main import create_app
            from tests.test_trade_booking_api import _payload,_headers
            from security_master_schema import models as m
            from sqlalchemy import select
            with FixtureTestClient(create_app(engine=ConnectionEngine(c))) as client:
                booked=client.post('/v1/trades',json=_payload(),headers=_headers('runtime-'+uuid4().hex))
                assert booked.status_code==201,booked.text
                trade=booked.json()['data']['trade']['tradeId']
                detail=client.get('/v1/trades/'+trade,headers=_headers('runtime-read'))
                assert detail.status_code==200,detail.text
            assert c.scalar(select(m.access_audit_event.c.event_id).where(
                m.access_audit_event.c.action=='TENANT_REQUEST',
                m.access_audit_event.c.details['resourceIds'].contains([trade])))
            # A normal business table remains writable; privileges do not impose
            # instrument, provider, tenant or financial population restrictions.
            assert c.scalar(text("SELECT has_table_privilege(current_user,'trd.trade','SELECT,INSERT,UPDATE,DELETE')"))
            assert c.scalar(text("SELECT has_table_privilege(current_user,'ten.access_audit_event','SELECT,INSERT')"))
            for sql in ['CREATE TABLE public.synthetic_forbidden(id integer)',
                'UPDATE ten.access_audit_event SET action=action WHERE false',
                'DELETE FROM ten.access_audit_event WHERE false','TRUNCATE ten.access_audit_event',
                'ALTER TABLE ten.access_audit_event DISABLE TRIGGER ALL',
                'UPDATE public.alembic_version SET version_num=version_num WHERE false']:
                with pytest.raises(DBAPIError) as error:
                    with c.begin_nested():c.exec_driver_sql(sql)
                assert error.value.orig.sqlstate=='42501'
        finally:tx.rollback()
    engine.dispose()
