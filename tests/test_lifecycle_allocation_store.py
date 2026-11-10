"""Governed policies and persisted annotations, in an owned disposable database."""
from uuid import uuid4
import pytest
from sqlalchemy import select, update
from sqlalchemy.exc import DBAPIError
from tests.test_valuation_service import valued
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids


def field(c,tenant,required=False):
    identity=uuid4()
    c.execute(m.trade_property_definition.insert().values(definition_id=identity,tenant_id=tenant,
        code='ALLOC_'+identity.hex,label='Allocation example',value_type='TEXT',required=required,
        created_by_user_account_id=ids['demo_user_account']))
    return identity


def test_policy_is_versioned_scoped_and_cannot_be_mutated(valued):
    from tests.profile_fixtures import configure_allocation as configure_policy,allocation_policy as load_allocation_policy
    c,r,_=valued;identity=field(c,r.tenant_id)
    baseline=load_allocation_policy(c,r.tenant_id,r.strategy_id).revision
    values=[dict(definitionId=str(identity),behavior='ALLOCATION')]
    configure_policy(c,r.tenant_id,ids['demo_user_account'],r.strategy_id,values,baseline,'Use allocation dimension')
    assert load_allocation_policy(c,r.tenant_id,r.strategy_id).revision==baseline+1
    with pytest.raises(ValueError,match='changed'):
        configure_policy(c,r.tenant_id,ids['demo_user_account'],r.strategy_id,values,baseline,'Stale edit')
    with pytest.raises(DBAPIError),c.begin_nested():
        c.execute(update(m.strategy_trade_profile_assignment).where(m.strategy_trade_profile_assignment.c.tenant_id==r.tenant_id,m.strategy_trade_profile_assignment.c.strategy_id==r.strategy_id).values(reason='rewritten'))
    with pytest.raises((PermissionError,ValueError)):
        configure_policy(c,r.tenant_id,uuid4(),r.strategy_id,values,baseline+1,'Unauthorised')


def test_policy_rejects_other_tenant_or_unknown_definitions(valued):
    from tests.profile_fixtures import configure_allocation as configure_policy,allocation_policy as load_allocation_policy
    c,r,_=valued
    with pytest.raises(ValueError,match='unavailable'):
        configure_policy(c,r.tenant_id,ids['demo_user_account'],r.strategy_id,[dict(definitionId=str(uuid4()),behavior='ALLOCATION')],load_allocation_policy(c,r.tenant_id,r.strategy_id).revision,'Unknown field')


def clone_execution(c,identity):
    row=dict(c.execute(select(m.trade).where(m.trade.c.trade_id==identity)).mappings().one())
    original=dict(c.execute(select(m.trade_lifecycle_event).where(m.trade_lifecycle_event.c.trade_id==identity)).mappings().one())
    other=uuid4();row['trade_id']=other
    c.execute(m.trade.insert().values(**row))
    original.update(trade_id=other,trade_lifecycle_event_id=uuid4())
    c.execute(m.trade_lifecycle_event.insert().values(**original))
    return other


def test_bond_maturity_closes_and_persists_each_allocation(valued):
    from tests.test_bond_redemption_service import setup
    from tests.profile_fixtures import configure_allocation as configure_policy,allocation_policy as load_allocation_policy
    from lifecycle import bond_service as svc
    from positions.repository import iter_ledger_facts
    from positions.reconstruction import reconstruct
    c,r,trade=valued;listing,booked,_=setup(c,r,trade)
    second=clone_execution(c,booked);dimension=field(c,r.tenant_id)
    for identity,value in [(booked,'alpha'),(second,'beta')]:
        c.execute(m.trade_property_value.insert().values(trade_id=identity,definition_id=dimension,tenant_id=r.tenant_id,value=value))
    configure_policy(c,r.tenant_id,ids['demo_user_account'],r.strategy_id,[dict(definitionId=str(dimension),behavior='ALLOCATION')],load_allocation_policy(c,r.tenant_id,r.strategy_id).revision,'Preserve allocation')
    svc.configure(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,'DIRECT',0,'Synthetic direct')
    data,fp,projection,_=svc.candidate(c,r.tenant_id,r.strategy_id,ids['bond_instrument_node'])
    assert len(data['movements'])==2
    result=svc.post(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,ids['bond_instrument_node'],fp,str(uuid4()))
    new=[__import__('uuid').UUID(t) for t in result['trade_ids']]
    assert len(new)==2
    assert set(c.scalars(select(m.trade_property_value.c.value).where(m.trade_property_value.c.trade_id.in_(new))))=={'alpha','beta'}
    assert not reconstruct(tuple(iter_ledger_facts(c,projection.request,subject_ids=[listing])),projection.request).buckets
    svc.cancel(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,__import__('uuid').UUID(result['posting_id']),'Synthetic correction',str(uuid4()))
    assert len(svc.candidate(c,r.tenant_id,r.strategy_id,ids['bond_instrument_node'])[0]['movements'])==2


