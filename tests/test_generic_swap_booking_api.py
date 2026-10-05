"""Generic contract booking against runner-owned disposable PostgreSQL state."""
from datetime import date
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select, func, text
from sqlalchemy.exc import DBAPIError
from apps.reference_api.db import get_engine
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS
from tests.test_fx_forward_booking_api import request
from tests.test_swap_creation_api import create_reference, proposal, submit, decide, create_index, clone_profile


def create_swap(funded=False, reference=None, **changes):
    data = proposal(reference or create_reference(), funded, **changes)
    response = decide(submit(data))
    assert response.status_code == 200, response.text
    return response.json()['data']['referenceNodeId']


def context(node, as_of='2026-10-01'):
    response = request('GET', f'/v1/trades/product-instruments/{node}?asOfDate={as_of}')
    assert response.status_code == 200, response.text
    return response.json()['data']


def ticket(node, **changes):
    return dict(instrumentId=node, executionRoute='OTC', strategyId=str(DEMO_IDS['strategy']), side='BUY',
        quantity='400000', executionPrice='2', tradeDatetime='2026-10-01T10:00:00Z',
        counterpartyOrganisationId=str(DEMO_IDS['bank_a_organisation']),
        expectedTermsFingerprint=context(node)['termsFingerprint']) | changes


@pytest.mark.parametrize('funded', [False, True])
def test_generic_non_autocall_context_preserves_approved_contract_and_optional_funding(funded):
    node = create_swap(funded)
    value = context(node)
    assert value['bookingEligible'], value
    details = value['swapDetails']
    assert details['genericTerms']['contractualNotional'] == '1000000'
    assert details['genericTerms']['leverage'] == '2'
    assert details['genericTerms']['tenantIdentifier'] == 'CONFIRMATION-42'
    assert details['fundingReferenceId'] == (str(DEMO_IDS['sonia_rate_index_node']) if funded else None)
    assert details['fundingDirection'] == ('PAY' if funded else None)
    assert details['fundingSpread'] is None if not funded else float(details['fundingSpread']) == -0.0015
    facts = details['sourceFacts']
    assert facts['performanceDefinition']['status'] == 'APPROVED'
    assert facts['genericDefinition']['schema_version'] == 1
    assert len(facts['legs']) == (2 if funded else 1)
    assert value['maturityDate'] == '2027-09-01'
    search = request('GET', '/v1/trades/product-instruments?kind=SWAP&route=OTC&q=Synthetic generic&asOfDate=2026-10-01')
    assert any(item['instrumentId'] == node and item['bookingEligible'] for item in search.json()['data'])


@pytest.mark.parametrize('funded', [False, True])
@pytest.mark.parametrize('side,price,want', [('BUY', '2', '8000'), ('BUY', '0', '0'),
    ('BUY', '-1.5', '-6000'), ('SELL', '2', '-8000'), ('SELL', '-1.5', '6000')])
def test_whole_swap_quote_applies_booked_nominal_and_side_once(funded, side, price, want):
    node = create_swap(funded, performanceDirection='PAY')
    data, key = ticket(node, side=side, executionPrice=price), str(uuid4())
    with get_engine().connect() as connection:
        before = connection.scalar(select(func.count()).select_from(m.trade))
    response = request('POST', '/v1/trades/swaps', data, key)
    assert response.status_code == 201, response.text
    trade = response.json()['data']['trade']; economics = trade['productEconomics']
    assert economics['amount'] == want
    assert economics['amountKind'] == 'ENTRY_REFERENCE_VALUE' and economics['direction'] is None
    assert float(economics['bookedNotional']) == 400000
    assert economics['terms']['swapDetails']['genericTerms']['contractualNotional'] == '1000000'
    assert trade['settlementDate'] is None
    assert float(trade['quantity']) == (-400000 if side == 'SELL' else 400000)
    replay = request('POST', '/v1/trades/swaps', data, key)
    assert replay.json()['data']['trade']['tradeId'] == trade['tradeId']
    with get_engine().connect() as connection:
        assert connection.scalar(select(func.count()).select_from(m.trade)) == before + 1
        events = connection.execute(select(m.trade_lifecycle_event.c.event_type).where(m.trade_lifecycle_event.c.trade_id == UUID(trade['tradeId']))).scalars().all()
        assert events == ['BOOKED']


