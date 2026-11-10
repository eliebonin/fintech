"""Paged typed reference sources shared by maintenance and scoped consumers."""
from uuid import UUID
from sqlalchemy import select,func,literal,union_all,String,cast,or_
from security_master_schema import models as m
from security_master_schema.booking_controls import authorize_booking
from security_master_schema.governance_clock import governance_date
from trading.annotations import restrict_selection

ROLES={'COUNTERPARTY':'Counterparties','EXECUTING_BROKER':'Executing brokers','TRADER':'Traders'}


def _page(statement,c,offset,limit):
    if offset<0 or not 1<=limit<=100:raise ValueError('Use a page size between 1 and 100 and a non-negative offset.')
    return dict(items=[dict(r) for r in c.execute(statement.offset(offset).limit(limit)).mappings()],
                total=c.scalar(select(func.count()).select_from(statement.order_by(None).subquery())),offset=offset,limit=limit)


def trader_statement(tenant_id,curated=True):
    p,a,t=m.person,m.user_account,m.tenant_user_account
    day=governance_date()
    statement=select(p.c.person_id.label('id'),p.c.display_name.label('label')).select_from(p.join(a,a.c.person_id==p.c.person_id).join(t,t.c.user_account_id==a.c.user_account_id)).where(
        p.c.status=='ACTIVE',a.c.status=='ACTIVE',t.c.tenant_id==tenant_id,t.c.status=='ACTIVE',t.c.valid_from<=day,or_(t.c.valid_to.is_(None),t.c.valid_to>=day)).distinct()
    return statement


def _role_statement(c,tenant,role):
    if role not in ROLES:raise ValueError('Unknown standard reference source.')
    statement=trader_statement(tenant) if role=='TRADER' else select(m.organisation.c.organisation_id.label('id'),m.organisation.c.display_name.label('label')).where(m.organisation.c.status=='ACTIVE')
    identity=m.person.c.person_id if role=='TRADER' else m.organisation.c.organisation_id
    return restrict_selection(c,tenant,role,statement,identity)


def _catalogue(c,tenant,key):
    if not key.startswith('catalogue:'):raise ValueError('Unknown reference source.')
    try:identifier=UUID(key.removeprefix('catalogue:'))
    except (ValueError,TypeError):raise ValueError('Unknown reference source.') from None
    row=c.execute(select(m.reference_catalogue).where(m.reference_catalogue.c.tenant_id==tenant,m.reference_catalogue.c.catalogue_id==identifier)).mappings().first()
    if row is None:raise LookupError('Reference source not found in this tenant.')
    return row


def source_detail(c,tenant_id,actor_id,source_key):
    authorize_booking(c,tenant_id,actor_id,action='TRADE_CONFIGURE')
    if source_key.startswith('standard:'):
        role=source_key.removeprefix('standard:')
        if role not in ROLES:raise ValueError('Unknown standard reference source.')
        return dict(sourceKey=source_key,kind='CANONICAL',code=role,label=ROLES[role],status='ACTIVE',description='Canonical tenant-eligible identities; maintained in their native workspace.')
    row=_catalogue(c,tenant_id,source_key)
    from .catalogues import catalogue_view
    return {**catalogue_view(row),'sourceKey':source_key,'kind':'CUSTOM'}


def list_sources(connection,tenant_id,actor_id,query='',offset=0,limit=25):
    authorize_booking(connection,tenant_id,actor_id,action='TRADE_CONFIGURE')
    cat,rec,field=m.reference_catalogue,m.reference_catalogue_record,m.trade_property_definition
    entries=select(rec.c.catalogue_id,func.count().label('n')).where(rec.c.status=='ACTIVE').group_by(rec.c.catalogue_id).subquery()
    uses=select(field.c.catalogue_id,func.count().label('n')).where(field.c.tenant_id==tenant_id,field.c.status=='ACTIVE').group_by(field.c.catalogue_id).subquery()
    statements=[select((literal('catalogue:')+cast(cat.c.catalogue_id,String)).label('sourceKey'),literal('CUSTOM').label('kind'),cat.c.code,cat.c.label,cat.c.status,
        func.coalesce(entries.c.n,0).label('activeEntryCount'),func.coalesce(uses.c.n,0).label('fieldCount')).outerjoin(entries,entries.c.catalogue_id==cat.c.catalogue_id).outerjoin(uses,uses.c.catalogue_id==cat.c.catalogue_id).where(cat.c.tenant_id==tenant_id)]
    for role,label in ROLES.items():
        count=select(func.count()).select_from(_role_statement(connection,tenant_id,role).subquery()).scalar_subquery()
        statements.append(select(literal('standard:'+role),literal('CANONICAL'),literal(role),literal(label),literal('ACTIVE'),count,literal(1)))
    all_sources=union_all(*statements).subquery()
    statement=select(all_sources)
    if query:statement=statement.where(or_(func.lower(all_sources.c.label).contains(query.lower(),autoescape=True),func.lower(all_sources.c.code).contains(query.lower(),autoescape=True)))
    return _page(statement.order_by(all_sources.c.label,all_sources.c.sourceKey),connection,offset,limit)


