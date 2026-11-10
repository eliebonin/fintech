"""Audited profile publication and explicit pinned strategy assignments."""
from uuid import uuid4
from sqlalchemy import select,func,or_
from security_master_schema import models as m
from security_master_schema.booking_controls import authorize_booking,lock_booking_strategy
from security_master_schema.strategy_access import strategy_predicate
from security_master_schema.evidence import evidence_hash
from tenant_reference.catalogues import audit,text_values
from tenant_reference.errors import ConfigurationConflict
from trading.annotations import lock_trade_catalogue
from .contracts import ProfileVersionInput,STANDARD_FIELDS


def _configure(c,tenant,actor):
    authorize_booking(c,tenant,actor,action='TRADE_CONFIGURE');lock_trade_catalogue(c,tenant)


def _profile(c,tenant,identity):
    row=c.execute(select(m.trade_profile).where(m.trade_profile.c.tenant_id==tenant,m.trade_profile.c.profile_id==identity)).mappings().first()
    if row is None:raise LookupError('Trade profile not found in this tenant.')
    return row


def create_profile(c,tenant,actor,code,label,reason):
    _configure(c,tenant,actor)
    values=text_values(dict(code=code,label=label));p=m.trade_profile
    prior=c.execute(select(p).where(p.c.tenant_id==tenant,p.c.code==values['code'])).mappings().first()
    if prior:return dict(profileId=prior['profile_id'],code=prior['code'],status=prior['status'])
    identity=uuid4()
    audit(c,tenant,actor,'TRADE_PROFILE_CREATED',identity,reason,{'label':label,'code':values['code']})
    c.execute(p.insert().values(profile_id=identity,tenant_id=tenant,code=values['code'],created_by=actor))
    return dict(profileId=identity,code=values['code'],status='ACTIVE')


def _version(c,tenant,version_id):
    row=c.execute(select(m.trade_profile_version).where(m.trade_profile_version.c.tenant_id==tenant,m.trade_profile_version.c.version_id==version_id)).mappings().first()
    if row is None:raise LookupError('Profile version not found in this tenant.')
    return row


def version_rules(c,tenant,version_id):
    t=m.trade_profile_field_rule
    return [dict(standardFieldKey=r['standard_field_key'],propertyCode=r['property_code'],propertyVersion=r['property_version'],requirement=r['requirement'],lifecycleBehavior=r['lifecycle_behavior']) for r in c.execute(select(t).where(t.c.tenant_id==tenant,t.c.profile_version_id==version_id).order_by(t.c.standard_field_key.nulls_last(),t.c.property_code)).mappings()]


def profile_version(c,tenant,actor,version_id):
    authorize_booking(c,tenant,actor,action='TRADE_CONFIGURE')
    r=_version(c,tenant,version_id)
    rules=version_rules(c,tenant,version_id)
    definitions={(row['code'],row['version_no']):row['label'] for row in c.execute(select(m.trade_property_definition).where(m.trade_property_definition.c.tenant_id==tenant,m.trade_property_definition.c.code.in_([rule['propertyCode'] for rule in rules if rule['propertyCode']]))).mappings()}
    labels={('STANDARD:'+rule['standardFieldKey'] if rule['standardFieldKey'] else 'CUSTOM:'+rule['propertyCode']):(STANDARD_FIELDS[rule['standardFieldKey']]['label'] if rule['standardFieldKey'] else definitions[(rule['propertyCode'],rule['propertyVersion'])]) for rule in rules}
    return dict(versionId=r['version_id'],profileId=r['profile_id'],profileStatus=_profile(c,tenant,r['profile_id'])['status'],versionNo=r['version_no'],label=r['label'],description=r['description'],reason=r['reason'],contentHash=r['content_hash'],fields=rules,fieldLabels=labels,publishedAt=r['recorded_at'])


