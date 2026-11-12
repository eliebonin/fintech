"""Distinct-contract query budgets and source/authority parity on disposable data."""
from copy import deepcopy
from uuid import uuid4
import pytest
from sqlalchemy import select,event
from security_master_schema import models as m
from tests.test_structured_notifications import notes,read,structured,note_swap,valued
from security_master_schema.demo_data import DEMO_IDS as ids


def clone_note(c,source,tenant,index):
    target=uuid4();terms_id=None
    for table,key in [(m.financial_reference_node,'reference_node_id'),(m.instrument,'instrument_node_id'),(m.instrument_definition_version,'instrument_node_id'),(m.instrument_dates,'instrument_node_id'),(m.structured_product_terms,'instrument_node_id'),(m.instrument_booking_convention,'instrument_node_id')]:
        records=c.execute(select(table).where(table.c[key]==source)).mappings().all()
        for record in records:
            row=dict(record);row[key]=target
            for pk in table.primary_key.columns:
                if pk.name!=key:row[pk.name]=uuid4()
            if table is m.financial_reference_node:row.update(canonical_name=f'Batch autocall {index:03d}',internal_code='BATCH_'+target.hex)
            if table is m.structured_product_terms:row['source_payload_id']=None;terms_id=row['structured_product_terms_id']
            c.execute(table.insert().values(**row))
    c.execute(m.reference_node_scope.insert().values(reference_node_id=target,scope_type='TENANT_PRIVATE',owner_tenant_id=tenant,status='ACTIVE'))
    schedule_map={};event_map={};group_map={}
    for record in c.execute(select(m.schedule).where(m.schedule.c.owner_reference_node_id==source)).mappings().all():
        row=dict(record);old=row['schedule_id'];row.update(schedule_id=uuid4(),owner_reference_node_id=target);schedule_map[old]=row['schedule_id'];c.execute(m.schedule.insert().values(**row))
    for record in c.execute(select(m.schedule_event).where(m.schedule_event.c.schedule_id.in_(schedule_map))).mappings().all():
        row=dict(record);old=row['schedule_event_id'];row.update(schedule_event_id=uuid4(),schedule_id=schedule_map[row['schedule_id']]);event_map[old]=row['schedule_event_id'];c.execute(m.schedule_event.insert().values(**row))
    source_terms=c.scalar(select(m.structured_product_terms.c.structured_product_terms_id).where(m.structured_product_terms.c.instrument_node_id==source,m.structured_product_terms.c.is_current))
    for record in c.execute(select(m.structured_product_condition_group).where(m.structured_product_condition_group.c.structured_product_terms_id==source_terms)).mappings().all():
        row=dict(record);old=row['condition_group_id'];row.update(condition_group_id=uuid4(),structured_product_terms_id=terms_id,schedule_event_id=event_map.get(row['schedule_event_id']));group_map[old]=row['condition_group_id'];c.execute(m.structured_product_condition_group.insert().values(**row))
    for table in (m.barrier_rule,m.condition_group_action):
        for record in c.execute(select(table).where(table.c.condition_group_id.in_(group_map))).mappings().all():
            row=dict(record);row['condition_group_id']=group_map[row['condition_group_id']]
            for pk in table.primary_key.columns:row[pk.name]=uuid4()
            for key in ('owner_reference_node_id','target_reference_node_id'):
                if row.get(key)==source:row[key]=target
            c.execute(table.insert().values(**row))
    return target


