"""Append-only access history is enforced below application code."""
import os
from uuid import uuid4
import pytest
from sqlalchemy import create_engine,select,text
from sqlalchemy.exc import DBAPIError
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids


def test_access_audit_allows_append_and_refuses_update_delete_truncate():
    engine=create_engine(os.environ['DATABASE_URL'])
    try:
        with engine.connect() as c:
            tx=c.begin()
            event=uuid4()
            c.execute(m.access_audit_event.insert().values(event_id=event,actor_id=ids['platform_admin_user_account'],
                tenant_id=ids['tenant'],subject_id=ids['demo_user_account'],action='SYNTHETIC_APPEND',details={'test':True}))
            for statement in [m.access_audit_event.update().where(m.access_audit_event.c.event_id==event).values(action='CHANGED'),
                m.access_audit_event.delete().where(m.access_audit_event.c.event_id==event),text('TRUNCATE ten.access_audit_event')]:
                with pytest.raises(DBAPIError) as error:
                    with c.begin_nested():c.execute(statement)
                assert error.value.orig.sqlstate=='23514'
                assert c.scalar(select(m.access_audit_event.c.action).where(m.access_audit_event.c.event_id==event))=='SYNTHETIC_APPEND'
            tx.rollback()
    finally:engine.dispose()
