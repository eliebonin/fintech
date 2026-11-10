"""Retired controlled values may close their proven original allocation only."""
from uuid import uuid4,UUID
from sqlalchemy import select,text
from tests.test_valuation_service import valued
from tests.test_bond_redemption_service import setup
from tests.test_governed_trade_configuration import catalogue,entry,field
from tests.profile_fixtures import assign
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from tenant_reference import catalogues as sources
from lifecycle import bond_service as svc


def test_retired_original_reference_remains_valid_for_exact_maturity_inheritance(valued):
    c,r,trade=valued;listing,original,_=setup(c,r,trade)
    cat=catalogue(c);record=entry(c,cat);prop=field(c,cat)
    c.execute(m.trade_property_reference.insert().values(tenant_id=r.tenant_id,trade_id=original,definition_id=prop['definitionId'],record_version_id=record['recordVersionId']))
    assign(c,r.tenant_id,ids['demo_user_account'],r.strategy_id,[dict(propertyCode=prop['code'],propertyVersion=1,lifecycleBehavior='ALLOCATION')])
    sources.change_record(c,r.tenant_id,ids['demo_user_account'],cat,record['recordVersionId'],reason='Retired for future classification only')
    instrument=c.scalar(select(m.listing.c.instrument_node_id).where(m.listing.c.listing_node_id==listing))
    svc.configure(c,r.tenant_id,ids['demo_user_account'],ids['platform_admin_user_account'],r.strategy_id,'DIRECT',0,'Synthetic closure')
    candidate,fingerprint,_,_=svc.candidate(c,r.tenant_id,r.strategy_id,instrument)
    assert candidate['annotationStatus']=='READY',candidate['movements'][0]['annotationIssues']
    result=svc.post(c,r.tenant_id,ids['demo_user_account'],ids['platform_admin_user_account'],r.strategy_id,instrument,fingerprint,str(uuid4()))
    assert c.scalar(select(m.trade_property_reference.c.record_version_id).where(m.trade_property_reference.c.trade_id==UUID(result['trade_ids'][0])))==record['recordVersionId']

    c.execute(text('SET CONSTRAINTS trd.preserved_profile_reference, trd.preserved_profile_scalar IMMEDIATE'))
