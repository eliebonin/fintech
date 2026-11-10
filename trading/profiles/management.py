"""Profile register queries and explicit default/adoption commands.

The caller owns commit and request audit. Publication never adopts a version.
"""
from sqlalchemy import select,func,or_
from security_master_schema import models as m
from security_master_schema.booking_controls import authorize_booking,lock_booking_strategy
from security_master_schema.strategy_access import strategy_predicate
from tenant_reference.catalogues import audit
from tenant_reference.errors import ConfigurationConflict
from .configuration import _configure,_profile,_version,current_assignment,assign_profile
from .impact import allocation_impact
from .resolution import resolve_trade_configuration


def _page(c,statement,offset,limit):
    if offset<0 or not 1<=limit<=100:
        raise ValueError('Invalid page. Use 1–100 rows and a nonnegative offset.')
    return dict(items=[dict(r) for r in c.execute(statement.offset(offset).limit(limit)).mappings()],
                total=c.scalar(select(func.count()).select_from(statement.order_by(None).subquery())),offset=offset,limit=limit)


def list_versions(c,tenant,actor,profile_id,offset=0,limit=25):
    authorize_booking(c,tenant,actor,action='TRADE_CONFIGURE')
    _profile(c,tenant,profile_id)
    v=m.trade_profile_version
    return _page(c,select(v.c.version_id.label('versionId'),v.c.version_no.label('versionNo'),v.c.label,
        v.c.description,v.c.reason,v.c.recorded_at.label('publishedAt')).where(v.c.tenant_id==tenant,
        v.c.profile_id==profile_id).order_by(v.c.version_no.desc()),offset,limit)


def _default_data(c,tenant):
    t=m.tenant_trade_profile_default
    row=c.execute(select(t).where(t.c.tenant_id==tenant).order_by(t.c.revision.desc()).limit(1)).mappings().first()
    if row is None:return dict(profileVersionId=None,revision=0)
    version=_version(c,tenant,row['profile_version_id'])
    return dict(profileVersionId=row['profile_version_id'],revision=row['revision'],profileId=version['profile_id'],
                label=version['label'],versionNo=version['version_no'],reason=row['reason'])


def default_profile(c,tenant,actor):
    authorize_booking(c,tenant,actor,action='TRADE_CONFIGURE')
    return _default_data(c,tenant)


def creation_default(c,tenant,actor):
    authorize_booking(c,tenant,actor,action='STRATEGY_CREATE')
    return _default_data(c,tenant)


def set_default(c,tenant,actor,version_id,expected_revision,reason):
    _configure(c,tenant,actor)
    version=_version(c,tenant,version_id)
    if _profile(c,tenant,version['profile_id'])['status']!='ACTIVE':raise ValueError('This profile is retired.')
    before=default_profile(c,tenant,actor)
    if before['revision']!=expected_revision:
        if before['revision']==expected_revision+1 and before['profileVersionId']==version_id:return before
        raise ConfigurationConflict('The tenant default changed. Reload before applying.')
    audit(c,tenant,actor,'TRADE_PROFILE_DEFAULT_CHANGED',version['profile_id'],reason,
          dict(versionId=str(version_id),previousRevision=expected_revision,revision=expected_revision+1))
    c.execute(m.tenant_trade_profile_default.insert().values(tenant_id=tenant,revision=expected_revision+1,
        profile_version_id=version_id,actor_id=actor,reason=reason.strip()))
    return default_profile(c,tenant,actor)


def strategy_configuration(c,tenant,actor,strategy_id):
    result=resolve_trade_configuration(c,tenant,strategy_id,actor,'STRATEGY_READ')
    from security_master_schema.tenant_workspace import resolve_tenant_workspace
    from security_master_schema.governance_clock import governance_date
    workspace=resolve_tenant_workspace(c,tenant,actor,governance_date())
    result['canAssign']='TRADE_CONFIGURE' in workspace.permission_codes and c.scalar(select(m.strategy.c.strategy_id).where(m.strategy.c.tenant_id==tenant,m.strategy.c.strategy_id==strategy_id,strategy_predicate(c,tenant,actor,'STRATEGY_WRITE',m.strategy.c.strategy_id))) is not None
    return result