def test_required_fresh_field_blocks_until_supplied_and_is_persisted(valued):
    from tests.profile_fixtures import configure_allocation as configure_policy,allocation_policy as load_allocation_policy
    from tests.test_bond_redemption_service import setup
    from lifecycle import bond_service as svc
    c,r,trade=valued;_,_,_=setup(c,r,trade);required=field(c,r.tenant_id,True)
    configure_policy(c,r.tenant_id,ids['demo_user_account'],r.strategy_id,[dict(definitionId=str(required),behavior='INPUT')],load_allocation_policy(c,r.tenant_id,r.strategy_id).revision,'Require fresh governed input')
    svc.configure(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,'DIRECT',0,'Synthetic direct')
    data,fp,_,_=svc.candidate(c,r.tenant_id,r.strategy_id,ids['bond_instrument_node'])
    assert data['annotationStatus']=='NEEDS_INFORMATION'
    with pytest.raises(ValueError,match='required|information'):
        svc.post(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,ids['bond_instrument_node'],fp,str(uuid4()))
    supplied={data['movements'][0]['movementKey']:[dict(definitionId=str(required),value='Fresh Ops input')]}
    data,fp,_,_=svc.candidate(c,r.tenant_id,r.strategy_id,ids['bond_instrument_node'],annotation_inputs=supplied)
    assert data['annotationStatus']=='READY'
    result=svc.post(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,ids['bond_instrument_node'],fp,str(uuid4()),annotation_inputs=supplied)
    assert c.scalar(select(m.trade_property_value.c.value).where(m.trade_property_value.c.trade_id==__import__('uuid').UUID(result['trade_ids'][0]),m.trade_property_value.c.definition_id==required))=='Fresh Ops input'


def test_forward_maturity_closes_and_replays_multiple_allocations(valued):
    from tests.test_fx_maturity_service import setup
    from tests.profile_fixtures import configure_allocation as configure_policy,allocation_policy as load_allocation_policy
    from lifecycle import fx_service as svc
    from positions.repository import iter_ledger_facts
    from positions.reconstruction import reconstruct
    from positions.contracts import ProjectionRequest
    c,r,_=valued;instrument,_,cut,_=setup(c,r,'BUY')
    first=c.scalar(select(m.trade.c.trade_id).where(m.trade.c.strategy_id==r.strategy_id,m.trade.c.trade_subject_reference_node_id==instrument))
    second=clone_execution(c,first);dimension=field(c,r.tenant_id)
    for identity,value in [(first,'alpha'),(second,'beta')]:
        c.execute(m.trade_property_value.insert().values(trade_id=identity,definition_id=dimension,tenant_id=r.tenant_id,value=value))
    configure_policy(c,r.tenant_id,ids['demo_user_account'],r.strategy_id,[dict(definitionId=str(dimension),behavior='ALLOCATION')],load_allocation_policy(c,r.tenant_id,r.strategy_id).revision,'Preserve FX allocations')
    svc.configure(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,'DIRECT',0,'Synthetic direct',r.policy_id,cut)
    data,fp,_,cutoff=svc.candidate(c,r.tenant_id,r.strategy_id,instrument)
    assert len(data['movements'])==2
    result=svc.post(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,instrument,fp,str(uuid4()))
    identities=[__import__('uuid').UUID(t) for t in result['trade_ids']]
    assert len(identities)==2
    assert set(c.scalars(select(m.trade_property_value.c.value).where(m.trade_property_value.c.trade_id.in_(identities))))=={'alpha','beta'}
    from datetime import datetime,timezone
    request=ProjectionRequest(r.tenant_id,r.strategy_id,cutoff,datetime.now(timezone.utc))
    assert not reconstruct(tuple(iter_ledger_facts(c,request,subject_ids=[instrument])),request).buckets
    svc.cancel(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,__import__('uuid').UUID(result['posting_id']),'Synthetic reopen',str(uuid4()))
    assert len(svc.candidate(c,r.tenant_id,r.strategy_id,instrument)[0]['movements'])==2