@pytest.mark.parametrize('as_of,eligible', [('2026-08-31', False), ('2026-09-01', True),
    ('2027-08-31', True), ('2027-09-01', False)])
def test_execution_effective_boundary_inclusive_and_maturity_exclusive(as_of, eligible):
    node = create_swap()
    assert context(node, as_of)['bookingEligible'] is eligible
    data = ticket(node, tradeDatetime=f'{as_of}T10:00:00Z')
    data['expectedTermsFingerprint'] = context(node, as_of)['termsFingerprint'] or data['expectedTermsFingerprint']
    response = request('POST', '/v1/trades/swaps', data)
    assert response.status_code == (201 if eligible else 422), response.text


def test_governed_index_source_profile_is_independent_and_preserved():
    source_profile = clone_profile('EXCESS_TOTAL_RETURN')
    selected_profile = clone_profile('EXCESS_TOTAL_RETURN')
    reference = create_index(source_profile)
    node = create_swap(reference=reference, returnBasis='EXCESS', returnProfileId=str(selected_profile), financingTreatment='EMBEDDED')
    value = context(node)
    assert value['bookingEligible'], value
    facts = value['swapDetails']['sourceFacts']
    assert facts['performanceIndex']['index_node_id'] == str(reference)
    assert facts['performanceReferenceProfile']['return_profile_id'] == str(source_profile)
    assert facts['returnProfile']['return_profile_id'] == str(selected_profile)
    data = ticket(node)
    with get_engine().begin() as connection:
        connection.execute(m.return_profile.update().where(m.return_profile.c.return_profile_id == source_profile).values(display_name='Corrected source label'))
    stale = request('POST', '/v1/trades/swaps', data)
    assert stale.status_code == 409, stale.text


@pytest.mark.parametrize('change', ['definition', 'funding', 'reference', 'profile', 'daycount', 'dates'])
def test_changed_economic_source_facts_invalidate_review(change):
    node = create_swap(True)
    data = ticket(node)
    with get_engine().begin() as connection:
        definition_id = connection.scalar(select(m.instrument_definition_version.c.instrument_definition_version_id).where(m.instrument_definition_version.c.instrument_node_id == UUID(node)))
        if change == 'definition':
            table = m.swap_definition_version
            row = connection.execute(select(table).where(table.c.instrument_definition_version_id == definition_id)).mappings().one()
            payload = row.economics_payload | {'leverage': '3'}
            connection.execute(table.update().where(table.c.instrument_definition_version_id == definition_id).values(economics_payload=payload))
        elif change == 'funding':
            connection.execute(m.swap_leg.update().where(m.swap_leg.c.swap_instrument_node_id == UUID(node), m.swap_leg.c.leg_role == 'FUNDING').values(spread='0.015'))
        elif change == 'reference':
            ref = context(node)['swapDetails']['performanceReferenceId']
            connection.execute(m.financial_reference_node.update().where(m.financial_reference_node.c.reference_node_id == UUID(ref)).values(canonical_name='Corrected reference name'))
        elif change == 'profile':
            profile = UUID(context(node)['swapDetails']['genericTerms']['returnProfileId'])
            connection.execute(m.return_profile.update().where(m.return_profile.c.return_profile_id == profile).values(display_name='Corrected profile name'))
        elif change == 'daycount':
            daycount = UUID(context(node)['swapDetails']['genericTerms']['dayCountConventionId'])
            connection.execute(m.day_count_convention.update().where(m.day_count_convention.c.day_count_convention_id == daycount).values(display_name='Corrected day-count name'))
        else:
            connection.execute(m.instrument_dates.update().where(m.instrument_dates.c.instrument_node_id == UUID(node)).values(maturity_date=date(2027, 8, 31)))
    response = request('POST', '/v1/trades/swaps', data)
    assert response.status_code in {409, 422}, response.text


