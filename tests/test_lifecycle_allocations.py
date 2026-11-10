"""Allocation identity must survive economic netting, without tax lots."""
from dataclasses import replace
from decimal import Decimal as D
from uuid import UUID
import pytest
from tests.test_position_reconstruction import booked, request, OPEN, event

FIELD=UUID(int=8001)
OTHER=UUID(int=8002)

def policy(*rules):
    from security_master_schema.allocation_contracts import AllocationPolicy, FieldRule
    return AllocationPolicy(1, tuple(FieldRule(*r) for r in (rules or ((FIELD, 'ALLOCATION'),))))

def annotations(*values):
    from security_master_schema.allocation_contracts import AnnotationValue
    return {f.trade_id: {FIELD: AnnotationValue(value)} for f,value in values}

def project(facts, values, selected=None):
    from positions.allocations import reconstruct_allocations
    return reconstruct_allocations(facts, request(), selected or policy(), values)

def test_joint_allocation_identity_uses_explicit_fields_only():
    from security_master_schema.allocation_contracts import AnnotationValue
    a,b,c=[booked(i,'10',OPEN) for i in (1,2,3)]
    values=annotations((a,'alpha'),(b,'alpha'),(c,'alpha'))
    values[b.trade_id][OTHER]=AnnotationValue('Desk B')
    values[c.trade_id][OTHER]=AnnotationValue('Desk C')
    assert len(project([a,b,c],values).buckets)==1
    assert len(project([a,b,c],values,policy((FIELD,'ALLOCATION'),(OTHER,'ALLOCATION'))).buckets)==3

def test_partial_sales_preserve_signed_remaining_allocations():
    a=booked(1,'1000000',OPEN);b=booked(2,'-200000',OPEN);c=booked(3,'500000',OPEN)
    result=project([a,b,c],annotations((a,'alpha'),(b,'alpha'),(c,'beta')))
    assert sorted(b.closing_quantity for b in result.buckets)==[D('500000'),D('800000')]

def test_opposing_allocations_survive_zero_economic_total():
    a=booked(1,'1000000',OPEN);b=booked(2,'-1000000',OPEN)
    result=project([a,b],annotations((a,'alpha'),(b,'beta')))
    assert len(result.buckets)==2
    assert sum(b.closing_quantity for b in result.buckets)==0

def test_unclassified_sale_is_not_allocated_to_a_purchase_by_guess():
    a=booked(1,'100',OPEN);b=booked(2,'-20',OPEN)
    result=project([a,b],annotations((a,'alpha')))
    assert sorted(b.closing_quantity for b in result.buckets)==[D('-20'),D('100')]

def test_cancelled_booking_does_not_create_allocation_exposure():
    a=booked(1,'100',OPEN);b=booked(2,'20',OPEN)
    result=project([a,event(a,'CANCELLED',OPEN),b],annotations((a,'alpha'),(b,'beta')))
    assert [b.closing_quantity for b in result.buckets]==[D('20')]

def test_catalogue_revision_does_not_change_allocation_identity():
    from security_master_schema.allocation_contracts import AnnotationValue
    a=booked(1,'100',OPEN);b=booked(2,'-20',OPEN)
    identity=UUID(int=9001)
    values={a.trade_id:{FIELD:AnnotationValue(str(UUID(int=9011)),identity)},b.trade_id:{FIELD:AnnotationValue(str(UUID(int=9012)),identity)}}
    result=project([a,b],values)
    assert len(result.buckets)==1 and result.buckets[0].closing_quantity==80

def test_distinct_listing_and_currency_never_merge():
    a=booked(1,'100',OPEN);b=booked(2,'100',OPEN,subject_id=UUID(int=999));c=booked(3,'100',OPEN,currency_id=UUID(int=998))
    assert len(project([a,b,c],annotations((a,'alpha'),(b,'alpha'),(c,'alpha'))).buckets)==3

def test_changed_source_annotation_changes_projection_hash():
    a=booked(1,'100',OPEN)
    assert project([a],annotations((a,'alpha'))).input_hash!=project([a],annotations((a,'beta'))).input_hash

def test_boolean_false_is_not_missing_or_text_false():
    a=booked(1,'100',OPEN);b=booked(2,'-20',OPEN);c=booked(3,'30',OPEN)
    assert len(project([a,b,c],annotations((a,False),(b,'false'))).buckets)==3

@pytest.mark.parametrize('rules', [((FIELD,'WRONG'),),((FIELD,'ALLOCATION'),(FIELD,'INPUT'))])
def test_invalid_or_duplicate_policy_rules_fail(rules):
    with pytest.raises(ValueError): policy(*rules)
