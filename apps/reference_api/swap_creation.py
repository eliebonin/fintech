"""Reference governance and atomic materialization of sourced performance swaps."""
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select, or_
from security_master_schema import models as m
from .swap_creation_contracts import GenericSwapTerms, SwapProposalRequest
from .product_booking import ProductBookingError, require_visible, append_convention
from .product_booking_contracts import SwapConvention


def validate_swap_references(connection, tenant_id, terms: GenericSwapTerms, *, lock=False, as_of=None) -> dict:
    """Check canonical facts, locking source rows before rereading at approval."""
    def rows(table, predicate):
        statement = select(table).where(predicate).order_by(*table.primary_key.columns)
        if lock:
            statement = statement.with_for_update()
        return [dict(row) for row in connection.execute(statement).mappings()]

    def checked_active(values, label):
        if len(values) != 1 or values[0]['status'] != 'ACTIVE':
            raise ProductBookingError(f'An active governed {label} is required.')
        return values[0]

    def active(table, predicate, label):
        return checked_active(rows(table, predicate), label)

    # Acquire identities/scopes completely before shared catalogue rows. A type
    # row must never be interleaved with the next identity's UUID lock order.
    node_ids = {terms.performance_reference_id}
    if terms.funding_reference_id:
        node_ids.add(terms.funding_reference_id)
    currency = active(m.currency, m.currency.c.currency_id == terms.notional_currency_id, 'currency')
    if currency['reference_node_id']:
        node_ids.add(currency['reference_node_id'])
    nodes = {}
    for node_id in sorted(node_ids, key=str):
        rows(m.financial_reference_node, m.financial_reference_node.c.reference_node_id == node_id)
        rows(m.reference_node_scope, m.reference_node_scope.c.reference_node_id == node_id)
        node = dict(require_visible(connection, tenant_id, node_id))
        nodes[node_id] = node
    node_types = rows(m.reference_node_type, or_(
        m.reference_node_type.c.reference_node_type_id.in_({node['reference_node_type_id'] for node in nodes.values()}),
        m.reference_node_type.c.type_code == 'INSTRUMENT'))
    types = {node_id: checked_active([item for item in node_types
        if item['reference_node_type_id'] == node['reference_node_type_id']], 'reference type')['type_code']
        for node_id, node in nodes.items()}
    creation_reference_type = next((item for item in node_types if item['type_code'] == 'INSTRUMENT'), None)

    reference_id = terms.performance_reference_id
    definition = index = None
    if types[reference_id] == 'INSTRUMENT':
        instruments = rows(m.instrument, m.instrument.c.instrument_node_id == reference_id)
        definitions = rows(m.instrument_definition_version, m.instrument_definition_version.c.instrument_node_id == reference_id)
        today = as_of or date.today()
        approved = [row for row in definitions if row['status'] == 'APPROVED' and row['is_current']
            and row['effective_from'] <= today and (row['effective_to'] is None or row['effective_to'] >= today)]
        if len(instruments) != 1 or len(approved) != 1 or not instruments[0]['is_current']:
            raise ProductBookingError('An active current approved performance instrument is required.')
        instrument, definition = instruments[0], approved[0]
        if any(instrument[key] != definition[key] for key in ('instrument_type_id', 'base_currency_id',
                'issuer_organisation_id', 'effective_from', 'effective_to', 'sequence_no', 'asset_class')):
            raise ProductBookingError('Performance instrument differs from its approved definition.')
    elif types[reference_id] == 'INDEX':
        index = active(m.index_terms, m.index_terms.c.index_node_id == reference_id, 'performance index')
    else:
        raise ProductBookingError('Performance reference must be an approved instrument or active index.')

    # Include materialization's target type in the same sorted catalogue phase;
    # creation reuses these facts and cannot acquire a late reverse-order lock.
    instrument_types = rows(m.instrument_type, or_(
        m.instrument_type.c.instrument_type_id.in_([definition['instrument_type_id']] if definition else []),
        m.instrument_type.c.type_code == 'SWAP'))
    creation_instrument_type = next((item for item in instrument_types if item['type_code'] == 'SWAP'), None)
    if definition:
        kind = checked_active([item for item in instrument_types
            if item['instrument_type_id'] == definition['instrument_type_id']], 'instrument type')
        if kind['type_code'] == 'SWAP':
            raise ProductBookingError('Swap-on-swap performance references are not supported.')

    profile_ids = {terms.return_profile_id}
    if index:
        if index['return_profile_id'] is None:
            raise ProductBookingError('An active governed reference-index return profile is required.')
        profile_ids.add(index['return_profile_id'])
    # Acquire source and selected profiles together so neither can change while
    # the approval checks whether financing is already embedded in the index.
    rows(m.return_profile, m.return_profile.c.return_profile_id.in_(profile_ids))
    profile = active(m.return_profile, m.return_profile.c.return_profile_id == terms.return_profile_id, 'return profile')
    financing = 'SUBTRACT_REFERENCE_RATE' if terms.return_basis == 'EXCESS' else 'NONE'
    if (profile['base_return_basis'] != 'TOTAL' or profile['financing_treatment'] != financing
            or profile['requires_financing_reference'] != (terms.return_basis == 'EXCESS')):
        raise ProductBookingError('Return profile must agree with the contractual total/excess return and financing treatment.')
    reference_profile = None
    if index:
        reference_profile = active(m.return_profile,
            m.return_profile.c.return_profile_id == index['return_profile_id'], 'reference-index return profile')
        if (reference_profile['financing_treatment'] != financing
                or reference_profile['requires_financing_reference'] != (terms.return_basis == 'EXCESS')):
            raise ProductBookingError('Declared financing must agree with the governed reference-index return profile.')
    funding = daycount = None
    if terms.funding_reference_id:
        if types[terms.funding_reference_id] != 'RATE_INDEX':
            raise ProductBookingError('Funding reference must be an active governed rate index.')
        funding = nodes[terms.funding_reference_id]
        daycount = active(m.day_count_convention,
            m.day_count_convention.c.day_count_convention_id == terms.day_count_convention_id, 'day-count convention')
    return dict(performanceReference=nodes[reference_id], performanceDefinition=definition, performanceIndex=index,
        performanceReferenceProfile=reference_profile, returnProfile=profile, currency=currency,
        fundingReference=funding, dayCountConvention=daycount,
        referenceTypes=node_types, instrumentTypes=instrument_types,
        currencyReference=nodes.get(currency['reference_node_id']),
        creationReferenceType=creation_reference_type, creationInstrumentType=creation_instrument_type)


