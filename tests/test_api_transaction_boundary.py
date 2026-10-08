"""HTTP success must mean the request transaction has finalized successfully."""
import asyncio
from contextlib import contextmanager
from uuid import UUID

from httpx import ASGITransport, AsyncClient

import apps.reference_api.main as api
from apps.reference_api.contracts import StrategyView

IDENTIFIER = UUID('00000000-0000-4000-8000-000000000001')


class TransactionEngine:
    """Fault injection at the outer commit, not at a domain savepoint."""
    def __init__(self, fail_commit=False):
        self.fail_commit = fail_commit
        self.outcome = None

    @contextmanager
    def begin(self):
        try:
            yield self
            if self.fail_commit:
                raise RuntimeError('synthetic-commit-failure')
            self.outcome = 'COMMITTED'
        except Exception:
            self.outcome = 'ROLLED_BACK'
            raise

    @contextmanager
    def begin_nested(self):
        yield self

    def execute(self,statement):
        # Budget setup is separately verified; this fake isolates commit order.
        return None


def strategy_app(monkeypatch, engine):
    # Domain/database behavior is covered by PostgreSQL tests. This test
    # injects the otherwise hard-to-schedule outer commit failure only.
    monkeypatch.setattr(api, '_assert_tenant_membership', lambda *_: IDENTIFIER)
    monkeypatch.setattr(api, 'resolve_tenant_workspace', lambda *_: None)
    monkeypatch.setattr(api, 'require_tenant_action', lambda *_: None)
    monkeypatch.setattr(api, 'create_strategy', lambda *_: StrategyView(
        strategyId=IDENTIFIER, tenantId=IDENTIFIER, strategyCode='BOUNDARY',
        displayName='Boundary', strategyType='FUND', baseCurrencyCode='GBP', status='ACTIVE'))
    return api.create_app(engine=engine)


async def create(app, engine):
    sent_outcomes = []

    async def observed_app(scope, receive, send):
        async def observed_send(message):
            if message['type'] == 'http.response.start':
                sent_outcomes.append(engine.outcome)
            await send(message)
        await app(scope, receive, observed_send)

    async with AsyncClient(transport=ASGITransport(app=observed_app, raise_app_exceptions=False), base_url='http://test') as client:
        response = await client.post('/v1/strategies',
            headers={'X-Tenant-Id': str(IDENTIFIER), 'X-User-Account-Id': str(IDENTIFIER)},
            json={'strategyCode': 'BOUNDARY', 'displayName': 'Boundary', 'strategyType': 'FUND'})
    return response, sent_outcomes


def test_commit_failure_does_not_advertise_created_resource(monkeypatch):
    engine = TransactionEngine(fail_commit=True)
    response, _ = asyncio.run(create(strategy_app(monkeypatch, engine), engine))
    assert response.status_code == 500
    assert response.json()['code'] == 'internal.error'
    assert engine.outcome == 'ROLLED_BACK'
    assert 'synthetic-commit-failure' not in response.text


def test_commit_finishes_before_success_headers_are_sent(monkeypatch):
    engine = TransactionEngine()
    response, outcomes = asyncio.run(create(strategy_app(monkeypatch, engine), engine))
    assert response.status_code == 201
    assert outcomes == ['COMMITTED']


def test_service_validation_refusal_rolls_back_instead_of_committing(monkeypatch):
    engine = TransactionEngine()
    app = strategy_app(monkeypatch, engine)
    monkeypatch.setattr(api, 'create_strategy', lambda *_: {'invalid': True})
    response, outcomes = asyncio.run(create(app, engine))
    assert response.status_code == 422
    assert engine.outcome == 'ROLLED_BACK'
    assert outcomes == ['ROLLED_BACK']