def clone_swap(c,source,reference,tenant,index):
    target=uuid4();definition=None;original_definition=None
    for table,key in [(m.financial_reference_node,'reference_node_id'),(m.instrument,'instrument_node_id'),(m.instrument_definition_version,'instrument_node_id'),(m.instrument_dates,'instrument_node_id'),(m.instrument_booking_convention,'instrument_node_id'),(m.swap_terms,'instrument_node_id'),(m.swap_leg,'swap_instrument_node_id')]:
        for record in c.execute(select(table).where(table.c[key]==source)).mappings().all():
            row=dict(record);row[key]=target
            for pk in table.primary_key.columns:
                if pk.name!=key:row[pk.name]=uuid4()
            if table is m.financial_reference_node:row.update(canonical_name=f'Batch held swap {index:03d}',internal_code='BATCH_SWAP_'+target.hex)
            if table is m.instrument_definition_version:definition=row['instrument_definition_version_id'];original_definition=record['instrument_definition_version_id']
            if table is m.swap_leg and row['leg_role']=='PERFORMANCE':row['reference_node_id']=reference
            c.execute(table.insert().values(**row))
    record=dict(c.execute(select(m.swap_definition_version).where(m.swap_definition_version.c.instrument_definition_version_id==original_definition)).mappings().one())
    record['instrument_definition_version_id']=definition;record['economics_payload']=deepcopy(record['economics_payload']);record['economics_payload']['performanceReferenceId']=str(reference)
    c.execute(m.swap_definition_version.insert().values(**record))
    c.execute(m.reference_node_scope.insert().values(reference_node_id=target,scope_type='TENANT_PRIVATE',owner_tenant_id=tenant,status='ACTIVE'))
    return target


class QueryCounter:
    def __init__(self,c):self.connection=c;self.count=0
    def before(self,c,cursor,statement,parameters,context,many):self.count+=1
    def __enter__(self):event.listen(self.connection,'before_cursor_execute',self.before);return self
    def __exit__(self,*args):event.remove(self.connection,'before_cursor_execute',self.before)


def test_many_distinct_swap_contracts_have_bounded_worklist_queries_and_search(notes):
    c,r,node,swap,trade,events,execute=notes;execute(swap)
    # Both populations must have the same dependency depth: a held swap whose
    # observed note is not itself a held root. New table/depth waves are allowed;
    # another query for each additional contract is not.
    seed=clone_note(c,node,r.tenant_id,999)
    c.execute(m.financial_reference_node.update().where(m.financial_reference_node.c.reference_node_id==seed).values(canonical_name='Existing source for baseline depth'))
    execute(clone_swap(c,swap,seed,r.tenant_id,999))
    with QueryCounter(c) as small:initial=read(c,r)
    roots=[]
    for index in range(24):
        reference=clone_note(c,node,r.tenant_id,index);held=clone_swap(c,swap,reference,r.tenant_id,index);execute(held);roots.append(held)
    with QueryCounter(c) as large:result=read(c,r)
    assert result['total']==initial['total']+96
    assert large.count<=120,(small.count,large.count)
    assert large.count<=small.count+12,(small.count,large.count)
    with QueryCounter(c) as searched:matched=read(c,r,q='Batch autocall',offset=25)
    assert matched['total']==96 and len(matched['items'])==25
    assert searched.count<=large.count+8,(large.count,searched.count)
    assert {x['instrumentId'] for x in matched['items']}<=set(roots)
    print('Distinct-contract query counts:',dict(small=small.count,large=large.count,search=searched.count))


def test_bulk_source_projection_keeps_each_root_isolated_and_chunks_have_identical_proofs(notes,monkeypatch):
    from security_master_schema.instrument_terms_schedule import load_terms_schedule,load_terms_schedules
    from security_master_schema import instrument_terms_batch as batch
    c,r,node,swap,trade,events,execute=notes
    second=clone_note(c,node,r.tenant_id,99)
    baseline={root:load_terms_schedule(c,r.tenant_id,root).model_dump(mode='json') for root in [node,swap,second]}
    missing=uuid4()
    bulk=load_terms_schedules(c,r.tenant_id,[node,swap,second,missing])
    assert bulk[missing] is None
    assert {root:bulk[root].model_dump(mode='json') for root in baseline}==baseline
    monkeypatch.setattr(batch,'ID_BATCH_SIZE',1)
    chunked=load_terms_schedules(c,r.tenant_id,list(bulk))
    assert {root:value.model_dump(mode='json') if value else None for root,value in chunked.items()}=={root:value.model_dump(mode='json') if value else None for root,value in bulk.items()}
    c.execute(m.reference_node_scope.update().where(m.reference_node_scope.c.reference_node_id==second).values(owner_tenant_id=ids['second_tenant']))
    isolated=load_terms_schedules(c,r.tenant_id,[node,swap,second])
    assert isolated[second] is None and isolated[node] and isolated[swap]


