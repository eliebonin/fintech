"""Transactional preparation, reasoned review and frozen manual export."""
from datetime import datetime,timezone
from uuid import uuid4
import hashlib
from sqlalchemy import select,func,text
from security_master_schema import models as m
from security_master_schema.strategy_access import require_strategy_action,strategy_predicate
from security_master_schema.tenant_workspace import resolve_tenant_workspace,require_tenant_action
from security_master_schema.governance_clock import governance_date
from security_master_schema.command_audit import current_command
from security_master_schema.reference_visibility import visible_clause
from . import tables as t
from .assessment import assess,fingerprint,preparation_csv
from .source import executions,canonical

class Conflict(ValueError):pass

def authority(c,tenant,actor,action,strategy=None):
    require_tenant_action(resolve_tenant_workspace(c,tenant,actor,governance_date()),action)
    if strategy is not None:require_strategy_action(c,tenant,actor,action,strategy)

def _profile(c,tenant,identity,lock=False):
    q=select(t.profile).where(t.profile.c.tenant_id==tenant,t.profile.c.profile_id==identity)
    if lock:q=q.with_for_update(read=True)
    row=c.execute(q).mappings().one_or_none()
    if row is None:raise LookupError('Reporting entity was not found')
    return dict(row)

def profiles(c,tenant,actor):
    authority(c,tenant,actor,'REPORTING_READ')
    return [dict(profileId=str(r.profile_id),name=r.name,lei=r.lei,firmCategory=r.firm_category,
        firmScope=r.firm_scope,revision=r.revision,reason=r.reason)
        for r in c.execute(select(t.profile).where(t.profile.c.tenant_id==tenant).order_by(t.profile.c.name))]

def save_profile(c,tenant,actor,data,identity=None):
    authority(c,tenant,actor,'REPORTING_CONFIGURE')
    old=None
    if identity:
        old=c.execute(select(t.profile).where(t.profile.c.tenant_id==tenant,t.profile.c.profile_id==identity).with_for_update()).mappings().one_or_none()
        if old is None:raise LookupError('Reporting entity was not found')
        if old['revision']!=data.expectedRevision:raise Conflict('Reporting entity changed. Reload before saving.')
    elif data.expectedRevision is not None:raise ValueError('A new profile cannot have an expected revision')
    identity=identity or uuid4();revision=old['revision']+1 if old else 1
    values=dict(tenant_id=tenant,name=data.name,lei=data.lei,firm_category=data.firmCategory,
        firm_scope=data.firmScope,reason=data.reason,revision=revision,actor_id=actor,recorded_at=datetime.now(timezone.utc))
    if old:c.execute(t.profile.update().where(t.profile.c.profile_id==identity).values(**values))
    else:c.execute(t.profile.insert().values(profile_id=identity,**values))
    c.execute(t.profile_revision.insert().values(profile_id=identity,revision=revision,tenant_id=tenant,
        actor_id=actor,payload=canonical(values)))
    return dict(profileId=str(identity),revision=revision)

def _scope_lock(c,tenant,profile,strategy):
    c.execute(text('SELECT pg_advisory_xact_lock(hashtextextended(:key,0))'),
        {'key':f'regulatory:{tenant}:{profile}:{strategy}'})

def _hash(source,profile):
    return fingerprint(dict(source=source['source'],profileRevision=profile['revision'],
        product=source['facts']['instrumentType'],visible=source['facts']['referenceVisible']))

def _write(c,tenant,actor,values,old=None):
    identity=old['candidate_id'] if old else uuid4();revision=old['revision']+1 if old else 1
    if old:values={k:old[k] for k in ('strategy_id','trade_id','profile_id','execution_date')}|values
    values=values|dict(revision=revision,actor_id=actor,recorded_at=datetime.now(timezone.utc))
    if old:c.execute(t.candidate.update().where(t.candidate.c.candidate_id==identity).values(**values))
    else:c.execute(t.candidate.insert().values(candidate_id=identity,tenant_id=tenant,**values))
    snapshot=canonical(values|dict(candidate_id=identity,tenant_id=tenant))
    c.execute(t.candidate_revision.insert().values(candidate_id=identity,revision=revision,tenant_id=tenant,
        actor_id=actor,payload=snapshot))
    return _view(snapshot)