def two_bond_allocations(valued,opposing=False):
    from tests.test_bond_redemption_service import setup
    from tests.profile_fixtures import configure_allocation as configure_policy,allocation_policy as load_allocation_policy
    from lifecycle import bond_service as svc
    c,r,trade=valued;listing,first,_=setup(c,r,trade);second=clone_execution(c,first)
    if opposing:c.execute(m.trade.update().where(m.trade.c.trade_id==second).values(quantity=-100000))
    dimension=field(c,r.tenant_id)
    for identity,value in [(first,'alpha'),(second,'beta')]:
        c.execute(m.trade_property_value.insert().values(trade_id=identity,definition_id=dimension,tenant_id=r.tenant_id,value=value))
    configure_policy(c,r.tenant_id,ids['demo_user_account'],r.strategy_id,[dict(definitionId=str(dimension),behavior='ALLOCATION')],load_allocation_policy(c,r.tenant_id,r.strategy_id).revision,'Classify source allocations')
    svc.configure(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,'DIRECT',0,'Synthetic direct')
    return svc,c,r,dimension


def test_zero_total_bond_still_closes_both_nonzero_allocations(valued):
    svc,c,r,_=two_bond_allocations(valued,True)
    data,fp,_,_=svc.candidate(c,r.tenant_id,r.strategy_id,ids['bond_instrument_node'])
    assert sorted(__import__('decimal').Decimal(m['quantity']) for m in data['movements'])==[-100000,100000]
    posted=svc.post(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,ids['bond_instrument_node'],fp,str(uuid4()))
    assert len(posted['trade_ids'])==2
    with pytest.raises(svc.RedemptionConflict):svc.candidate(c,r.tenant_id,r.strategy_id,ids['bond_instrument_node'])


def test_failure_in_second_entry_rolls_back_the_whole_posting(valued,monkeypatch):
    svc,c,r,_=two_bond_allocations(valued)
    _,fp,_,_=svc.candidate(c,r.tenant_id,r.strategy_id,ids['bond_instrument_node'])
    original=svc.persist_annotations;calls=[]
    def fail_after_first(*args):
        calls.append(1)
        if len(calls)==2:raise ValueError('Synthetic second-entry failure')
        return original(*args)
    monkeypatch.setattr(svc,'persist_annotations',fail_after_first)
    with pytest.raises(ValueError,match='second-entry'):
        svc.post(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,ids['bond_instrument_node'],fp,str(uuid4()))
    assert not list(c.scalars(select(m.trade.c.trade_id).where(m.trade.c.strategy_id==r.strategy_id,m.trade.c.trade_type=='MATURITY_REDEMPTION')))
    assert not list(c.scalars(select(m.bond_redemption_posting.c.posting_id).where(m.bond_redemption_posting.c.strategy_id==r.strategy_id)))


def test_policy_change_invalidates_prepared_economics_and_readonly_fields(valued):
    from tests.profile_fixtures import configure_allocation as configure_policy,allocation_policy as load_allocation_policy
    svc,c,r,dimension=two_bond_allocations(valued)
    data,fp,_,_=svc.candidate(c,r.tenant_id,r.strategy_id,ids['bond_instrument_node'])
    move=data['movements'][0]
    with pytest.raises(ValueError,match='read-only'):
        svc.candidate(c,r.tenant_id,r.strategy_id,ids['bond_instrument_node'],annotation_inputs={move['movementKey']:[dict(definitionId=str(dimension),value='redirected')]})
    configure_policy(c,r.tenant_id,ids['demo_user_account'],r.strategy_id,[dict(definitionId=str(dimension),behavior='ALLOCATION')],load_allocation_policy(c,r.tenant_id,r.strategy_id).revision,'Retain revised configuration decision')
    with pytest.raises(svc.RedemptionConflict):
        svc.post(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,ids['bond_instrument_node'],fp,str(uuid4()))


def test_annotations_are_not_visible_through_a_different_tenant(valued):
    from trading.annotation_snapshots import load_trade_annotations
    svc,c,r,dimension=two_bond_allocations(valued)
    identities=list(c.scalars(select(m.trade.c.trade_id).where(m.trade.c.strategy_id==r.strategy_id)))
    assert load_trade_annotations(c,uuid4(),identities)=={}


def test_bond_closure_detail_has_fresh_receipt_direction(valued):
    from apps.reference_api.product_booking import load_economics
    svc,c,r,_=two_bond_allocations(valued)
    source_ids=list(c.scalars(select(m.trade.c.trade_id).where(m.trade.c.strategy_id==r.strategy_id,m.trade.c.reference_instrument_node_id==ids['bond_instrument_node'])))
    assert load_economics(c,source_ids)
    _,fp,_,_=svc.candidate(c,r.tenant_id,r.strategy_id,ids['bond_instrument_node'])
    posted=svc.post(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,ids['bond_instrument_node'],fp,str(uuid4()))
    detail=load_economics(c,[__import__('uuid').UUID(t) for t in posted['trade_ids']])
    assert len(detail)==2
    assert all(d['direction']=='RECEIVE' for d in detail.values())


