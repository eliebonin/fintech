"""Focused red/green checks for configuration and safe denial evidence."""
import asyncio
import json
import logging
from pathlib import Path
import tomllib
from uuid import uuid4

from fastapi import FastAPI
from httpx import ASGITransport,AsyncClient
from apps.reference_api.problem_details import configure_problem_details,ApiProblem
from apps.reference_api.config import Settings

ROOT=Path(__file__).resolve().parents[1]


def test_secret_scanner_keeps_the_maintainers_default_rules():
    config=tomllib.loads((ROOT/'.gitleaks.toml').read_text())
    assert config.get('extend',{}).get('useDefault') is True
    assert not config.get('allowlist')


def test_api_configuration_never_invents_database_credentials(monkeypatch):
    monkeypatch.delenv('DATABASE_URL',raising=False)
    config=Settings.from_environment()
    assert not config.database_url


def test_database_credentials_are_not_in_settings_repr(monkeypatch):
    monkeypatch.setenv('DATABASE_URL','postgresql+psycopg://sample:synthetic-password@localhost/example')
    assert 'synthetic-password' not in repr(Settings.from_environment())


def test_denials_produce_correlated_safe_security_events(caplog):
    app=FastAPI();configure_problem_details(app)
    @app.get('/denied/{value}')
    def denied(value:str):raise ApiProblem(403,'access.forbidden','Denied','Not allowed')
    request_id=str(uuid4())
    async def run():
        async with AsyncClient(transport=ASGITransport(app=app),base_url='http://test') as client:
            return await client.get('/denied/private-value',headers={'X-Request-ID':request_id,
                'Authorization':'Bearer synthetic-private-token','X-Local-Operator-Key':'synthetic-private-bootstrap'},
                params={'password':'synthetic-query-password'})
    with caplog.at_level(logging.WARNING,logger='apps.reference_api.security'):
        response=asyncio.run(run())
    assert response.status_code==403
    records=[r for r in caplog.records if r.name=='apps.reference_api.security']
    assert len(records)==1
    event=json.loads(records[0].getMessage())
    assert event['event']=='access_denied' and event['requestId']==request_id
    assert event['route']=='/denied/{value}' and event['status']==403
    assert event['actorId'] is None
    for secret in ['synthetic-private-token','synthetic-private-bootstrap','synthetic-query-password','private-value']:
        assert secret not in records[0].getMessage()
