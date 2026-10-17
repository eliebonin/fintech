"""Explanations must match enforcement, not invent additional permissions."""
from security_master_schema.access_explanations import explain_actions


def action(rows, code):
    return next(row for row in rows if row['code'] == code)


def test_group_union_and_disabled_subscription_are_explained():
    rows = explain_actions(role='MEMBER', tenant_modules=['TRADING'], groups=[
        dict(name='Readers', status='ACTIVE', actions=['TRADE_READ']),
        dict(name='Writers', status='ACTIVE', actions=['TRADE_WRITE','MARKET_DATA_READ']),
        dict(name='Old operations', status='SUSPENDED', actions=['TRADE_CORRECT']),
    ])
    assert action(rows,'TRADE_READ')['allowed'] is True
    assert action(rows,'TRADE_WRITE')['grantSources'] == ['Writers']
    assert action(rows,'MARKET_DATA_READ')['blockers'] == ['MODULE_NOT_ENABLED']
    assert action(rows,'TRADE_CORRECT')['blockers'] == ['NO_ACTIVE_ACTION_GRANT']
    assert action(rows,'ACCESS_MANAGE')['allowed'] is False


def test_admin_requires_subscription_but_can_manage_access_without_modules():
    rows = explain_actions(role='TENANT_ADMIN', tenant_modules=[], groups=[])
    assert action(rows,'ACCESS_MANAGE')['allowed'] is True
    assert action(rows,'TRADE_WRITE')['allowed'] is False
    assert action(rows,'TRADE_WRITE')['grantSources'] == []


def test_suspended_member_and_account_deny_even_with_grants():
    rows = explain_actions(role='TENANT_ADMIN', tenant_modules=['TRADING'],
                           groups=[dict(name='Traders',status='ACTIVE',actions=['TRADE_WRITE'])],
                           account_status='SUSPENDED', membership_status='SUSPENDED')
    assert not any(row['allowed'] for row in rows)
    assert action(rows,'TRADE_WRITE')['blockers'] == ['ACCOUNT_INACTIVE','MEMBERSHIP_INACTIVE']