def _view(row):
    p=row['payload']
    return dict(candidateId=str(row['candidate_id']),tradeId=str(row['trade_id']),strategyId=str(row['strategy_id']),
        profileId=str(row['profile_id']),revision=row['revision'],executionDate=str(row['execution_date']),
        facts=p['facts'],mapping=p['mapping'],reason=p['reason'],action=p['action'],
        needsReassessment=p.get('needsReassessment',False),**p['assessment'])

def _values(profile,source,*,mapping=None,decision=None,disposition='AUTO',reason,action,changed=False):
    facts=source['facts'];mapping=mapping or {}
    assessment=assess(facts,firm_scope=profile['firm_scope'],mapping=mapping,decision=decision,
        disposition=disposition,needs_reassessment=changed)
    cmd=current_command()
    payload=dict(facts=facts,source=source['source'],profile=canonical(profile),mapping=mapping,
        decision=decision,disposition=disposition,assessment=assessment,reason=reason,action=action,
        needsReassessment=changed,operatorId=str(cmd.operator) if cmd else None)
    return dict(source_hash=_hash(source,profile),payload=payload,
        **{k:assessment[k] for k in ('reportability','readiness','disposition','included')})

def prepare(c,tenant,actor,data):
    authority(c,tenant,actor,'REPORTING_PREPARE',data.strategyId)
    profile=_profile(c,tenant,data.profileId,True);_scope_lock(c,tenant,data.profileId,data.strategyId)
    sources=executions(c,tenant,data.strategyId,data.fromDate,data.toDate,lock=True)
    existing={r['trade_id']:dict(r) for r in c.execute(select(t.candidate).where(
        t.candidate.c.tenant_id==tenant,t.candidate.c.profile_id==data.profileId,
        t.candidate.c.strategy_id==data.strategyId,t.candidate.c.execution_date>=data.fromDate,
        t.candidate.c.execution_date<=data.toDate)).mappings()}
    created=changed=0
    for identity,source in sources.items():
        old=existing.get(identity)
        if old and old['source_hash']==_hash(source,profile):continue
        prior=old['payload'] if old else {}
        values=_values(profile,source,mapping=prior.get('mapping'),decision=prior.get('decision'),
            disposition=prior.get('disposition','AUTO'),changed=bool(old),action='PREPARED',
            reason='Source changed; retained human choices require reassessment.' if old else 'Generated from execution evidence; instrument scope needs assessment.')
        _write(c,tenant,actor,values|dict(strategy_id=data.strategyId,trade_id=identity,profile_id=data.profileId,
            execution_date=datetime.fromisoformat(source['facts']['executionTime']).date()),old)
        if old:changed+=1
        else:created+=1
    return dict(created=created,changed=changed,examined=len(sources),validationLevel='PREPARATION_ONLY')

def _base(tenant,actor,c,data,action='REPORTING_READ'):
    authority(c,tenant,actor,action,data.strategyId)
    _profile(c,tenant,data.profileId)
    return select(t.candidate).where(t.candidate.c.tenant_id==tenant,t.candidate.c.profile_id==data.profileId,
        t.candidate.c.strategy_id==data.strategyId,t.candidate.c.execution_date>=data.fromDate,
        t.candidate.c.execution_date<=data.toDate,_visible_trade(t.candidate.c.trade_id,tenant))

def _visible_trade(identity,tenant):
    trade=m.trade.alias('report_visible_trade');listing=m.listing.alias('report_visible_listing')
    return select(trade.c.trade_id).outerjoin(listing,listing.c.listing_node_id==trade.c.trade_subject_reference_node_id).where(
        trade.c.trade_id==identity,visible_clause(trade.c.trade_subject_reference_node_id,tenant),
        visible_clause(func.coalesce(listing.c.instrument_node_id,trade.c.trade_subject_reference_node_id),tenant)).exists()

def _totals(c,query):
    rows=query.subquery()
    counts=c.execute(select(func.count().label('total'),func.count().filter(rows.c.included).label('included'),
        func.count().filter(rows.c.disposition=='HOLD').label('held'),
        func.count().filter((rows.c.reportability=='NOT_REPORTABLE')&(rows.c.disposition!='HOLD')).label('notReportable'),
        func.count().filter((rows.c.reportability!='NOT_REPORTABLE')&(~rows.c.included)&(rows.c.disposition!='HOLD')).label('attention'))).mappings().one()
    return dict(counts)