def test_independent_approval_retains_reviewed_entry_values(valued):
    from security_master_schema import access_management as am
    svc,c,r,dimension=two_bond_allocations(valued)
    required=field(c,r.tenant_id,True)
    from tests.profile_fixtures import configure_allocation,allocation_policy
    configure_allocation(c,r.tenant_id,ids['demo_user_account'],r.strategy_id,[dict(definitionId=str(dimension),behavior='ALLOCATION'),dict(definitionId=str(required),behavior='INPUT')],allocation_policy(c,r.tenant_id,r.strategy_id).revision,'Require reviewed fresh entry values')
    svc.configure(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,'REVIEW',1,'Independent review')
    data,_,_,_=svc.candidate(c,r.tenant_id,r.strategy_id,ids['bond_instrument_node'])
    supplied={move['movementKey']:[dict(definitionId=str(required),value='Reviewed source '+str(index))] for index,move in enumerate(data['movements'])}
    data,fp,_,_=svc.candidate(c,r.tenant_id,r.strategy_id,ids['bond_instrument_node'],annotation_inputs=supplied)
    proposal=svc.prepare(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,ids['bond_instrument_node'],fp,annotation_inputs=supplied)
    reviewer=am.add_user(c,r.tenant_id,ids['demo_user_account'],name='Synthetic allocation reviewer')
    group=am.save_group(c,r.tenant_id,ids['demo_user_account'],code='ALLOC_REVIEW_'+uuid4().hex,name='Allocation reviewer',actions=['LIFECYCLE_APPROVE','TRADE_WRITE'],scope_mode='SELECTED',strategy_ids=[r.strategy_id])
    am.set_user_groups(c,r.tenant_id,ids['demo_user_account'],reviewer,[group])
    posted=svc.post(c,r.tenant_id,reviewer,reviewer,r.strategy_id,ids['bond_instrument_node'],fp,str(uuid4()),proposal_id=__import__('uuid').UUID(proposal['proposalId']))
    actual=set(c.scalars(select(m.trade_property_value.c.value).where(m.trade_property_value.c.trade_id.in_([__import__('uuid').UUID(t) for t in posted['trade_ids']]),m.trade_property_value.c.definition_id==required)))
    assert actual=={'Reviewed source 0','Reviewed source 1'}


def test_activation_does_not_relabel_old_unclassified_closures(valued):
    from tests.test_bond_redemption_service import setup
    from tests.profile_fixtures import configure_allocation as configure_policy,allocation_policy as load_allocation_policy
    from lifecycle import bond_service as svc
    c,r,trade=valued;_,booked,_=setup(c,r,trade);dimension=field(c,r.tenant_id)
    c.execute(m.trade_property_value.insert().values(trade_id=booked,definition_id=dimension,tenant_id=r.tenant_id,value='Historical allocation'))
    svc.configure(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,'DIRECT',0,'Synthetic direct')
    _,fp,_,_=svc.candidate(c,r.tenant_id,r.strategy_id,ids['bond_instrument_node'])
    svc.post(c,r.tenant_id,ids['demo_user_account'],ids['demo_user_account'],r.strategy_id,ids['bond_instrument_node'],fp,str(uuid4()))
    baseline=load_allocation_policy(c,r.tenant_id,r.strategy_id).revision
    with pytest.raises(ValueError,match='reconciliation'):
        configure_policy(c,r.tenant_id,ids['demo_user_account'],r.strategy_id,[dict(definitionId=str(dimension),behavior='ALLOCATION')],baseline,'Do not relabel history')
    assert load_allocation_policy(c,r.tenant_id,r.strategy_id).revision==baseline


def test_retired_existing_policy_fields_are_not_silently_dropped(valued):
    from tests.profile_fixtures import configure_allocation as configure_policy,allocation_policy as load_allocation_policy
    from datetime import datetime,timezone
    c,r,_=valued;dimension=field(c,r.tenant_id)
    rules=[dict(definitionId=str(dimension),behavior='ALLOCATION')]
    baseline=load_allocation_policy(c,r.tenant_id,r.strategy_id).revision
    configure_policy(c,r.tenant_id,ids['demo_user_account'],r.strategy_id,rules,baseline,'Original rule')
    c.execute(m.trade_property_definition.update().where(m.trade_property_definition.c.definition_id==dimension).values(status='RETIRED',retired_at_utc=datetime.now(timezone.utc),retired_by_user_account_id=ids['demo_user_account']))
    with pytest.raises(ValueError,match='not available'):
        configure_policy(c,r.tenant_id,ids['demo_user_account'],r.strategy_id,rules,baseline+1,'Cannot republish a retired definition')
    retained=load_allocation_policy(c,r.tenant_id,r.strategy_id)
    assert retained.revision==baseline+1
    assert [(str(rule.definition_id),rule.behavior) for rule in retained.fields if rule.behavior=='ALLOCATION']==[(str(dimension),'ALLOCATION')]
