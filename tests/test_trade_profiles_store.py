"""Profile versions and assignments retain tenant-owned relational evidence."""
from uuid import uuid4
import pytest
from sqlalchemy import select,update
from sqlalchemy.exc import IntegrityError,DBAPIError
from security_master_schema import models as m
from tests.test_governed_trade_configuration import engine,connection,TENANT,ACTOR
from tenant_reference.errors import ConfigurationConflict
from trading.profiles.configuration import create_profile,publish_profile_version,assign_profile,list_profiles,profile_version,current_assignment


def profile(connection):
    return create_profile(connection,TENANT,ACTOR,'TEST_'+uuid4().hex,'Test dealing','Synthetic profile')


def publish(connection,identity,expected=0,fields=None):
    return publish_profile_version(connection,TENANT,ACTOR,identity,dict(label='Fund dealing',reason='Synthetic publication',expectedVersion=expected,fields=fields or [dict(standardFieldKey='COUNTERPARTY',requirement='OPTIONAL')]))


def test_publication_is_pinned_and_successful_retry_is_unchanged(connection):
    identity=profile(connection)['profileId'];first=publish(connection,identity)
    assert publish(connection,identity)['versionId']==first['versionId']
    second=publish(connection,identity,1)
    assert second['versionNo']==2 and first['versionId']!=second['versionId']
    retained=profile_version(connection,TENANT,ACTOR,first['versionId'])
    assert retained['versionNo']==1
    with pytest.raises(DBAPIError),connection.begin_nested():
        connection.execute(m.trade_profile_version.update().where(m.trade_profile_version.c.version_id==first['versionId']).values(label='Overwritten'))


def test_assignment_revisions_conflict_without_silently_upgrading(connection):
    identity=profile(connection)['profileId'];first=publish(connection,identity)
    mock_strategy=__import__('security_master_schema.demo_data',fromlist=['DEMO_IDS']).DEMO_IDS['strategy']
    baseline=current_assignment(connection,TENANT,mock_strategy)['revision']
    assigned=assign_profile(connection,TENANT,ACTOR,mock_strategy,first['versionId'],baseline,'Initial assignment')
    second=publish(connection,identity,1)
    assert assigned['profileVersionId']==first['versionId']
    assert assign_profile(connection,TENANT,ACTOR,mock_strategy,first['versionId'],baseline,'Initial assignment')['revision']==baseline+1
    with pytest.raises(ConfigurationConflict):assign_profile(connection,TENANT,ACTOR,mock_strategy,second['versionId'],baseline,'Stale change')


def test_foreign_profile_version_cannot_be_bound_to_this_tenant_strategy(connection):
    from security_master_schema.demo_data import DEMO_IDS as ids
    foreign=uuid4();version=uuid4()
    connection.execute(m.trade_profile.insert().values(profile_id=foreign,tenant_id=ids['second_tenant'],code='FOREIGN_'+uuid4().hex,created_by=ACTOR))
    connection.execute(m.trade_profile_version.insert().values(version_id=version,tenant_id=ids['second_tenant'],profile_id=foreign,version_no=1,label='Foreign',reason='Synthetic',content_hash='0'*64,published_by=ACTOR))
    with pytest.raises(IntegrityError),connection.begin_nested():
        connection.execute(m.strategy_trade_profile_assignment.insert().values(tenant_id=TENANT,strategy_id=ids['strategy'],revision=2,previous_revision=1,profile_version_id=version,actor_id=ACTOR,reason='Invalid scope'))


def test_profile_rule_has_real_tenant_definition_version_fk(connection):
    identity=profile(connection)['profileId']
    with pytest.raises(ValueError,match='definition'):
        publish(connection,identity,fields=[dict(propertyCode='MISSING',propertyVersion=1)])


def test_deferred_membership_check_runs_at_commit_boundary(connection):
    from sqlalchemy import text
    identity=profile(connection)['profileId']
    publish(connection,identity)
    connection.execute(text('SET CONSTRAINTS trd.profile_rule_count_version, trd.profile_rule_count_member IMMEDIATE'))


def test_membership_cannot_be_appended_after_publication(connection):
    from sqlalchemy import text
    identity=profile(connection)['profileId']
    version=publish(connection,identity)
    connection.execute(text('SET CONSTRAINTS trd.profile_rule_count_version, trd.profile_rule_count_member IMMEDIATE'))
    with pytest.raises(DBAPIError,match='membership'),connection.begin_nested():
        connection.execute(m.trade_profile_field_rule.insert().values(rule_id=uuid4(),tenant_id=TENANT,profile_version_id=version['versionId'],standard_field_key='COMMENT',requirement='OPTIONAL',lifecycle_behavior='INPUT'))
