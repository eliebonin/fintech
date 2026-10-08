"""Approval-time dependency validation for the older FX, bond and ETP paths."""
from datetime import date
from sqlalchemy import select, or_
from security_master_schema import models as m
from .booking_errors import RepositoryNotFound, InvalidWorkflowState


def _rows(connection, table, column, value):
    return connection.execute(select(table).where(column == value)
        .order_by(*table.primary_key.columns).with_for_update()).mappings().all()


def _active(connection, table, column, value, label):
    rows = _rows(connection, table, column, value)
    if len(rows) != 1 or rows[0].status != 'ACTIVE':
        raise RepositoryNotFound(f'{label} does not exist or is not active')
    return rows[0]


def _etp_reference(connection, tenant, reference_id):
    from .product_booking import require_visible
    _rows(connection, m.financial_reference_node, m.financial_reference_node.c.reference_node_id, reference_id)
    _rows(connection, m.reference_node_scope, m.reference_node_scope.c.reference_node_id, reference_id)
    node = require_visible(connection, tenant, reference_id)
    instrument = _rows(connection, m.instrument, m.instrument.c.instrument_node_id, reference_id)
    if instrument:
        definitions = _rows(connection, m.instrument_definition_version, m.instrument_definition_version.c.instrument_node_id, reference_id)
        current = [row for row in definitions if row.status == 'APPROVED' and row.is_current]
        today = date.today()
        if not instrument[0].is_current or len(current) != 1 or current[0].effective_from > today or (current[0].effective_to and current[0].effective_to < today):
            raise InvalidWorkflowState('ETP reference requires a current effective approved instrument definition')
        for key in ('instrument_type_id', 'base_currency_id', 'issuer_organisation_id', 'asset_class', 'effective_to', 'sequence_no'):
            if instrument[0][key] != current[0][key]:
                raise InvalidWorkflowState('ETP reference differs from its approved instrument definition')
        if instrument[0].effective_from and instrument[0].effective_from != current[0].effective_from:
            raise InvalidWorkflowState('ETP reference differs from its approved instrument definition')
    indexes = _rows(connection, m.index_terms, m.index_terms.c.index_node_id, reference_id)
    if indexes and indexes[0].status != 'ACTIVE':
        raise RepositoryNotFound('ETP reference index is not active')
    return node.reference_node_type_id, instrument[0].instrument_type_id if instrument else None


def _types(connection, table, id_column, target_code, reference_id, label):
    predicate = table.c.type_code == target_code
    if reference_id:
        predicate = or_(predicate, id_column == reference_id)
    rows = connection.execute(select(table).where(predicate).order_by(id_column).with_for_update()).mappings().all()
    if not any(row.type_code == target_code for row in rows) or any(row.status != 'ACTIVE' for row in rows):
        raise RepositoryNotFound(f'Active {label} configuration is required')
    if reference_id and not any(row[id_column.name] == reference_id for row in rows):
        raise RepositoryNotFound(f'Active reference {label} is required')


def validate_approval_references(connection, tenant, request, kind):
    currency_ids = {request.base_currency_id}
    if kind == 'FX_FORWARD':
        currency_ids.update((request.quote_currency_id, request.fixing_currency_id))
        if request.base_currency_id == request.quote_currency_id or request.maturity_date < request.effective_from:
            raise InvalidWorkflowState('FX currencies and effective/maturity dates are inconsistent')
        if any(value and value < request.maturity_date for value in
               (request.settlement_date, request.cash_settlement_date, request.final_settlement_date)):
            raise InvalidWorkflowState('FX settlement dates cannot precede maturity')
    for currency_id in sorted(currency_ids - {None}, key=str):
        _active(connection, m.currency, m.currency.c.currency_id, currency_id, 'Selected currency')
    reference_type_id = instrument_type_id = None
    if kind == 'ETP' and request.reference_node_id:
        reference_type_id, instrument_type_id = _etp_reference(connection, tenant, request.reference_node_id)
    # Complete reference-type phase before product-type phase, including all
    # reference and target IDs in UUID order. Never reacquire a lower phase.
    _types(connection, m.reference_node_type, m.reference_node_type.c.reference_node_type_id,
           'INSTRUMENT', reference_type_id, 'reference type')
    _types(connection, m.instrument_type, m.instrument_type.c.instrument_type_id,
           request.etp_kind if kind == 'ETP' else kind, instrument_type_id, 'instrument type')
    if kind != 'FX_FORWARD' and request.issuer_organisation_id:
        _active(connection, m.organisation, m.organisation.c.organisation_id, request.issuer_organisation_id, 'Issuer organisation')
    if kind == 'BOND' and request.day_count_convention:
        _active(connection, m.day_count_convention, m.day_count_convention.c.code, request.day_count_convention, 'Day-count convention')
