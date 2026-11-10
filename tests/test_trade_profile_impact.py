"""Changing profiles cannot silently erase still-open allocation dimensions."""
from uuid import uuid4
import pytest
from sqlalchemy import select
from tests.test_valuation_service import valued
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from tenant_reference.errors import ConfigurationConflict
from trading.profiles.configuration import create_profile,publish_profile_version,assign_profile,current_assignment


def test_removing_used_open_allocation_requires_remediation(valued):
    c,r,trade=valued
    identity=uuid4();code='BUCKET_'+identity.hex
    c.execute(m.trade_property_definition.insert().values(definition_id=identity,tenant_id=r.tenant_id,code=code,label='Bucket',value_type='TEXT',created_by_user_account_id=ids['demo_user_account']))
    c.execute(m.trade_property_value.insert().values(trade_id=trade,tenant_id=r.tenant_id,definition_id=identity,value='Income'))
    profile=create_profile(c,r.tenant_id,ids['demo_user_account'],'IMPACT_'+uuid4().hex,'Impact','Synthetic setup')
    first=publish_profile_version(c,r.tenant_id,ids['demo_user_account'],profile['profileId'],dict(label='Impact',reason='Keep allocation',expectedVersion=0,fields=[dict(propertyCode=code,propertyVersion=1,lifecycleBehavior='ALLOCATION')]))
    assign_profile(c,r.tenant_id,ids['demo_user_account'],r.strategy_id,first['versionId'],current_assignment(c,r.tenant_id,r.strategy_id)['revision'],'Initial profile')
    second=publish_profile_version(c,r.tenant_id,ids['demo_user_account'],profile['profileId'],dict(label='Impact',reason='New rules',expectedVersion=1,fields=[]))
    with pytest.raises(ConfigurationConflict,match='allocation'):
        assign_profile(c,r.tenant_id,ids['demo_user_account'],r.strategy_id,second['versionId'],current_assignment(c,r.tenant_id,r.strategy_id)['revision'],'Would erase an open classification')
