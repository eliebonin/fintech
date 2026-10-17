from uuid import uuid4
import pytest
from security_master_schema.access_control import effective_permissions
from tests.test_access_management import connection


@pytest.mark.parametrize('action',['LIFECYCLE_READ','LIFECYCLE_PREPARE','LIFECYCLE_BOOK','LIFECYCLE_APPROVE','LIFECYCLE_CONFIGURE'])
def test_explicit_lifecycle_grants_are_bounded_by_trading_subscription(action):
    assert effective_permissions(role='MEMBER',tenant_modules={'TRADING'},grants={action})==frozenset({action})
    assert effective_permissions(role='MEMBER',tenant_modules={'VALUATION'},grants={action})==frozenset()
    assert effective_permissions(role='TENANT_ADMIN',tenant_modules={'TRADING'},grants=set())==frozenset({'ACCESS_MANAGE'})


def test_direct_booking_cannot_bypass_required_approval_and_reuses_trade_write():
    from security_master_schema.lifecycle_authority import required_permissions
    assert required_permissions('BOOK','DIRECT')==('LIFECYCLE_BOOK','TRADE_WRITE')
    assert required_permissions('BOOK','MANUAL')==('LIFECYCLE_BOOK','TRADE_WRITE')
    assert required_permissions('APPROVE','REVIEW')==('LIFECYCLE_APPROVE','TRADE_WRITE')
    assert required_permissions('CORRECT','DIRECT')==('TRADE_CORRECT',)
    with pytest.raises(ValueError): required_permissions('BOOK','REVIEW')
    with pytest.raises(ValueError): required_permissions('APPROVE','DIRECT')
    with pytest.raises(ValueError): required_permissions('BOOK','AUTOMATIC')


def test_review_checks_both_selected_user_and_real_operator():
    from security_master_schema.lifecycle_authority import assert_independent_review
    maker,reviewer,operator=uuid4(),uuid4(),uuid4()
    assert_independent_review(reviewer,reviewer,maker,operator)
    for actors in [(maker,reviewer,maker,operator),(reviewer,operator,maker,operator),
                   (operator,reviewer,maker,operator),(reviewer,maker,maker,operator)]:
        with pytest.raises(PermissionError): assert_independent_review(*actors)
    with pytest.raises(PermissionError): assert_independent_review(reviewer,reviewer,maker,None)
    with pytest.raises(PermissionError): assert_independent_review(reviewer,str(maker),maker,operator)
    with pytest.raises(PermissionError): assert_independent_review(reviewer,reviewer,'invalid',operator)


def test_lifecycle_read_does_not_widen_configuration_scope(connection):
    from security_master_schema import access_management as am
    from security_master_schema.demo_data import DEMO_IDS as ids
    from security_master_schema.lifecycle_authority import require_lifecycle_operation
    tenant,admin=ids['tenant'],ids['demo_user_account']
    user=am.add_user(connection,tenant,admin,name='Lifecycle controller')
    read=am.save_group(connection,tenant,admin,code='READ_'+uuid4().hex,name='All lifecycle readers',
        actions=['LIFECYCLE_READ'],scope_mode='ALL')
    configure=am.save_group(connection,tenant,admin,code='CONFIG_'+uuid4().hex,name='One strategy configuration',
        actions=['LIFECYCLE_CONFIGURE'],scope_mode='SELECTED',strategy_ids=[ids['strategy']])
    am.set_user_groups(connection,tenant,admin,user,[read,configure])
    require_lifecycle_operation(connection,tenant,user,ids['uk_fund_strategy'],'READ','DIRECT')
    with pytest.raises(PermissionError): require_lifecycle_operation(connection,tenant,user,ids['uk_fund_strategy'],'CONFIGURE','DIRECT')
    require_lifecycle_operation(connection,tenant,user,ids['strategy'],'CONFIGURE','DIRECT')
    with pytest.raises(PermissionError): require_lifecycle_operation(connection,tenant,user,ids['strategy'],'PREPARE','REVIEW')


def test_grant_in_other_strategy_does_not_authorise_booking(connection):
    from security_master_schema import access_management as am
    from security_master_schema.demo_data import DEMO_IDS as ids
    from security_master_schema.lifecycle_authority import require_lifecycle_operation
    tenant,admin=ids['tenant'],ids['demo_user_account']
    user=am.add_user(connection,tenant,admin,name='Lifecycle scoped Ops')
    lifecycle=am.save_group(connection,tenant,admin,code='LIFE_'+uuid4().hex,name='Lifecycle desk',
        actions=['LIFECYCLE_BOOK'],scope_mode='SELECTED',strategy_ids=[ids['strategy']])
    trade=am.save_group(connection,tenant,admin,code='TRADE_'+uuid4().hex,name='Other trade desk',
        actions=['TRADE_WRITE'],scope_mode='SELECTED',strategy_ids=[ids['uk_fund_strategy']])
    am.set_user_groups(connection,tenant,admin,user,[lifecycle,trade])
    with pytest.raises(PermissionError): require_lifecycle_operation(connection,tenant,user,ids['strategy'],'BOOK','DIRECT')
    with pytest.raises(PermissionError): require_lifecycle_operation(connection,tenant,user,ids['uk_fund_strategy'],'BOOK','DIRECT')
    am.set_user_groups(connection,tenant,admin,user,[lifecycle])
    trade=am.save_group(connection,tenant,admin,code='MATCH_'+uuid4().hex,name='Matching trade desk',
        actions=['TRADE_WRITE'],scope_mode='SELECTED',strategy_ids=[ids['strategy']])
    am.set_user_groups(connection,tenant,admin,user,[lifecycle,trade])
    proof=require_lifecycle_operation(connection,tenant,user,ids['strategy'],'BOOK','DIRECT')
    assert proof['actorId']==str(user) and proof['strategyId']==str(ids['strategy'])
    assert proof['permissions']==['LIFECYCLE_BOOK','TRADE_WRITE']
    with pytest.raises(PermissionError): require_lifecycle_operation(connection,ids['second_tenant'],user,ids['strategy'],'BOOK','DIRECT')
