"""Explicit resolved metadata carried alongside ordinary annotation rows."""
from sqlalchemy import select
from security_master_schema import models as m
from security_master_schema.errors import TradeFieldError
from .contracts import STANDARD_FIELDS
from .resolution import resolve_trade_configuration,proof_values,frozen_configuration

class ProfiledAnnotations(list):
    def __init__(self,configuration):
        super().__init__();self.configuration=configuration


def annotation_context(c,tenant,request,actor,configuration=None,operation='TRADE_WRITE',native_required=()):
    if configuration is None:
        if actor is None:raise ValueError('A verified actor and strategy profile context are required.')
        configuration=resolve_trade_configuration(c,tenant,request.strategy_id,actor,operation,getattr(request,'profile_assignment_revision',None))
    else:
        from .resolution import load_assigned_configuration
        from tenant_reference.errors import ConfigurationConflict
        current=load_assigned_configuration(c,tenant,request.strategy_id)
        if str(configuration['strategyId'])!=str(request.strategy_id) or str(configuration['profileVersionId'])!=str(current['profileVersionId']) or configuration['assignmentRevision']!=current['assignmentRevision'] or configuration['configurationHash']!=current['configurationHash']:
            raise ConfigurationConflict('Profile context changed or does not match this booking strategy.')
        configuration=current
    from .inheritance import request_sources
    _,original_standard=request_sources(c,tenant,actor,request)
    minimum=set(native_required)
    if getattr(request,'trade_purpose',None)=='OTHER':minimum.add('COMMENT')
    standard={f['standardFieldKey']:f for f in configuration['fields'] if f.get('standardFieldKey')}
    for key,native in STANDARD_FIELDS.items():
        field=standard.get(key,{'requirement':'NOT_USED','label':native['label']})
        value=getattr(request,native['attribute'],None)
        specified=value is not None and (not isinstance(value,str) or bool(value.strip()))
        if (field['requirement']=='REQUIRED' or key in minimum) and not specified:raise TradeFieldError({'COUNTERPARTY':'counterpartyOrganisationId','EXECUTING_BROKER':'executingBrokerOrganisationId','TRADER':'traderPersonId','COMMENT':'comment'}[key],field['label']+' is required by the trade configuration.')
        unchanged=key in original_standard and str(original_standard[key])==str(value)
        if field['requirement']=='NOT_USED' and key not in minimum and specified and not unchanged:raise TradeFieldError({'COUNTERPARTY':'counterpartyOrganisationId','EXECUTING_BROKER':'executingBrokerOrganisationId','TRADER':'traderPersonId','COMMENT':'comment'}[key],field['label']+' is not used by the assigned profile.')
    return configuration


def annotation_profile_values(values):
    return proof_values(values.configuration)


def annotation_event_proof(values):
    return {'tradeConfiguration':frozen_configuration(values.configuration),**({'sourcePreservedAnnotations':values.source_preservation} if getattr(values,'source_preservation',None) else {})}
