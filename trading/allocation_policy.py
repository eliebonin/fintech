"""Governed, versioned lifecycle field selection; no product pricing rules."""
from collections import defaultdict
from decimal import Decimal,localcontext
from uuid import UUID
from sqlalchemy import select
from security_master_schema import models as m
from security_master_schema.allocation_contracts import AllocationPolicy,FieldRule
from .annotations import lock_trade_catalogue
from .annotation_snapshots import load_trade_annotations


def load_allocation_policy(connection,tenant_id,strategy_id=None):
    if strategy_id is not None:
        from .profiles.resolution import load_assigned_configuration
        return allocation_policy_from_context(connection,tenant_id,load_assigned_configuration(connection,tenant_id,strategy_id))
    t=m.lifecycle_allocation_policy
    row=connection.execute(select(t).where(t.c.tenant_id==tenant_id).order_by(t.c.revision.desc()).limit(1)).mappings().one_or_none()
    if row is None:return AllocationPolicy()
    return AllocationPolicy(row['revision'],tuple(FieldRule(UUID(f['definitionId']),f['behavior']) for f in row['fields']))


def policy_view(connection,tenant_id,actor_id):
    from security_master_schema.booking_controls import authorize_booking
    authorize_booking(connection,tenant_id,actor_id,action='TRADE_CONFIGURE')
    return load_allocation_policy(connection,tenant_id).payload()


def _check_closed_history(connection,tenant_id,policy):
    # An activation may expose allocations hidden by a historical unclassified
    # closure. Report the conflict instead of silently rewriting that history.
    from positions.allocations import allocation_signature
    t=m.trade;s=m.strategy
    matured=select(t.c.reference_instrument_node_id).join(s,s.c.strategy_id==t.c.strategy_id).where(
        s.c.tenant_id==tenant_id,t.c.trade_type.in_(['MATURITY_CLOSE','MATURITY_REDEMPTION']),t.c.lifecycle_status=='BOOKED')
    rows=connection.execute(select(t).join(s,s.c.strategy_id==t.c.strategy_id).where(s.c.tenant_id==tenant_id,
        t.c.reference_instrument_node_id.in_(matured),t.c.lifecycle_status=='BOOKED')).mappings().all()
    annotations=load_trade_annotations(connection,tenant_id,[r['trade_id'] for r in rows])
    amounts=defaultdict(lambda:defaultdict(Decimal))
    with localcontext() as ctx:
        ctx.prec=512
        for r in rows:
            key=(r['strategy_id'],r['trade_subject_reference_node_id'],r['price_currency_id'],r['quantity_unit'],r['price_basis'])
            amounts[key][allocation_signature(policy,annotations.get(r['trade_id'],{}))]+=r['quantity']
    with localcontext() as ctx:
        ctx.prec=512
        conflicts=sum(1 for groups in amounts.values() if sum(groups.values(),Decimal(0))==0 and any(groups.values()))
    if conflicts:raise ValueError(f'Allocation activation requires reconciliation of {conflicts} historically closed position scopes; no history was changed.')


def configure_policy(connection,tenant_id,actor_id,fields,expected_revision,reason):
    from security_master_schema.booking_controls import authorize_booking
    authorize_booking(connection,tenant_id,actor_id,action='TRADE_CONFIGURE')
    if not isinstance(reason,str) or not reason.strip() or len(reason)>2000:raise ValueError('A change reason is required')
    lock_trade_catalogue(connection,tenant_id)
    if connection.scalar(select(m.tenant_trade_profile_default.c.revision).where(m.tenant_trade_profile_default.c.tenant_id==tenant_id).limit(1)) is not None:
        raise ValueError('Lifecycle allocation rules now belong to published trade profiles. Existing history is read-only.')
    old=load_allocation_policy(connection,tenant_id)
    if old.revision!=expected_revision:raise ValueError('Allocation policy changed; reload')
    proposed=AllocationPolicy(expected_revision+1,tuple(FieldRule(UUID(str(f['definitionId'])),f['behavior']) for f in fields))
    identifiers=[r.definition_id for r in proposed.fields]
    definitions={d['definition_id']:d for d in connection.execute(select(m.trade_property_definition).where(
        m.trade_property_definition.c.tenant_id==tenant_id,m.trade_property_definition.c.definition_id.in_(identifiers))).mappings()}
    previous={r.definition_id:r.behavior for r in old.fields}
    if any(r.definition_id not in definitions or definitions[r.definition_id]['status']!='ACTIVE' and previous.get(r.definition_id)!=r.behavior for r in proposed.fields):
        raise ValueError('An allocation field is unavailable in this tenant')
    if {r.definition_id for r in old.fields if r.behavior=='ALLOCATION'}!={r.definition_id for r in proposed.fields if r.behavior=='ALLOCATION'}:
        _check_closed_history(connection,tenant_id,proposed)
    connection.execute(m.lifecycle_allocation_policy.insert().values(tenant_id=tenant_id,revision=proposed.revision,
        fields=proposed.payload()['fields'],reason=reason.strip(),actor_id=actor_id))
    return proposed.payload()


def allocation_policy_from_context(connection,tenant_id,context):
    from .profiles.contracts import standard_input_id
    rules=[]
    f=m.trade_property_definition
    codes=[field['propertyCode'] for field in context['fields'] if field['propertyCode']]
    definitions=connection.execute(select(f).where(f.c.tenant_id==tenant_id,f.c.code.in_(codes))).mappings().all()
    for field in context['fields']:
        if field['requirement']=='NOT_USED':continue
        if field['standardFieldKey']:
            rules.append(FieldRule(standard_input_id(field['standardFieldKey']),field['lifecycleBehavior'],field['fieldKey'],(),field['standardFieldKey']))
        else:
            pinned=next(d for d in definitions if d['definition_id']==field['definitionId'])
            family=[d for d in definitions if d['code']==pinned['code']]
            compatible=[d for d in family if d['value_type']==pinned['value_type'] and d['catalogue_id']==pinned['catalogue_id']]
            # Earlier installations could replace an ordinary input with another
            # type/source. Do not alias that history into the current meaning.
            # Allocation/inheritance still require an unambiguous whole family.
            if len(compatible)!=len(family) and field['lifecycleBehavior']!='INPUT':
                raise ValueError('Field meaning/type/source changed across versions; reconcile this allocation family.')
            family=compatible
            rules.append(FieldRule(pinned['definition_id'],field['lifecycleBehavior'],field['fieldKey'],tuple(d['definition_id'] for d in family)))
    return AllocationPolicy(context['assignmentRevision'],tuple(rules),context)
