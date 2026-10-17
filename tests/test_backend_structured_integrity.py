"""Economic intake regressions: explicit source graph, never silent defaults."""
from copy import deepcopy
from decimal import Decimal
import pytest
from apps.reference_api.structured_product_contracts import validate_autocall_draft
from tests.test_structured_product_draft import _base_payload


@pytest.mark.parametrize('location',['root','underlying','row'])
def test_unknown_contract_terms_are_rejected(location):
    payload=_base_payload()
    target=payload if location=='root' else payload['underlyings'][0] if location=='underlying' else payload['rows'][0]
    target['unmodelledTermsheetClause']='must not disappear'
    with pytest.raises(ValueError,match='unmodelledTermsheetClause'):
        validate_autocall_draft(payload)


def test_missing_headline_is_derived_from_explicit_flat_coupon_not_zero():
    request=validate_autocall_draft(_base_payload())
    assert request.coupon_rate==Decimal('6.5')


def test_contradictory_flat_headline_and_graph_are_rejected():
    payload=_base_payload();payload['couponRate']='1.25'
    with pytest.raises(ValueError,match='headline coupon'):
        validate_autocall_draft(payload)


def test_variable_period_coupons_remain_explicit_without_a_flat_headline():
    payload=_base_payload()
    for row in deepcopy(payload['rows'][:2]):
        row.update(rowId=row['rowId']+'-step',observationDate='2027-07-01',paymentDate='2027-07-05',couponRate='7.5')
        payload['rows'].append(row)
    request=validate_autocall_draft(payload)
    assert request.coupon_rate is None
    assert {r.coupon_rate for r in request.rows if r.condition_role=='COUPON_ELIGIBILITY'}=={Decimal('6.5'),Decimal('7.5')}


def test_explicit_zero_coupon_is_not_missing():
    payload=_base_payload();payload['couponRate']='0'
    for row in payload['rows']:
        if row['conditionRole']=='COUPON_ELIGIBILITY':row['couponRate']='0'
    assert validate_autocall_draft(payload).coupon_rate==0


def test_missing_row_coupon_without_default_is_blocked():
    payload=_base_payload()
    for row in payload['rows']:
        if row['conditionRole']=='COUPON_ELIGIBILITY':row.pop('couponRate',None)
    with pytest.raises(ValueError,match='coupon rate'):
        validate_autocall_draft(payload)


def test_one_coupon_period_cannot_hide_conflicting_payment_dates():
    payload=_base_payload()
    payload['rows'][1]['paymentDate']='2027-01-06'
    with pytest.raises(ValueError,match='payment date'):
        validate_autocall_draft(payload)


def test_kip_headline_must_match_explicit_protection_barrier():
    payload=_base_payload();payload['kipBarrier']='25'
    payload.update(productSubtype='AUTOCALL',includeConsolation=False)
    payload['rows']=[row for row in payload['rows'] if row['conditionRole']!='CONSOLATION']
    with pytest.raises(ValueError,match='KIP barrier'):
        validate_autocall_draft(payload)


def test_omitted_barrier_summaries_do_not_turn_into_zero():
    payload=_base_payload()
    request=validate_autocall_draft(payload)
    assert request.coupon_barrier is None
    assert request.autocall_barrier_start is None
    assert request.autocall_barrier_step is None
    assert request.autocall_barrier_floor is None


def test_fixed_coupon_barrier_must_match_explicit_rows():
    payload=_base_payload();payload.update(couponBarrierFollowsAutocall=False,couponBarrier=60)
    with pytest.raises(ValueError,match='Coupon barrier'):
        validate_autocall_draft(payload)


def test_explicit_autocall_generator_summary_must_match_actual_rows():
    payload=_base_payload()
    payload.update(autocallBarrierStart=100,autocallBarrierStep=-10,autocallBarrierFloor=70)
    payload['rows'].append(dict(rowId='autocall',rowKind='ACTION',groupCode='AUTOCALL_ACTION',
        componentKind='PARENT_ACTION',conditionRole='AUTOCALL',conditionOperator='GE',conditionScope='WORST_OF',
        observationDate='2027-01-01',paymentDate='2027-01-05',conditionLevel=90,
        conditionLevelBasis='PCT_OF_INITIAL',actionCode='REDEEM_PARENT',actionTarget='PARENT'))
    with pytest.raises(ValueError,match='Autocall barrier'):
        validate_autocall_draft(payload)


def test_payment_preview_rejects_noncontractual_calendar_kind(monkeypatch):
    from apps.reference_api import structured_product_dependencies as dependencies
    from datetime import date
    monkeypatch.setattr(dependencies,'visible_calendar',lambda *_:{'sealed':True,'calendar_kind':'VALUATION'})
    with pytest.raises(ValueError,match='eligible'):
        dependencies.contractual_payment_dates(None,None,None,[date(2026,10,16)],0)


def test_explicit_graph_remains_valid_after_normalized_proposal_round_trip():
    payload=_base_payload()
    payload['rows'].append(dict(rowId='autocall',rowKind='ACTION',groupCode='AUTOCALL_ACTION',
        componentKind='PARENT_ACTION',conditionRole='AUTOCALL',conditionOperator='GE',conditionScope='WORST_OF',
        observationDate='2027-01-01',paymentDate='2027-01-05',conditionLevel=90,
        conditionLevelBasis='PCT_OF_INITIAL',actionCode='REDEEM_PARENT',actionTarget='PARENT'))
    first=validate_autocall_draft(payload)
    again=validate_autocall_draft(first.model_dump(mode='json',by_alias=True))
    assert again.rows==first.rows
    payload['paymentDateConvention']='CALENDAR_LAG'
    with pytest.raises(ValueError,match='inheritance'):
        validate_autocall_draft(payload)