def list_source_options(connection,tenant_id,actor_id,source_key,*,consumer_context=None,query='',offset=0,limit=25,selected_ids=()):
    if consumer_context is None:authorize_booking(connection,tenant_id,actor_id,action='TRADE_CONFIGURE')
    else:
        action,strategy=consumer_context
        if action not in {'TRADE_READ','TRADE_WRITE','LIFECYCLE_READ'} or strategy is None:raise ValueError('A scoped reference consumer is required.')
        authorize_booking(connection,tenant_id,actor_id,action=action,strategy_id=strategy)
    if len(selected_ids)>20:raise ValueError('Select at most 20 retained values.')
    if source_key.startswith('standard:'):
        base=_role_statement(connection,tenant_id,source_key.removeprefix('standard:')).subquery()
    else:
        cat=_catalogue(connection,tenant_id,source_key)
        if cat['status']!='ACTIVE':raise ValueError('Reference source is not published.')
        rec=m.reference_catalogue_record
        base=select(rec.c.record_version_id.label('id'),rec.c.label,rec.c.record_id.label('recordId'),rec.c.code,rec.c.version_no.label('versionNo')).where(rec.c.catalogue_id==cat['catalogue_id'],rec.c.status=='ACTIVE').subquery()
    statement=select(base)
    if query:statement=statement.where(func.lower(base.c.label).contains(query.lower(),autoescape=True))
    result=_page(statement.order_by(base.c.label,base.c.id),connection,offset,limit)
    result['selected']=[dict(r) for r in connection.execute(select(base).where(base.c.id.in_(selected_ids))).mappings()] if selected_ids else []
    return result


def source_entries(c,tenant_id,actor_id,source_key,*,query='',offset=0,limit=25,history=False):
    authorize_booking(c,tenant_id,actor_id,action='TRADE_CONFIGURE')
    cat=_catalogue(c,tenant_id,source_key);r=m.reference_catalogue_record
    statement=select(r.c.record_version_id.label('recordVersionId'),r.c.record_id.label('recordId'),r.c.code,r.c.label,r.c.description,r.c.version_no.label('versionNo'),r.c.status).where(r.c.catalogue_id==cat['catalogue_id'])
    if not history:statement=statement.where(r.c.status=='ACTIVE')
    if query:statement=statement.where(or_(func.lower(r.c.label).contains(query.lower(),autoescape=True),func.lower(r.c.code).contains(query.lower(),autoescape=True)))
    return _page(statement.order_by(r.c.code,r.c.version_no.desc(),r.c.record_version_id),c,offset,limit)


def source_usage(c,tenant_id,actor_id,source_key,*,query='',offset=0,limit=25):
    """Definitions, pinned profile versions and readable current strategies."""
    from sqlalchemy import literal,union_all
    from security_master_schema.strategy_access import strategy_predicate
    authorize_booking(c,tenant_id,actor_id,action='TRADE_CONFIGURE')
    cat=_catalogue(c,tenant_id,source_key)
    f,p,v,r,a,s=m.trade_property_definition,m.trade_profile,m.trade_profile_version,m.trade_profile_field_rule,m.strategy_trade_profile_assignment,m.strategy
    definitions=select(literal('FIELD').label('kind'),f.c.definition_id.label('identity'),f.c.definition_id.label('definitionId'),f.c.code,f.c.label,f.c.version_no.label('versionNo'),f.c.status).where(f.c.tenant_id==tenant_id,f.c.catalogue_id==cat['catalogue_id'])
    source_versions=select(r.c.profile_version_id).join(f,(f.c.tenant_id==r.c.tenant_id)&(f.c.code==r.c.property_code)&(f.c.version_no==r.c.property_version)).where(r.c.tenant_id==tenant_id,f.c.catalogue_id==cat['catalogue_id'],r.c.requirement!='NOT_USED')
    profiles=select(literal('PROFILE'),v.c.version_id,v.c.version_id,p.c.code,v.c.label,v.c.version_no,p.c.status).join(p,p.c.profile_id==v.c.profile_id).where(v.c.tenant_id==tenant_id,v.c.version_id.in_(source_versions))
    current=select(a.c.strategy_id,func.max(a.c.revision).label('revision')).where(a.c.tenant_id==tenant_id).group_by(a.c.strategy_id).subquery()
    strategies=(select(literal('STRATEGY'),s.c.strategy_id,s.c.strategy_id,s.c.strategy_code,s.c.display_name,v.c.version_no,s.c.status)
        .join(a,a.c.strategy_id==s.c.strategy_id).join(current,(current.c.strategy_id==a.c.strategy_id)&(current.c.revision==a.c.revision))
        .join(v,v.c.version_id==a.c.profile_version_id).where(s.c.tenant_id==tenant_id,a.c.profile_version_id.in_(source_versions),strategy_predicate(c,tenant_id,actor_id,'STRATEGY_READ',s.c.strategy_id)))
    all_usage=union_all(definitions,profiles,strategies).subquery()
    statement=select(all_usage)
    if query:statement=statement.where(or_(all_usage.c.label.icontains(query,autoescape=True),all_usage.c.code.icontains(query,autoescape=True)))
    return _page(statement.order_by(all_usage.c.kind,all_usage.c.label,all_usage.c.versionNo.desc(),all_usage.c.identity),c,offset,limit)


def source_history(c,tenant_id,actor_id,source_key,*,query='',offset=0,limit=25):
    authorize_booking(c,tenant_id,actor_id,action='TRADE_CONFIGURE')
    cat=_catalogue(c,tenant_id,source_key);event=m.trade_configuration_event;r=m.reference_catalogue_record
    statement=select(event.c.event_id.label('eventId'),event.c.action,event.c.subject_id.label('subjectId'),event.c.reason,event.c.recorded_at_utc.label('recordedAtUtc')).where(event.c.tenant_id==tenant_id,or_(event.c.subject_id==cat['catalogue_id'],event.c.subject_id.in_(select(r.c.record_id).where(r.c.catalogue_id==cat['catalogue_id'])),event.c.subject_id.in_(select(r.c.record_version_id).where(r.c.catalogue_id==cat['catalogue_id']))))
    if query:statement=statement.where(func.lower(event.c.reason).contains(query.lower(),autoescape=True))
    return _page(statement.order_by(event.c.recorded_at_utc.desc(),event.c.event_id),c,offset,limit)
