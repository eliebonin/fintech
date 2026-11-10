"""Exact metadata-impact checks; no tax lots, price changes or reclassification."""
from collections import defaultdict
from decimal import Decimal,localcontext
from sqlalchemy import select
from security_master_schema import models as m
from security_master_schema.evidence import evidence_hash
from tenant_reference.errors import ConfigurationConflict


def allocation_impact(c,tenant,strategy,new_version_id,*,policy_cache=None):
    from .configuration import current_assignment
    from .resolution import load_assigned_configuration,load_version_configuration
    from trading.allocation_policy import load_allocation_policy,allocation_policy_from_context
    from trading.annotation_snapshots import load_trade_annotations
    from positions.allocations import allocation_signature
    prior=current_assignment(c,tenant,strategy)
    from dataclasses import replace
    cache={} if policy_cache is None else policy_cache
    def bound_policy(version,revision):
        cache_key=('version',str(version))
        if cache_key not in cache:
            context=load_version_configuration(c,tenant,strategy,version,revision)
            cache[cache_key]=(context,allocation_policy_from_context(c,tenant,context))
        base,policy=cache[cache_key]
        from .configuration import _version
        hash_key=('content',str(version))
        if hash_key not in cache:cache[hash_key]=_version(c,tenant,version)['content_hash']
        context={**base,'strategyId':strategy,'assignmentRevision':revision,
            'configurationHash':evidence_hash(dict(profileVersionId=str(version),assignmentRevision=revision,profileContentHash=cache[hash_key]))}
        return context,replace(policy,revision=revision,configuration=context)
    new_context,new_policy=bound_policy(new_version_id,(prior['revision'] if prior else 0)+1)
    if prior:
        _,old_policy=bound_policy(prior['profile_version_id'],prior['revision'])
    else:
        if 'legacy' not in cache:
            legacy=load_allocation_policy(c,tenant)
            definitions={r['definition_id']:r['code'] for r in c.execute(select(m.trade_property_definition).where(m.trade_property_definition.c.tenant_id==tenant)).mappings()}
            cache['legacy']=replace(legacy,fields=tuple(replace(rule,field_key='CUSTOM:'+definitions[rule.definition_id]) for rule in legacy.fields))
        old_policy=cache['legacy']
    old_dims={r.field_key or str(r.definition_id):r for r in old_policy.fields if r.behavior=='ALLOCATION'}
    new_dims={r.field_key or str(r.definition_id):r for r in new_policy.fields if r.behavior=='ALLOCATION'}
    # Existing write/cancel commands own lifecycle_status. Consider all retained
    # live bookings, including future recognition, before changing their closure basis.
    t=m.trade;s=m.strategy
    rows=c.execute(select(t).join(s,s.c.strategy_id==t.c.strategy_id).where(s.c.tenant_id==tenant,t.c.strategy_id==strategy,t.c.lifecycle_status=='BOOKED',t.c.trade_type.in_(['INVESTMENT','TRANSFER','REINVESTMENT','MATURITY_CLOSE','MATURITY_REDEMPTION'])).order_by(t.c.trade_id)).mappings().all()
    new_annotations=load_trade_annotations(c,tenant,[r['trade_id'] for r in rows],new_policy)
    old_annotations=load_trade_annotations(c,tenant,[r['trade_id'] for r in rows],old_policy)
    native_keys={}
    if rows and set(old_dims)!=set(new_dims):
        from datetime import datetime,time,timezone
        from positions.contracts import ProjectionRequest,PositionError
        from positions.repository import iter_ledger_facts
        from positions.equity import booking_key
        from sqlalchemy import func
        cutoff=datetime.combine(max((r['valuation_effective_date'] or r['trade_datetime_utc'].date()) for r in rows),time.max,timezone.utc)
        request=ProjectionRequest(tenant,strategy,cutoff,c.scalar(select(func.clock_timestamp())))
        try:
            for fact in iter_ledger_facts(c,request):
                if fact.booking:native_keys[fact.trade_id]=booking_key(fact.booking,tenant,strategy)
        except PositionError as exc:
            raise ConfigurationConflict('Allocation changes require assessable frozen booking conventions; reconcile unsupported source evidence first.') from exc
        if any(row['trade_id'] not in native_keys for row in rows):
            raise ConfigurationConflict('Allocation changes require complete source booking evidence; reconcile the unassessed history first.')
    old_groups=defaultdict(lambda:defaultdict(Decimal));new_groups=defaultdict(lambda:defaultdict(Decimal));matured_scopes=set()
    with localcontext() as context:
        context.prec=512
        for row in rows:
            scope=native_keys.get(row['trade_id']) or (str(row['trade_subject_reference_node_id']),str(row['price_currency_id']),row['quantity_unit'],row['price_basis'])
            if row['trade_type'] in {'MATURITY_CLOSE','MATURITY_REDEMPTION'}:matured_scopes.add(scope)
            old_groups[scope][allocation_signature(old_policy,old_annotations.get(row['trade_id'],{}))]+=row['quantity']
            new_groups[scope][allocation_signature(new_policy,new_annotations.get(row['trade_id'],{}))]+=row['quantity']
        removed=set(old_dims)-set(new_dims)
        affected=sum(1 for groups in old_groups.values() for signature,quantity in groups.items() if quantity and any(key in removed and value!='null' for key,value in signature))
        reopened={scope for scope,groups in new_groups.items() if sum(groups.values(),Decimal(0))==0 and any(groups.values())}
        old_reopened={scope for scope,groups in old_groups.items() if sum(groups.values(),Decimal(0))==0 and any(groups.values())}
        required={f['fieldKey'] for f in new_context['fields'] if f['requirement']=='REQUIRED' and f['lifecycleBehavior']=='ALLOCATION'}
        missing=sum(1 for groups in new_groups.values() for signature,quantity in groups.items() if quantity and any(key in required and value=='null' for key,value in signature))
    issues=[]
    if affected:issues.append(f'{affected} open allocation scope(s) would lose classified dimensions; reconcile first.')
    if (reopened-old_reopened)&matured_scopes:issues.append('New allocation rules would expose historically closed but unreconciled allocations.')
    if missing:issues.append(f'{missing} open allocation scope(s) lack required source classifications; reconcile first.')
    proof=dict(strategyId=str(strategy),profileVersionId=str(new_version_id),assignmentRevision=prior['revision'] if prior else 0,
        rows=[dict(tradeId=str(r['trade_id']),quantity=str(r['quantity'])) for r in rows],oldPolicy=old_policy.payload(),newPolicy=new_policy.payload(),
        annotations={str(trade):{str(key):value.identity() for key,value in values.items()} for trade,values in new_annotations.items()})
    return dict(strategyId=strategy,allowed=not issues,issues=issues,affectedTradeCount=len(rows),inputHash=evidence_hash(proof))


def require_safe_allocation_change(c,tenant,strategy,version):
    impact=allocation_impact(c,tenant,strategy,version)
    if not impact['allowed']:raise ConfigurationConflict('Profile allocation change requires reconciliation. '+' '.join(impact['issues']))
    return impact