def test_wrapper_share_facts_depth_and_cycle_guards_survive_batching(notes):
    from datetime import date
    from decimal import Decimal
    from security_master_schema.instrument_terms_schedule import load_terms_schedule,load_terms_schedules
    c,r,node,swap,trade,events,execute=notes
    chain=[node]+[clone_note(c,node,r.tenant_id,200+i) for i in range(4)]
    terms={identity:c.scalar(select(m.structured_product_terms.c.structured_product_terms_id).where(m.structured_product_terms.c.instrument_node_id==identity,m.structured_product_terms.c.is_current)) for identity in chain}
    for parent,child in zip(chain[:3],chain[1:4]):
        c.execute(m.structured_product_wrapper_terms.insert().values(structured_product_terms_id=terms[parent],preference_share_instrument_id=child,denomination=100,transfer_terms_json={'source':'retained test transfer'},note_inputs_json={'exactRatio':'0.123456789012'}))
    share=uuid4();leaf=chain[3]
    c.execute(m.preference_share_terms.insert().values(preference_share_terms_id=share,structured_product_terms_id=terms[leaf],instrument_node_id=leaf,tenant_id=r.tenant_id,issuer_organisation_id=ids['bank_a_organisation'],identity_key='BATCH_'+share.hex,denomination=100,inputs_json={'exactShareRatio':'0.123456789012'}))
    c.execute(m.preference_share_redemption_period.insert().values(preference_share_terms_id=share,sequence_no=1,observation_date=date(2027,10,1),payment_date=date(2027,10,5),trigger_level=Decimal('100.123456789012'),comparison_operator='GE',redemption_rate=Decimal('1.01')))
    c.execute(m.preference_share_terminal_branch.insert().values(preference_share_terms_id=share,sequence_no=1,lower_bound=0,upper_bound=100,lower_inclusive=True,upper_inclusive=False,formula='FIXED_PERCENT_OF_PAR',payout_rate=Decimal('0.5')))
    bulk=load_terms_schedules(c,r.tenant_id,[node,swap,leaf,chain[4]])
    assert len(bulk[node].layers)==4 and bulk[swap] is None
    assert bulk[node].layers[-1].facts['shareCalls'][0]['trigger_level']=='100.123456789012'
    assert bulk[node].layers[-1].facts['terminalBranches'][0]['upper_inclusive'] is False
    assert bulk[node].model_dump(mode='json')==load_terms_schedule(c,r.tenant_id,node).model_dump(mode='json')
    # New immutable contracts form a separate cyclic fixture. Do not edit a
    # retained wrapper just to create an adverse reader case.
    cyclic_roots=[clone_note(c,node,r.tenant_id,300+i) for i in range(2)]
    for parent,child in [(cyclic_roots[0],cyclic_roots[1]),(cyclic_roots[1],cyclic_roots[0])]:
        parent_terms=c.scalar(select(m.structured_product_terms.c.structured_product_terms_id).where(m.structured_product_terms.c.instrument_node_id==parent,m.structured_product_terms.c.is_current))
        c.execute(m.structured_product_wrapper_terms.insert().values(structured_product_terms_id=parent_terms,preference_share_instrument_id=child,denomination=100,transfer_terms_json={},note_inputs_json={}))
    cyclic=load_terms_schedules(c,r.tenant_id,[*cyclic_roots,leaf,chain[4]])
    assert all(cyclic[root] is None for root in cyclic_roots) and cyclic[leaf] and cyclic[chain[4]]
