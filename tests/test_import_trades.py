"""Imports use the actual API/writer in an owned disposable database."""
import asyncio
import base64
import os
from io import BytesIO
from openpyxl import load_workbook
import pytest
from sqlalchemy import create_engine,select,func
from uuid import uuid4,UUID
from httpx import ASGITransport, AsyncClient
from apps.reference_api.main import create_app
from security_master_schema.demo_data import DEMO_IDS
from security_master_schema import models as m
from data_imports import tables as t
from apps.reference_api import import_service as service
from apps.reference_api.import_routes import ImportCreate


@pytest.fixture
def connection():
    engine=create_engine(os.environ['DATABASE_URL'])
    with engine.connect() as c:
        transaction=c.begin()
        try:yield c
        finally:transaction.rollback()
    engine.dispose()


def headers():
    return {'X-Tenant-Id':str(DEMO_IDS['tenant']), 'X-User-Account-Id':str(DEMO_IDS['demo_user_account']),
            'Idempotency-Key':str(uuid4())}


def file_body(source, count=2, invalid=False):
    listing=str(DEMO_IDS['hsbc_xlon_listing_node'])
    lines=['sourceTradeId,listingId,side,quantity,executionPrice,tradeDatetime,settlementDate']
    for n in range(count):
        lines.append(f'{n},{listing},BUY,{"bad" if invalid and n==count-1 else "10"},10.23,2026-09-30T14:32:00Z,2026-10-02')
    return dict(strategyId=str(DEMO_IDS['strategy']),source=source,filename='trades.csv',
                contentBase64=base64.b64encode(('\n'.join(lines)).encode()).decode())


def test_invalid_row_blocks_whole_batch_and_valid_staging_survives():
    async def run():
        async with AsyncClient(transport=ASGITransport(app=create_app()),base_url='http://test') as client:
            h=headers();created=await client.post('/v1/trades/imports',json=file_body(str(uuid4()),10,True),headers=h)
            assert created.status_code==201,created.text
            job=created.json()['jobId'];result=await client.post(f'/v1/trades/imports/{job}/validate',json={},headers=headers())
            assert result.status_code==200,result.text
            report=result.json()
            assert (report['valid'],report['invalid'],report['applied'],report['status'])==(9,1,0,'NEEDS_CORRECTION')
            assert len(report['rows'])==10
            booked=await client.post(f'/v1/trades/imports/{job}/confirm',json={'reviewHash':report['reviewHash']},headers=headers())
            assert booked.status_code==409,booked.text
    asyncio.run(run())


def test_mid_batch_failure_rolls_back_every_trade_identity_and_receipt(connection,monkeypatch):
    c=connection;tenant=DEMO_IDS['tenant'];actor=DEMO_IDS['demo_user_account']
    job=service.submit(c,tenant,actor,ImportCreate.model_validate(file_body(str(uuid4()))),str(uuid4()))
    review=service.validate(c,tenant,actor,UUID(job['jobId']))
    before=c.scalar(select(func.count()).select_from(m.trade));writer=service.book_listed_cash_trade;calls=0
    def fail_second(*args,**kwargs):
        nonlocal calls
        calls+=1
        if calls==2:raise RuntimeError('injected second-row failure')
        return writer(*args,**kwargs)
    monkeypatch.setattr(service,'book_listed_cash_trade',fail_second)
    with pytest.raises(RuntimeError,match='second-row'):
        with c.begin_nested():service.confirm(c,tenant,actor,UUID(job['jobId']),review['reviewHash'],'failure-test')
    assert c.scalar(select(func.count()).select_from(m.trade))==before
    assert c.scalar(select(func.count()).select_from(t.row).where(t.row.c.job_id==UUID(job['jobId'])))==0
    assert service.load(c,tenant,actor,UUID(job['jobId']))['status']=='READY'


def test_missing_listing_is_a_row_error_not_a_failed_validation_request(connection):
    c=connection;tenant=DEMO_IDS['tenant'];actor=DEMO_IDS['demo_user_account']
    body=file_body(str(uuid4()),1);decoded=base64.b64decode(body['contentBase64']).decode()
    body['contentBase64']=base64.b64encode(decoded.replace(str(DEMO_IDS['hsbc_xlon_listing_node']),str(uuid4())).encode()).decode()
    job=service.submit(c,tenant,actor,ImportCreate.model_validate(body),str(uuid4()))
    report=service.validate(c,tenant,actor,UUID(job['jobId']))
    assert report['status']=='NEEDS_CORRECTION' and report['invalid']==1


def test_decimal_precision_supported_by_database_is_not_rejected_by_python_context(connection):
    from apps.reference_api.import_adapters.trades import prepare
    values=dict(sourceTradeId='max',listingId=str(DEMO_IDS['hsbc_xlon_listing_node']),side='BUY',quantity='123456789012345678.123456789012',
        executionPrice='1',tradeDatetime='2026-09-30T14:32:00Z',settlementDate='2026-10-02')
    request,_=prepare(connection,DEMO_IDS['tenant'],DEMO_IDS['demo_user_account'],DEMO_IDS['strategy'],values)
    assert str(request.quantity)=='123456789012345678.123456789012'


