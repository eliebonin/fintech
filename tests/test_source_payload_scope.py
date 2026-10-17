"""Structured-product evidence scope, exercised against owned disposable PostgreSQL."""
import json
from uuid import uuid4
import pytest
from sqlalchemy import select, update, func
from tests.test_access_management import connection
from tests.test_structured_product_draft import _base_payload, CURRENCY, CALENDAR, UNDERLYING_A, UNDERLYING_B
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids
from apps.reference_api.structured_product_contracts import AutocallDraftRequest
from apps.reference_api.repository import submit_structured_product_proposal, RepositoryNotFound, InvalidWorkflowState


def draft(c, payload_id=None, source_id=None, key=None):
    # A new contract pins a published version; never mutate the shared source.
    source = c.scalar(select(m.market_calendar.c.market_calendar_id).where(
        m.market_calendar.c.status=='ACTIVE',m.market_calendar.c.tenant_id.is_(None),
        m.market_calendar.c.sealed.is_(False)).limit(1))
    from datetime import date
    if c.scalar(select(m.market_calendar_session.c.market_calendar_session_id).where(
            m.market_calendar_session.c.market_calendar_id==source,
            m.market_calendar_session.c.session_date==date(2027,1,1))) is None:
        c.execute(m.market_calendar_session.insert().values(market_calendar_id=source,
            session_date=date(2027,1,1),session_status='CLOSED',source_reference='synthetic://contract-calendar'))
    from market_data.calendar_store import publish_reference_calendar
    calendar=publish_reference_calendar(c,source,ids['platform_admin_user_account'],'Synthetic contract test')
    text = json.dumps(_base_payload())
    for before, after in [(CURRENCY,ids['gbp_currency']),(CALENDAR,calendar),
                          (UNDERLYING_A,ids['hsbc_instrument_node']),(UNDERLYING_B,ids['bond_instrument_node'])]:
        text = text.replace(str(before),str(after))
    body = json.loads(text)
    body.update(internalCode='SCOPE_'+uuid4().hex, sourcePayloadId=str(payload_id) if payload_id else None,
                sourceSystemId=str(source_id) if source_id else None, idempotencyKey=key)
    return AutocallDraftRequest.model_validate(body)


def evidence(c, owner, source=None):
    payload_id=uuid4()
    c.execute(m.source_payload.insert().values(source_payload_id=payload_id,tenant_id=owner,
        integration_source_system_id=source or ids['source_system'],payload_format='PDF',
        payload_locator='synthetic://scope-test/'+str(payload_id),payload_sha256='a'*64))
    return payload_id


@pytest.mark.parametrize('owner',[ids['tenant'],None])
def test_owned_and_explicit_shared_payload_can_be_submitted(connection,owner):
    payload_id=evidence(connection,owner)
    result=submit_structured_product_proposal(connection,ids['tenant'],ids['demo_user_account'],
        draft(connection,payload_id,ids['source_system']))
    assert result is not None


@pytest.mark.parametrize('case',['foreign','missing','mismatched','foreign_source','missing_source'])
def test_invalid_evidence_cannot_create_proposal(connection,case):
    source=ids['source_system']
    if case in {'mismatched','foreign_source'}:
        source=uuid4()
        connection.execute(m.integration_source_system.insert().values(integration_source_system_id=source,
            tenant_id=ids['second_tenant'] if case=='foreign_source' else None,
            system_code='SCOPE_'+uuid4().hex,display_name='Scope test',source_kind='INTERNAL'))
    payload_id=uuid4() if case=='missing' else evidence(connection,
        ids['second_tenant'] if case=='foreign' else ids['tenant'],source if case=='foreign_source' else None)
    before=connection.scalar(select(func.count()).select_from(m.reference_data_proposal))
    with pytest.raises((RepositoryNotFound,InvalidWorkflowState)):
        submit_structured_product_proposal(connection,ids['tenant'],ids['demo_user_account'],
            draft(connection,payload_id,None if case=='missing_source' else source))
    assert connection.scalar(select(func.count()).select_from(m.reference_data_proposal))==before


def test_retry_revalidates_evidence_scope(connection):
    payload_id=evidence(connection,ids['tenant'])
    request=draft(connection,payload_id,ids['source_system'],'scope-'+uuid4().hex)
    submit_structured_product_proposal(connection,ids['tenant'],ids['demo_user_account'],request)
    connection.execute(update(m.source_payload).where(m.source_payload.c.source_payload_id==payload_id)
        .values(tenant_id=ids['second_tenant']))
    with pytest.raises(RepositoryNotFound):
        submit_structured_product_proposal(connection,ids['tenant'],ids['demo_user_account'],request)
