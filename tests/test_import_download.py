"""Download presentation independent of operating database configuration."""
from types import SimpleNamespace
from uuid import uuid4

from apps.reference_api import import_routes


def test_trade_template_download_has_business_readable_filename(monkeypatch):
    tenant, strategy = uuid4(), uuid4()
    monkeypatch.setattr(import_routes, 'descriptor', lambda *args: dict(
        tenantId=str(tenant), strategyId=str(strategy),
        columns=[dict(key='sourceTradeId', label='Source trade ID', required=True)]))
    router = import_routes.import_router(lambda: None, lambda *args: 'test-actor')
    endpoint = next(route.endpoint for route in router.routes if route.path.endswith('/template'))
    response = endpoint(strategyId=strategy, context=SimpleNamespace(tenant_id=tenant), c=None)
    assert response.headers['content-disposition'] == 'attachment; filename="trade-upload-template.xlsx"'
    assert response.headers['cache-control'] == 'private, no-store'
    assert response.body.startswith(b'PK')
