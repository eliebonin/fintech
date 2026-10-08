"""Bounded queue reads and precise published instrument contracts."""
from uuid import uuid4
from tests.test_api_reference_authority import connection, request
from apps.reference_api.main import create_app
from apps.reference_api import repository as r
from apps.reference_api.contracts import StrategyCreateRequest
from security_master_schema.demo_data import DEMO_IDS as ids


def test_work_queue_page_bounds_and_total_are_explicit(connection):
    for i in range(3):
        response = request(connection, 'POST', '/v1/bond-proposals', {
            'canonicalName': f'Page {uuid4()}', 'effectiveFrom': '2026-09-01', 'couponType': 'ZERO'})
        assert response.status_code == 201, response.text
    page = request(connection, 'GET', '/v1/work-queue?limit=1&offset=1')
    assert page.status_code == 200, page.text
    body = page.json()
    assert len(body['items']) == 1
    assert body['meta']['limit'] == 1
    assert body['meta']['offset'] == 1
    assert body['meta']['total'] >= 3
    assert request(connection, 'GET', '/v1/work-queue?limit=101').status_code == 422


def test_strategy_detail_does_not_load_the_tenant_register(connection, monkeypatch):
    strategy = r.create_strategy(connection, ids['tenant'], ids['demo_user_account'],
        StrategyCreateRequest(strategyCode=f'TEST_{uuid4().hex[:8]}', displayName='Direct lookup', strategyType='FUND'))
    def reject_list(*args, **kwargs): raise AssertionError('Detail must not list all strategies')
    monkeypatch.setattr(r, 'list_strategies', reject_list)
    assert r.get_strategy(connection, ids['tenant'], strategy.strategy_id) == strategy


def test_instrument_detail_has_a_typed_openapi_contract():
    schema = create_app().openapi()
    response = schema['paths']['/v1/instruments/{instrument_id}']['get']['responses']['200']['content']['application/json']['schema']
    assert response == {'$ref': '#/components/schemas/InstrumentResponse'}


def test_custom_field_history_is_paged(connection):
    for _ in range(2):
        result=request(connection,'POST','/v1/trade-configuration/properties',{'code':f'PAGE_{uuid4().hex[:8].upper()}', 'label':'Page test','valueType':'TEXT'})
        assert result.status_code==201,result.text
    result=request(connection,'GET','/v1/trade-configuration/properties?limit=1&offset=1')
    assert result.status_code==200,result.text
    assert len(result.json()['data'])==1
    assert result.json()['pagination']['total']>=2


def test_duplicate_strategy_code_is_an_explicit_conflict(connection):
    payload={'strategyCode':f'UNIQUE_{uuid4().hex[:8]}','displayName':'Natural identity','strategyType':'FUND'}
    assert request(connection,'POST','/v1/strategies',payload).status_code==201
    duplicate=request(connection,'POST','/v1/strategies',payload)
    assert duplicate.status_code==409,duplicate.text