def materialize_swap(connection, tenant_id, actor_id, request: SwapProposalRequest) -> UUID:
    """Write the entire approved canonical contract in the caller's transaction."""
    terms = request.terms
    facts = validate_swap_references(connection, tenant_id, terms, lock=True)

    def type_id(fact, key, code):
        if fact is None or fact['status'] != 'ACTIVE':
            raise ProductBookingError(f'An active {code} catalogue is required.')
        return fact[key]

    node_id = connection.scalar(m.financial_reference_node.insert().values(
        reference_node_type_id=type_id(facts['creationReferenceType'], 'reference_node_type_id', 'INSTRUMENT'),
        canonical_name=request.canonical_name, is_tradable=True, status='ACTIVE').returning(m.financial_reference_node.c.reference_node_id))
    fields = dict(instrument_type_id=type_id(facts['creationInstrumentType'], 'instrument_type_id', 'SWAP'),
        asset_class='DERIVATIVE', base_currency_id=terms.notional_currency_id,
        effective_from=terms.effective_date, is_current=True, sequence_no=1)
    connection.execute(m.instrument.insert().values(instrument_node_id=node_id, **fields))
    version_id = connection.scalar(m.instrument_definition_version.insert().values(instrument_node_id=node_id, **fields,
        status='APPROVED', approved_by_user_account_id=actor_id, approved_at_utc=datetime.now(timezone.utc))
        .returning(m.instrument_definition_version.c.instrument_definition_version_id))
    connection.execute(m.reference_node_scope.insert().values(reference_node_id=node_id,
        scope_type='TENANT_PRIVATE', owner_tenant_id=tenant_id, status='ACTIVE'))
    connection.execute(m.swap_definition_version.insert().values(instrument_definition_version_id=version_id,
        schema_version=terms.schema_version, economics_payload=terms.model_dump(mode='json', by_alias=True)))
    connection.execute(m.instrument_dates.insert().values(instrument_node_id=node_id,
        effective_date=terms.effective_date, maturity_date=terms.maturity_date))
    connection.execute(m.swap_terms.insert().values(instrument_node_id=node_id, swap_type='TOTAL_RETURN'))
    connection.execute(m.swap_leg.insert().values(swap_instrument_node_id=node_id, leg_number=1, leg_role='PERFORMANCE',
        pay_receive=terms.performance_direction, reference_node_id=terms.performance_reference_id,
        return_profile_id=terms.return_profile_id, currency_id=terms.notional_currency_id))
    if terms.funding_reference_id:
        connection.execute(m.swap_leg.insert().values(swap_instrument_node_id=node_id, leg_number=2, leg_role='FUNDING',
            pay_receive='PAY' if terms.performance_direction == 'RECEIVE' else 'RECEIVE',
            reference_node_id=terms.funding_reference_id, currency_id=terms.notional_currency_id, spread=terms.funding_spread))
    # A nominal can vary at the existing decimal precision; no invented contract
    # size or schedule is inferred from the sourced reset-frequency labels.
    append_convention(connection, node_id, SwapConvention(kind='SWAP', effectiveFrom=terms.effective_date,
        priceCurrencyId=terms.quote_currency_id, quoteFactor=terms.quote_factor, sourceReference=terms.source_reference,
        quantityUnit='NOMINAL', priceBasis='SWAP_VALUE_PER_NOTIONAL', quantityMinimum=Decimal('0.000000000001'),
        quantityIncrement=Decimal('0.000000000001'), otcAllowed=True), actor_id)
    return node_id


def inspection_terms(connection, tenant_id, instrument_id, definition_version):
    """Project this approved version, omitting terms if a reference becomes private."""
    from .repository import RepositoryNotFound
    row = connection.execute(select(m.swap_definition_version.c.economics_payload)
        .join(m.instrument_definition_version, m.instrument_definition_version.c.instrument_definition_version_id ==
              m.swap_definition_version.c.instrument_definition_version_id)
        .where(m.instrument_definition_version.c.instrument_node_id == instrument_id,
            m.instrument_definition_version.c.sequence_no == definition_version,
            m.instrument_definition_version.c.status == 'APPROVED')).mappings().first()
    if row is None:
        return None
    terms = GenericSwapTerms.model_validate(row.economics_payload)
    require_visible(connection, tenant_id, instrument_id)
    try:
        require_visible(connection, tenant_id, terms.performance_reference_id)
        if terms.funding_reference_id:
            require_visible(connection, tenant_id, terms.funding_reference_id)
    except RepositoryNotFound:
        return None
    return terms