@pytest.mark.parametrize('funding', [False, True])
@pytest.mark.parametrize('change', ['private', 'retired'])
def test_hidden_or_retired_reference_cannot_be_booked_or_disclosed(funding, change):
    reference = create_reference()
    node = create_swap(funding, reference)
    value = context(node)
    assert value['bookingEligible'], value
    data = ticket(node)
    reference = DEMO_IDS['sonia_rate_index_node'] if funding else reference
    with get_engine().begin() as connection:
        if change == 'private':
            connection.execute(m.reference_node_scope.insert().values(reference_node_id=reference, scope_type='TENANT_PRIVATE', owner_tenant_id=DEMO_IDS['second_tenant'], status='ACTIVE')) if funding else connection.execute(m.reference_node_scope.update().where(m.reference_node_scope.c.reference_node_id == reference).values(owner_tenant_id=DEMO_IDS['second_tenant']))
        else:
            connection.execute(m.financial_reference_node.update().where(m.financial_reference_node.c.reference_node_id == reference).values(status='RETIRED'))
    try:
        assert request('POST', '/v1/trades/swaps', data).status_code == 404
        response = request('GET', f'/v1/trades/product-instruments/{node}?asOfDate=2026-10-01')
        assert response.status_code == 404 or not response.json()['data']['bookingEligible']
        assert str(reference) not in response.text
    finally:
        if funding:
            with get_engine().begin() as connection:
                if change == 'private':
                    connection.execute(m.reference_node_scope.delete().where(m.reference_node_scope.c.reference_node_id == reference, m.reference_node_scope.c.owner_tenant_id == DEMO_IDS['second_tenant']))
                else:
                    connection.execute(m.financial_reference_node.update().where(m.financial_reference_node.c.reference_node_id == reference).values(status='ACTIVE'))


def test_historical_generic_snapshot_and_idempotent_replay_survive_new_terms():
    node = create_swap(True)
    data, key = ticket(node), str(uuid4())
    booked = request('POST', '/v1/trades/swaps', data, key)
    assert booked.status_code == 201, booked.text
    trade = booked.json()['data']['trade']; original = trade['productEconomics']
    with get_engine().begin() as connection:
        row = connection.execute(select(m.swap_definition_version).join(m.instrument_definition_version, m.swap_definition_version.c.instrument_definition_version_id == m.instrument_definition_version.c.instrument_definition_version_id).where(m.instrument_definition_version.c.instrument_node_id == UUID(node))).mappings().one()
        connection.execute(m.swap_definition_version.update().where(m.swap_definition_version.c.instrument_definition_version_id == row.instrument_definition_version_id).values(economics_payload=row.economics_payload | {'contractualNotional': '3000000', 'leverage': '4'}))
    assert request('GET', f"/v1/trades/{trade['tradeId']}").json()['data']['trade']['productEconomics'] == original
    assert request('POST', '/v1/trades/swaps', data, key).json()['data']['trade']['productEconomics'] == original
    assert request('POST', '/v1/trades/swaps', data).status_code == 409


def test_failure_after_trade_insert_rolls_back_all_evidence(monkeypatch):
    from apps.reference_api import repository
    node = create_swap(); data = ticket(node); key = str(uuid4())
    def fail(*args, **kwargs):
        raise RuntimeError('Synthetic persistence failure')
    monkeypatch.setattr(repository, 'persist_trade_annotations', fail)
    with get_engine().connect() as connection:
        before = connection.scalar(select(func.count()).select_from(m.trade))
    with pytest.raises(RuntimeError, match='Synthetic persistence failure'):
        request('POST', '/v1/trades/swaps', data, key)
    with get_engine().connect() as connection:
        assert connection.scalar(select(func.count()).select_from(m.trade)) == before
        assert not connection.scalar(select(m.trade_booking_idempotency.c.trade_id).where(m.trade_booking_idempotency.c.idempotency_key == key))


