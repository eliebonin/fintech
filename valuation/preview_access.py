"""Current release authority for a preview computed in an older snapshot."""
from uuid import UUID
from market_data.display_access import assert_dataset_display
from security_master_schema.governance_clock import governance_date
from security_master_schema.strategy_access import require_strategy_action
from security_master_schema.tenant_workspace import resolve_tenant_workspace, require_tenant_action


def selected_series(value):
    result = set()
    if isinstance(value, dict):
        if value.get('dataset_id') and value.get('market_data_series_id'):
            result.add((UUID(str(value['dataset_id'])), UUID(str(value['market_data_series_id']))))
        for child in value.values():
            result.update(selected_series(child))
    elif isinstance(value, (list, tuple)):
        for child in value:
            result.update(selected_series(child))
    return result


def assert_preview_release(c, tenant, actor, strategy, result):
    for action in ('STRATEGY_READ', 'TRADE_READ', 'VALUATION_READ', 'VALUATION_RUN'):
        require_strategy_action(c, tenant, actor, action, strategy)
    workspace = resolve_tenant_workspace(c, tenant, actor, governance_date())
    require_tenant_action(workspace, 'MARKET_DATA_READ')
    contexts = selected_series(result)
    assert_dataset_display(c, tenant, {dataset for dataset, _ in contexts}, series_contexts=contexts)
