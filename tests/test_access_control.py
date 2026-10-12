"""Action grants cannot escape a tenant's subscription boundary."""
from datetime import date
from uuid import uuid4

import pytest

from security_master_schema import tenant_workspace as tw


def test_group_union_is_intersected_with_enabled_modules():
    from security_master_schema import access_control as ac
    result = ac.effective_permissions(
        role='MEMBER', tenant_modules={'TRADING'},
        grants={'TRADE_READ', 'TRADE_WRITE', 'REFERENCE_APPROVE', 'PLATFORM_ADMIN'},
    )
    assert result == frozenset({'TRADE_READ', 'TRADE_WRITE'})


def test_admin_cannot_gain_disabled_module_or_platform_authority():
    from security_master_schema import access_control as ac
    result = ac.effective_permissions(role='TENANT_ADMIN', tenant_modules={'TRADING'}, grants=set())
    assert 'TRADE_WRITE' in result
    assert 'ACCESS_MANAGE' in result
    assert 'REFERENCE_APPROVE' not in result
    assert 'PLATFORM_ADMIN' not in result


def test_member_without_groups_has_no_implicit_role_grants():
    from security_master_schema import access_control as ac
    assert ac.effective_permissions(role='OPERATIONS', tenant_modules={'TRADING'}, grants=set()) == frozenset()


def test_trader_permission_allows_booking_without_admin_role():
    workspace = tw.TenantWorkspaceView(uuid4(), 'TEST', 'Test tenant', 'MEMBER', frozenset({'TRADING'}), None,
                                       permission_codes=frozenset({'TRADE_WRITE'}))
    tw.require_tenant_action(workspace, 'TRADE_WRITE')


def test_unknown_action_denied_even_for_admin():
    workspace = tw.TenantWorkspaceView(uuid4(), 'TEST', 'Test tenant', 'TENANT_ADMIN', frozenset({'TRADING'}), None)
    with pytest.raises(tw.TenantActionForbidden):
        tw.require_tenant_action(workspace, 'PLATFORM_ADMIN')
