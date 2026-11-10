"""Every supported writer uses the same pinned profile and required-field rule."""
import json
from uuid import UUID,uuid4
import pytest
from sqlalchemy import select
from tests.test_governed_trade_configuration import engine,connection,TENANT,ACTOR
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from tests.test_product_booking_api import future,structured,payload as product_payload,approve
from tests.test_bond_booking_api import bond,ticket as bond_payload
from tests.test_fx_forward_booking_api import instrument,payload as forward_payload,request as http_request
from tests.test_option_booking_api import listing,payload as option_payload
from tests.test_generic_swap_booking_api import create_swap,ticket as swap_payload
from tests.test_amc import draft as amc_draft
from tests.profile_fixtures import assign
from apps.reference_api.trade_configuration import create_property
from security_master_schema.errors import TradeFieldError

@pytest.fixture(scope='module')
def swap():return create_swap()

@pytest.fixture(scope='module')
def amc():return approve(http_request('POST','/v1/instruments/amc-proposals',amc_draft()))

@pytest.mark.parametrize('kind',['CASH','FX_FORWARD','OPTION','FUTURE','STRUCTURED_PRODUCT','BOND','SWAP','ACTIVELY_MANAGED_CERTIFICATE'])
def test_native_writer_retains_profile_and_enforces_selected_required_field(connection,future,structured,bond,instrument,listing,swap,amc,kind):
    c=connection
    prop=create_property(c,TENANT,ACTOR,dict(code='NATIVE_'+uuid4().hex,label='Required mandate',valueType='TEXT'))
    version,assignment=assign(c,TENANT,ACTOR,ids['strategy'],[dict(propertyCode=prop['code'],propertyVersion=1,requirement='REQUIRED')])
    if kind=='CASH':
        from trading.booking import book_cash_trade
        from trading.booking_contracts import TradeBookingRequest as Model
        from tests.test_cash_booking_integrity import payload
        values=payload().model_dump(mode='json',by_alias=True)
        def execute(request,key):return book_cash_trade(c,TENANT,ACTOR,request,key).trade_id
    elif kind=='FX_FORWARD':
        from apps.reference_api.fx_forward_booking import book_fx_forward_trade
        from apps.reference_api.contracts import FxForwardBookingRequest as Model
        values=forward_payload(instrument)
        def execute(request,key):return book_fx_forward_trade(c,TENANT,ACTOR,request,key,'isolated-profile').data.trade.trade_id
    elif kind=='OPTION':
        from apps.reference_api.option_booking import book
        from apps.reference_api.contracts import OptionBookingRequest as Model
        values=option_payload(listing)
        def execute(request,key):return book(c,TENANT,ACTOR,request,key,'isolated-profile').data.trade.trade_id
    else:
        from apps.reference_api.product_booking import book
        from apps.reference_api.product_booking_contracts import ProductBookingRequest as Model
        values=product_payload(*future) if kind=='FUTURE' else bond_payload(bond) if kind=='BOND' else swap_payload(swap) if kind=='SWAP' else product_payload(amc,quantity='10.25',executionPrice='123.45') if kind=='ACTIVELY_MANAGED_CERTIFICATE' else product_payload(structured)
        def execute(request,key):return book(c,TENANT,ACTOR,request,key,kind,'isolated-profile').data.trade.trade_id
    values.update(profileAssignmentRevision=assignment['revision'],properties=[dict(definitionId=str(prop['definitionId']),value='Income')])
    with pytest.raises(TradeFieldError,match='Required mandate'):
        execute(Model.model_validate(values|dict(properties=[])),str(uuid4()))
    key=str(uuid4());trade=execute(Model.model_validate(values),key)
    assert execute(Model.model_validate(values),key)==trade
    stored=c.execute(select(m.trade).where(m.trade.c.trade_id==trade)).mappings().one()
    assert stored['trade_profile_version_id']==version['versionId'] and stored['trade_profile_assignment_revision']==assignment['revision']
    proof=json.loads(c.scalar(select(m.trade_lifecycle_event.c.event_payload).where(m.trade_lifecycle_event.c.trade_id==trade,m.trade_lifecycle_event.c.event_type=='BOOKED')))
    assert proof['tradeConfiguration']['profileVersionId']==str(version['versionId'])
    assert c.scalar(select(m.trade_property_value.c.value).where(m.trade_property_value.c.trade_id==trade,m.trade_property_value.c.definition_id==prop['definitionId']))=='Income'
