from datetime import date
from uuid import UUID,uuid4
from sqlalchemy import select,func
import pytest
from tests.test_composite_policy_api import call
from tests.test_access_api import client
from apps.reference_api.db import get_engine
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids


def account():
    with get_engine().connect() as c:
        company=c.scalar(select(m.organisation.c.organisation_id).where(m.organisation.c.status=='ACTIVE').limit(1))
    response=call('POST','/v1/valuation/cash-accounts',dict(strategyId=str(ids['strategy']),companyId=str(company),label='Test '+uuid4().hex,accountType='CUSTODY'))
    assert response.status_code==201,response.text
    return response.json()['accountId']


def upload_payload(account_id):
    return dict(strategyId=str(ids['strategy']),rows=[dict(accountId=account_id,currencyId=str(ids['gbp_currency']),
        valueDate='2026-10-10',amount='100.123456789012',sourceReference='Synthetic statement',note='Restricted')])


def test_upload_retry_correction_and_no_carry_or_trade_creation():
    a=account();payload=upload_payload(a);key=str(uuid4())
    with get_engine().connect() as c: trade_count=c.scalar(select(func.count()).select_from(m.trade))
    first=call('POST','/v1/valuation/cash-balances',payload,key)
    assert first.status_code==201,first.text
    identity=first.json()['items'][0]['cash_balance_id']
    assert call('POST','/v1/valuation/cash-balances',payload,key).json()['items'][0]['cash_balance_id']==identity
    payload['rows'][0].update(amount='200',expectedRevision=1,correctionReason='Statement correction')
    assert call('POST','/v1/valuation/cash-balances',payload,key).status_code==409
    corrected=call('POST','/v1/valuation/cash-balances',payload)
    assert corrected.status_code==201,corrected.text
    assert corrected.json()['items'][0]['supersedes_balance_id']==identity
    day=call('GET',f"/v1/valuation/cash-balances?strategyId={ids['strategy']}&valueDate=2026-10-10")
    item=next(r for r in day.json()['items'] if r['cash_account_id']==a)
    assert item['amount']=='200' and item['note']=='Restricted' and item['revision']==2
    assert call('GET',f"/v1/valuation/cash-balances?strategyId={ids['strategy']}&valueDate=2026-10-11").json()['items']==[]
    with get_engine().begin() as c:
        assert c.scalar(select(func.count()).select_from(m.trade))==trade_count
        with pytest.raises(Exception,match='immutable'):
            with c.begin_nested(): c.execute(m.cash_balance.update().where(m.cash_balance.c.cash_balance_id==UUID(identity)).values(amount=0))


def test_wrong_strategy_account_and_atomic_upload_rejected():
    payload=upload_payload(str(uuid4()))
    assert call('POST','/v1/valuation/cash-balances',payload).status_code==404
    payload['strategyId']=str(uuid4())
    assert call('POST','/v1/valuation/cash-balances',payload).status_code==403


def test_failed_batch_writes_no_partial_rows():
    a=account();data=upload_payload(a);key=str(uuid4())
    data['rows'].append(data['rows'][0]|dict(accountId=str(uuid4())))
    assert call('POST','/v1/valuation/cash-balances',data,key).status_code==404
    with get_engine().connect() as c:
        assert not c.scalar(select(m.cash_balance.c.cash_balance_id).where(m.cash_balance.c.cash_account_id==UUID(a)))


def test_cash_access_is_action_and_strategy_scoped(client):
    from tests.test_strategy_scopes_api import scoped_user
    from tests.test_access_api import headers
    a=account();data=upload_payload(a)
    h,_=scoped_user(client,['VALUATION_READ','MARKET_DATA_READ'],[ids['strategy']])
    assert client.get(f"/v1/valuation/cash-accounts?strategyId={ids['strategy']}",headers=h).status_code==200
    assert client.post('/v1/valuation/cash-balances',headers=h|{'Idempotency-Key':str(uuid4())},json=data).status_code==403
    h,_=scoped_user(client,['VALUATION_READ','VALUATION_RUN','MARKET_DATA_READ'],[ids['uk_fund_strategy']])
    assert client.get(f"/v1/valuation/cash-balances?strategyId={ids['strategy']}&valueDate=2026-10-10",headers=h).status_code==403
    assert client.post('/v1/valuation/cash-balances',headers=h|{'Idempotency-Key':str(uuid4())},json=data).status_code==403


def test_read_scoped_accounts_and_preview_requirements():
    a=account();payload=upload_payload(a)
    assert call('POST','/v1/valuation/cash-balances',payload).status_code==201
    result=call('POST','/v1/valuation/cash-balance-preview',dict(strategyId=str(ids['strategy']),valueDate='2026-10-10',
        policyId=str(ids['valuation_policy']),cutId=str(ids['valuation_cut']),reportingCurrencyId=str(ids['gbp_currency'])))
    assert result.status_code==200,result.text
    assert result.json()['scope']=='DATED_CASH_VALUE_ONLY'
    assert 'NOT_CASH_PNL' in result.json()['limitations']
    assert next(i for i in result.json()['items'] if i['snapshot']['cash_account_id']==a)['fxRate']=='1'
    assert call('GET',f"/v1/valuation/cash-accounts?strategyId={uuid4()}").status_code==403
