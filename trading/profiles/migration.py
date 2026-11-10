"""Trusted maintenance cutover; never exposed as a tenant request command.

Copies existing settings and records a technical migration, not a new user choice.
The caller owns the transaction and must supply a retained maintenance actor.
"""
from uuid import UUID,uuid4
from sqlalchemy import select,func
from security_master_schema import models as m
from security_master_schema.evidence import evidence_hash
from trading.annotations import lock_trade_catalogue
from tenant_reference.catalogues import audit
from .contracts import FieldRule,STANDARD_FIELDS
from .configuration import _append_assignment,current_assignment


def backfill_profiles(c,actor_id,tenant_id=None):
    if c.scalar(select(m.user_account.c.user_account_id).where(m.user_account.c.user_account_id==actor_id)) is None:raise ValueError('A recorded maintenance actor is required.')
    tenants=c.execute(select(m.tenant.c.tenant_id).where(m.tenant.c.tenant_id==tenant_id) if tenant_id else select(m.tenant.c.tenant_id).order_by(m.tenant.c.tenant_id)).scalars().all()
    created=assigned=0
    reason='Technical cutover: copied existing tenant trade configuration; no business rules changed.'
    for tenant in tenants:
        lock_trade_catalogue(c,tenant)
        default=c.execute(select(m.tenant_trade_profile_default).where(m.tenant_trade_profile_default.c.tenant_id==tenant).order_by(m.tenant_trade_profile_default.c.revision.desc()).limit(1)).mappings().first()
        if default:version_id=default['profile_version_id']
        else:
            definitions=c.execute(select(m.trade_property_definition).where(m.trade_property_definition.c.tenant_id==tenant)).mappings().all()
            by_id={r['definition_id']:r for r in definitions}
            active={r['code']:r for r in definitions if r['status']=='ACTIVE' and r['value_type']!='CHOICE'}
            if any(r['status']=='ACTIVE' and r['value_type']=='CHOICE' and r['required'] for r in definitions):raise ValueError('Required legacy dropdown needs remediation before profile cutover.')
            policy=c.execute(select(m.lifecycle_allocation_policy.c.fields).where(m.lifecycle_allocation_policy.c.tenant_id==tenant).order_by(m.lifecycle_allocation_policy.c.revision.desc()).limit(1)).scalar_one_or_none() or []
            behaviors={}
            for item in policy:
                original=by_id.get(UUID(item['definitionId']))
                if original is None:raise ValueError('Allocation policy has no tenant-owned source definition.')
                current=active.get(original['code'])
                if current is not None and current['definition_id']!=original['definition_id']:raise ValueError('Reconcile allocation definition versions before profile cutover.')
                active[original['code']]=original;behaviors[original['code']]=item['behavior']
            rules=[FieldRule(standardFieldKey=key) for key in STANDARD_FIELDS]
            rules.extend(FieldRule(propertyCode=r['code'],propertyVersion=r['version_no'],requirement='REQUIRED' if r['required'] else 'OPTIONAL',lifecycleBehavior=behaviors.get(r['code'],'INPUT')) for r in active.values())
            normalized=sorted([r.model_dump(by_alias=True) for r in rules],key=lambda r:r['standardFieldKey'] or 'CUSTOM:'+r['propertyCode'])
            profile_id,version_id=uuid4(),uuid4()
            if c.scalar(select(m.trade_profile.c.profile_id).where(m.trade_profile.c.tenant_id==tenant,m.trade_profile.c.code=='STANDARD')):raise ValueError('STANDARD profile already exists without a default; inspect before cutover.')
            c.execute(m.trade_profile.insert().values(profile_id=profile_id,tenant_id=tenant,code='STANDARD',created_by=actor_id))
            label='Standard trade configuration'
            c.execute(m.trade_profile_version.insert().values(version_id=version_id,tenant_id=tenant,profile_id=profile_id,version_no=1,label=label,reason=reason,content_hash=evidence_hash(dict(label=label,description=None,fields=normalized)),field_count=len(normalized),published_by=actor_id))
            if normalized:c.execute(m.trade_profile_field_rule.insert(),[dict(rule_id=uuid4(),tenant_id=tenant,profile_version_id=version_id,standard_field_key=r['standardFieldKey'],property_code=r['propertyCode'],property_version=r['propertyVersion'],requirement=r['requirement'],lifecycle_behavior=r['lifecycleBehavior']) for r in normalized])
            c.execute(m.tenant_trade_profile_default.insert().values(tenant_id=tenant,revision=1,profile_version_id=version_id,actor_id=actor_id,reason=reason))
            audit(c,tenant,actor_id,'TRADE_PROFILE_CUTOVER',profile_id,reason,dict(versionId=str(version_id),fieldCount=len(normalized)))
            created+=1
        existing=select(m.strategy_trade_profile_assignment.c.strategy_id).where(m.strategy_trade_profile_assignment.c.tenant_id==tenant)
        strategies=c.execute(select(m.strategy.c.strategy_id).where(m.strategy.c.tenant_id==tenant,~m.strategy.c.strategy_id.in_(existing)).order_by(m.strategy.c.strategy_id)).scalars().all()
        if strategies:
            from .impact import require_safe_allocation_change
            for strategy in strategies:require_safe_allocation_change(c,tenant,strategy,version_id)
            rows=[dict(tenant_id=tenant,strategy_id=s,revision=1,previous_revision=None,profile_version_id=version_id,actor_id=actor_id,reason=reason) for s in strategies]
            for start in range(0,len(rows),500):c.execute(m.strategy_trade_profile_assignment.insert(),rows[start:start+500])
            audit(c,tenant,actor_id,'STRATEGY_PROFILE_CUTOVER',None,reason,dict(strategyCount=len(rows),versionId=str(version_id)))
            assigned+=len(rows)
    return dict(createdTenants=created,assignedStrategies=assigned)


def initialize_strategy_profile(c,tenant,actor,strategy):
    """Called only inside authorized native strategy creation, never as a fallback read."""
    lock_trade_catalogue(c,tenant)
    if c.scalar(select(m.strategy.c.strategy_id).where(m.strategy.c.tenant_id==tenant,m.strategy.c.strategy_id==strategy)) is None:raise ValueError('Strategy is outside this tenant.')
    if current_assignment(c,tenant,strategy):raise ValueError('The strategy already has an explicit profile assignment.')
    default=c.execute(select(m.tenant_trade_profile_default.c.profile_version_id).where(m.tenant_trade_profile_default.c.tenant_id==tenant).order_by(m.tenant_trade_profile_default.c.revision.desc()).limit(1)).scalar_one_or_none()
    if default is None:raise ValueError('Configure the tenant default trade profile before creating a strategy.')
    return _append_assignment(c,tenant,actor,strategy,default,None,'Inherited the explicit tenant default at strategy creation.')