def test_required_custom_properties_and_settlement_input():
    from apps.reference_api.trade_configuration import create_property, retire_property
    node = create_swap(); data = ticket(node); tenant = DEMO_IDS['tenant']; actor = DEMO_IDS['demo_user_account']
    definitions = []
    try:
        with get_engine().begin() as connection:
            for kind in ['BOOLEAN', 'DECIMAL']:
                definitions.append(create_property(connection, tenant, actor, dict(code='GENERIC_'+uuid4().hex,
                    label='Synthetic generic '+kind, valueType=kind, required=True, acknowledgeRequiredImpact=True, choices=[]))['definitionId'])
        assert request('POST', '/v1/trades/swaps', data).status_code == 422
        data['properties'] = [dict(definitionId=str(definitions[0]), value=False), dict(definitionId=str(definitions[1]), value='0')]
        assert request('POST', '/v1/trades/swaps', data | {'settlementDate': '2026-10-05'}).status_code == 422
        response = request('POST', '/v1/trades/swaps', data)
        assert response.status_code == 201, response.text
        assert {str(p['definitionId']): p['value'] for p in response.json()['data']['properties']} == {str(definitions[0]): False, str(definitions[1]): '0'}
    finally:
        with get_engine().begin() as connection:
            for identifier in definitions:
                retire_property(connection, tenant, actor, identifier)


def test_generic_booking_locks_definition_leg_and_source_profile():
    from apps.reference_api.product_booking import load_context
    profile = clone_profile('GROSS_TOTAL_RETURN'); reference = create_index(profile)
    node = UUID(create_swap(True, reference))
    with get_engine().begin() as booking:
        value = load_context(booking, DEMO_IDS['tenant'], node, as_of=date(2026, 10, 1), lock=True)
        assert value.booking_eligible, value
        definition = booking.scalar(select(m.instrument_definition_version.c.instrument_definition_version_id).where(m.instrument_definition_version.c.instrument_node_id == node))
        updates = [(m.swap_definition_version, 'instrument_definition_version_id', definition, dict(schema_version=1)),
            (m.swap_leg, 'swap_instrument_node_id', node, dict(spread='0.015')),
            (m.return_profile, 'return_profile_id', profile, dict(status='RETIRED')),
            (m.index_terms, 'index_node_id', reference, dict(status='RETIRED'))]
        for table, key, identifier, changes in updates:
            with get_engine().begin() as competing:
                competing.execute(text("SET LOCAL lock_timeout = '50ms'"))
                with pytest.raises(DBAPIError) as error, competing.begin_nested():
                    competing.execute(table.update().where(table.c[key] == identifier).values(**changes))
                assert error.value.orig.sqlstate == '55P03'


def test_direct_generic_loader_locks_contract_identity_and_visibility():
    from apps.reference_api.generic_swap_booking import load_generic_swap_context
    node = UUID(create_swap())
    with get_engine().begin() as booking:
        load_generic_swap_context(booking, DEMO_IDS['tenant'], node, date(2026, 10, 1), lock=True)
        for table, changes in [(m.financial_reference_node, dict(status='RETIRED')),
                (m.reference_node_scope, dict(status='RETIRED'))]:
            with get_engine().begin() as competing:
                competing.execute(text("SET LOCAL lock_timeout = '50ms'"))
                with pytest.raises(DBAPIError) as error, competing.begin_nested():
                    competing.execute(table.update().where(table.c.reference_node_id == node).values(**changes))
                assert error.value.orig.sqlstate == '55P03'


