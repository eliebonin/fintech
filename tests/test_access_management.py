"""Real database tests for tenant administration, not UI-only hiding."""
from datetime import date
import os
from uuid import uuid4
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS
from security_master_schema.tenant_workspace import resolve_tenant_workspace, TenantActionForbidden


@pytest.fixture
def connection():
    engine = create_engine(os.environ['DATABASE_URL'])
    with engine.connect() as c:
        tx = c.begin()
        yield c
        tx.rollback()
    engine.dispose()


def test_group_assignment_cannot_reach_another_tenant(connection):
    from security_master_schema import access_management as am
    actor, tenant = DEMO_IDS['demo_user_account'], DEMO_IDS['tenant']
    group = am.save_group(connection, tenant, actor, code='TEST_'+uuid4().hex, name='Traders', actions=['TRADE_READ','TRADE_WRITE'])
    user = am.add_user(connection, tenant, actor, name='Test Trader', role='MEMBER')
    am.set_user_groups(connection, tenant, actor, user, [group])
    workspace = resolve_tenant_workspace(connection, tenant, user, date.today())
    assert 'TRADE_WRITE' in workspace.permission_codes
    with pytest.raises(TenantActionForbidden):
        am.set_user_groups(connection, DEMO_IDS['second_tenant'], actor, user, [group])


def test_member_cannot_manage_groups_or_platform_modules(connection):
    from security_master_schema import access_management as am
    user = am.add_user(connection, DEMO_IDS['tenant'], DEMO_IDS['demo_user_account'], name='Read only', role='MEMBER')
    with pytest.raises(TenantActionForbidden):
        am.save_group(connection, DEMO_IDS['tenant'], user, code='ESCAPE', name='Escape', actions=['TRADE_WRITE'])
    with pytest.raises(TenantActionForbidden):
        am.set_module(connection, DEMO_IDS['tenant'], user, 'TRADING', False)


def test_repeated_same_day_module_toggle_is_unambiguous_and_preserves_data(connection):
    from security_master_schema import access_management as am
    tenant, actor = DEMO_IDS['tenant'], DEMO_IDS['platform_admin_user_account']
    trade_count = len(connection.execute(select(m.trade.c.trade_id)).all())
    for enabled in (False, True, False, True):
        am.set_module(connection, tenant, actor, 'TRADING', enabled)
        workspace = resolve_tenant_workspace(connection, tenant, DEMO_IDS['demo_user_account'], date.today())
        assert ('TRADING' in workspace.module_codes) == enabled
    assert len(connection.execute(select(m.trade.c.trade_id)).all()) == trade_count
    assert len(connection.execute(select(m.access_audit_event).where(m.access_audit_event.c.action=='MODULE_CHANGED')).all()) == 4


def test_removed_group_and_suspended_membership_revoke_permissions(connection):
    from security_master_schema import access_management as am
    tenant, actor = DEMO_IDS['tenant'], DEMO_IDS['demo_user_account']
    group = am.save_group(connection, tenant, actor, code='TEST_'+uuid4().hex, name='Read', actions=['TRADE_READ'])
    user = am.add_user(connection, tenant, actor, name='Test User', role='MEMBER')
    am.set_user_groups(connection, tenant, actor, user, [group])
    assert resolve_tenant_workspace(connection, tenant, user, date.today()).module_codes == frozenset({'TRADING'})
    am.set_user_groups(connection, tenant, actor, user, [])
    assert resolve_tenant_workspace(connection, tenant, user, date.today()).permission_codes == frozenset()
    am.set_user_status(connection, tenant, actor, user, 'SUSPENDED')
    with pytest.raises(TenantActionForbidden):
        resolve_tenant_workspace(connection, tenant, user, date.today())


def test_last_admin_cannot_be_suspended(connection):
    from security_master_schema import access_management as am
    with pytest.raises(ValueError, match='last active'):
        am.set_user_status(connection, DEMO_IDS['tenant'], DEMO_IDS['demo_user_account'], DEMO_IDS['demo_user_account'], 'SUSPENDED')


def test_database_rejects_cross_tenant_group_grant(connection):
    group = connection.execute(m.access_group.insert().values(tenant_id=DEMO_IDS['tenant'], code=uuid4().hex, display_name='Scoped').returning(m.access_group.c.group_id)).scalar_one()
    with pytest.raises(IntegrityError):
        with connection.begin_nested():
            connection.execute(m.access_group_grant.insert().values(tenant_id=DEMO_IDS['second_tenant'],group_id=group, action_code='TRADE_READ'))


