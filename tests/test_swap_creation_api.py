"""Governed proposal creation and atomic approval on a disposable database."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select, func
from apps.reference_api.db import get_engine
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS
from tests.test_fx_forward_booking_api import request


def create_reference(node_id=None, **definition_changes):
    """A separate tenant-owned approved bond: eligibility is not autocall-specific."""
    node = node_id or uuid4()
    with get_engine().begin() as connection:
        for table, key in ((m.financial_reference_node, 'reference_node_id'),
                           (m.instrument, 'instrument_node_id'),
                           (m.instrument_definition_version, 'instrument_node_id')):
            values = dict(connection.execute(select(table).where(table.c[key] == DEMO_IDS['bond_instrument_node'])).mappings().one())
            values[key] = node
            for primary in table.primary_key.columns:
                if primary.name != key:
                    values[primary.name] = uuid4()
            if table is m.financial_reference_node:
                values.update(canonical_name=f'Private reference {node}', internal_code=f'REF_{node.hex}')
            else:
                values.update(effective_from=date(2026, 1, 1), effective_to=None, is_current=True)
            if table is m.instrument_definition_version:
                values['status'] = 'APPROVED'
            if table in (m.instrument, m.instrument_definition_version):
                values.update({key: value for key, value in definition_changes.items() if key in table.c})
            connection.execute(table.insert().values(**values))
        connection.execute(m.reference_node_scope.insert().values(reference_node_id=node,
            scope_type='TENANT_PRIVATE', owner_tenant_id=DEMO_IDS['tenant'], status='ACTIVE'))
    return node


@pytest.fixture
def reference():
    return create_reference()


def proposal(reference, funded=False, **changes):
    with get_engine().connect() as connection:
        profile = connection.scalar(select(m.return_profile.c.return_profile_id).where(m.return_profile.c.profile_code == 'GROSS_TOTAL_RETURN'))
        daycount = connection.scalar(select(m.day_count_convention.c.day_count_convention_id).where(m.day_count_convention.c.code == 'ACT_365F'))
    terms = dict(performanceReferenceId=str(reference), contractualNotional='1000000',
        notionalCurrencyId=str(DEMO_IDS['gbp_currency']), effectiveDate='2026-09-01', maturityDate='2027-09-01',
        performanceDirection='RECEIVE', returnBasis='TOTAL', returnProfileId=str(profile), leverage='2',
        quoteCurrencyId=str(DEMO_IDS['gbp_currency']), quoteFactor='100', sourceReference='Synthetic signed confirmation',
        financingTreatment='NONE', performanceResetFrequency='QUARTERLY', redemptionRule='TERMINATE')
    if funded:
        terms.update(fundingReferenceId=str(DEMO_IDS['sonia_rate_index_node']), fundingSpread='-0.0015',
            fundingNotionalBasis='LEVERAGED_NOMINAL', dayCountConventionId=str(daycount),
            interestCalculationMethod='Daily compounded; see confirmation section 3', fundingResetFrequency='MONTHLY',
            fundingPaymentFrequency='QUARTERLY', financingTreatment='SEPARATE')
    return dict(canonicalName=f'Synthetic generic swap {uuid4()}', tenantIdentifier='CONFIRMATION-42', terms=terms | changes)


def submit(data):
    response = request('POST', '/v1/instruments/swap-proposals', data)
    assert response.status_code == 201, response.text
    return response.json()['data']['proposalId']


def decide(proposal_id, decision='APPROVED', tenant='tenant', app=None):
    if app is not None:
        import asyncio
        from httpx import ASGITransport, AsyncClient
        async def run():
            async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
                return await client.post(f'/v1/reference-data-proposals/{proposal_id}/decision',
                    json=dict(decision=decision, reason='Synthetic confirmation checked.'),
                    headers={'X-Tenant-Id': str(DEMO_IDS[tenant]), 'X-User-Account-Id': str(DEMO_IDS['demo_user_account'])})
        return asyncio.run(run())
    return request('POST', f'/v1/reference-data-proposals/{proposal_id}/decision',
        dict(decision=decision, reason='Synthetic confirmation checked.'), tenant=tenant)


@pytest.mark.parametrize('funded', [False, True])
def test_approval_materializes_typed_terms_and_only_contractual_legs(reference, funded):
    data = proposal(reference, funded)
    proposal_id = submit(data)
    queue = request('GET', '/v1/work-queue').json()['items']
    item = next(i for i in queue if i['referenceId'] == proposal_id)
    assert item['category'] == 'REFERENCE_DATA_REVIEW'
    assert item['proposalType'] == 'CREATE_SWAP' and item['reviewPath']
    assert 'swap' in item['title'].lower()
    review = request('GET', f'/v1/reference-data-proposals/{proposal_id}').json()['data']
    assert review['status'] == 'PENDING' and review['referenceNodeId'] is None
    assert review['proposedPayload']['tenantIdentifier'] == 'CONFIRMATION-42'
    result = decide(proposal_id)
    assert result.status_code == 200, result.text
    node = UUID(result.json()['data']['referenceNodeId'])
    with get_engine().connect() as connection:
        definition = connection.execute(select(m.instrument_definition_version).where(m.instrument_definition_version.c.instrument_node_id == node)).mappings().one()
        assert definition.status == 'APPROVED' and definition.approved_by_user_account_id == DEMO_IDS['demo_user_account']
        assert connection.scalar(select(m.instrument_type.c.type_code).where(m.instrument_type.c.instrument_type_id == definition.instrument_type_id)) == 'SWAP'
        economics = connection.execute(select(m.swap_definition_version).where(m.swap_definition_version.c.instrument_definition_version_id == definition.instrument_definition_version_id)).mappings().one()
        assert economics.schema_version == 1
        assert economics.economics_payload['contractualNotional'] == '1000000'
        assert economics.economics_payload['leverage'] == '2'
        assert economics.economics_payload['fundingReferenceId'] == (str(DEMO_IDS['sonia_rate_index_node']) if funded else None)
        dates = connection.execute(select(m.instrument_dates).where(m.instrument_dates.c.instrument_node_id == node)).mappings().one()
        assert dates.effective_date == date(2026, 9, 1) and dates.maturity_date == date(2027, 9, 1)
        assert dates.final_settlement_date is None
        legs = connection.execute(select(m.swap_leg).where(m.swap_leg.c.swap_instrument_node_id == node).order_by(m.swap_leg.c.leg_number)).mappings().all()
        assert len(legs) == (2 if funded else 1)
        assert legs[0].leg_role == 'PERFORMANCE' and legs[0].pay_receive == 'RECEIVE'
        assert legs[0].reference_node_id == reference
        assert all(leg.schedule_id is None for leg in legs)
        if funded:
            assert legs[1].leg_role == 'FUNDING' and legs[1].pay_receive == 'PAY'
            assert legs[1].spread == Decimal('-0.0015')
        convention = connection.execute(select(m.instrument_booking_convention).where(m.instrument_booking_convention.c.instrument_node_id == node)).mappings().one()
        assert convention.kind == 'SWAP'
        import json
        approved = json.loads(convention.convention_payload)
        assert approved['priceBasis'] == 'SWAP_VALUE_PER_NOTIONAL' and approved['quoteFactor'] == '100'
        assert Decimal(approved['quantityMinimum']) == Decimal('0.000000000001')
    detail = request('GET', f'/v1/instruments/{node}')
    assert detail.status_code == 200, detail.text
    assert detail.json()['data']['genericTerms']['contractualNotional'] == '1000000'
    assert detail.json()['data']['genericTerms']['tenantIdentifier'] == 'CONFIRMATION-42'
    assert request('GET', f'/v1/instruments/{node}', tenant='second_tenant').status_code == 404


@pytest.mark.parametrize('change', ['hidden', 'retired', 'draft', 'not_current', 'expired', 'swap'])
def test_ineligible_instrument_reference_is_rejected(reference, change):
    with get_engine().begin() as connection:
        if change == 'hidden':
            connection.execute(m.reference_node_scope.update().where(m.reference_node_scope.c.reference_node_id == reference).values(owner_tenant_id=DEMO_IDS['second_tenant']))
        elif change == 'retired':
            connection.execute(m.financial_reference_node.update().where(m.financial_reference_node.c.reference_node_id == reference).values(status='RETIRED'))
        elif change == 'swap':
            kind = connection.scalar(select(m.instrument_type.c.instrument_type_id).where(m.instrument_type.c.type_code == 'SWAP'))
            reference = create_reference(instrument_type_id=kind)
        else:
            values = {'draft': {'status': 'DRAFT'}, 'not_current': {'is_current': False}, 'expired': {'effective_to': date(2026, 1, 2)}}[change]
            reference = create_reference(**values)
    response = request('POST', '/v1/instruments/swap-proposals', proposal(reference))
    assert response.status_code in {404, 422}, response.text
    assert f'Private reference {reference}' not in response.text


@pytest.mark.parametrize('field', ['fundingReferenceId', 'returnProfileId', 'dayCountConventionId'])
def test_governed_funding_and_profile_references_are_required(reference, field):
    value = str(reference) if field == 'fundingReferenceId' else str(uuid4())
    response = request('POST', '/v1/instruments/swap-proposals', proposal(reference, True, **{field: value}))
    assert response.status_code == 422, response.text


@pytest.mark.parametrize('change', ['hidden', 'draft', 'retired'])
def test_approval_revalidates_source_without_partial_materialization(reference, change):
    data = proposal(reference)
    proposal_id = submit(data)
    with get_engine().begin() as connection:
        if change == 'hidden':
            connection.execute(m.reference_node_scope.update().where(m.reference_node_scope.c.reference_node_id == reference).values(status='RETIRED'))
        elif change == 'draft':
            definition = dict(connection.execute(select(m.instrument_definition_version).where(m.instrument_definition_version.c.instrument_node_id == reference)).mappings().one())
            definition.update(instrument_definition_version_id=uuid4(), sequence_no=2, status='DRAFT')
            connection.execute(m.instrument_definition_version.insert().values(**definition))
            connection.execute(m.instrument.update().where(m.instrument.c.instrument_node_id == reference).values(sequence_no=2))
        else:
            connection.execute(m.financial_reference_node.update().where(m.financial_reference_node.c.reference_node_id == reference).values(status='RETIRED'))
    response = decide(proposal_id)
    assert response.status_code in {404, 409}, response.text
    with get_engine().connect() as connection:
        assert connection.scalar(select(func.count()).select_from(m.financial_reference_node).where(m.financial_reference_node.c.canonical_name == data['canonicalName'])) == 0
        assert connection.scalar(select(func.count()).select_from(m.reference_data_approval).where(m.reference_data_approval.c.reference_data_proposal_id == UUID(proposal_id))) == 0
    assert request('GET', f'/v1/reference-data-proposals/{proposal_id}').json()['data']['status'] == 'PENDING'


def test_concurrent_and_duplicate_approval_create_one_instrument(reference):
    from apps.reference_api.main import create_app
    data = proposal(reference)
    proposal_id = submit(data)
    app = create_app()
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: decide(proposal_id, app=app), range(2)))
    assert sorted(r.status_code for r in results) == [200, 409], [r.text for r in results]
    assert decide(proposal_id).status_code == 409
    with get_engine().connect() as connection:
        assert connection.scalar(select(func.count()).select_from(m.financial_reference_node).where(m.financial_reference_node.c.canonical_name == data['canonicalName'])) == 1
        assert connection.scalar(select(func.count()).select_from(m.reference_data_approval).where(m.reference_data_approval.c.reference_data_proposal_id == UUID(proposal_id))) == 1


def test_rejection_and_tenant_permissions(reference):
    data = proposal(reference)
    assert request('POST', '/v1/instruments/swap-proposals', data, tenant='second_tenant').status_code == 403
    proposal_id = submit(data)
    assert decide(proposal_id, tenant='second_tenant').status_code == 404
    rejected = decide(proposal_id, 'REJECTED')
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()['data']['status'] == 'REJECTED'
    assert rejected.json()['data']['referenceNodeId'] is None
    assert rejected.json()['data']['decisionReason'] == 'Synthetic confirmation checked.'


def test_non_admin_cannot_submit_or_approve(reference):
    data = proposal(reference)
    proposal_id = submit(data)
    with get_engine().begin() as connection:
        connection.execute(m.tenant_user_account.update().where(m.tenant_user_account.c.tenant_user_account_id == DEMO_IDS['demo_tenant_membership']).values(membership_role='OPERATIONS'))
    try:
        assert request('POST', '/v1/instruments/swap-proposals', data).status_code == 403
        assert decide(proposal_id).status_code == 409
    finally:
        with get_engine().begin() as connection:
            connection.execute(m.tenant_user_account.update().where(m.tenant_user_account.c.tenant_user_account_id == DEMO_IDS['demo_tenant_membership']).values(membership_role='TENANT_ADMIN'))


def clone_profile(code, **changes):
    with get_engine().begin() as connection:
        row = dict(connection.execute(select(m.return_profile).where(m.return_profile.c.profile_code == code)).mappings().one())
        node = uuid4()
        row.update(return_profile_id=node, profile_code=f'TEST_{node.hex}', **changes)
        connection.execute(m.return_profile.insert().values(**row))
    return node


@pytest.mark.parametrize('changes', [dict(base_return_basis='PRICE'), dict(financing_treatment='SUBTRACT_REFERENCE_RATE'),
    dict(requires_financing_reference=True), dict(status='RETIRED')])
def test_incompatible_governed_total_return_profile_is_rejected(reference, changes):
    profile = clone_profile('GROSS_TOTAL_RETURN', **changes)
    response = request('POST', '/v1/instruments/swap-proposals', proposal(reference, returnProfileId=str(profile)))
    assert response.status_code == 422, response.text


@pytest.mark.parametrize('funded', [False, True])
def test_excess_return_uses_governed_embedded_financing_profile(reference, funded):
    profile = clone_profile('EXCESS_TOTAL_RETURN')
    terms = dict(returnProfileId=str(profile), returnBasis='EXCESS',
        financingTreatment='EMBEDDED_AND_SEPARATE' if funded else 'EMBEDDED')
    if funded:
        terms.update(additionalFundingAcknowledged=True, additionalFundingEvidence='Confirmation explicitly charges additional financing.')
    result = decide(submit(proposal(reference, funded, **terms)))
    assert result.status_code == 200, result.text


@pytest.mark.parametrize('active', [False, True])
def test_governed_index_performance_reference_must_be_active(reference, active):
    with get_engine().begin() as connection:
        node = uuid4()
        values = dict(connection.execute(select(m.financial_reference_node).where(m.financial_reference_node.c.reference_node_id == DEMO_IDS['mvp_sp500_price_index_node'])).mappings().one())
        values.update(reference_node_id=node, canonical_name=f'Test index {node}', internal_code=f'IDX_{node.hex}')
        connection.execute(m.financial_reference_node.insert().values(**values))
        values = dict(connection.execute(select(m.index_terms).where(m.index_terms.c.index_node_id == DEMO_IDS['mvp_sp500_price_index_node'])).mappings().one())
        values.update(index_node_id=node, status='ACTIVE' if active else 'RETIRED')
        connection.execute(m.index_terms.insert().values(**values))
    response = request('POST', '/v1/instruments/swap-proposals', proposal(node))
    assert response.status_code == (201 if active else 422), response.text
    if active:
        assert decide(response.json()['data']['proposalId']).status_code == 200


@pytest.mark.parametrize('what', ['rate', 'daycount', 'profile'])
def test_approval_rechecks_funding_catalogue_and_status(reference, what):
    data = proposal(reference, True)
    with get_engine().begin() as connection:
        if what == 'rate':
            table, key = m.financial_reference_node, 'reference_node_id'
            identifier = uuid4()
            values = dict(connection.execute(select(table).where(table.c[key] == DEMO_IDS['sonia_rate_index_node'])).mappings().one())
            values.update(reference_node_id=identifier, internal_code=f'RATE_{identifier.hex}')
            connection.execute(table.insert().values(**values))
            data['terms']['fundingReferenceId'] = str(identifier)
        elif what == 'daycount':
            table, key = m.day_count_convention, 'day_count_convention_id'
            values = dict(connection.execute(select(table).where(table.c[key] == UUID(data['terms']['dayCountConventionId']))).mappings().one())
            identifier = uuid4()
            values.update(day_count_convention_id=identifier, code=f'TEST_{identifier.hex[:20]}')
            connection.execute(table.insert().values(**values))
            data['terms']['dayCountConventionId'] = str(identifier)
        else:
            table, key = m.return_profile, 'return_profile_id'
            identifier = clone_profile('GROSS_TOTAL_RETURN')
            data['terms']['returnProfileId'] = str(identifier)
    proposal_id = submit(data)
    with get_engine().begin() as connection:
        connection.execute(table.update().where(table.c[key] == identifier).values(status='RETIRED'))
    assert decide(proposal_id).status_code in {404, 409}
    with get_engine().connect() as connection:
        assert connection.scalar(select(func.count()).select_from(m.financial_reference_node).where(m.financial_reference_node.c.canonical_name == data['canonicalName'])) == 0


def test_failure_after_identity_insert_rolls_back_materialization(reference):
    data = proposal(reference)
    proposal_id = submit(data)
    with get_engine().begin() as connection:
        connection.execute(m.instrument_type.update().where(m.instrument_type.c.type_code == 'SWAP').values(status='RETIRED'))
    try:
        response = decide(proposal_id)
        assert response.status_code == 409, response.text
        with get_engine().connect() as connection:
            assert connection.scalar(select(func.count()).select_from(m.financial_reference_node).where(m.financial_reference_node.c.canonical_name == data['canonicalName'])) == 0
            assert connection.scalar(select(func.count()).select_from(m.reference_data_approval).where(m.reference_data_approval.c.reference_data_proposal_id == UUID(proposal_id))) == 0
    finally:
        with get_engine().begin() as connection:
            connection.execute(m.instrument_type.update().where(m.instrument_type.c.type_code == 'SWAP').values(status='ACTIVE'))


def test_instrument_inspection_does_not_expose_newly_hidden_reference(reference):
    node = decide(submit(proposal(reference))).json()['data']['referenceNodeId']
    with get_engine().begin() as connection:
        connection.execute(m.reference_node_scope.update().where(m.reference_node_scope.c.reference_node_id == reference).values(owner_tenant_id=DEMO_IDS['second_tenant']))
    detail = request('GET', f'/v1/instruments/{node}')
    assert detail.status_code == 200, detail.text
    assert detail.json()['data']['genericTerms'] is None
    assert str(reference) not in detail.text


def test_instrument_inspection_hides_swap_with_retired_visibility_scope(reference):
    node = decide(submit(proposal(reference))).json()['data']['referenceNodeId']
    with get_engine().begin() as connection:
        connection.execute(m.reference_node_scope.update().where(m.reference_node_scope.c.reference_node_id == UUID(node)).values(status='RETIRED'))
    response = request('GET', f'/v1/instruments/{node}')
    assert response.status_code == 404, response.text
    assert 'Synthetic generic swap' not in response.text


def test_validation_locks_reference_scope_and_governed_rows(reference):
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError
    from apps.reference_api.swap_creation import validate_swap_references
    from apps.reference_api.swap_creation_contracts import GenericSwapTerms
    terms = GenericSwapTerms.model_validate(proposal(reference, True)['terms'])
    with get_engine().begin() as approving:
        facts = validate_swap_references(approving, DEMO_IDS['tenant'], terms, lock=True)
        assert facts['performanceReference']['reference_node_id'] == reference
        for table, key, value in ((m.reference_node_scope, 'reference_node_id', reference),
                (m.financial_reference_node, 'reference_node_id', terms.funding_reference_id),
                (m.return_profile, 'return_profile_id', terms.return_profile_id),
                (m.day_count_convention, 'day_count_convention_id', terms.day_count_convention_id)):
            with get_engine().begin() as concurrent:
                concurrent.execute(text("SET LOCAL lock_timeout = '50ms'"))
                with pytest.raises(DBAPIError) as error, concurrent.begin_nested():
                    concurrent.execute(table.update().where(table.c[key] == value).values(status='RETIRED'))
                assert error.value.orig.sqlstate == '55P03'


def create_index(profile_id):
    with get_engine().begin() as connection:
        node = uuid4()
        values = dict(connection.execute(select(m.financial_reference_node).where(m.financial_reference_node.c.reference_node_id == DEMO_IDS['mvp_sp500_price_index_node'])).mappings().one())
        values.update(reference_node_id=node, canonical_name=f'Profiled index {node}', internal_code=f'IDX_{node.hex}')
        connection.execute(m.financial_reference_node.insert().values(**values))
        values = dict(connection.execute(select(m.index_terms).where(m.index_terms.c.index_node_id == DEMO_IDS['mvp_sp500_price_index_node'])).mappings().one())
        values.update(index_node_id=node, return_profile_id=profile_id)
        connection.execute(m.index_terms.insert().values(**values))
    return node


@pytest.mark.parametrize('funded', [False, True])
def test_excess_index_cannot_be_declared_as_unfinanced_total_return(funded):
    node = create_index(clone_profile('EXCESS_TOTAL_RETURN'))
    response = request('POST', '/v1/instruments/swap-proposals', proposal(node, funded))
    assert response.status_code == 422, response.text


@pytest.mark.parametrize('funded', [False, True])
def test_excess_index_preserves_embedded_financing_and_optional_acknowledged_charge(funded):
    profile = clone_profile('EXCESS_TOTAL_RETURN')
    node = create_index(profile)
    changes = dict(returnBasis='EXCESS', returnProfileId=str(profile),
        financingTreatment='EMBEDDED_AND_SEPARATE' if funded else 'EMBEDDED')
    if funded:
        changes.update(additionalFundingAcknowledged=True, additionalFundingEvidence='Explicit additional charge in confirmation.')
    data = proposal(node, funded, **changes)
    result = decide(submit(data))
    assert result.status_code == 200, result.text
    from apps.reference_api.swap_creation import validate_swap_references
    from apps.reference_api.swap_creation_contracts import GenericSwapTerms
    with get_engine().connect() as connection:
        facts = validate_swap_references(connection, DEMO_IDS['tenant'], GenericSwapTerms.model_validate(data['terms']))
    assert facts.get('performanceReferenceProfile', {}).get('return_profile_id') == profile
    assert facts['performanceReferenceProfile']['financing_treatment'] == 'SUBTRACT_REFERENCE_RATE'


@pytest.mark.parametrize('change', ['financing', 'retired'])
def test_approval_rechecks_reference_index_profile_without_partial_instrument(change):
    profile = clone_profile('GROSS_TOTAL_RETURN')
    node = create_index(profile)
    data = proposal(node)
    proposal_id = submit(data)
    with get_engine().begin() as connection:
        changes = dict(financing_treatment='SUBTRACT_REFERENCE_RATE', requires_financing_reference=True) if change == 'financing' else dict(status='RETIRED')
        connection.execute(m.return_profile.update().where(m.return_profile.c.return_profile_id == profile).values(**changes))
    response = decide(proposal_id)
    assert response.status_code == 409, response.text
    with get_engine().connect() as connection:
        assert connection.scalar(select(func.count()).select_from(m.financial_reference_node).where(m.financial_reference_node.c.canonical_name == data['canonicalName'])) == 0


def test_approval_locks_reference_index_profile_for_booking_facts():
    from apps.reference_api.swap_creation import validate_swap_references
    from apps.reference_api.swap_creation_contracts import GenericSwapTerms
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError
    profile = clone_profile('GROSS_TOTAL_RETURN')
    node = create_index(profile)
    with get_engine().begin() as approving:
        validate_swap_references(approving, DEMO_IDS['tenant'], GenericSwapTerms.model_validate(proposal(node)['terms']), lock=True)
        with get_engine().begin() as concurrent:
            concurrent.execute(text("SET LOCAL lock_timeout = '50ms'"))
            with pytest.raises(DBAPIError) as error, concurrent.begin_nested():
                concurrent.execute(m.return_profile.update().where(m.return_profile.c.return_profile_id == profile).values(status='RETIRED'))
            assert error.value.orig.sqlstate == '55P03'


def test_distinct_proposal_approvals_do_not_deadlock_on_opposing_reference_type_order():
    """Two currencies and opposing UUID orders expose the former global type cycle."""
    from threading import Event, Lock
    from sqlalchemy import event
    from sqlalchemy.exc import DBAPIError
    from apps.reference_api.main import create_app

    def node_id(prefix):
        return UUID(int=(prefix << 96) | (uuid4().int & ((1 << 96) - 1)))

    references = [create_reference(node_id=node_id(1)), create_reference(node_id=node_id(4))]
    rates = [node_id(2), node_id(3)]
    currencies = [uuid4(), uuid4()]
    with get_engine().begin() as connection:
        for index in range(2):
            rate = dict(connection.execute(select(m.financial_reference_node).where(m.financial_reference_node.c.reference_node_id == DEMO_IDS['sonia_rate_index_node'])).mappings().one())
            rate.update(reference_node_id=rates[index], internal_code=f'RATE_{rates[index].hex}')
            connection.execute(m.financial_reference_node.insert().values(**rate))
            currency = dict(connection.execute(select(m.currency).where(m.currency.c.currency_id == DEMO_IDS['gbp_currency'])).mappings().one())
            currency.update(currency_id=currencies[index], currency_code='TAA' if index == 0 else 'TAB', reference_node_id=None)
            connection.execute(m.currency.insert().values(**currency))
    data = [proposal(references[index], True, fundingReferenceId=str(rates[index]),
        notionalCurrencyId=str(currencies[index]), quoteCurrencyId=str(currencies[index])) for index in range(2)]
    proposals = [submit(item) for item in data]
    app = create_app()  # Construct schema once before the concurrent HTTP requests.
    first_types_acquired, guard, both_started = set(), Lock(), Event()

    def schedule_first_type_locks(connection, cursor, statement, parameters, context, executemany):
        if 'FROM secm.reference_node_type' not in statement or 'FOR UPDATE' not in statement:
            return
        with guard:
            identity = id(connection)
            if identity in first_types_acquired:
                return
            first_types_acquired.add(identity)
            if len(first_types_acquired) == 2:
                both_started.set()
        # Yield after each transaction's first successful type lock. Disjoint
        # first locks reach this point together; one deterministic batch causes
        # the second transaction to wait safely until the first completes.
        both_started.wait(timeout=0.5)

    def approve_distinct(proposal_id):
        try:
            return decide(proposal_id, app=app).status_code
        except DBAPIError as error:
            return error.orig.sqlstate

    engine = get_engine()
    event.listen(engine, 'after_cursor_execute', schedule_first_type_locks)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(approve_distinct, proposals))
    finally:
        event.remove(engine, 'after_cursor_execute', schedule_first_type_locks)
    assert results == [200, 200], results
    with engine.connect() as connection:
        assert connection.scalar(select(func.count()).select_from(m.reference_data_approval).where(m.reference_data_approval.c.reference_data_proposal_id.in_([UUID(item) for item in proposals]))) == 2