def test_source_instrument_type_catalogue_edit_changes_review_fingerprint():
    from apps.reference_api.product_booking import load_context
    node = UUID(create_swap())
    with get_engine().connect() as connection:
        transaction = connection.begin()
        try:
            before = load_context(connection, DEMO_IDS['tenant'], node, as_of=date(2026, 10, 1))
            assert before.booking_eligible
            connection.execute(m.instrument_type.update().where(m.instrument_type.c.type_code == 'BOND').values(display_name='Corrected source instrument type'))
            after = load_context(connection, DEMO_IDS['tenant'], node, as_of=date(2026, 10, 1))
            assert after.booking_eligible
            assert before.terms_fingerprint != after.terms_fingerprint
        finally:
            transaction.rollback()


def test_direct_generic_loader_rejects_retired_contract_type():
    from apps.reference_api.generic_swap_booking import load_generic_swap_context
    node = UUID(create_swap())
    with get_engine().connect() as connection:
        transaction = connection.begin()
        try:
            connection.execute(m.instrument_type.update().where(m.instrument_type.c.type_code == 'SWAP').values(status='RETIRED'))
            with pytest.raises(ValueError, match='active'):
                load_generic_swap_context(connection, DEMO_IDS['tenant'], node, date(2026, 10, 1))
        finally:
            transaction.rollback()


def test_performance_instrument_effectiveness_is_checked_at_execution_date():
    reference = create_reference(effective_to=date(2026, 11, 1))
    node = create_swap(reference=reference)
    assert context(node, '2026-11-01')['bookingEligible']
    assert not context(node, '2026-11-02')['bookingEligible']


@pytest.mark.parametrize('quantity', ['0.000000000001', '1000000.25', '3000000'])
def test_positive_booked_nominal_can_differ_from_contract_without_capacity_limit(quantity):
    node = create_swap()
    response = request('POST', '/v1/trades/swaps', ticket(node, quantity=quantity, executionPrice='0'))
    assert response.status_code == 201, response.text
    economics = response.json()['data']['trade']['productEconomics']
    assert float(economics['bookedNotional']) == float(quantity)
    assert economics['amount'] == '0'


def test_legacy_economics_serialization_omits_absent_booked_notional():
    from apps.reference_api.product_booking_contracts import ProductTradeEconomicsView
    historic = dict(terms=dict(instrumentId=str(uuid4()), name='Historic swap', kind='SWAP', executionRoute='OTC'),
        amount='20000', amountKind='ENTRY_REFERENCE_VALUE', direction=None)
    serialized = ProductTradeEconomicsView.model_validate(historic).model_dump(mode='json', by_alias=True)
    assert 'bookedNotional' not in serialized


def test_invalid_current_generic_payload_cannot_fall_back_to_legacy():
    from apps.reference_api.swap_booking import load_swap_context
    from tests.test_swap_booking_api import swap
    node = UUID(swap.__wrapped__())
    with get_engine().connect() as connection:
        transaction = connection.begin()
        try:
            definition = connection.scalar(select(m.instrument_definition_version.c.instrument_definition_version_id).where(m.instrument_definition_version.c.instrument_node_id == node))
            payload = proposal(DEMO_IDS['autocall_instrument_node'])['terms'] | {'schemaVersion': 1, 'contractualNotional': '-1'}
            connection.execute(m.swap_definition_version.insert().values(instrument_definition_version_id=definition, schema_version=1, economics_payload=payload))
            with pytest.raises(ValueError, match='contractualNotional'):
                load_swap_context(connection, DEMO_IDS['tenant'], node, date(2026, 10, 1))
        finally:
            transaction.rollback()


@pytest.mark.parametrize('change', ['schedule', 'performance_spread', 'funding_profile'])
def test_untyped_leg_economics_cannot_be_accepted_by_refreshing_ticket(change):
    node = create_swap(True)
    assert context(node)['bookingEligible']
    with get_engine().begin() as connection:
        predicate = m.swap_leg.c.swap_instrument_node_id == UUID(node)
        if change == 'schedule':
            schedule = connection.scalar(m.schedule.insert().values(owner_reference_node_id=UUID(node), schedule_type='RESET_PAYMENT').returning(m.schedule.c.schedule_id))
            connection.execute(m.swap_leg.update().where(predicate).values(schedule_id=schedule))
        elif change == 'performance_spread':
            connection.execute(m.swap_leg.update().where(predicate, m.swap_leg.c.leg_role == 'PERFORMANCE').values(spread='0.02'))
        else:
            profile = connection.scalar(select(m.swap_leg.c.return_profile_id).where(predicate, m.swap_leg.c.leg_role == 'PERFORMANCE'))
            connection.execute(m.swap_leg.update().where(predicate, m.swap_leg.c.leg_role == 'FUNDING').values(return_profile_id=profile))
    assert not context(node)['bookingEligible']


