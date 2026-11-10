"""Pinned metadata survives label revisions and authorised linked corrections."""
import json
from uuid import uuid4
import pytest
from sqlalchemy import select
from tests.test_governed_trade_configuration import engine,connection,TENANT,ACTOR
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from apps.reference_api.trade_configuration import create_property,replace_property
from apps.reference_api.trade_properties import get_trade_booking_context
from trading.booking import book_cash_trade
from trading.booking_contracts import TradeBookingRequest
from trading.annotations import validate_trade_annotations
from security_master_schema.errors import TradeFieldError
from tenant_reference.errors import ConfigurationConflict
from tests.profile_fixtures import assign


def request(**changes):
    return TradeBookingRequest.model_validate(dict(strategyId=ids['strategy'],listingId=ids['hsbc_xlon_listing_node'],side='BUY',quantity='1',executionPrice='1',tradeDatetime='2026-10-01T10:00:00Z',settlementDate='2026-10-05')|changes)


def test_label_revision_keeps_pinned_meaning_and_new_meaning_needs_new_code(connection):
    prop=create_property(connection,TENANT,ACTOR,dict(code='LABEL_'+uuid4().hex,label='Old label',valueType='TEXT'))
    first,_=assign(connection,TENANT,ACTOR,ids['strategy'],[dict(propertyCode=prop['code'],propertyVersion=1)])
    revised=replace_property(connection,TENANT,ACTOR,prop['definitionId'],dict(code=prop['code'],label='New label',valueType='TEXT',reason='Clarify label'))
    values=validate_trade_annotations(connection,TENANT,request(properties=[dict(definitionId=prop['definitionId'],value='Retained meaning')]),actor_id=ACTOR)
    assert values.configuration['profileVersionId']==first['versionId']
    assert values[0]['definition_id']==prop['definitionId']
    with pytest.raises(ValueError,match='type and source'),connection.begin_nested():
        replace_property(connection,TENANT,ACTOR,revised['definitionId'],dict(code=prop['code'],label='Different meaning',valueType='INTEGER'))


def test_hidden_original_value_can_be_preserved_but_not_changed(connection):
    prop=create_property(connection,TENANT,ACTOR,dict(code='INHERIT_'+uuid4().hex,label='Historical note',valueType='TEXT'))
    assign(connection,TENANT,ACTOR,ids['strategy'],[dict(propertyCode=prop['code'],propertyVersion=1)])
    original=book_cash_trade(connection,TENANT,ACTOR,request(properties=[dict(definitionId=prop['definitionId'],value='Original')]),str(uuid4())).trade_id
    assign(connection,TENANT,ACTOR,ids['strategy'])
    context=get_trade_booking_context(connection,TENANT,ACTOR,ids['strategy'],original)
    assert next(p for p in context['properties'] if p['definitionId']==prop['definitionId'])['inheritedOnly'] is True
    corrected=request(properties=[dict(definitionId=prop['definitionId'],value='Original')],correction=dict(tradeId=original,expectedSequenceNo=1,reason='Correct executed amount'))
    changed=corrected.model_copy(update={'quantity':corrected.quantity*2})
    replacement=book_cash_trade(connection,TENANT,ACTOR,changed,str(uuid4())).trade_id
    proof=json.loads(connection.scalar(select(m.trade_lifecycle_event.c.event_payload).where(m.trade_lifecycle_event.c.trade_id==replacement,m.trade_lifecycle_event.c.event_type=='BOOKED')))
    assert proof['sourcePreservedAnnotations']['originalTradeId']==str(original)
    forged=request(properties=[dict(definitionId=prop['definitionId'],value='Different')],correction=dict(tradeId=replacement,expectedSequenceNo=2,reason='Attempt hidden change'))
    with pytest.raises(TradeFieldError,match='unchanged'):
        book_cash_trade(connection,TENANT,ACTOR,forged,str(uuid4()))


def test_stale_new_booking_conflicts_but_original_success_replays(connection):
    _,first=assign(connection,TENANT,ACTOR,ids['strategy'])
    payload=request(profileAssignmentRevision=first['revision']);key=str(uuid4())
    original=book_cash_trade(connection,TENANT,ACTOR,payload,key).trade_id
    assign(connection,TENANT,ACTOR,ids['strategy'])
    assert book_cash_trade(connection,TENANT,ACTOR,payload,key).trade_id==original
    with pytest.raises(ConfigurationConflict,match='changed'):
        book_cash_trade(connection,TENANT,ACTOR,payload,str(uuid4()))
