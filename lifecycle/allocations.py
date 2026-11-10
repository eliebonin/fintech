"""Shared annotation preparation and persistence for product-specific closures."""
from dataclasses import asdict
from functools import wraps
from types import SimpleNamespace
from uuid import UUID
from sqlalchemy import select
from security_master_schema import models as m
from security_master_schema.allocation_contracts import AnnotationValue
from security_master_schema.evidence import evidence_hash,canonical_payload
from trading.booking_contracts import TradePropertyInput
from trading.annotations import validate_trade_annotations,lock_trade_catalogue
from trading.booking_store import persist_trade_annotations


def atomic_post(function):
    @wraps(function)
    def run(connection,*args,**kwargs):
        with connection.begin_nested():return function(connection,*args,**kwargs)
    return run


def annotation_request(properties,strategy_id=None,standard_inputs=None):
    values=standard_inputs or {}
    return SimpleNamespace(properties=[TradePropertyInput.model_validate(p) for p in properties],tag_ids=[],strategy_id=strategy_id,
        counterparty_organisation_id=UUID(str(values['COUNTERPARTY'])) if values.get('COUNTERPARTY') else None,
        executing_broker_organisation_id=UUID(str(values['EXECUTING_BROKER'])) if values.get('EXECUTING_BROKER') else None,
        trader_person_id=UUID(str(values['TRADER'])) if values.get('TRADER') else None,
        comment=values.get('COMMENT'),external_references=[],external_reference=None)


def prepare_annotations(c,tenant,policy,movements,source_annotations,annotation_inputs=None):
    """Inherited dimensions are immutable; other applicable fields use Ops inputs."""
    lock_trade_catalogue(c,tenant)
    if policy.configuration is None:raise ValueError('A strategy trade profile is required for lifecycle preparation.')
    from trading.profiles.contracts import STANDARD_FIELDS,standard_input_id
    context=policy.configuration
    required={f['definitionId']:f['requirement']=='REQUIRED' for f in context['fields'] if f['definitionId'] is not None and f['requirement']!='NOT_USED'}
    definitions={r['definition_id']:dict(r,required=required[r['definition_id']]) for r in c.execute(select(m.trade_property_definition).where(
        m.trade_property_definition.c.tenant_id==tenant,m.trade_property_definition.c.definition_id.in_(required)).order_by(m.trade_property_definition.c.definition_id)).mappings()}
    standard_rules={standard_input_id(f['standardFieldKey']):f for f in context['fields'] if f['standardFieldKey'] and f['requirement']!='NOT_USED'}
    for identity,f in standard_rules.items():
        definitions[identity]=dict(definition_id=identity,label=f['label'],value_type='REFERENCE' if f['standardFieldKey']!='COMMENT' else 'TEXT',catalogue_id=None,required=f['requirement']=='REQUIRED',status='ACTIVE',standard_field_key=f['standardFieldKey'],source_key=f['sourceKey'])
    rules={r.definition_id:r.behavior for r in policy.fields}
    supplied=annotation_inputs or {}
    known=set()
    for move in movements:
        # Stable identity excludes new entry inputs and mutable display labels.
        move['movementKey']=evidence_hash(dict(subjectId=move['subjectId'],allocation=move.get('allocation',[])))
        key=move['movementKey'];known.add(key)
        fresh=[TradePropertyInput.model_validate(p) for p in supplied.get(key,[])]
        if len({p.definition_id for p in fresh})!=len(fresh):raise ValueError('Duplicate lifecycle property input')
        values={};locked=set();issues=[]
        sources=[source_annotations.get(UUID(str(t)),{}) for t in move['tradeIds']]
        for identity,behavior in rules.items():
            if behavior=='INPUT':continue
            candidates=[s.get(identity) for s in sources]
            defined=[v for v in candidates if v is not None]
            identities={v.identity() for v in defined}
            if behavior=='ALLOCATION':locked.add(identity)
            if len(identities)==1 and len(defined)==len(candidates) and defined:
                # Equivalent reference record revisions share allocation identity;
                # prefer a still-active sourced revision, never invent a new one.
                chosen=sorted(defined,key=lambda v:str(v.value))[0]
                if chosen.record_id:
                    versions=[UUID(str(v.value)) for v in defined]
                    active=c.scalar(select(m.reference_catalogue_record.c.record_version_id).where(
                        m.reference_catalogue_record.c.record_version_id.in_(versions),m.reference_catalogue_record.c.status=='ACTIVE')
                        .order_by(m.reference_catalogue_record.c.version_no.desc()).limit(1))
                    if active:chosen=AnnotationValue(str(active),chosen.record_id)
                values[identity]=chosen.value
            elif behavior=='ALLOCATION' and defined:
                issues.append('Allocation source values disagree; reconcile original bookings.')
            elif behavior=='INHERIT' and len(identities)>1:
                # A non-allocation metadata disagreement can be resolved explicitly.
                pass
        for p in fresh:
            if p.definition_id in locked:
                if p.definition_id not in values or values[p.definition_id]!=p.value:
                    raise ValueError('Inherited allocation fields are read-only; reconcile source classifications')
            else:values[p.definition_id]=p.value
        properties=[dict(definitionId=str(k),value=v) for k,v in sorted(values.items(),key=lambda p:str(p[0])) if k not in standard_rules]
        standard_inputs={standard_rules[k]['standardFieldKey']:v for k,v in values.items() if k in standard_rules}
        try:
            validated=validate_trade_annotations(c,tenant,annotation_request(properties,context['strategyId'],standard_inputs),configuration=context,operation='LIFECYCLE_PREPARE',source_trade_ids=move['tradeIds'])
            move['sourcePreservation']=validated.source_preservation
        except ValueError as error:issues.append(str(error))
        reference_values=[UUID(str(v)) for identity,v in values.items() if definitions.get(identity,{}).get('value_type')=='REFERENCE' and isinstance(v,str) and len(v)==36]
        labels={str(r.record_version_id):r.label for r in c.execute(select(m.reference_catalogue_record.c.record_version_id,m.reference_catalogue_record.c.label)
            .join(m.reference_catalogue,m.reference_catalogue.c.catalogue_id==m.reference_catalogue_record.c.catalogue_id)
            .where(m.reference_catalogue.c.tenant_id==tenant,m.reference_catalogue_record.c.record_version_id.in_(reference_values)))}
        organisation_ids=[UUID(str(v)) for k,v in standard_inputs.items() if k in {'COUNTERPARTY','EXECUTING_BROKER'}]
        labels.update({str(r.organisation_id):r.display_name for r in c.execute(select(m.organisation.c.organisation_id,m.organisation.c.display_name).where(m.organisation.c.organisation_id.in_(organisation_ids)))})
        if standard_inputs.get('TRADER'):
            labels.update({str(r.person_id):r.display_name for r in c.execute(select(m.person.c.person_id,m.person.c.display_name).where(m.person.c.person_id==UUID(str(standard_inputs['TRADER']))))})
        move['properties']=properties;move['standardInputs']=standard_inputs;move['profileConfiguration']=context;move['annotationIssues']=issues
        move['annotationFields']=[dict(definitionId=str(d['definition_id']),label=d['label'],valueType=d['value_type'],
            catalogueId=str(d['catalogue_id']) if d['catalogue_id'] else None,sourceKey=d.get('source_key'),standardFieldKey=d.get('standard_field_key'),required=d['required'],
            behavior=rules.get(d['definition_id'],'INPUT'),locked=d['definition_id'] in locked,
            value=values.get(d['definition_id']),displayValue=labels.get(str(values.get(d['definition_id']))) if d['value_type']=='REFERENCE' else None) for d in definitions.values() if d['status']=='ACTIVE' or d['definition_id'] in values]
    if set(supplied)-known:raise ValueError('Lifecycle property inputs refer to a changed or unknown allocation')
    return dict(allocationPolicy=policy.payload(),annotationStatus='NEEDS_INFORMATION' if any(m['annotationIssues'] for m in movements) else 'READY')