@pytest.mark.parametrize('entry_point', ['product_booking', 'direct_loader', 'proposal_approval'])
def test_direct_bond_booking_and_swap_source_path_do_not_deadlock(entry_point):
    """Observe actual locks to schedule the former currency/identity cycle."""
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from sqlalchemy import event
    from apps.reference_api import product_booking as service
    from apps.reference_api.generic_swap_booking import load_generic_swap_context
    from apps.reference_api.product_booking_contracts import ProductBookingRequest
    from tests.test_bond_booking_api import bond as bond_fixture, ticket as bond_ticket

    bond = bond_fixture.__wrapped__()
    node = UUID(create_swap(reference=UUID(bond)))
    bond_request = ProductBookingRequest.model_validate(bond_ticket(bond))
    swap_request = ProductBookingRequest.model_validate(ticket(str(node)))
    proposal_id = UUID(submit(proposal(UUID(bond)))) if entry_point == 'proposal_approval' else None
    bond_identity_acquired = Event()
    swap_currency_attempted = Event()
    swap_currency_acquired = Event()
    engine = get_engine()

    def before_execute(connection, cursor, statement, parameters, execution_context, executemany):
        if (connection.info.get('cross_path_role') == 'swap' and 'FROM secm.currency' in statement
                and 'FOR UPDATE' in statement):
            swap_currency_attempted.set()

    def after_execute(connection, cursor, statement, parameters, execution_context, executemany):
        if 'FOR UPDATE' not in statement:
            return
        role = connection.info.get('cross_path_role')
        if 'FROM secm.currency' in statement:
            if role == 'swap':
                swap_currency_acquired.set()
            elif role == 'bond':
                connection.info['cross_path_currency_held'] = True
        if (role == 'bond' and 'FROM secm.financial_reference_node' in statement
                and not bond_identity_acquired.is_set()):
            bond_identity_acquired.set()
            # Original code holds bond identity while the other transaction
            # acquires currency. Correct code already holds currency; release
            # it after observing the other transaction's real lock attempt.
            pending = swap_currency_attempted if connection.info.get('cross_path_currency_held') else swap_currency_acquired
            assert pending.wait(timeout=5), 'Swap did not reach the currency lock.'

    def run(role):
        try:
            with engine.begin() as connection:
                connection.info['cross_path_role'] = role
                try:
                    connection.execute(text("SET LOCAL statement_timeout = '10s'"))
                    if role == 'bond':
                        result = service.book(connection, DEMO_IDS['tenant'], DEMO_IDS['demo_user_account'],
                            bond_request, str(uuid4()), 'BOND', 'cross-path-bond')
                        return ('BOOKED', str(result.data.trade.trade_id))
                    if entry_point == 'product_booking':
                        result = service.book(connection, DEMO_IDS['tenant'], DEMO_IDS['demo_user_account'],
                            swap_request, str(uuid4()), 'SWAP', 'cross-path-swap')
                        return ('BOOKED', str(result.data.trade.trade_id))
                    if entry_point == 'direct_loader':
                        details, maturity = load_generic_swap_context(connection, DEMO_IDS['tenant'], node, date(2026, 10, 1), lock=True)
                        assert details.generic_terms.contractual_notional == 1000000
                        return ('LOADED', str(node))
                    result = service.decide_proposal(connection, DEMO_IDS['tenant'], DEMO_IDS['demo_user_account'],
                        proposal_id, 'APPROVED', 'Synthetic source verified under concurrent booking.')
                    return ('APPROVED', str(result.reference_node_id))
                finally:
                    connection.info.pop('cross_path_role', None)
                    connection.info.pop('cross_path_currency_held', None)
        except DBAPIError as error:
            return (error.orig.sqlstate, None)

    event.listen(engine, 'before_cursor_execute', before_execute)
    event.listen(engine, 'after_cursor_execute', after_execute)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            bond_work = pool.submit(run, 'bond')
            assert bond_identity_acquired.wait(timeout=5), 'Bond did not acquire its identity.'
            swap_work = pool.submit(run, 'swap')
            results = [bond_work.result(timeout=20), swap_work.result(timeout=20)]
    finally:
        event.remove(engine, 'before_cursor_execute', before_execute)
        event.remove(engine, 'after_cursor_execute', after_execute)
    expected = {'product_booking': 'BOOKED', 'direct_loader': 'LOADED', 'proposal_approval': 'APPROVED'}[entry_point]
    assert [status for status, identifier in results] == ['BOOKED', expected], results
    with engine.connect() as connection:
        trade_ids = [UUID(identifier) for status, identifier in results if status == 'BOOKED']
        assert connection.scalar(select(func.count()).select_from(m.trade).where(m.trade.c.trade_id.in_(trade_ids))) == len(trade_ids)


