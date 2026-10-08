import asyncio
from dataclasses import replace
from httpx import ASGITransport,AsyncClient
from apps.reference_api.config import Settings
from apps.reference_api.main import create_app


def test_router_metadata_uses_the_configured_api_version():
    from apps.reference_api.problem_details import current_api_version
    app=create_app(settings=replace(Settings.from_environment(),api_version='test-version'))
    @app.get('/metadata-test')
    def endpoint(): return {'version':current_api_version()}
    async def run():
        async with AsyncClient(transport=ASGITransport(app=app),base_url='http://test') as client:
            return await client.get('/metadata-test')
    assert asyncio.run(run()).json()['version']=='test-version'