def candidates(c,tenant,actor,data,*,status='ALL',limit=25,offset=0):
    query=_base(tenant,actor,c,data);totals=_totals(c,query)
    filters={'ALL':None,'READY':t.candidate.c.included,'HELD':t.candidate.c.disposition=='HOLD',
        'NOT_REPORTABLE':t.candidate.c.reportability=='NOT_REPORTABLE',
        'NEEDS_ATTENTION':(t.candidate.c.reportability!='NOT_REPORTABLE')&(~t.candidate.c.included)&(t.candidate.c.disposition!='HOLD')}
    if status not in filters:raise ValueError('Unknown reporting status filter')
    if filters[status] is not None:query=query.where(filters[status])
    total=c.scalar(select(func.count()).select_from(query.subquery()))
    rows=c.execute(query.order_by(t.candidate.c.execution_date,t.candidate.c.candidate_id).limit(limit).offset(offset)).mappings()
    return dict(items=[_view(r) for r in rows],total=total,totals=totals,limit=limit,offset=offset)

def _candidate(c,tenant,actor,identity,action):
    row=c.execute(select(t.candidate).where(t.candidate.c.tenant_id==tenant,t.candidate.c.candidate_id==identity)).mappings().one_or_none()
    if row is None:raise LookupError('Report candidate was not found')
    authority(c,tenant,actor,action,row['strategy_id'])
    if not c.scalar(select(_visible_trade(row['trade_id'],tenant))):raise PermissionError('Current reference access is required to inspect this report')
    return dict(row)

def detail(c,tenant,actor,identity):
    row=_candidate(c,tenant,actor,identity,'REPORTING_READ')
    history=[r['payload']['payload'] for r in c.execute(select(t.candidate_revision).where(
        t.candidate_revision.c.tenant_id==tenant,t.candidate_revision.c.candidate_id==identity)
        .order_by(t.candidate_revision.c.revision)).mappings()]
    return _view(row)|dict(history=history)

def review(c,tenant,actor,identity,data):
    old=_candidate(c,tenant,actor,identity,'REPORTING_REVIEW')
    profile=_profile(c,tenant,old['profile_id'],True);_scope_lock(c,tenant,old['profile_id'],old['strategy_id'])
    old=dict(c.execute(select(t.candidate).where(t.candidate.c.candidate_id==identity).with_for_update()).mappings().one())
    if old['revision']!=data.expectedRevision:raise Conflict('Report changed. Reload before reviewing.')
    source=executions(c,tenant,old['strategy_id'],old['execution_date'],old['execution_date'],lock=True,trade_id=old['trade_id']).get(old['trade_id'])
    if source is None or old['source_hash']!=_hash(source,profile):raise Conflict('Execution or profile changed. Prepare this period again before reviewing.')
    p=old['payload'];decision=p.get('decision');disposition=p['disposition']
    mapping=p['mapping']|(data.mapping.model_dump(exclude_unset=True) if data.mapping else {})
    if data.action in {'REPORTABLE','NOT_REPORTABLE'}:decision=data.action;disposition='AUTO'
    elif data.action=='HOLD':disposition='HOLD'
    elif data.action=='AUTOMATIC':decision=None;disposition='AUTO'
    values=_values(profile,source,mapping=mapping,decision=decision,disposition=disposition,reason=data.reason,action=data.action)
    return _write(c,tenant,actor,values,old)

def export_preview(c,tenant,actor,data):
    query=_base(tenant,actor,c,data,'REPORTING_EXPORT')
    return dict(totals=_totals(c,query),expectedRevisions={str(r.candidate_id):r.revision
        for r in c.execute(query.where(t.candidate.c.included))},validationLevel='PREPARATION_ONLY')

