"""Tenant organisation register over the original, authoritative trading lists.

Profiles carry private presentation, never a second copy of role membership.
All writers share the existing catalogue lock, including old whole-list clients.
"""
from datetime import datetime, timezone
import hashlib
import json
from uuid import UUID, uuid4

from sqlalchemy import select, insert, update, delete, func, or_, exists
from security_master_schema import models as m
from security_master_schema.governance_clock import governance_date
from .trade_properties import assert_trade_configurator, lock_trade_catalogue
from .trade_configuration import ConfigurationConflict
from .governed_trade_configuration import audit

ROLES = ('COUNTERPARTY', 'EXECUTING_BROKER')

def policies(c, tenant):
    rows = dict(c.execute(select(m.trade_selection_policy.c.role, m.trade_selection_policy.c.version_no)
        .where(m.trade_selection_policy.c.tenant_id == tenant, m.trade_selection_policy.c.role.in_(ROLES))).all())
    return {r: dict(mode='CURATED' if r in rows else 'LEGACY', versionNo=rows.get(r, 0)) for r in ROLES}

def _member(tenant, role):
    member = m.trade_selection_member
    return exists(select(1).where(member.c.tenant_id == tenant, member.c.role == role,
        member.c.organisation_id == m.organisation.c.organisation_id)).correlate(m.organisation)

def _query(tenant):
    o, p, i = m.organisation, m.tenant_organisation_profile, m.organisation_identifier
    today = governance_date()
    leis = select(func.array_agg(i.c.identifier_value.distinct())).where(i.c.organisation_id == o.c.organisation_id,
        i.c.identifier_scheme == 'LEI', i.c.valid_from <= today,
        or_(i.c.valid_to.is_(None), i.c.valid_to >= today)).correlate(o).scalar_subquery()
    return select(o, p.c.label, p.c.internal_code, p.c.notes, p.c.version_no,
        leis.label('leis'), *[_member(tenant, r).label(r) for r in ROLES]).outerjoin(p,
        (p.c.organisation_id == o.c.organisation_id) & (p.c.tenant_id == tenant))

def _view(row):
    return dict(organisationId=str(row['organisation_id']), displayName=row['label'] or row['display_name'],
        legalName=row['legal_name'] or row['display_name'], status=row['status'], leis=sorted(row['leis'] or []),
        label=row['label'], internalCode=row['internal_code'], notes=row['notes'], versionNo=row['version_no'] or 0,
        roles={r: bool(row[r]) for r in ROLES})

def list_organisations(c, tenant, actor, q='', offset=0, limit=25, role=None, candidates=False):
    assert_trade_configurator(c, tenant, actor)
    if not 1 <= limit <= 100 or offset < 0 or len(q) > 250 or role not in (None, *ROLES):
        raise ValueError('Invalid organisation search or page')
    statement = _query(tenant)
    if candidates:
        statement = statement.where(m.organisation.c.status == 'ACTIVE')
    else:
        statement = statement.where(or_(m.tenant_organisation_profile.c.version_no.is_not(None),
            *[_member(tenant, r) for r in ROLES]))
    if role:
        statement = statement.where(_member(tenant, role))
    if q.strip():
        i = m.organisation_identifier
        lei_match = exists(select(1).where(i.c.organisation_id == m.organisation.c.organisation_id,
            i.c.identifier_scheme == 'LEI', i.c.identifier_value.ilike('%'+q.strip().replace('!','!!').replace('%','!%').replace('_','!_')+'%',escape='!')))
        statement = statement.where(or_(
            func.lower(m.organisation.c.display_name).contains(q.strip().lower(), autoescape=True),
            func.lower(m.organisation.c.legal_name).contains(q.strip().lower(), autoescape=True),
            func.lower(m.tenant_organisation_profile.c.label).contains(q.strip().lower(), autoescape=True),
            func.lower(m.tenant_organisation_profile.c.internal_code).contains(q.strip().lower(), autoescape=True), lei_match))
    total = c.scalar(select(func.count()).select_from(statement.subquery()))
    rows = c.execute(statement.order_by(func.lower(m.organisation.c.display_name),m.organisation.c.organisation_id)
        .offset(offset).limit(limit)).mappings()
    return dict(items=[_view(r) for r in rows], total=total, limit=limit, offset=offset, policies=policies(c,tenant))

def organisation_detail(c, tenant, actor, identifier):
    assert_trade_configurator(c, tenant, actor)
    row = c.execute(_query(tenant).where(m.organisation.c.organisation_id == identifier)).mappings().first()
    if row is None: raise LookupError('Organisation not found')
    events = c.execute(select(m.trade_configuration_event).where(
        m.trade_configuration_event.c.tenant_id == tenant, m.trade_configuration_event.c.subject_id == identifier,
        m.trade_configuration_event.c.action == 'ORGANISATION_SAVED').order_by(
        m.trade_configuration_event.c.recorded_at_utc.desc(),m.trade_configuration_event.c.event_id.desc()).limit(20)).mappings()
    return _view(row) | dict(policies=policies(c,tenant), history=[dict(eventId=str(e['event_id']),
        actorId=str(e['actor_id']), reason=e['reason'], recordedAtUtc=e['recorded_at_utc'].isoformat(),
        changes=e['payload'].get('changes',{})) for e in events])