def test_required_custom_fields_and_governed_choice_roundtrip(connection):
    from apps.reference_api.governed_trade_configuration import create_catalogue,create_record,catalogue_lifecycle
    from apps.reference_api.trade_properties import provision_trade_catalogue
    from apps.reference_api.import_adapters.trades import descriptor
    from data_imports.formats import render_template
    c=connection;tenant=DEMO_IDS['tenant'];actor=DEMO_IDS['demo_user_account'];strategy=DEMO_IDS['strategy']
    code='IMPORT_'+uuid4().hex.upper()
    catalogue=create_catalogue(c,tenant,actor,dict(code=code,label='Coverage team',reason='Synthetic import acceptance'))
    record=create_record(c,tenant,actor,catalogue['catalogueId'],dict(code='OPS',label='Operations',reason='Synthetic import acceptance'))
    catalogue_lifecycle(c,tenant,actor,catalogue['catalogueId'],'ACTIVE','Synthetic import acceptance')
    provision_trade_catalogue(c,tenant,actor,[dict(code=code,label='Coverage team',valueType='REFERENCE',required=True,catalogueId=catalogue['catalogueId'])],[])
    definition=c.scalar(select(m.trade_property_definition.c.definition_id).where(m.trade_property_definition.c.code==code))
    spec=descriptor(c,tenant,actor,strategy);key='property:'+str(definition)
    assert next(col for col in spec['columns'] if col['key']==key)['choices']==[f"{record['recordVersionId']} — OPS: Operations"]
    book=load_workbook(BytesIO(render_template(spec)));sheet=book['Trades']
    values=dict(sourceTradeId='one',listingId=str(DEMO_IDS['hsbc_xlon_listing_node']),side='BUY',quantity='10',executionPrice='10.23',
        tradeDatetime='2026-09-30T14:32:00Z',settlementDate='2026-10-02')
    sheet.append([values.get(cell.value,'') for cell in sheet[1]])
    out=BytesIO();book.save(out)
    body=file_body(str(uuid4()),1)|dict(filename='trades.xlsx',contentBase64=base64.b64encode(out.getvalue()).decode())
    job=service.submit(c,tenant,actor,ImportCreate.model_validate(body),str(uuid4()))
    report=service.validate(c,tenant,actor,UUID(job['jobId']))
    assert report['invalid']==1 and 'required' in report['rows'][0]['errors'][0]['message']
    values[key]=f"{record['recordVersionId']} — OPS: Operations"
    for col in sheet[1]:sheet.cell(3,col.column).value=values.get(col.value,'')
    out=BytesIO();book.save(out)
    body['contentBase64']=base64.b64encode(out.getvalue()).decode()
    job=service.submit(c,tenant,actor,ImportCreate.model_validate(body),str(uuid4()))
    report=service.validate(c,tenant,actor,UUID(job['jobId']))
    assert report['status']=='READY',report
    receipt=service.confirm(c,tenant,actor,UUID(job['jobId']),report['reviewHash'],'custom-fields')
    trade=UUID(receipt['receipt'][0]['tradeId'])
    assert c.scalar(select(m.trade_property_reference.c.record_version_id).where(m.trade_property_reference.c.trade_id==trade))==record['recordVersionId']


def test_retired_field_after_preview_blocks_confirmation(connection):
    from apps.reference_api.trade_properties import provision_trade_catalogue
    c=connection;tenant=DEMO_IDS['tenant'];actor=DEMO_IDS['demo_user_account']
    code='IMPORT_'+uuid4().hex.upper()
    provision_trade_catalogue(c,tenant,actor,[dict(code=code,label='Desk',valueType='TEXT',required=False)],[])
    definition=c.scalar(select(m.trade_property_definition.c.definition_id).where(m.trade_property_definition.c.code==code))
    body=file_body(str(uuid4()),1);text=base64.b64decode(body['contentBase64']).decode().splitlines()
    body['contentBase64']=base64.b64encode((text[0]+f',property:{definition}\n'+text[1]+',My desk').encode()).decode()
    job=service.submit(c,tenant,actor,ImportCreate.model_validate(body),str(uuid4()));job_id=UUID(job['jobId'])
    report=service.validate(c,tenant,actor,job_id);assert report['status']=='READY',report
    from apps.reference_api.trade_configuration import retire_property
    retire_property(c,tenant,actor,definition)
    with pytest.raises(service.ImportConflict):service.confirm(c,tenant,actor,job_id,report['reviewHash'],'stale')
    assert service.load(c,tenant,actor,job_id)['status']=='READY'