def create_export(c,tenant,actor,data,key):
    authority(c,tenant,actor,'REPORTING_EXPORT',data.strategyId)
    request_hash=fingerprint(data.model_dump(mode='json'))
    c.execute(text('SELECT pg_advisory_xact_lock(hashtextextended(:key,0))'),{'key':f'regulatory-export:{tenant}:{key}'})
    prior=c.execute(select(t.export).where(t.export.c.tenant_id==tenant,t.export.c.request_key==key)).mappings().one_or_none()
    if prior:
        authority(c,tenant,actor,'REPORTING_EXPORT',prior['strategy_id'])
        if prior['request_hash']!=request_hash:raise Conflict('Export key already belongs to a different request')
        return download(c,tenant,actor,prior['export_id'])
    profile=_profile(c,tenant,data.profileId,True);_scope_lock(c,tenant,data.profileId,data.strategyId)
    query=_base(tenant,actor,c,data,'REPORTING_EXPORT');rows=list(c.execute(query.order_by(t.candidate.c.candidate_id).with_for_update()).mappings())
    selected=[r for r in rows if r['included']]
    if not selected:raise Conflict('No ready, reportable, non-held candidates are available')
    if {str(r['candidate_id']):r['revision'] for r in selected}!={str(k):v for k,v in data.expectedRevisions.items()}:
        raise Conflict('Export population changed. Review the complete preview again.')
    sources=executions(c,tenant,data.strategyId,data.fromDate,data.toDate,lock=True)
    # Newly booked executions must also enter the reconciliation population.
    if set(sources)!={r['trade_id'] for r in rows}:raise Conflict('Execution population changed. Prepare this period again.')
    if any(r['source_hash']!=_hash(sources[r['trade_id']],profile) for r in rows):
        raise Conflict('Execution/profile evidence changed. Prepare and review the period again.')
    items=[_view(r) for r in selected];content=preparation_csv(items)
    manifest=dict(validationLevel='PREPARATION_ONLY',regime='UK_MIFIR_CURRENT',submissionStatus='NOT_SUBMITTED',
        profile=canonical(profile),fromDate=str(data.fromDate),toDate=str(data.toDate),totals=_totals(c,query),
        population=[dict(candidateId=str(r['candidate_id']),revision=r['revision'],reportability=r['reportability'],
            readiness=r['readiness'],disposition=r['disposition'],included=r['included']) for r in rows],
        includedItems=items,limitation='Preparation export; official schema/field applicability and submission acceptance are not validated.')
    values=dict(export_id=uuid4(),tenant_id=tenant,profile_id=data.profileId,strategy_id=data.strategyId,
        request_key=key,request_hash=request_hash,manifest=manifest,csv_content=content,
        content_hash=hashlib.sha256(content.encode()).hexdigest(),actor_id=actor)
    c.execute(t.export.insert().values(**values))
    return _export_view(values)

def _export_view(row):
    return canonical(dict(exportId=row['export_id'],manifest=row['manifest'],contentHash=row['content_hash'],
        recordedAt=row.get('recorded_at'),csvContent=row['csv_content']))

def exports(c,tenant,actor,*,limit=25,offset=0):
    authority(c,tenant,actor,'REPORTING_READ')
    query=select(t.export).where(t.export.c.tenant_id==tenant,
        strategy_predicate(c,tenant,actor,'REPORTING_READ',t.export.c.strategy_id))
    return dict(items=[dict(exportId=str(r.export_id),recordedAt=r.recorded_at,profileName=r.manifest['profile']['name'],
        fromDate=r.manifest['fromDate'],toDate=r.manifest['toDate'],totals=r.manifest['totals'])
        for r in c.execute(query.order_by(t.export.c.recorded_at.desc(),t.export.c.export_id).limit(limit).offset(offset))],
        total=c.scalar(select(func.count()).select_from(query.subquery())))

def download(c,tenant,actor,identity):
    row=c.execute(select(t.export).where(t.export.c.tenant_id==tenant,t.export.c.export_id==identity)).mappings().one_or_none()
    if row is None:raise LookupError('Export was not found')
    authority(c,tenant,actor,'REPORTING_EXPORT',row['strategy_id'])
    ids=[entry['candidateId'] for entry in row['manifest']['population']]
    visible=c.scalar(select(func.count()).select_from(t.candidate).where(t.candidate.c.tenant_id==tenant,
        t.candidate.c.candidate_id.in_(ids),_visible_trade(t.candidate.c.trade_id,tenant)))
    if visible!=len(ids):raise PermissionError('Current reference access is required for every report in this export')
    if hashlib.sha256(row['csv_content'].encode()).hexdigest()!=row['content_hash']:raise Conflict('Retained export failed its content check')
    return _export_view(row)
