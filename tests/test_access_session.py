"""Local testing context must remain attributable and fail closed."""
from datetime import datetime, timedelta, timezone, date
import os
import pytest
from sqlalchemy import create_engine, select, update
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS


@pytest.fixture
def connection():
    engine=create_engine(os.environ['DATABASE_URL'])
    with engine.connect() as c:
        tx=c.begin()
        yield c
        tx.rollback()
    engine.dispose()


def test_context_retains_real_operator_without_inheriting_platform_authority(connection):
    from security_master_schema import access_sessions as sessions
    token=sessions.start(connection,DEMO_IDS['platform_admin_user_account'],DEMO_IDS['tenant'],DEMO_IDS['demo_user_account'],environment='local')
    result=sessions.resolve(connection,token,environment='local')
    assert result['actorId']==str(DEMO_IDS['platform_admin_user_account'])
    assert result['userId']==str(DEMO_IDS['demo_user_account'])
    assert result['platformRole'] is None
    assert result['tenantId']==str(DEMO_IDS['tenant'])
    with pytest.raises(PermissionError):
        sessions.resolve(connection,token+'tampered',environment='local')


def test_expired_or_suspended_authority_invalidates_session(connection):
    from security_master_schema import access_sessions as sessions
    token=sessions.start(connection,DEMO_IDS['platform_admin_user_account'],None,None,environment='local')
    connection.execute(update(m.local_access_session).values(expires_at_utc=datetime.now(timezone.utc)-timedelta(seconds=1)))
    with pytest.raises(PermissionError):
        sessions.resolve(connection,token,environment='local')


def test_target_membership_and_production_mode_cannot_be_bypassed(connection):
    from security_master_schema import access_sessions as sessions
    with pytest.raises(PermissionError):
        sessions.start(connection,DEMO_IDS['demo_user_account'],None,None,environment='local')
    with pytest.raises(PermissionError):
        sessions.start(connection,DEMO_IDS['platform_admin_user_account'],DEMO_IDS['second_tenant'],DEMO_IDS['platform_admin_user_account'],environment='local')
    with pytest.raises(PermissionError):
        sessions.start(connection,DEMO_IDS['platform_admin_user_account'],None,None,environment='production')


def test_seed_is_idempotent_and_provides_three_distinct_tenant_admins(connection):
    from security_master_schema import access_seed
    access_seed.seed_access(connection)
    access_seed.seed_access(connection)
    tenants=list(connection.scalars(select(m.tenant.c.tenant_id)))
    assert len(tenants)==3
    admins=list(connection.scalars(select(m.tenant_user_account.c.user_account_id).where(
        m.tenant_user_account.c.membership_role=='TENANT_ADMIN',m.tenant_user_account.c.status=='ACTIVE')))
    assert len(set(admins))==3
    for tenant in tenants:
        assert len(connection.execute(select(m.tenant_user_account).where(m.tenant_user_account.c.tenant_id==tenant)).all())>=4