def publish_profile_version(c,tenant,actor,profile_id,values):
    _configure(c,tenant,actor);profile=_profile(c,tenant,profile_id)
    if profile['status']!='ACTIVE':raise ValueError('This profile is retired.')
    payload=ProfileVersionInput.model_validate(values)
    normalized=sorted([r.model_dump(by_alias=True) for r in payload.fields],key=lambda r:r['standardFieldKey'] or 'CUSTOM:'+r['propertyCode'])
    fingerprint=evidence_hash(dict(label=payload.label,description=payload.description,fields=normalized))
    v=m.trade_profile_version
    latest=c.execute(select(v).where(v.c.tenant_id==tenant,v.c.profile_id==profile_id).order_by(v.c.version_no.desc()).limit(1)).mappings().first()
    current=latest['version_no'] if latest else 0
    if current!=payload.expected_version:
        if current==payload.expected_version+1 and latest['content_hash']==fingerprint:return profile_version(c,tenant,actor,latest['version_id'])
        raise ConfigurationConflict('Profile changed. Reload before publishing a version.')
    f=m.trade_property_definition
    definitions={(r['code'],r['version_no']):r for r in c.execute(select(f).where(f.c.tenant_id==tenant,f.c.code.in_([r.property_code for r in payload.fields if r.property_code]))).mappings()}
    for rule in payload.fields:
        if not rule.property_code:continue
        definition=definitions.get((rule.property_code,rule.property_version))
        if definition is None:raise ValueError('A selected custom definition does not exist in this tenant.')
        if rule.requirement=='NOT_USED':continue
        from .resolution import definition_available
        if not definition_available(definition,definitions.values()) or definition['value_type']=='CHOICE':raise ValueError('A selected definition is not available for new profile versions.')
        if definition['catalogue_id'] is not None:
            cat=c.execute(select(m.reference_catalogue).where(m.reference_catalogue.c.tenant_id==tenant,m.reference_catalogue.c.catalogue_id==definition['catalogue_id'],m.reference_catalogue.c.status=='ACTIVE')).first()
            if cat is None:raise ValueError('A selected field catalogue is not published in this tenant.')
            if rule.requirement=='REQUIRED' and c.scalar(select(m.reference_catalogue_record.c.record_version_id).where(m.reference_catalogue_record.c.catalogue_id==definition['catalogue_id'],m.reference_catalogue_record.c.status=='ACTIVE').limit(1)) is None:raise ValueError('A required dropdown needs at least one eligible published catalogue entry.')
    identity=uuid4()
    with c.begin_nested():
        c.execute(v.insert().values(version_id=identity,tenant_id=tenant,profile_id=profile_id,version_no=current+1,label=payload.label,description=payload.description,reason=payload.reason,content_hash=fingerprint,field_count=len(normalized),published_by=actor))
        if normalized:c.execute(m.trade_profile_field_rule.insert(),[dict(rule_id=uuid4(),tenant_id=tenant,profile_version_id=identity,standard_field_key=r['standardFieldKey'],property_code=r['propertyCode'],property_version=r['propertyVersion'],requirement=r['requirement'],lifecycle_behavior=r['lifecycleBehavior']) for r in normalized])
        audit(c,tenant,actor,'TRADE_PROFILE_PUBLISHED',profile_id,payload.reason,dict(versionId=str(identity),versionNo=current+1,contentHash=fingerprint))
    return profile_version(c,tenant,actor,identity)


def current_assignment(c,tenant,strategy):
    t=m.strategy_trade_profile_assignment
    return c.execute(select(t).where(t.c.tenant_id==tenant,t.c.strategy_id==strategy).order_by(t.c.revision.desc()).limit(1)).mappings().first()


def _append_assignment(c,tenant,actor,strategy,version,previous,reason):
    if not reason.strip() or len(reason)>2000:raise ValueError('A change reason of at most 2000 characters is required.')
    revision=(previous['revision'] if previous else 0)+1
    c.execute(m.strategy_trade_profile_assignment.insert().values(tenant_id=tenant,strategy_id=strategy,revision=revision,previous_revision=previous['revision'] if previous else None,profile_version_id=version,actor_id=actor,reason=reason.strip()))
    audit(c,tenant,actor,'STRATEGY_PROFILE_ASSIGNED',strategy,reason,dict(versionId=str(version),revision=revision))
    return dict(strategyId=strategy,profileVersionId=version,revision=revision)


def assign_profile(c,tenant,actor,strategy_id,version_id,expected_revision,reason):
    _configure(c,tenant,actor)
    authorize_booking(c,tenant,actor,action='STRATEGY_WRITE',strategy_id=strategy_id)
    lock_booking_strategy(c,tenant,strategy_id)
    version=_version(c,tenant,version_id);profile=_profile(c,tenant,version['profile_id'])
    if profile['status']!='ACTIVE':raise ValueError('This profile is retired.')
    previous=current_assignment(c,tenant,strategy_id)
    revision=previous['revision'] if previous else 0
    if revision!=expected_revision:
        if revision==expected_revision+1 and previous['profile_version_id']==version_id:return dict(strategyId=strategy_id,profileVersionId=version_id,revision=revision)
        raise ConfigurationConflict('Strategy profile assignment changed. Reload before applying.')
    from .impact import require_safe_allocation_change
    require_safe_allocation_change(c,tenant,strategy_id,version_id)
    return _append_assignment(c,tenant,actor,strategy_id,version_id,previous,reason)


def list_profiles(c,tenant,actor,query='',offset=0,limit=25):
    authorize_booking(c,tenant,actor,action='TRADE_CONFIGURE')
    if offset<0 or not 1<=limit<=100:raise ValueError('Invalid profile page.')
    p,v=m.trade_profile,m.trade_profile_version
    latest=select(v.c.profile_id,func.max(v.c.version_no).label('version_no')).where(v.c.tenant_id==tenant).group_by(v.c.profile_id).subquery()
    statement=select(p.c.profile_id.label('profileId'),p.c.code,p.c.status,v.c.version_id.label('versionId'),v.c.version_no.label('versionNo'),func.coalesce(v.c.label,p.c.code).label('label')).outerjoin(latest,latest.c.profile_id==p.c.profile_id).outerjoin(v,(v.c.profile_id==p.c.profile_id)&(v.c.version_no==latest.c.version_no)).where(p.c.tenant_id==tenant)
    if query:statement=statement.where(or_(func.lower(p.c.code).contains(query.lower(),autoescape=True),func.lower(v.c.label).contains(query.lower(),autoescape=True)))
    return dict(items=[dict(r) for r in c.execute(statement.order_by(p.c.code).offset(offset).limit(limit)).mappings()],total=c.scalar(select(func.count()).select_from(statement.subquery())),offset=offset,limit=limit)
