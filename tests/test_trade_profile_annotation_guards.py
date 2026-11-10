"""A copied JSON flag never substitutes for a completed retained operation."""
import json
from uuid import UUID,uuid4
import pytest
from sqlalchemy import select,text
from sqlalchemy.exc import DBAPIError
from tests.test_governed_trade_configuration import engine,connection,TENANT,ACTOR,catalogue,entry,field
from tests.profile_fixtures import assign
from tests.test_trade_profile_corrections import request
from trading.booking import book_cash_trade
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from tenant_reference import catalogues as sources


def test_forged_inheritance_without_correction_link_cannot_commit(connection):
    c=connection;cat=catalogue(c);record=entry(c,cat);prop=field(c,cat)
    assign(c,TENANT,ACTOR,ids['strategy'],[dict(propertyCode=prop['code'],propertyVersion=1)])
    original=book_cash_trade(c,TENANT,ACTOR,request(properties=[dict(definitionId=prop['definitionId'],value=str(record['recordVersionId']))]),str(uuid4())).trade_id
    c.execute(text('SET CONSTRAINTS trd.preserved_profile_reference, trd.preserved_profile_scalar IMMEDIATE'))
    sources.change_record(c,TENANT,ACTOR,cat,record['recordVersionId'],reason='Retire for new use')
    trade=dict(c.execute(select(m.trade).where(m.trade.c.trade_id==original)).mappings().one())
    event=dict(c.execute(select(m.trade_lifecycle_event).where(m.trade_lifecycle_event.c.trade_id==original)).mappings().one())
    forged=uuid4();trade['trade_id']=forged
    snapshot=json.loads(event['event_payload']);snapshot['sourcePreservedAnnotations']=dict(originalTradeId=str(original),definitionIds=[str(prop['definitionId'])])
    event.update(trade_id=forged,trade_lifecycle_event_id=uuid4(),source_event_id=str(uuid4()),event_payload=json.dumps(snapshot))
    with pytest.raises(DBAPIError,match='retained source-preserving'),c.begin_nested():
        c.execute(m.trade.insert().values(**trade));c.execute(m.trade_lifecycle_event.insert().values(**event))
        c.execute(m.trade_property_reference.insert().values(trade_id=forged,tenant_id=TENANT,definition_id=prop['definitionId'],record_version_id=record['recordVersionId'],source_inherited=False))
