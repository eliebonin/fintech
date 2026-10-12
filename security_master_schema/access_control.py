"""Fixed action catalogue and deny-by-default tenant permission resolution.

Groups express job responsibilities; module entitlements remain the upper bound.
No group name, legacy membership label or platform role implies tenant access.
"""
ACTION_MODULES = {
    'STRATEGY_READ': frozenset({'TRADING', 'FUND_MANAGEMENT'}),
    'STRATEGY_WRITE': frozenset({'TRADING', 'FUND_MANAGEMENT'}),
    'TRADE_READ': frozenset({'TRADING'}),
    'TRADE_WRITE': frozenset({'TRADING'}),
    'TRADE_CORRECT': frozenset({'TRADING'}),
    'REFERENCE_READ': frozenset({'SECURITY_MASTER'}),
    'REFERENCE_PROPOSE': frozenset({'SECURITY_MASTER'}),
    'REFERENCE_APPROVE': frozenset({'SECURITY_MASTER'}),
    'TRADE_CONFIGURE': frozenset({'TRADING'}),
    'MARKET_DATA_READ': frozenset({'MARKET_DATA'}),
    'MARKET_DATA_MANAGE': frozenset({'MARKET_DATA'}),
    'VALUATION_READ': frozenset({'VALUATION'}),
    'VALUATION_RUN': frozenset({'VALUATION'}),
    'VALUATION_REVIEW': frozenset({'VALUATION'}),
    'CALENDAR_READ': frozenset({'FUND_MANAGEMENT', 'VALUATION'}),
    'CALENDAR_MANAGE': frozenset({'FUND_MANAGEMENT', 'VALUATION'}),
    'ACCESS_MANAGE': frozenset(),
}


def effective_permissions(*, role, tenant_modules, grants):
    """Union allowed group grants, then intersect with subscribed capabilities."""
    candidates = ACTION_MODULES if role == 'TENANT_ADMIN' else grants
    return frozenset(action for action in candidates if action in ACTION_MODULES
                     and (bool(ACTION_MODULES[action] & set(tenant_modules))
                          or (action == 'ACCESS_MANAGE' and role == 'TENANT_ADMIN')))


def effective_modules(tenant_modules, permissions):
    return frozenset(module for module in tenant_modules
                     if any(module in ACTION_MODULES.get(action, ()) for action in permissions))
