"""Cutover copies a legacy tenant's actual settings without rewriting evidence."""
from uuid import uuid4
from sqlalchemy import select,func
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from tests.test_governed_trade_configuration import engine,connection,ACTOR
from trading.profiles.migration import backfill_profiles
from trading.profiles.configuration import current_assignment,version_rules


def test_cutover_is_repeatable_and_preserves_actual_required_settings(connection):
    tenant,strategy=uuid4(),uuid4()
    legacy=dict(connection.execute(select(m.tenant).where(m.tenant.c.tenant_id==ids['tenant'])).mappings().one())
    connection.execute(m.tenant.insert().values(**(legacy|dict(tenant_id=tenant,tenant_code='CUTOVER_'+tenant.hex))))
    parent=dict(connection.execute(select(m.strategy).where(m.strategy.c.strategy_id==ids['strategy'])).mappings().one())
    connection.execute(m.strategy.insert().values(**(parent|dict(tenant_id=tenant,strategy_id=strategy,strategy_code='LEGACY'))))
    code='MANDATE_'+uuid4().hex.upper()
    connection.execute(m.trade_property_definition.insert().values(definition_id=uuid4(),tenant_id=tenant,code=code,label='Legacy mandatory mandate',value_type='TEXT',required=True,created_by_user_account_id=ACTOR))
    before=connection.execute(select(m.trade_lifecycle_event.c.trade_lifecycle_event_id,m.trade_lifecycle_event.c.event_payload)).all()
    grants=connection.scalar(select(func.count()).select_from(m.access_group_grant))
    first=backfill_profiles(connection,ACTOR,tenant)
    assignments=connection.scalar(select(func.count()).select_from(m.strategy_trade_profile_assignment).where(m.strategy_trade_profile_assignment.c.tenant_id==tenant))
    assert first==dict(createdTenants=1,assignedStrategies=1) and assignments==1
    again=backfill_profiles(connection,ACTOR,tenant)
    assert again==dict(createdTenants=0,assignedStrategies=0)
    assignment=current_assignment(connection,tenant,strategy)
    rule=next(r for r in version_rules(connection,tenant,assignment['profile_version_id']) if r['propertyCode']==code)
    assert rule['requirement']=='REQUIRED'
    assert connection.execute(select(m.trade_lifecycle_event.c.trade_lifecycle_event_id,m.trade_lifecycle_event.c.event_payload)).all()==before
    assert connection.scalar(select(func.count()).select_from(m.access_group_grant))==grants


def test_legacy_repurposed_input_is_not_a_lifecycle_alias(connection):
    """Old optional input migrations must not prevent otherwise unchanged cutover."""
    import pytest
    from trading.allocation_policy import allocation_policy_from_context
    code='LEGACY_'+uuid4().hex.upper()
    old,new=uuid4(),uuid4()
    connection.execute(m.trade_property_definition.insert().values(definition_id=old,tenant_id=ids['tenant'],code=code,label='Old legacy meaning',value_type='TEXT',status='RETIRED',version_no=1,retired_at_utc=func.now(),retired_by_user_account_id=ACTOR,created_by_user_account_id=ACTOR))
    connection.execute(m.trade_property_definition.insert().values(definition_id=new,tenant_id=ids['tenant'],code=code,label='Current input',value_type='DECIMAL',status='ACTIVE',version_no=2,created_by_user_account_id=ACTOR))
    field=dict(propertyCode=code,definitionId=new,standardFieldKey=None,requirement='OPTIONAL',lifecycleBehavior='INPUT',fieldKey='CUSTOM:'+code)
    context=dict(assignmentRevision=1,fields=[field])
    policy=allocation_policy_from_context(connection,ids['tenant'],context)
    assert policy.fields[0].source_definition_ids==(new,)
    for behavior in ('ALLOCATION','INHERIT'):
        with pytest.raises(ValueError,match='meaning/type/source'):
            allocation_policy_from_context(connection,ids['tenant'],dict(context,fields=[dict(field,lifecycleBehavior=behavior)]))