@pytest.mark.parametrize('entry_point', ['product_context', 'direct_loader'])
def test_currency_discovery_drift_is_rejected_without_late_currency_lock(entry_point):
    from sqlalchemy import event
    from apps.reference_api.product_booking import load_context
    from apps.reference_api.generic_swap_booking import load_generic_swap_context
    node = UUID(create_swap())
    engine = get_engine()
    currencies_locked = []
    changed = {'done': False}

    def change_after_discovery(connection, cursor, statement, parameters, execution_context, executemany):
        if (connection.info.get('discovery_drift') and 'FROM secm.currency' in statement
                and 'FOR UPDATE' in statement and not changed['done']):
            changed['done'] = True
            # An actual distinct transaction changes the discovered currency
            # before booking owns the instrument; no DB triggers are bypassed.
            with engine.begin() as editing:
                editing.execute(text("SET LOCAL statement_timeout = '2s'"))
                editing.execute(m.instrument.update().where(m.instrument.c.instrument_node_id == node)
                    .values(base_currency_id=DEMO_IDS['usd_currency']))

    def record_acquired_currency(connection, cursor, statement, parameters, execution_context, executemany):
        if connection.info.get('discovery_drift') and 'FROM secm.currency' in statement and 'FOR UPDATE' in statement:
            currencies_locked.extend(value for value in parameters.values() if isinstance(value, UUID))

    event.listen(engine, 'before_cursor_execute', change_after_discovery)
    event.listen(engine, 'after_cursor_execute', record_acquired_currency)
    try:
        with engine.begin() as booking:
            booking.info['discovery_drift'] = True
            try:
                if entry_point == 'product_context':
                    value = load_context(booking, DEMO_IDS['tenant'], node, as_of=date(2026, 10, 1), lock=True)
                    assert not value.booking_eligible
                    assert 'currency changed' in value.ineligibility_message
                else:
                    with pytest.raises(ValueError, match='currency changed'):
                        load_generic_swap_context(booking, DEMO_IDS['tenant'], node, date(2026, 10, 1), lock=True)
                assert changed['done']
                assert currencies_locked == [DEMO_IDS['gbp_currency']]
                with engine.begin() as competing:
                    # USD was never acquired late by the booking transaction.
                    competing.execute(select(m.currency).where(m.currency.c.currency_id == DEMO_IDS['usd_currency']).with_for_update(nowait=True)).all()
            finally:
                booking.info.pop('discovery_drift', None)
    finally:
        event.remove(engine, 'before_cursor_execute', change_after_discovery)
        event.remove(engine, 'after_cursor_execute', record_acquired_currency)
