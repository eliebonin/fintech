"""Explicit synthetic profiles for tests; never a product runtime fallback."""
from uuid import uuid4
from trading.profiles.configuration import create_profile,publish_profile_version,assign_profile,current_assignment
from trading.profiles.contracts import STANDARD_FIELDS


def assign(c,tenant,actor,strategy,fields=()):
    profile=create_profile(c,tenant,actor,'FIXTURE_'+uuid4().hex,'Synthetic dealing','Isolated test setup')
    rules=[dict(standardFieldKey=key,requirement='OPTIONAL') for key in STANDARD_FIELDS]+list(fields)
    version=publish_profile_version(c,tenant,actor,profile['profileId'],dict(label='Synthetic dealing',reason='Isolated profile',expectedVersion=0,fields=rules))
    before=current_assignment(c,tenant,strategy)
    assignment=assign_profile(c,tenant,actor,strategy,version['versionId'],before['revision'] if before else 0,'Explicit isolated assignment')
    return version,assignment


def registry_profile(c,tenant,actor,strategy):
    """Registry regression fixtures explicitly choose their active test fields.

    Older tests exercise typed value/source validation, not profile selection.
    Map their synthetic required setup into a real profile; product code never
    reads the legacy global flag as an effective booking requirement.
    """
    from sqlalchemy import select
    from security_master_schema import models as m
    from trading.profiles.resolution import load_assigned_configuration
    definitions=c.execute(select(m.trade_property_definition).where(m.trade_property_definition.c.tenant_id==tenant,m.trade_property_definition.c.status=='ACTIVE',m.trade_property_definition.c.value_type!='CHOICE')).mappings().all()
    fields=[dict(propertyCode=row['code'],propertyVersion=row['version_no'],requirement='REQUIRED' if row['required'] else 'OPTIONAL') for row in definitions]
    prior=current_assignment(c,tenant,strategy)
    if prior:
        context=load_assigned_configuration(c,tenant,strategy)
        configured={(field['propertyCode'],field['propertyVersion'],field['requirement']) for field in context['fields'] if field['propertyCode']}
        expected={(field['propertyCode'],field['propertyVersion'],field['requirement']) for field in fields}
        if configured==expected:return
    assign(c,tenant,actor,strategy,fields)


def configure_allocation(c,tenant,actor,strategy,fields,expected_revision,reason):
    """Port allocation regression setup to the actual strategy-profile command."""
    from sqlalchemy import select
    from security_master_schema import models as m
    from trading.profiles.configuration import _configure
    from tenant_reference.errors import ConfigurationConflict
    _configure(c,tenant,actor)
    before=current_assignment(c,tenant,strategy)
    if (before['revision'] if before else 0)!=expected_revision:raise ConfigurationConflict('Profile assignment changed; reload')
    definitions={row['definition_id']:row for row in c.execute(select(m.trade_property_definition).where(m.trade_property_definition.c.tenant_id==tenant)).mappings()}
    rules=[]
    from uuid import UUID
    for field in fields:
        row=definitions.get(UUID(field['definitionId']))
        if row is None:raise ValueError('The selected definition is unavailable in this tenant')
        rules.append(dict(propertyCode=row['code'],propertyVersion=row['version_no'],requirement='REQUIRED' if row['required'] else 'OPTIONAL',lifecycleBehavior=field['behavior']))
    assign(c,tenant,actor,strategy,rules)
    return allocation_policy(c,tenant,strategy).payload()


def allocation_policy(c,tenant,strategy):
    from trading.allocation_policy import load_allocation_policy
    return load_allocation_policy(c,tenant,strategy)
