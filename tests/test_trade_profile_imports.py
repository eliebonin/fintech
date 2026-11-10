"""Retained import review and template metadata follow the strategy assignment."""
from io import BytesIO
from uuid import UUID,uuid4
import pytest
from openpyxl import load_workbook
from sqlalchemy import select
from tests.test_governed_trade_configuration import engine,connection,TENANT,ACTOR
from tests.profile_fixtures import assign
from tests.test_import_trades import file_body
from apps.reference_api import import_service as service
from apps.reference_api.import_routes import ImportCreate
from apps.reference_api.import_adapters.trades import descriptor
from data_imports.formats import render_template,parse_file,ImportFormatError
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids


def test_review_rejects_assignment_change_and_confirmed_rows_retain_profile(connection):
    c=connection
    assign(c,TENANT,ACTOR,ids['strategy'])
    job=service.submit(c,TENANT,ACTOR,ImportCreate.model_validate(file_body(str(uuid4()))),str(uuid4()))
    job_id=UUID(job['jobId']);review=service.validate(c,TENANT,ACTOR,job_id)
    assert review['status']=='READY'
    version,assignment=assign(c,TENANT,ACTOR,ids['strategy'])
    with pytest.raises(service.ImportConflict,match='changed'):
        service.confirm(c,TENANT,ACTOR,job_id,review['reviewHash'],'stale-profile')
    refreshed=service.validate(c,TENANT,ACTOR,job_id)
    assert refreshed['reviewHash']!=review['reviewHash']
    receipt=service.confirm(c,TENANT,ACTOR,job_id,refreshed['reviewHash'],'current-profile')
    assert receipt['status']=='APPLIED' and receipt['applied']==2
    for row in receipt['receipt']:
        assert c.scalar(select(m.trade.c.trade_profile_version_id).where(m.trade.c.trade_id==UUID(row['tradeId'])))==version['versionId']


def test_old_excel_template_is_rejected_without_reinterpreting_columns(connection):
    assign(connection,TENANT,ACTOR,ids['strategy'])
    first=descriptor(connection,TENANT,ACTOR,ids['strategy'])
    content=render_template(first)
    workbook=load_workbook(BytesIO(content));meta=dict(workbook['Template'].values)
    assert meta['profileVersionId']==first['profileVersionId']
    assign(connection,TENANT,ACTOR,ids['strategy'])
    with pytest.raises(ImportFormatError,match='profile changed'):
        parse_file(content,'trades.xlsx',descriptor(connection,TENANT,ACTOR,ids['strategy']))
