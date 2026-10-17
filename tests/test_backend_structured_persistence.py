"""Persist explicit period economics, using disposable PostgreSQL only."""
from copy import deepcopy
from decimal import Decimal

from sqlalchemy import select

from tests.test_access_management import connection
from tests.test_source_payload_scope import draft
from apps.reference_api.repository import submit_structured_product_proposal, decide_structured_product_proposal
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from uuid import uuid4
import pytest
from sqlalchemy import update
from apps.reference_api.booking_errors import RepositoryNotFound, InvalidWorkflowState
from tests.test_source_payload_scope import evidence


def test_nested_foreign_payload_is_rejected(connection):
    request=draft(connection)
    item=request.underlyings[0].model_copy(update={
        'source_system_id':ids['source_system'],
        'source_payload_id':evidence(connection,ids['second_tenant'])})
    request=request.model_copy(update={'underlyings':[item,*request.underlyings[1:]]})
    with pytest.raises(RepositoryNotFound):
        submit_structured_product_proposal(connection,ids['tenant'],ids['demo_user_account'],request)


def test_foreign_calendar_is_rejected(connection):
    calendar=uuid4()
    connection.execute(m.market_calendar.insert().values(market_calendar_id=calendar,
        tenant_id=ids['second_tenant'],calendar_code='PRIVATE_'+calendar.hex,
        display_name='Private calendar',timezone_name='Europe/London',calendar_kind='SETTLEMENT'))
    request=draft(connection).model_copy(update={'calendar_id':calendar})
    with pytest.raises(RepositoryNotFound):
        submit_structured_product_proposal(connection,ids['tenant'],ids['demo_user_account'],request)


def test_visible_unpublished_calendar_is_not_contractual_evidence(connection):
    calendar=uuid4()
    connection.execute(m.market_calendar.insert().values(market_calendar_id=calendar,
        tenant_id=ids['tenant'],calendar_code='DRAFT_'+calendar.hex,
        display_name='Unpublished',timezone_name='Europe/London',calendar_kind='SETTLEMENT'))
    with pytest.raises(InvalidWorkflowState,match='published'):
        submit_structured_product_proposal(connection,ids['tenant'],ids['demo_user_account'],
            draft(connection).model_copy(update={'calendar_id':calendar}))


def test_approval_revalidates_nested_source_scope(connection):
    payload=evidence(connection,ids['tenant'])
    request=draft(connection)
    item=request.underlyings[0].model_copy(update={
        'source_system_id':ids['source_system'],'source_payload_id':payload})
    request=request.model_copy(update={'underlyings':[item,*request.underlyings[1:]]})
    proposal=submit_structured_product_proposal(connection,ids['tenant'],ids['demo_user_account'],request)
    connection.execute(update(m.source_payload).where(m.source_payload.c.source_payload_id==payload)
        .values(tenant_id=ids['second_tenant']))
    with pytest.raises(RepositoryNotFound):
        decide_structured_product_proposal(connection,ids['tenant'],ids['demo_user_account'],proposal.proposal_id,'APPROVED','Revalidation')


@pytest.mark.parametrize('field',['market_data_observation_id','market_data_resolution_snapshot_id'])
def test_missing_nested_market_reference_is_rejected_before_insert(connection,field):
    request=draft(connection)
    item=request.underlyings[0].model_copy(update={field:uuid4(),'fixing_source':'MARKET_DATA'})
    request=request.model_copy(update={'underlyings':[item,*request.underlyings[1:]]})
    with pytest.raises((RepositoryNotFound,InvalidWorkflowState)):
        submit_structured_product_proposal(connection,ids['tenant'],ids['demo_user_account'],request)


@pytest.mark.parametrize('mismatch',[None,'instrument','date','value','basis','quality','rights'])
def test_market_fixing_reconciles_actual_observation_and_current_rights(connection,mismatch):
    request=draft(connection)
    fixing=request.underlyings[0]
    series=uuid4(); observation=uuid4()
    connection.execute(m.market_data_series.insert().values(market_data_series_id=series,
        reference_node_id=ids['bond_instrument_node'] if mismatch=='instrument' else fixing.reference_node_id,
        series_type='CLOSE',value_type='PRICE',currency_id=ids['gbp_currency'],
        default_dataset_id=ids['dataset'],source_system_id='SYNTHETIC'))
    from datetime import timedelta, datetime, timezone
    connection.execute(m.market_data_observation.insert().values(market_data_observation_id=observation,
        market_data_series_id=series,dataset_id=ids['dataset'],market_date=fixing.fixing_date or request.start_date,
        observed_at_utc=datetime.now(timezone.utc),received_at_utc=datetime.now(timezone.utc),
        value=fixing.initial_fixing+1 if mismatch=='value' else fixing.initial_fixing,
        value_basis='SPLIT_ADJUSTED' if mismatch=='basis' else 'RAW',
        quality_status='REJECTED' if mismatch=='quality' else 'ACCEPTED'))
    if mismatch=='date':
        connection.execute(update(m.market_data_observation).where(m.market_data_observation.c.market_data_observation_id==observation)
            .values(market_date=request.start_date+timedelta(days=1)))
    if mismatch=='rights':
        from sqlalchemy import delete
        connection.execute(delete(m.tenant_dataset_entitlement).where(m.tenant_dataset_entitlement.c.tenant_id==ids['tenant'],
            m.tenant_dataset_entitlement.c.dataset_id==ids['dataset']))
    fixing=fixing.model_copy(update={'fixing_source':'MARKET_DATA','market_data_observation_id':observation})
    request=request.model_copy(update={'underlyings':[fixing,*request.underlyings[1:]]})
    if mismatch is None:
        assert submit_structured_product_proposal(connection,ids['tenant'],ids['demo_user_account'],request).status=='PENDING'
    else:
        with pytest.raises((InvalidWorkflowState,PermissionError)):
            submit_structured_product_proposal(connection,ids['tenant'],ids['demo_user_account'],request)


def test_variable_coupon_periods_persist_without_flattening(connection):
    body=draft(connection).model_dump(mode='json',by_alias=True,exclude_none=True)
    for row in deepcopy(body['rows'][:2]):
        row.update(rowId=row['rowId']+'-step',observationDate='2027-07-01',paymentDate='2027-07-05',couponRate='7.5')
        body['rows'].append(row)
    from apps.reference_api.structured_product_contracts import AutocallDraftRequest
    proposal=submit_structured_product_proposal(connection,ids['tenant'],ids['demo_user_account'],AutocallDraftRequest.model_validate(body))
    approved=decide_structured_product_proposal(connection,ids['tenant'],ids['demo_user_account'],proposal.proposal_id,'APPROVED','Synthetic regression')
    # Identify the newly approved parent rather than relying on preseeded rows.
    terms=approved.terms_id
    programme=connection.execute(select(m.structured_product_coupon_programme).where(
        m.structured_product_coupon_programme.c.structured_product_terms_id==terms)).mappings().one()
    assert programme['default_coupon_rate'] is None
    rates=connection.scalars(select(m.structured_product_coupon_period.c.coupon_rate).where(
        m.structured_product_coupon_period.c.coupon_programme_id==programme['coupon_programme_id'])
        .order_by(m.structured_product_coupon_period.c.period_sequence)).all()
    assert rates==[Decimal('6.5'),Decimal('7.5')]