def test_switching_subject_does_not_allow_operator_to_review_own_valuation(connection):
    from apps.reference_api import access_boundary as boundary
    batch=uuid4()
    connection.execute(m.access_audit_event.insert().values(tenant_id=DEMO_IDS['tenant'],
        actor_id=DEMO_IDS['platform_admin_user_account'],subject_id=DEMO_IDS['demo_user_account'],action='TENANT_REQUEST',
        details={'path':'/v1/valuation/attempts','resourceIds':[str(batch)],'permission':'VALUATION_RUN'}))
    with pytest.raises(PermissionError):
        boundary.assert_independent_operator(connection,DEMO_IDS['tenant'],DEMO_IDS['platform_admin_user_account'],str(batch))


def test_reference_queue_excludes_ungranted_valuation_counts(connection):
    from apps.reference_api.repository import work_queue
    result = work_queue(connection, DEMO_IDS['tenant'], 'test', 'test', permission_codes={'REFERENCE_READ'})
    assert result.counts['NAV_REVIEW'] == 0
    assert all(item.category != 'NAV_REVIEW' for item in result.items)


def test_operations_cancellation_uses_correction_not_new_booking_permission(connection):
    from security_master_schema import access_management as am
    from tests.test_trade_corrections import original
    from apps.reference_api.trade_corrections import cancel_booking
    from apps.reference_api.contracts import CancelBookingRequest
    tenant, admin = DEMO_IDS['tenant'], DEMO_IDS['demo_user_account']
    user=am.add_user(connection,tenant,admin,name='Correction operator',role='MEMBER')
    group=am.save_group(connection,tenant,admin,code=uuid4().hex,name='Correct',actions=['TRADE_READ','TRADE_CORRECT'])
    am.set_user_groups(connection,tenant,admin,user,[group])
    first=original(connection)
    result=cancel_booking(connection,tenant,user,first.trade.trade_id,
        CancelBookingRequest(expectedSequenceNo=1,reason='Test correction'),str(uuid4()),'test')
    assert result.data.trade.lifecycle_status=='CANCELLED'


def test_booking_permission_alone_cannot_replace_existing_record(connection):
    from security_master_schema import access_management as am
    from apps.reference_api.trade_corrections import prepare_correction
    from apps.reference_api.contracts import TradeBookingRequest
    from tests.test_cash_booking_integrity import payload
    from tests.test_trade_corrections import original
    tenant,admin=DEMO_IDS['tenant'],DEMO_IDS['demo_user_account']
    user=am.add_user(connection,tenant,admin,name='New booking only',role='MEMBER')
    group=am.save_group(connection,tenant,admin,code=uuid4().hex,name='Book',actions=['TRADE_WRITE'])
    am.set_user_groups(connection,tenant,admin,user,[group])
    first=original(connection)
    request=TradeBookingRequest(**(payload().model_dump(by_alias=True)|dict(correction={
        'tradeId':str(first.trade.trade_id),'expectedSequenceNo':1,'reason':'Test'})))
    with pytest.raises(TenantActionForbidden):
        prepare_correction(connection,tenant,request,'CASH',actor=user)


def delegated_user(c, actions):
    from security_master_schema import access_management as am
    tenant,admin=DEMO_IDS['tenant'],DEMO_IDS['demo_user_account']
    user=am.add_user(c,tenant,admin,name='Delegated operator',role='MEMBER')
    group=am.save_group(c,tenant,admin,code=uuid4().hex,name='Delegated',actions=actions)
    am.set_user_groups(c,tenant,admin,user,[group])
    return user


def test_configuration_grant_does_not_need_new_booking_grant(connection):
    from apps.reference_api.trade_properties import provision_trade_catalogue
    user=delegated_user(connection,['TRADE_CONFIGURE'])
    provision_trade_catalogue(connection,DEMO_IDS['tenant'],user,[],[])


def test_calendar_grant_does_not_need_market_data_management_grant(connection):
    from apps.reference_api.calendar_service import authority
    user=delegated_user(connection,['CALENDAR_READ','CALENDAR_MANAGE'])
    assert authority(connection,DEMO_IDS['tenant'],user,True)


def test_valuation_input_grant_does_not_need_market_data_management_grant(connection):
    from apps.reference_api.valuation_input_routes import input_authority
    from apps.reference_api.tenant_context import TenantContext
    user=delegated_user(connection,['VALUATION_RUN','MARKET_DATA_READ'])
    context=TenantContext(DEMO_IDS['tenant'],user,'test')
    assert input_authority(connection,context,lambda c,ctx:user,True)==user


def test_overlapping_memberships_cannot_choose_an_arbitrary_role(connection):
    connection.execute(m.tenant_user_account.insert().values(tenant_id=DEMO_IDS['tenant'],
        user_account_id=DEMO_IDS['demo_user_account'],membership_role='MEMBER',status='ACTIVE',valid_from=date(2020,1,1)))
    with pytest.raises(TenantActionForbidden):
        resolve_tenant_workspace(connection,DEMO_IDS['tenant'],DEMO_IDS['demo_user_account'],date.today())
