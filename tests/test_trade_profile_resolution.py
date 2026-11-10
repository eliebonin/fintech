"""One contextual resolver controls every supported booking path."""
from uuid import uuid4
import pytest
from tests.test_governed_trade_configuration import engine,connection,TENANT,ACTOR
from security_master_schema.demo_data import DEMO_IDS as ids
from apps.reference_api.trade_configuration import create_property
from tenant_reference.errors import ConfigurationConflict
from trading.profiles.configuration import create_profile,publish_profile_version,assign_profile,current_assignment
from trading.profiles.resolution import resolve_trade_configuration


def test_same_custom_definition_can_be_required_optional_or_hidden_by_strategy(connection):
    prop=create_property(connection,TENANT,ACTOR,dict(code='PROFILE_'+uuid4().hex,label='Mandate',valueType='TEXT'))
    strategies=[ids['strategy'],ids['uk_fund_strategy'],ids['us_fund_strategy']]
    for i,requirement in enumerate(['REQUIRED','OPTIONAL','NOT_USED']):
        p=create_profile(connection,TENANT,ACTOR,'PROFILE_'+uuid4().hex,'Dealing','Synthetic test')
        v=publish_profile_version(connection,TENANT,ACTOR,p['profileId'],dict(label='Dealing',reason='Synthetic test',expectedVersion=0,fields=[dict(propertyCode=prop['code'],propertyVersion=1,requirement=requirement)]))
        assign_profile(connection,TENANT,ACTOR,strategies[i],v['versionId'],current_assignment(connection,TENANT,strategies[i])['revision'],'Explicit rules')
        result=resolve_trade_configuration(connection,TENANT,strategies[i],ACTOR,'TRADE_WRITE')
        assert result['fields'][0]['requirement']==requirement
        assert result['fields'][0]['definitionId']==prop['definitionId']
        assert result['profileVersionId']==v['versionId']


def test_unassigned_strategy_never_silently_uses_a_tenant_default(connection):
    from sqlalchemy import select
    from security_master_schema import models as m
    identity=uuid4();original=dict(connection.execute(select(m.strategy).where(m.strategy.c.strategy_id==ids['strategy'])).mappings().one())
    connection.execute(m.strategy.insert().values(**(original|dict(strategy_id=identity,strategy_code='UNASSIGNED_'+identity.hex))))
    with pytest.raises(ConfigurationConflict,match='assigned'):
        resolve_trade_configuration(connection,TENANT,identity,ACTOR,'TRADE_WRITE')


def test_expected_assignment_revision_is_checked(connection):
    p=create_profile(connection,TENANT,ACTOR,'PROFILE_'+uuid4().hex,'Dealing','Synthetic test')
    v=publish_profile_version(connection,TENANT,ACTOR,p['profileId'],dict(label='Dealing',reason='Synthetic test',expectedVersion=0,fields=[]))
    assign_profile(connection,TENANT,ACTOR,ids['strategy'],v['versionId'],current_assignment(connection,TENANT,ids['strategy'])['revision'],'Explicit rules')
    with pytest.raises(ConfigurationConflict,match='changed'):
        resolve_trade_configuration(connection,TENANT,ids['strategy'],ACTOR,'TRADE_WRITE',expected_assignment_revision=current_assignment(connection,TENANT,ids['strategy'])['revision']+1)


def test_annotation_validation_uses_profile_requirement_instead_of_legacy_global_flag(connection):
    from trading.annotations import validate_trade_annotations
    from trading.booking_contracts import TradeBookingRequest
    prop=create_property(connection,TENANT,ACTOR,dict(code='OPTIONAL_'+uuid4().hex,label='Optional mandate',valueType='TEXT',required=True,acknowledgeRequiredImpact=True))
    profile=create_profile(connection,TENANT,ACTOR,'PROFILE_'+uuid4().hex,'Dealing','Synthetic test')
    v=publish_profile_version(connection,TENANT,ACTOR,profile['profileId'],dict(label='Dealing',reason='Synthetic test',expectedVersion=0,fields=[dict(propertyCode=prop['code'],propertyVersion=1,requirement='OPTIONAL')]))
    assign_profile(connection,TENANT,ACTOR,ids['strategy'],v['versionId'],current_assignment(connection,TENANT,ids['strategy'])['revision'],'Explicit rules')
    request=TradeBookingRequest(strategyId=ids['strategy'],listingId=ids['hsbc_xlon_listing_node'],side='BUY',quantity='1',executionPrice='1',tradeDatetime='2026-10-01T10:00:00Z',settlementDate='2026-10-05')
    values=validate_trade_annotations(connection,TENANT,request,actor_id=ACTOR)
    assert values==[] and values.configuration['profileVersionId']==v['versionId']
