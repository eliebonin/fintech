from uuid import uuid4
from sqlalchemy import select
from tests.test_access_api import client,headers
from tests.test_strategy_scopes_api import scoped_user
from tests.test_bond_coupons import schedule_data
from security_master_schema.demo_data import DEMO_IDS as ids


def json_schedule():
    return schedule_data()|dict(instrumentId=str(ids['bond_instrument_node']))


def test_coupon_api_permissions_payment_report_and_retained_corrections(client):
    h= headers(); key=str(uuid4())
    reader,_=scoped_user(client,['LIFECYCLE_READ'],[ids['strategy']])
    opts=client.get('/v1/lifecycle/coupons/options',headers=reader)
    assert opts.status_code==200,opts.text
    scoped_options=client.get(f"/v1/lifecycle/coupons/options?strategyId={ids['strategy']}",headers=reader)
    assert scoped_options.status_code==200,scoped_options.text
    assert 'bonds' in scoped_options.json() and scoped_options.json()['permissions']['LIFECYCLE_BOOK'] is False
    first=client.post('/v1/lifecycle/coupons/schedules',headers=h|{'Idempotency-Key':key},json=json_schedule())
    assert first.status_code==201,first.text
    assert client.post('/v1/lifecycle/coupons/schedules',headers=h|{'Idempotency-Key':key},json=json_schedule()).json()['schedule_id']==first.json()['schedule_id']
    period=first.json()['periods'][0]['period_id']
    assert client.post('/v1/lifecycle/coupons/schedules',headers=reader|{'Idempotency-Key':str(uuid4())},json=json_schedule()).status_code==403
    target=f"strategyId={ids['strategy']}&instrumentId={ids['bond_instrument_node']}"
    assert client.get('/v1/lifecycle/coupons/schedule?'+target,headers=reader).status_code==200
    data=dict(strategyId=str(ids['strategy']),periodId=period,paymentDate='2026-10-01',amount='1000',currencyId=str(ids['gbp_currency']),
        sourceReference='Synthetic HTTP receipt '+uuid4().hex,confirmPayment=True)
    assert client.post('/v1/lifecycle/coupons/payments',headers=reader|{'Idempotency-Key':str(uuid4())},json=data).status_code==403
    writer,_=scoped_user(client,['LIFECYCLE_READ','LIFECYCLE_BOOK','TRADE_CORRECT'],[ids['strategy']])
    receipt_key=str(uuid4())
    receipt=client.post('/v1/lifecycle/coupons/payments',headers=writer|{'Idempotency-Key':receipt_key},json=data)
    assert receipt.status_code==201,receipt.text
    assert receipt.json()['effects']=={'additionalInterestPnl':'0','cashBalanceUpdated':False,'accrualInputsUpdated':False,'tradeCreated':False}
    item=receipt.json()['payment']
    corrected=data|dict(supersedesPaymentId=item['payment_id'],amount='900',paymentDate='2026-10-02',note='Corrected receipt date')
    result=client.post('/v1/lifecycle/coupons/payments/correct',headers=writer|{'Idempotency-Key':str(uuid4())},json=corrected)
    assert result.status_code==201,result.text
    base=f"/v1/lifecycle/coupons/payments?strategyId={ids['strategy']}&fromDate=2026-10-02&toDate=2026-10-02&limit=1&offset=0"
    report=client.get(base,headers=reader)
    assert report.status_code==200 and report.json()['total']>=1
    assert report.json()['items'][0]['amount']=='900'
    wrong=data|dict(strategyId=str(ids['uk_fund_strategy']))
    assert client.post('/v1/lifecycle/coupons/payments',headers=writer|{'Idempotency-Key':str(uuid4())},json=wrong).status_code==403
    assert client.get(base.replace(str(ids['strategy']),str(ids['uk_fund_strategy'])),headers=reader).status_code==403
    assert client.get('/v1/lifecycle/coupons/options',headers=reader).json()['strategies']==[{'id':str(ids['strategy']),'label':opts.json()['strategies'][0]['label']}]
    # Current authority is checked before replay; admin identity is not a bypass.
    user=writer['X-User-Account-Id']
    assert client.put(f'/v1/access/users/{user}/groups',headers=headers(),json={'groupIds':[]}).status_code==200
    assert client.post('/v1/lifecycle/coupons/payments',headers=writer|{'Idempotency-Key':receipt_key},json=data).status_code==403


def test_foreign_coupon_period_is_not_visible_through_known_uuid(client):
    from apps.reference_api.db import get_engine
    from lifecycle import coupon_tables as t
    h=headers()
    reader,_=scoped_user(client,['LIFECYCLE_READ'],[ids['strategy']])
    writer,_=scoped_user(client,['LIFECYCLE_BOOK'],[ids['strategy']])
    view=client.get(f"/v1/lifecycle/coupons/schedule?strategyId={ids['strategy']}&instrumentId={ids['bond_instrument_node']}",headers=reader)
    prior=(view.json().get('schedule') or {}).get('revision',0) if view.status_code==200 else 0
    response=client.post('/v1/lifecycle/coupons/schedules',headers=h|{'Idempotency-Key':str(uuid4())},json=json_schedule()|dict(expectedRevision=prior))
    assert response.status_code==201,response.text
    with get_engine().begin() as c:
        header=dict(c.execute(select(t.schedule).where(t.schedule.c.schedule_id==response.json()['schedule_id'])).mappings().one())
        period=dict(c.execute(select(t.period).where(t.period.c.schedule_id==header['schedule_id'])).mappings().first())
        foreign=uuid4();foreign_period=uuid4()
        c.execute(t.schedule.insert().values(**(header|dict(schedule_id=foreign,tenant_id=ids['second_tenant'],revision=1,supersedes_schedule_id=None,request_key=uuid4().hex))))
        c.execute(t.period.insert().values(**(period|dict(period_id=foreign_period,schedule_id=foreign))))
    path=f"/v1/lifecycle/coupons/schedule?strategyId={ids['strategy']}&instrumentId={ids['bond_instrument_node']}&scheduleId={foreign}"
    assert client.get(path,headers=reader).status_code==404
    data=dict(strategyId=str(ids['strategy']),periodId=str(foreign_period),paymentDate='2026-10-01',amount='1',
        currencyId=str(ids['gbp_currency']),sourceReference='Not owned',confirmPayment=True)
    assert client.post('/v1/lifecycle/coupons/payments',headers=writer|{'Idempotency-Key':str(uuid4())},json=data).status_code==404
