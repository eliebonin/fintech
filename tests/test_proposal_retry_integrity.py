"""A source retry must preserve the original proposal's economic intent."""
from uuid import uuid4
import pytest
from tests.test_api_reference_authority import connection, request
from security_master_schema.demo_data import DEMO_IDS as ids


@pytest.mark.parametrize('kind', ['bond', 'equity'])
def test_proposal_retry_replays_identical_payload_but_rejects_changed_payload(connection, kind):
    payload = {'canonicalName': f'Retry {uuid4()}', 'effectiveFrom': '2026-09-01',
        'sourceSystemId': str(ids['source_system']), 'idempotencyKey': str(uuid4()),
        'baseCurrencyId': str(ids['usd_currency'])}
    if kind == 'bond': payload['couponType'] = 'ZERO'
    first = request(connection, 'POST', f'/v1/{kind}-proposals', payload)
    assert first.status_code == 201, first.text
    retry = request(connection, 'POST', f'/v1/{kind}-proposals', payload)
    assert retry.status_code == 201, retry.text
    assert retry.json()['data']['proposalId'] == first.json()['data']['proposalId']
    changed = request(connection, 'POST', f'/v1/{kind}-proposals', {**payload, 'canonicalName': 'Different intent'})
    assert changed.status_code == 409, changed.text


def test_trade_configuration_rejects_inactive_actor(connection):
    from sqlalchemy import update
    from security_master_schema import models as m
    from security_master_schema.tenant_workspace import TenantActionForbidden
    from apps.reference_api.trade_properties import assert_trade_writer
    connection.execute(update(m.user_account).where(m.user_account.c.user_account_id == ids['demo_user_account']).values(status='INACTIVE'))
    with pytest.raises(TenantActionForbidden):
        assert_trade_writer(connection, ids['tenant'], ids['demo_user_account'])


def test_manual_option_proposal_accepts_a_tenant_retry_key(connection):
    payload=dict(canonicalName=f'Retry option {uuid4()}',idempotencyKey=str(uuid4()),
        effectiveFrom='2026-09-01',underlyingId=str(ids['hsbc_instrument_node']),optionType='CALL',
        strike='10',strikeCurrencyId=str(ids['gbp_currency']),premiumCurrencyId=str(ids['gbp_currency']),
        premiumMultiplier='100',deliverableUnits='100',expiryDate='2027-09-17',
        lastTradingAtUtc='2027-09-17T16:30:00Z',exerciseStyle='AMERICAN',settlementMethod='PHYSICAL')
    first=request(connection,'POST','/v1/option-proposals',payload)
    assert first.status_code==201,first.text
    retry=request(connection,'POST','/v1/option-proposals',payload)
    assert retry.status_code==201,retry.text
    assert retry.json()['data']['proposalId']==first.json()['data']['proposalId']
    changed=request(connection,'POST','/v1/option-proposals',payload|{'strike':'11'})
    assert changed.status_code==409,changed.text


def test_source_key_cannot_be_reused_for_another_instrument_type(connection):
    payload={'canonicalName':f'Type retry {uuid4()}','effectiveFrom':'2026-09-01',
        'baseCurrencyId':str(ids['gbp_currency']),'sourceSystemId':str(ids['source_system']),'idempotencyKey':str(uuid4())}
    assert request(connection,'POST','/v1/bond-proposals',payload|{'couponType':'ZERO'}).status_code==201
    assert request(connection,'POST','/v1/equity-proposals',payload).status_code==409


def test_concurrent_identical_source_retries_create_one_proposal():
    from concurrent.futures import ThreadPoolExecutor
    from tests.test_bond_onboarding import _post
    payload={'canonicalName':f'Concurrent retry {uuid4()}','effectiveFrom':'2026-09-01','couponType':'ZERO',
        'sourceSystemId':str(ids['source_system']),'idempotencyKey':str(uuid4())}
    with ThreadPoolExecutor(max_workers=3) as pool:
        results=list(pool.map(lambda _: _post('/v1/bond-proposals',payload),range(3)))
    assert [response.status_code for response in results]==[201,201,201]
    assert len({response.json()['data']['proposalId'] for response in results})==1