def test_scope_and_revocation_cover_artifacts_receipts_and_confirmation(connection):
    c=connection;tenant=DEMO_IDS['tenant'];actor=DEMO_IDS['demo_user_account']
    job=service.submit(c,tenant,actor,ImportCreate.model_validate(file_body(str(uuid4()),1)),str(uuid4()));job_id=UUID(job['jobId'])
    review=service.validate(c,tenant,actor,job_id)
    with pytest.raises(LookupError):service.load(c,DEMO_IDS['second_tenant'],actor,job_id)
    c.execute(m.tenant_user_account.update().where(m.tenant_user_account.c.tenant_id==tenant,
        m.tenant_user_account.c.user_account_id==actor).values(status='SUSPENDED'))
    with pytest.raises(PermissionError):service.load(c,tenant,actor,job_id)
    with pytest.raises(PermissionError):service.confirm(c,tenant,actor,job_id,review['reviewHash'],'revoked')


def test_confirmation_rechecks_frozen_listing_economics(connection):
    c=connection;tenant=DEMO_IDS['tenant'];actor=DEMO_IDS['demo_user_account']
    job=service.submit(c,tenant,actor,ImportCreate.model_validate(file_body(str(uuid4()),1)),str(uuid4()));job_id=UUID(job['jobId'])
    report=service.validate(c,tenant,actor,job_id)
    c.execute(m.listing.update().where(m.listing.c.listing_node_id==DEMO_IDS['hsbc_xlon_listing_node']).values(status='INACTIVE'))
    with pytest.raises(service.ImportConflict):service.confirm(c,tenant,actor,job_id,report['reviewHash'],'stale-listing')


def test_conflicting_source_id_cannot_overwrite_booked_trade(connection):
    c=connection;tenant=DEMO_IDS['tenant'];actor=DEMO_IDS['demo_user_account'];body=file_body(str(uuid4()),1)
    job=service.submit(c,tenant,actor,ImportCreate.model_validate(body),str(uuid4()));job_id=UUID(job['jobId'])
    report=service.validate(c,tenant,actor,job_id);original=service.confirm(c,tenant,actor,job_id,report['reviewHash'],'first')
    content=base64.b64decode(body['contentBase64']).decode().replace(',10,10.23,',',20,10.23,')
    changed=service.submit(c,tenant,actor,ImportCreate.model_validate(body|dict(contentBase64=base64.b64encode(content.encode()).decode())),str(uuid4()))
    report=service.validate(c,tenant,actor,UUID(changed['jobId']))
    assert report['status']=='NEEDS_CORRECTION' and report['invalid']==1
    assert c.scalar(select(m.trade.c.quantity).where(m.trade.c.trade_id==UUID(original['receipt'][0]['tradeId'])))==10


def test_equivalent_decimal_formatting_replays_same_source_row(connection):
    c=connection;tenant=DEMO_IDS['tenant'];actor=DEMO_IDS['demo_user_account'];body=file_body(str(uuid4()),1)
    job=service.submit(c,tenant,actor,ImportCreate.model_validate(body),str(uuid4()));job_id=UUID(job['jobId'])
    report=service.validate(c,tenant,actor,job_id);service.confirm(c,tenant,actor,job_id,report['reviewHash'],'original')
    content=base64.b64decode(body['contentBase64']).decode().replace(',10,10.23,',',10.000,10.2300,')
    new=service.submit(c,tenant,actor,ImportCreate.model_validate(body|dict(contentBase64=base64.b64encode(content.encode()).decode())),str(uuid4()))
    review=service.validate(c,tenant,actor,UUID(new['jobId']))
    assert review['status']=='READY' and review['replayed']==1,review


def test_atomic_booking_replay_and_repackaged_delivery():
    async def run():
        async with AsyncClient(transport=ASGITransport(app=create_app()),base_url='http://test') as client:
            body=file_body(str(uuid4()));h=headers()
            created=await client.post('/v1/trades/imports',json=body,headers=h)
            assert created.status_code==201,created.text
            same=await client.post('/v1/trades/imports',json=body,headers=h)
            assert same.json()['jobId']==created.json()['jobId']
            job=created.json()['jobId'];report=(await client.post(f'/v1/trades/imports/{job}/validate',json={},headers=headers())).json()
            assert report['status']=='READY',report
            confirmation={'reviewHash':report['reviewHash']}
            booked=await client.post(f'/v1/trades/imports/{job}/confirm',json=confirmation,headers=headers())
            assert booked.status_code==200,booked.text
            assert booked.json()['applied']==2
            replay=await client.post(f'/v1/trades/imports/{job}/confirm',json=confirmation,headers=headers())
            assert replay.json()['receipt']==booked.json()['receipt']
            new=await client.post('/v1/trades/imports',json=body|{'filename':'repackaged.csv'},headers=headers())
            second=new.json()['jobId'];again=(await client.post(f'/v1/trades/imports/{second}/validate',json={},headers=headers())).json()
            assert again['replayed']==2 and again['status']=='READY',again
            final=await client.post(f'/v1/trades/imports/{second}/confirm',json={'reviewHash':again['reviewHash']},headers=headers())
            assert final.json()['applied']==0 and final.json()['replayed']==2,final.text
            detail=await client.get('/v1/trades/'+booked.json()['receipt'][0]['tradeId'],headers=headers())
            assert detail.status_code==200 and detail.json()['data']['trade']['quantity']=='10.000000000000'
    asyncio.run(run())
