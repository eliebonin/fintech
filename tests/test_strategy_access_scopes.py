"""Real scope decisions and administration, not client-only filtering."""
from datetime import date
from uuid import uuid4
import pytest
from sqlalchemy import select
from tests.test_access_management import connection
from security_master_schema import access_management as am,models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from security_master_schema.tenant_workspace import TenantActionForbidden


def test_broad_read_group_never_widens_restricted_booking(connection):
    from security_master_schema.strategy_access import strategy_predicate,require_strategy_action
    tenant,admin=ids['tenant'],ids['demo_user_account']
    user=am.add_user(connection,tenant,admin,name='Scoped trader')
    read=am.save_group(connection,tenant,admin,code='READ_'+uuid4().hex,name='All readers',actions=['TRADE_READ'],scope_mode='ALL')
    write=am.save_group(connection,tenant,admin,code='WRITE_'+uuid4().hex,name='One strategy',actions=['TRADE_WRITE'],scope_mode='SELECTED',strategy_ids=[ids['strategy']])
    am.set_user_groups(connection,tenant,admin,user,[read,write])
    require_strategy_action(connection,tenant,user,'TRADE_WRITE',ids['strategy'])
    with pytest.raises(TenantActionForbidden):
        require_strategy_action(connection,tenant,user,'TRADE_WRITE',ids['uk_fund_strategy'])
    require_strategy_action(connection,tenant,user,'TRADE_READ',ids['uk_fund_strategy'])
    allowed=list(connection.scalars(select(m.strategy.c.strategy_id).where(m.strategy.c.tenant_id==tenant,
        strategy_predicate(connection,tenant,user,'TRADE_WRITE',m.strategy.c.strategy_id))))
    assert allowed==[ids['strategy']]
    am.set_user_groups(connection,tenant,admin,user,[read])
    with pytest.raises(TenantActionForbidden): require_strategy_action(connection,tenant,user,'TRADE_WRITE',ids['strategy'])


def test_empty_selected_scope_and_foreign_assignment_fail_closed(connection):
    from security_master_schema.strategy_access import require_strategy_action
    tenant,admin=ids['tenant'],ids['demo_user_account']
    user=am.add_user(connection,tenant,admin,name='No scope')
    group=am.save_group(connection,tenant,admin,code='EMPTY_'+uuid4().hex,name='Empty selected',actions=['TRADE_READ'],scope_mode='SELECTED',strategy_ids=[])
    am.set_user_groups(connection,tenant,admin,user,[group])
    with pytest.raises(TenantActionForbidden): require_strategy_action(connection,tenant,user,'TRADE_READ',ids['strategy'])
    with pytest.raises(TenantActionForbidden): am.save_group(connection,ids['second_tenant'],admin,code='BAD',name='Bad',actions=['TRADE_READ'],scope_mode='SELECTED',strategy_ids=[ids['strategy']])
