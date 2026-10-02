"""Checked, versioned generic swap contracts consumed by the shared trade writer."""
from datetime import date
from sqlalchemy import select
from security_master_schema import models as m
from .product_booking_contracts import SwapDetailsView
from .swap_creation_contracts import GenericSwapTerms


def load_generic_swap_context(connection, tenant_id, instrument_id, as_of, *, lock=False) -> tuple[SwapDetailsView, date]:
    from .product_booking import CONVENTION, require_visible
    from .swap_creation import validate_swap_references

    def rows(table, predicate):
        statement = select(table).where(predicate).order_by(*table.primary_key.columns)
        return [dict(row) for row in connection.execute(statement.with_for_update() if lock else statement).mappings()]

    rows(m.financial_reference_node, m.financial_reference_node.c.reference_node_id == instrument_id)
    rows(m.reference_node_scope, m.reference_node_scope.c.reference_node_id == instrument_id)
    require_visible(connection, tenant_id, instrument_id)
    definitions = rows(m.instrument_definition_version,
        (m.instrument_definition_version.c.instrument_node_id == instrument_id)
        & m.instrument_definition_version.c.is_current
        & (m.instrument_definition_version.c.status == 'APPROVED'))
    if len(definitions) != 1:
        raise ValueError('Exactly one current approved generic swap definition is required.')
    definition = definitions[0]
    generic = rows(m.swap_definition_version,
        m.swap_definition_version.c.instrument_definition_version_id == definition['instrument_definition_version_id'])
    if len(generic) != 1:
        raise ValueError('Approved generic swap economics are required.')
    terms = GenericSwapTerms.model_validate(generic[0]['economics_payload'])
    if generic[0]['schema_version'] != terms.schema_version:
        raise ValueError('Generic swap schema version differs from approved economics.')
    instruments = rows(m.instrument, m.instrument.c.instrument_node_id == instrument_id)
    if len(instruments) != 1 or not instruments[0]['is_current'] or any(
            definition[key] != instruments[0][key] for key in ('base_currency_id', 'instrument_type_id',
                'issuer_organisation_id', 'effective_from', 'effective_to', 'sequence_no', 'asset_class')):
        raise ValueError('Generic swap differs from its current approved definition.')
    if (definition['base_currency_id'] != terms.notional_currency_id
            or definition['effective_from'] != terms.effective_date
            or (definition['effective_to'] and as_of > definition['effective_to'])
            or not terms.effective_date <= as_of < terms.maturity_date):
        raise ValueError('Execution must be within the approved swap effective and maturity dates.')

    # Reuse approval's deterministic reference/catalogue lock phases. These are
    # the same complete checked facts used for both review and immutable evidence.
    facts = validate_swap_references(connection, tenant_id, terms, lock=lock, as_of=as_of)
    node = dict(require_visible(connection, tenant_id, instrument_id))
    if (not node['is_tradable'] or facts['creationInstrumentType']['status'] != 'ACTIVE'
            or facts['creationReferenceType']['status'] != 'ACTIVE'
            or facts['creationInstrumentType']['instrument_type_id'] != definition['instrument_type_id']
            or facts['creationReferenceType']['reference_node_type_id'] != node['reference_node_type_id']):
        raise ValueError('An active tradable canonical swap is required.')
    dates = rows(m.instrument_dates, m.instrument_dates.c.instrument_node_id == instrument_id)
    swap_terms = rows(m.swap_terms, m.swap_terms.c.instrument_node_id == instrument_id)
    legs = rows(m.swap_leg, m.swap_leg.c.swap_instrument_node_id == instrument_id)
    expected_roles = {'PERFORMANCE', 'FUNDING'} if terms.funding_reference_id else {'PERFORMANCE'}
    if (len(dates) != 1 or dates[0]['effective_date'] != terms.effective_date
            or dates[0]['maturity_date'] != terms.maturity_date
            or len(swap_terms) != 1 or swap_terms[0]['swap_type'] != 'TOTAL_RETURN'
            or len(legs) != len(expected_roles) or {leg['leg_role'] for leg in legs} != expected_roles
            or any(leg['schedule_id'] is not None for leg in legs)):
        raise ValueError('Canonical swap dates and legs differ from approved generic terms.')
    performance = next(leg for leg in legs if leg['leg_role'] == 'PERFORMANCE')
    if (performance['reference_node_id'] != terms.performance_reference_id
            or performance['pay_receive'] != terms.performance_direction
            or performance['return_profile_id'] != terms.return_profile_id
            or performance['currency_id'] != terms.notional_currency_id or performance['spread'] is not None):
        raise ValueError('Performance leg differs from approved generic terms.')
    funding = next((leg for leg in legs if leg['leg_role'] == 'FUNDING'), None)
    funding_direction = 'PAY' if terms.performance_direction == 'RECEIVE' else 'RECEIVE'
    if funding and (funding['reference_node_id'] != terms.funding_reference_id
            or funding['pay_receive'] != funding_direction or funding['currency_id'] != terms.notional_currency_id
            or funding['spread'] != terms.funding_spread or funding['return_profile_id'] is not None):
        raise ValueError('Funding leg differs from approved generic terms.')
    conventions = rows(m.instrument_booking_convention,
        (m.instrument_booking_convention.c.instrument_node_id == instrument_id)
        & (m.instrument_booking_convention.c.effective_from <= as_of))
    if not conventions:
        raise ValueError('Approved generic swap booking convention is required.')
    stored = max(conventions, key=lambda row: (row['effective_from'], row['version_no']))
    convention = CONVENTION.validate_json(stored['convention_payload'])
    if (convention.kind != 'SWAP' or convention.price_currency_id != terms.quote_currency_id
            or convention.quote_factor != terms.quote_factor or not convention.otc_allowed):
        raise ValueError('Booking quote convention differs from approved generic terms.')
    facts.update(genericDefinition=generic[0], approvedDefinition=definition, instrument=instruments[0],
        swapReference=node, dates=dates, swapTerms=swap_terms, legs=legs, bookingConvention=stored)
    # Scopes already locked by approval validation; retain them so a still-visible
    # scope edit also changes the review fingerprint, without acquiring late locks.
    reference_ids = {instrument_id, terms.performance_reference_id}
    if terms.funding_reference_id:
        reference_ids.add(terms.funding_reference_id)
    if facts['currency']['reference_node_id']:
        reference_ids.add(facts['currency']['reference_node_id'])
    facts['referenceScopes'] = [dict(row) for row in connection.execute(select(m.reference_node_scope)
        .where(m.reference_node_scope.c.reference_node_id.in_(reference_ids))
        .order_by(*m.reference_node_scope.primary_key.columns)).mappings()]
    reference = facts['performanceReference']; rate = facts['fundingReference']
    return SwapDetailsView(performanceReferenceId=terms.performance_reference_id,
        performanceReferenceName=reference['canonical_name'], performanceDirection=terms.performance_direction,
        returnProfileCode=facts['returnProfile']['profile_code'], fundingReferenceId=terms.funding_reference_id,
        fundingReferenceName=rate['canonical_name'] if rate else None,
        fundingDirection=funding_direction if rate else None, fundingSpread=terms.funding_spread,
        effectiveDate=terms.effective_date, genericTerms=terms, sourceFacts=facts), terms.maturity_date