def _intent(c, tenant, actor, identifier, data, action):
    """Authority first, then tenant-serialized exact command replay."""
    assert_trade_configurator(c, tenant, actor)
    lock_trade_catalogue(c, tenant)
    if not data.get('reason','').strip() or len(data['reason']) > 2000: raise ValueError('A reason is required (at most 2000 characters)')
    key = str(UUID(str(data['idempotencyKey'])))
    digest = hashlib.sha256(json.dumps(dict(action=action,subject=str(identifier),data=data),
        sort_keys=True,default=str,separators=(',',':')).encode()).hexdigest()
    e = m.trade_configuration_event
    previous = c.execute(select(e.c.payload).where(e.c.tenant_id==tenant,
        e.c.payload['requestKey'].astext == key)).scalar_one_or_none()
    if previous:
        if previous.get('fingerprint')!=digest or previous.get('actorId')!=str(actor):
            raise ConfigurationConflict('This request key belongs to a different command')
        return previous['result'], key, digest
    return None, key, digest

def save_organisation(c, tenant, actor, identifier, data):
    with c.begin_nested():
        replay,key,digest = _intent(c,tenant,actor,identifier,data,'ORGANISATION_SAVED')
        if replay is not None: return replay
        before = organisation_detail(c,tenant,actor,identifier)
        if before['versionNo'] != data['expectedVersion']: raise ConfigurationConflict('Organisation changed; reload before editing')
        current = before['policies']
        if data['expectedRoleVersions'] != {r:current[r]['versionNo'] for r in ROLES}:
            raise ConfigurationConflict('Role eligibility changed; reload before editing')
        if set(data['roles']) - set(ROLES): raise ValueError('Unsupported organisation role')
        for role,enabled in data['roles'].items():
            if type(enabled) is not bool: raise ValueError('Role eligibility must be true or false')
            if current[role]['mode']!='CURATED': raise ConfigurationConflict('Activate the curated list explicitly before editing its members')
            if enabled and not before['roles'][role] and before['status']!='ACTIVE': raise ValueError('Inactive organisations cannot be newly enabled')
        values={}
        for api,column,maximum in [('label','label',250),('internalCode','internal_code',100),('notes','notes',2000)]:
            value=(data.get(api) or '').strip() or None
            if value and len(value)>maximum: raise ValueError(f'{api} exceeds {maximum} characters')
            values[column]=value.upper() if api=='internalCode' and value else value
        p=m.tenant_organisation_profile
        if values['internal_code'] and c.scalar(select(p.c.organisation_id).where(p.c.tenant_id==tenant,
            p.c.internal_code==values['internal_code'],p.c.organisation_id!=identifier)):
            raise ConfigurationConflict('Internal code is already used by another organisation in this tenant')
        values.update(version_no=before['versionNo']+1, updated_by_user_account_id=actor,updated_at_utc=datetime.now(timezone.utc))
        if before['versionNo']:
            c.execute(update(p).where(p.c.tenant_id==tenant,p.c.organisation_id==identifier).values(**values))
        else:
            c.execute(insert(p).values(tenant_id=tenant,organisation_id=identifier,**values))
        member,policy=m.trade_selection_member,m.trade_selection_policy
        changes={}
        for role,enabled in data['roles'].items():
            if enabled==before['roles'][role]: continue
            predicate=(member.c.tenant_id==tenant)&(member.c.role==role)&(member.c.organisation_id==identifier)
            if enabled: c.execute(insert(member).values(tenant_id=tenant,role=role,organisation_id=identifier))
            else: c.execute(delete(member).where(predicate))
            c.execute(update(policy).where(policy.c.tenant_id==tenant,policy.c.role==role).values(
                version_no=current[role]['versionNo']+1,updated_by_user_account_id=actor,updated_at_utc=datetime.now(timezone.utc)))
            changes[role]=dict(before=before['roles'][role],after=enabled)
        # Store a bounded command result, not recursively embedded previous history.
        result=organisation_detail(c,tenant,actor,identifier)
        result['history']=[]
        audit(c,tenant,actor,'ORGANISATION_SAVED',identifier,data['reason'],dict(requestKey=key,
            fingerprint=digest,actorId=str(actor),changes=changes,metadataBefore={k:before[k] for k in ('label','internalCode','notes')},
            metadataAfter={k:result[k] for k in ('label','internalCode','notes')},result=result))
        return result

def activate_role(c, tenant, actor, role, data):
    with c.begin_nested():
        replay,key,digest=_intent(c,tenant,actor,role,data,'ORGANISATION_ROLE_ACTIVATED')
        if replay is not None:return replay
        if role not in ROLES:raise ValueError('Unsupported organisation role')
        if data['expectedVersion']!=0 or policies(c,tenant)[role]['versionNo']!=0:
            raise ConfigurationConflict('This role already has a curated list; reload before editing')
        identifiers=[UUID(str(i)) for i in data['ids']]
        if len(set(identifiers))!=len(identifiers):raise ValueError('Use distinct organisations')
        eligible=set(c.execute(select(m.organisation.c.organisation_id).where(
            m.organisation.c.organisation_id.in_(identifiers),m.organisation.c.status=='ACTIVE')).scalars())
        if eligible!=set(identifiers):raise ValueError('Select active organisations')
        c.execute(insert(m.trade_selection_policy).values(tenant_id=tenant,role=role,version_no=1,updated_by_user_account_id=actor))
        if identifiers:c.execute(insert(m.trade_selection_member),[dict(tenant_id=tenant,role=role,organisation_id=i) for i in identifiers])
        result=policies(c,tenant)
        audit(c,tenant,actor,'ORGANISATION_ROLE_ACTIVATED',None,data['reason'],dict(requestKey=key,
            fingerprint=digest,actorId=str(actor),role=role,ids=[str(i) for i in identifiers],result=result))
        return result