def require_annotations(data):
    if data.get('annotationStatus')!='READY':raise ValueError('Required lifecycle booking information is missing or invalid; review the allocation inputs')


def persist_annotations(c,tenant,trade_id,move):
    request=annotation_request(move['properties'],UUID(str(move['profileConfiguration']['strategyId'])),move.get('standardInputs'))
    values=validate_trade_annotations(c,tenant,request,configuration=move['profileConfiguration'],operation='LIFECYCLE_BOOK',source_trade_ids=move['tradeIds'])
    if values.source_preservation!=move.get('sourcePreservation'):
        raise ValueError('Lifecycle source inheritance changed; prepare the allocation again.')
    persist_trade_annotations(c,tenant,trade_id,request,values)


def source_annotations_hash(annotations):
    return evidence_hash({str(t):{str(d):asdict(value) for d,value in values.items()} for t,values in annotations.items()})


def reference_options(c,tenant,actor,strategy,catalogue,q='',offset=0,limit=26):
    """Read only published values bound to an active tenant booking field."""
    from security_master_schema.strategy_access import require_strategy_action
    from sqlalchemy import func
    require_strategy_action(c,tenant,actor,'LIFECYCLE_READ',strategy)
    cat=m.reference_catalogue;definitions=m.trade_property_definition;record=m.reference_catalogue_record
    bound=select(definitions.c.definition_id).where(definitions.c.tenant_id==tenant,definitions.c.status=='ACTIVE',
        definitions.c.catalogue_id==catalogue).exists()
    if c.scalar(select(cat.c.catalogue_id).where(cat.c.catalogue_id==catalogue,cat.c.tenant_id==tenant,cat.c.status=='ACTIVE',bound)) is None:
        raise LookupError('Published lifecycle field catalogue unavailable')
    query=select(record).where(record.c.catalogue_id==catalogue,record.c.status=='ACTIVE')
    if q:query=query.where(func.lower(record.c.code+' '+record.c.label).contains(q.lower(),autoescape=True))
    rows=c.execute(query.order_by(record.c.code,record.c.record_version_id).offset(offset).limit(limit)).mappings()
    return dict(items=[dict(recordVersionId=r['record_version_id'],recordId=r['record_id'],code=r['code'],label=r['label'],
        description=r['description'],versionNo=r['version_no'],status=r['status']) for r in rows])


def lifecycle_profile_values(move):
    from trading.profiles.resolution import proof_values
    return proof_values(move['profileConfiguration'])|dict(trader_person_id=UUID(str(move['standardInputs']['TRADER'])) if move.get('standardInputs',{}).get('TRADER') else None)
