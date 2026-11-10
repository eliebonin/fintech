"""Server-proven unchanged annotations on linked corrections, never a client bypass."""
from sqlalchemy import select
from security_master_schema import models as m
from security_master_schema.booking_controls import authorize_trade_action
from security_master_schema.errors import TradeFieldError
from trading.annotation_snapshots import load_trade_annotations
from trading.corrections import _original,_chain


def correction_sources(c,tenant,actor,strategy,trade_id,expected_sequence=None):
    authorize_trade_action(c,tenant,actor,trade_id,'TRADE_CORRECT')
    original=_original(c,tenant,trade_id)
    if original['strategy_id']!=strategy:raise TradeFieldError('correction','A correction must retain the original strategy.')
    if expected_sequence is not None:_chain(c,original,expected_sequence)
    values=load_trade_annotations(c,tenant,[trade_id]).get(trade_id,{})
    standard={'TRADER':original['trader_person_id'],'COMMENT':original['comment']}
    for row in c.execute(select(m.trade_party_role).where(m.trade_party_role.c.trade_id==trade_id,m.trade_party_role.c.role.in_(['COUNTERPARTY','EXECUTING_BROKER']))).mappings():
        if row['role'] in standard and standard[row['role']]!=row['organisation_id']:raise ValueError('Ambiguous original party evidence requires reconciliation.')
        standard[row['role']]=row['organisation_id']
    return values,standard


def request_sources(c,tenant,actor,request):
    correction=getattr(request,'correction',None)
    if correction is None:return {},{}
    if actor is None:raise ValueError('A verified correcting actor is required.')
    return correction_sources(c,tenant,actor,request.strategy_id,correction.trade_id,correction.expected_sequence_no)


def lifecycle_sources(c,tenant,strategy,source_ids,configuration):
    """Only exact, unanimous values from this closure's current source trades."""
    from uuid import UUID
    from trading.allocation_policy import allocation_policy_from_context
    identities=sorted({UUID(str(value)) for value in source_ids},key=str)
    if not identities:return {}
    owned=set(c.execute(select(m.trade.c.trade_id).join(m.strategy,m.strategy.c.strategy_id==m.trade.c.strategy_id).where(m.strategy.c.tenant_id==tenant,m.trade.c.strategy_id==strategy,m.trade.c.trade_id.in_(identities),m.trade.c.lifecycle_status=='BOOKED')).scalars())
    if owned!=set(identities):raise TradeFieldError('properties','Lifecycle sources must be current bookings in this strategy.')
    policy=allocation_policy_from_context(c,tenant,configuration)
    snapshots=load_trade_annotations(c,tenant,identities,policy)
    result={}
    for rule in policy.fields:
        if rule.standard_field_key or rule.behavior not in {'ALLOCATION','INHERIT'}:continue
        values=[snapshots.get(identity,{}).get(rule.definition_id) for identity in identities]
        if all(value is not None for value in values) and len({value.identity() for value in values})==1:
            result[rule.definition_id]=tuple(values)
    return result