def preview_assignment(c,tenant,actor,strategy_id,version_id):
    _configure(c,tenant,actor)
    authorize_booking(c,tenant,actor,action='STRATEGY_WRITE',strategy_id=strategy_id)
    lock_booking_strategy(c,tenant,strategy_id)
    _version(c,tenant,version_id)
    prior=current_assignment(c,tenant,strategy_id)
    return {**allocation_impact(c,tenant,strategy_id,version_id),'assignmentRevision':prior['revision'] if prior else 0}


def adopt_assignment(c,tenant,actor,strategy_id,version_id,expected_revision,input_hash,reason):
    # Same lock and complete population as preview; no trust in client counts.
    preview=preview_assignment(c,tenant,actor,strategy_id,version_id)
    current=current_assignment(c,tenant,strategy_id)
    if current and current['revision']==expected_revision+1 and current['profile_version_id']==version_id:
        return assign_profile(c,tenant,actor,strategy_id,version_id,expected_revision,reason)
    if preview['assignmentRevision']!=expected_revision or preview['inputHash']!=input_hash:
        raise ConfigurationConflict('Profile, assignment or source bookings changed. Review a fresh preview.')
    return assign_profile(c,tenant,actor,strategy_id,version_id,expected_revision,reason)


def profile_usage(c,tenant,actor,profile_id,query='',offset=0,limit=25):
    authorize_booking(c,tenant,actor,action='TRADE_CONFIGURE')
    _profile(c,tenant,profile_id)
    a,v,s=m.strategy_trade_profile_assignment,m.trade_profile_version,m.strategy
    current=select(a.c.strategy_id,func.max(a.c.revision).label('revision')).where(a.c.tenant_id==tenant).group_by(a.c.strategy_id).subquery()
    statement=(select(s.c.strategy_id.label('strategyId'),s.c.strategy_code.label('strategyCode'),s.c.display_name.label('label'),
        a.c.revision,v.c.version_id.label('versionId'),v.c.version_no.label('versionNo'))
        .join(a,a.c.strategy_id==s.c.strategy_id).join(current,(current.c.strategy_id==a.c.strategy_id)&(current.c.revision==a.c.revision))
        .join(v,v.c.version_id==a.c.profile_version_id).where(s.c.tenant_id==tenant,v.c.profile_id==profile_id,
        strategy_predicate(c,tenant,actor,'STRATEGY_READ',s.c.strategy_id)))
    if query:statement=statement.where(or_(s.c.strategy_code.icontains(query,autoescape=True),s.c.display_name.icontains(query,autoescape=True)))
    return _page(c,statement.order_by(s.c.strategy_code),offset,limit)


def profile_history(c,tenant,actor,profile_id,offset=0,limit=25):
    authorize_booking(c,tenant,actor,action='TRADE_CONFIGURE')
    _profile(c,tenant,profile_id)
    t=m.trade_configuration_event
    return _page(c,select(t.c.action,t.c.reason,t.c.actor_id.label('actorId'),t.c.recorded_at_utc.label('recordedAt'),t.c.payload)
        .where(t.c.tenant_id==tenant,t.c.subject_id==profile_id).order_by(t.c.recorded_at_utc.desc()),offset,limit)


def retire_profile(c,tenant,actor,profile_id,reason):
    _configure(c,tenant,actor)
    profile=_profile(c,tenant,profile_id)
    if profile['status']=='RETIRED':return dict(profileId=profile_id,status='RETIRED')
    a,v=m.strategy_trade_profile_assignment,m.trade_profile_version
    current=select(a.c.strategy_id,func.max(a.c.revision).label('revision')).where(a.c.tenant_id==tenant).group_by(a.c.strategy_id).subquery()
    used=c.scalar(select(a.c.strategy_id).join(current,(current.c.strategy_id==a.c.strategy_id)&(current.c.revision==a.c.revision))
        .join(v,v.c.version_id==a.c.profile_version_id).where(a.c.tenant_id==tenant,v.c.profile_id==profile_id).limit(1))
    default=default_profile(c,tenant,actor)
    if used is not None or default.get('profileId')==profile_id:
        raise ConfigurationConflict('Reassign strategies and the tenant default before retiring this profile.')
    audit(c,tenant,actor,'TRADE_PROFILE_RETIRED',profile_id,reason)
    c.execute(m.trade_profile.update().where(m.trade_profile.c.tenant_id==tenant,m.trade_profile.c.profile_id==profile_id).values(status='RETIRED'))
    return dict(profileId=profile_id,status='RETIRED')


