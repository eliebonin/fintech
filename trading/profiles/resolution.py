"""One explicit strategy/profile context; no tenant-required fallback."""
from uuid import UUID
from sqlalchemy import select
from security_master_schema import models as m
from security_master_schema.booking_controls import authorize_booking
from security_master_schema.evidence import evidence_hash
from tenant_reference.errors import ConfigurationConflict
from trading.annotations import lock_trade_catalogue
from .configuration import current_assignment,_version,version_rules
from .contracts import STANDARD_FIELDS


def resolve_trade_configuration(connection,tenant_id,strategy_id,actor_id,operation,expected_assignment_revision=None):
    if operation not in {'STRATEGY_READ','TRADE_READ','TRADE_WRITE','TRADE_CORRECT','LIFECYCLE_READ','LIFECYCLE_PREPARE','LIFECYCLE_BOOK','LIFECYCLE_APPROVE'}:raise ValueError('Unknown profile consumer operation.')
    authorize_booking(connection,tenant_id,actor_id,action=operation,strategy_id=strategy_id)
    return load_assigned_configuration(connection,tenant_id,strategy_id,expected_assignment_revision)


def load_assigned_configuration(connection,tenant_id,strategy_id,expected_assignment_revision=None):
    """Data layer for already-authorised native workflows; never an HTTP authority."""
    lock_trade_catalogue(connection,tenant_id)
    assignment=current_assignment(connection,tenant_id,strategy_id)
    if assignment is None:raise ConfigurationConflict('No trade profile is assigned to this strategy. Configure it before booking.')
    if expected_assignment_revision is not None and expected_assignment_revision!=assignment['revision']:raise ConfigurationConflict('Strategy trade configuration changed. Reload and revalidate this request.')
    return load_version_configuration(connection,tenant_id,strategy_id,assignment['profile_version_id'],assignment['revision'])


def load_version_configuration(connection,tenant_id,strategy_id,version_id,assignment_revision):
    version=_version(connection,tenant_id,version_id)
    rules=version_rules(connection,tenant_id,version['version_id'])
    codes=[r['propertyCode'] for r in rules if r['propertyCode']]
    f=m.trade_property_definition
    definitions={(r['code'],r['version_no']):r for r in connection.execute(select(f).where(f.c.tenant_id==tenant_id,f.c.code.in_(codes))).mappings()}
    fields=[]
    for rule in rules:
        if rule['standardFieldKey']:
            native=STANDARD_FIELDS[rule['standardFieldKey']]
            fields.append({**rule,'fieldKey':'STANDARD:'+rule['standardFieldKey'],'label':native['label'],'sourceKey':native['source'],'definitionId':None})
        else:
            row=definitions.get((rule['propertyCode'],rule['propertyVersion']))
            if row is None:raise ConfigurationConflict('A pinned field definition is unavailable in this tenant.')
            fields.append({**rule,'fieldKey':'CUSTOM:'+row['code'],'label':row['label'],'definitionId':row['definition_id'],'valueType':row['value_type'],'catalogueId':row['catalogue_id'],'definitionStatus':row['status'],'sourceKey':'catalogue:'+str(row['catalogue_id']) if row['catalogue_id'] else None})
    proof=dict(profileVersionId=str(version['version_id']),assignmentRevision=assignment_revision,profileContentHash=version['content_hash'])
    return dict(tenantId=tenant_id,strategyId=strategy_id,profileVersionId=version['version_id'],profileId=version['profile_id'],profileLabel=version['label'],versionNo=version['version_no'],assignmentRevision=assignment_revision,configurationHash=evidence_hash(proof),fields=fields)


def proof_values(context):
    return dict(trade_profile_version_id=context['profileVersionId'],trade_profile_assignment_revision=context['assignmentRevision'])


def frozen_configuration(context):
    return dict(profileVersionId=str(context['profileVersionId']),assignmentRevision=context['assignmentRevision'],profileId=str(context['profileId']),profileLabel=context['profileLabel'],versionNo=context['versionNo'],configurationHash=context['configurationHash'])


def definition_available(definition,family):
    """A label-only successor does not invalidate a pinned semantic definition.

    An explicit final retirement has no active successor and remains unavailable.
    """
    return definition['status']=='ACTIVE' or any(row['status']=='ACTIVE' and row['code']==definition['code'] and row['value_type']==definition['value_type'] and row['catalogue_id']==definition['catalogue_id'] for row in family)