def field_library(c,tenant,actor,query='',offset=0,limit=25,history=False):
    authorize_booking(c,tenant,actor,action='TRADE_CONFIGURE')
    f=m.trade_property_definition
    statement=select(f.c.definition_id.label('definitionId'),f.c.code,f.c.label,f.c.description,
        f.c.version_no.label('versionNo'),f.c.value_type.label('valueType'),f.c.catalogue_id.label('catalogueId'),f.c.status).where(f.c.tenant_id==tenant)
    if not history:statement=statement.where(f.c.status=='ACTIVE',f.c.value_type!='CHOICE')
    if query:statement=statement.where(or_(f.c.code.icontains(query,autoescape=True),f.c.label.icontains(query,autoescape=True)))
    return _page(c,statement.order_by(f.c.label,f.c.code,f.c.version_no.desc()),offset,limit)


def assignment_targets(c,tenant,actor,query='',offset=0,limit=25):
    authorize_booking(c,tenant,actor,action='TRADE_CONFIGURE')
    s=m.strategy
    statement=select(s.c.strategy_id.label('strategyId'),s.c.strategy_code.label('code'),s.c.display_name.label('label')).where(s.c.tenant_id==tenant,s.c.status=='ACTIVE',strategy_predicate(c,tenant,actor,'STRATEGY_WRITE',s.c.strategy_id))
    if query:statement=statement.where(or_(s.c.strategy_code.icontains(query,autoescape=True),s.c.display_name.icontains(query,autoescape=True)))
    return _page(c,statement.order_by(s.c.strategy_code,s.c.strategy_id),offset,limit)


def _batch_targets(c,tenant,actor,strategies,version):
    _configure(c,tenant,actor)
    if not strategies or len(strategies)!=len(set(strategies)):raise ValueError('Select distinct strategies explicitly.')
    s=m.strategy
    visible=c.execute(select(s.c.strategy_id,s.c.display_name).where(s.c.tenant_id==tenant,s.c.status=='ACTIVE',s.c.strategy_id.in_(strategies),strategy_predicate(c,tenant,actor,'STRATEGY_WRITE',s.c.strategy_id))).all()
    if len(visible)!=len(strategies):raise PermissionError('The complete selected population requires current strategy-write access.')
    v=_version(c,tenant,version)
    if _profile(c,tenant,v['profile_id'])['status']!='ACTIVE':raise ValueError('This profile is retired.')
    for strategy in sorted(strategies,key=str):lock_booking_strategy(c,tenant,strategy)
    return dict(visible)


def preview_assignments(c,tenant,actor,strategies,version):
    labels=_batch_targets(c,tenant,actor,strategies,version)
    cache={};items=[]
    for strategy in sorted(strategies,key=str):
        prior=current_assignment(c,tenant,strategy)
        result=allocation_impact(c,tenant,strategy,version,policy_cache=cache)
        before=cache.get(('version',str(prior['profile_version_id'])),(None,None))[0] if prior else None
        items.append({**result,'label':labels[strategy],'assignmentRevision':prior['revision'] if prior else 0,
            'previousProfileLabel':before['profileLabel'] if before else None,'previousVersionNo':before['versionNo'] if before else None})
    return dict(items=items,allowed=all(row['allowed'] for row in items),profileVersionId=version)


def adopt_assignments(c,tenant,actor,version,assignments,reason):
    strategies=[row['strategyId'] for row in assignments]
    with c.begin_nested():
        _batch_targets(c,tenant,actor,strategies,version)
        current={strategy:current_assignment(c,tenant,strategy) for strategy in strategies}
        cache={};pending=[];results=[]
        for row in assignments:
            strategy=row['strategyId'];prior=current[strategy]
            if prior and prior['revision']==row['expectedRevision']+1 and prior['profile_version_id']==version:
                results.append(dict(strategyId=strategy,profileVersionId=version,revision=prior['revision']));continue
            impact=allocation_impact(c,tenant,strategy,version,policy_cache=cache)
            if (prior['revision'] if prior else 0)!=row['expectedRevision'] or impact['inputHash']!=row['inputHash']:
                raise ConfigurationConflict('A selected assignment or its booking sources changed. Review the whole selection again.')
            if not impact['allowed']:raise ConfigurationConflict('A selected strategy requires allocation reconciliation. '+' '.join(impact['issues']))
            pending.append(strategy)
        from .configuration import _append_assignment
        for strategy in pending:results.append(_append_assignment(c,tenant,actor,strategy,version,current[strategy],reason))
        return dict(items=results,profileVersionId=version)
